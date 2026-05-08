#data_extract/visual/visual_pdf_evidence_extractor.py
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from google import genai as google_genai
    from google.genai import types as google_types

    HAS_GOOGLE_API = True
except ImportError:
    google_genai = None
    google_types = None
    HAS_GOOGLE_API = False

from helpers import (
    CombinedRecord,
    ExtractionPromptBuilder,
    JSONParser,
    RecordNormalizer,
    b64_dir_for_chunk,
    page_as_int,
    read_chunks,
    source_file_name,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=False)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3-flash-preview")

INPUT_JSON = ROOT_DIR / "data_extract" / "extract_input.json"
IMAGES_DIR = SCRIPT_DIR / "images"
OUTPUT_DIR = SCRIPT_DIR / "extracted_visual"

CONTEXT_RADIUS = 2
TEMPERATURE = 0.0
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 180


class VisualPDFEvidenceExtractor:
    page_file_pattern = re.compile(
        r"^(?:page[_\-\s]?)?0*(\d+)\.(?:b64|txt)$",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.model = OPENROUTER_MODEL
        self.output_dir = OUTPUT_DIR.resolve()
        self.context_radius = CONTEXT_RADIUS
        self.temperature = TEMPERATURE
        self.max_tokens = MAX_TOKENS
        self.timeout_seconds = TIMEOUT_SECONDS

        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        # Backup only. OpenRouter is always primary.
        self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.google_model = self._normalize_google_model_name(GOOGLE_MODEL)

    @staticmethod
    def _normalize_google_model_name(model: str) -> str:
        model = model.strip()
        return model.split("/", 1)[1] if model.startswith("google/") else model

    @staticmethod
    def _read_b64_as_data_url(path: Path) -> str:
        raw_text = path.read_text(encoding="utf-8").strip()

        if not raw_text:
            raise ValueError(f"Empty page file: {path}")

        if raw_text.startswith("data:image/"):
            header, b64_text = raw_text.split(",", 1)
            return f"{header},{''.join(b64_text.split())}"

        return f"data:image/jpeg;base64,{''.join(raw_text.split())}"

    @classmethod
    def list_page_b64_files(cls, b64_dir: Path) -> dict[int, Path]:
        page_files = sorted(
            {
                path
                for pattern in ("*.b64", "*.txt")
                for path in b64_dir.glob(pattern)
            },
            key=lambda path: path.name.lower(),
        )

        matched: dict[int, Path] = {}
        unmatched: list[Path] = []

        for page_file in page_files:
            match = cls.page_file_pattern.match(page_file.name)

            if match:
                matched.setdefault(int(match.group(1)), page_file)
            else:
                unmatched.append(page_file)

        if matched:
            return dict(sorted(matched.items()))

        return {
            index + 1: path
            for index, path in enumerate(sorted(unmatched, key=lambda p: p.name.lower()))
        }

    @classmethod
    def find_page_b64_file(cls, b64_dir: Path, page_number: int) -> Path | None:
        names: list[str] = []

        for ext in ("b64", "txt"):
            names.extend(
                [
                    f"page_{page_number:03d}.{ext}",
                    f"page_{page_number}.{ext}",
                    f"page-{page_number:03d}.{ext}",
                    f"page-{page_number}.{ext}",
                    f"page{page_number:03d}.{ext}",
                    f"page{page_number}.{ext}",
                    f"{page_number:03d}.{ext}",
                    f"{page_number}.{ext}",
                ]
            )

        for name in names:
            candidate = b64_dir / name

            if candidate.exists():
                return candidate

        return cls.list_page_b64_files(b64_dir).get(page_number)

    def build_messages(
        self,
        pdf_file: str,
        b64_dir: Path,
        page_number: int,
    ) -> tuple[list[dict[str, Any]], list[int], int, int]:
        start_page = max(1, page_number - self.context_radius)
        end_page = page_number + self.context_radius

        included_pages: list[int] = []
        page_payloads: list[tuple[int, str]] = []

        for page in range(start_page, end_page + 1):
            page_file = self.find_page_b64_file(b64_dir, page)

            if page_file is None:
                if page == page_number:
                    raise FileNotFoundError(
                        f"Center page {page_number} not found in {b64_dir}"
                    )
                continue

            included_pages.append(page)
            page_payloads.append((page, self._read_b64_as_data_url(page_file)))

        prompt = ExtractionPromptBuilder.build(
            pdf_file=pdf_file,
            page_selection=page_number,
            requested_start_page=start_page,
            requested_end_page=end_page,
            included_pages=included_pages,
        )

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        for page, data_url in page_payloads:
            label = f"PAGE {page} IN COMBINED RANGE {start_page}-{end_page}"

            if page == page_number:
                label += " (CENTER PAGE)"

            content.append({"type": "text", "text": label})
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        return [{"role": "user", "content": content}], included_pages, start_page, end_page

    def call_openrouter(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.openrouter_api_key:
            raise EnvironmentError(f"Missing OPENROUTER_API_KEY in {ENV_PATH}")

        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "X-Title": "Sepsis Visual PDF Extraction",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            timeout=self.timeout_seconds,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"OpenRouter error {response.status_code}:\n{response.text}")

        return response.json()

    @staticmethod
    def get_message_content(response_json: dict[str, Any]) -> str:
        content = response_json["choices"][0]["message"]["content"]

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and "text" in item
            ).strip()

        return str(content)

    @staticmethod
    def _messages_to_google_contents(messages: list[dict[str, Any]]) -> list[Any]:
        if google_types is None:
            raise ImportError("google-genai package not available")

        parts: list[Any] = []

        for message in messages:
            if message.get("role") != "user":
                continue

            for item in message.get("content", []):
                if not isinstance(item, dict):
                    continue

                if item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        parts.append(text)
                    continue

                if item.get("type") != "image_url":
                    continue

                data_url = item.get("image_url", {}).get("url", "")

                if not data_url.startswith("data:image/"):
                    raise ValueError("Google backup expected image data URL")

                header, b64_data = data_url.split(",", 1)

                mime_match = re.match(
                    r"^data:(image/[^;]+);base64$",
                    header,
                    re.IGNORECASE,
                )
                mime_type = mime_match.group(1) if mime_match else "image/jpeg"

                try:
                    image_bytes = base64.b64decode(b64_data, validate=True)
                except binascii.Error as exc:
                    raise ValueError("Invalid base64 image data") from exc

                parts.append(
                    google_types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    )
                )

        return parts

    @staticmethod
    def _extract_google_text(response: Any) -> str:
        try:
            if response.text:
                return response.text
        except Exception:
            pass

        chunks: list[str] = []

        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)

            for part in getattr(content, "parts", []) or []:
                text = getattr(part, "text", None)

                if text:
                    chunks.append(text)

        return "\n".join(chunks).strip()

    def call_google_backup(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if not HAS_GOOGLE_API:
            raise ImportError("google-genai package not installed")

        if not self.google_api_key:
            raise EnvironmentError("Google backup key not configured")

        client = google_genai.Client(api_key=self.google_api_key)

        response = client.models.generate_content(
            model=self.google_model,
            contents=self._messages_to_google_contents(messages),
            config=google_types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json",
            ),
        )

        text = self._extract_google_text(response)

        if not text.strip():
            raise RuntimeError("Google backup returned no text")

        try:
            raw_response = response.model_dump(mode="json", exclude_none=True)
        except Exception:
            raw_response = {"text": text}

        return {
            "provider": "google_backup",
            "model": self.google_model,
            "raw_response": raw_response,
            "choices": [{"message": {"content": text}}],
        }

    def call_model(self, messages: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        try:
            return "openrouter", self.call_openrouter(messages)

        except EnvironmentError:
            raise

        except Exception as openrouter_error:
            if not HAS_GOOGLE_API or not self.google_api_key:
                raise RuntimeError(
                    "OpenRouter failed and Google backup is not configured.\n"
                    f"OpenRouter error: {openrouter_error}"
                ) from openrouter_error

            try:
                return "google_backup", self.call_google_backup(messages)

            except Exception as google_error:
                raise RuntimeError(
                    "OpenRouter failed and Google backup also failed.\n"
                    f"OpenRouter error: {openrouter_error}\n"
                    f"Google backup error: {google_error}"
                ) from openrouter_error

    def extract_pdf(
        self,
        source_file: str,
        page_number: int,
        b64_dir: Path,
    ) -> CombinedRecord:
        pdf_output_dir = self.output_dir / Path(source_file).stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)

        messages, included_pages, start_page, end_page = self.build_messages(
            pdf_file=source_file,
            b64_dir=b64_dir,
            page_number=page_number,
        )

        provider, response_json = self.call_model(messages)
        model_text = self.get_message_content(response_json)

        try:
            parsed_json = JSONParser.parse(model_text)

        except Exception:
            if provider == "openrouter" and HAS_GOOGLE_API and self.google_api_key:
                provider = "google_backup"
                response_json = self.call_google_backup(messages)
                model_text = self.get_message_content(response_json)
                parsed_json = JSONParser.parse(model_text)
            else:
                raise

        file_prefix = f"pages_{start_page:03d}_to_{end_page:03d}"

        (pdf_output_dir / f"{file_prefix}_raw_{provider}_response.json").write_text(
            json.dumps(response_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        (pdf_output_dir / f"{file_prefix}_raw_model_text.txt").write_text(
            model_text,
            encoding="utf-8",
        )

        record = RecordNormalizer.normalize(
            parsed_json=parsed_json,
            pdf_file=source_file,
            page_selection=page_number,
            requested_start_page=start_page,
            requested_end_page=end_page,
            included_pages=included_pages,
        )

        (pdf_output_dir / f"{file_prefix}_visual_extract.json").write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return record

    def extract_from_input_json(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        chunks = read_chunks(INPUT_JSON)

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        cache: dict[tuple[str, int], CombinedRecord] = {}

        for input_index, chunk in enumerate(chunks):
            try:
                source_file = source_file_name(chunk)
                page_number = page_as_int(chunk)
                cache_key = (source_file, page_number)

                if cache_key not in cache:
                    b64_dir = b64_dir_for_chunk(chunk, IMAGES_DIR)

                    cache[cache_key] = self.extract_pdf(
                        source_file=source_file,
                        page_number=page_number,
                        b64_dir=b64_dir,
                    )

                results.append(
                    {
                        "input_index": input_index,
                        "input_chunk": chunk,
                        "record": cache[cache_key].model_dump(),
                    }
                )

            except Exception as exc:
                errors.append(
                    {
                        "input_index": input_index,
                        "input_chunk": chunk,
                        "error": str(exc),
                    }
                )

        output_file = self.output_dir / "extract_input_visual_results.json"

        payload = {
            "input_json": str(INPUT_JSON),
            "images_dir": str(IMAGES_DIR),
            "output_file": str(output_file),
            "total_chunks": len(chunks),
            "successful_chunks": len(results),
            "failed_chunks": len(errors),
            "deduplicated_extractions": len(cache),
            "results": results,
            "errors": errors,
        }

        output_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return payload


def main() -> None:
    try:
        payload = VisualPDFEvidenceExtractor().extract_from_input_json()

        summary: dict[str, Any] = {
            "output_file": payload["output_file"],
            "total_chunks": payload["total_chunks"],
            "successful_chunks": payload["successful_chunks"],
            "failed_chunks": payload["failed_chunks"],
            "deduplicated_extractions": payload["deduplicated_extractions"],
        }

        if payload["errors"]:
            summary["errors"] = payload["errors"]

        print(json.dumps(summary, indent=2, ensure_ascii=False))

        if payload["errors"]:
            sys.exit(1)

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()