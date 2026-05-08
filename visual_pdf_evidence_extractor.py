from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Literal, Sequence
import argparse
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent

# Original expected layout:
#   root/data_extract/visual/<this_script>.py
#   root/.env
# This fallback keeps the module importable if it is moved elsewhere later.
try:
    ROOT_DIR = SCRIPT_DIR.parents[1]
except IndexError:
    ROOT_DIR = SCRIPT_DIR.parent

ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "extracted_visual"
DEFAULT_CONTEXT_RADIUS = 2
DEFAULT_PAGE_SELECTION: Literal["all"] = "all"

REQUIRED_FIELDS = [
    "study",
    "population",
    "sample_size",
    "predictor",
    "outcome",
    "timing",
    "method",
    "effect_size",
    "performance",
    "notes",
    "source_info",
]

PageSelection = int | str | Literal["all"]
CombinedRecord = dict[str, Any]


class VisualPDFEvidenceExtractor:
    """
    Reusable OpenRouter visual PDF evidence extractor.

    Default behavior:
        - page_number="all"
        - all detected page_*.b64 images for each PDF are sent to the model
        - one combined JSON dictionary is produced per PDF

    Backward-compatible behavior:
        - pass page_number=<int> to use the old n-2 through n+2 center-page window
        - context_radius controls the window size in center-page mode

    Typical pipeline usage:
        extractor = VisualPDFEvidenceExtractor()
        records = extractor.extract_pdfs([
            Path("images/pdf1/b64"),
            Path("images/pdf2/b64"),
        ])
    """

    page_file_pattern = re.compile(r"^page[_-]?(\d+)\.b64$", flags=re.IGNORECASE)

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        output_dir: Path | str = DEFAULT_OUTPUT_DIR,
        context_radius: int = DEFAULT_CONTEXT_RADIUS,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout_seconds: int = 180,
        save_raw_response: bool = True,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.output_dir = self.resolve_path_from_cwd_or_script_dir(Path(output_dir))
        self.context_radius = context_radius
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.save_raw_response = save_raw_response
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    @staticmethod
    def resolve_path_from_cwd_or_script_dir(path: Path) -> Path:
        """
        Resolves paths robustly.

        If a relative path exists from the current working directory, use that.
        Otherwise, resolve it relative to this script's folder.
        """

        path = Path(path)

        if path.is_absolute():
            return path.resolve()

        cwd_candidate = (Path.cwd() / path).resolve()

        if cwd_candidate.exists():
            return cwd_candidate

        return (SCRIPT_DIR / path).resolve()

    @staticmethod
    def read_b64_image_as_data_url(b64_path: Path) -> str:
        """
        Reads a .b64 file and returns a valid image data URL.

        Supports either:
        - raw base64 text
        - already-prefixed data URLs like data:image/jpeg;base64,...

        The earlier screenshot pipeline stores JPG screenshots, so raw base64
        is treated as image/jpeg.
        """

        if not b64_path.exists():
            raise FileNotFoundError(f"Missing b64 image file: {b64_path}")

        b64_text = b64_path.read_text(encoding="utf-8").strip()

        if not b64_text:
            raise ValueError(f"Empty b64 image file: {b64_path}")

        if b64_text.startswith("data:image/"):
            return b64_text

        return f"data:image/jpeg;base64,{b64_text}"

    @classmethod
    def list_page_b64_files(cls, b64_dir: Path) -> dict[int, Path]:
        """
        Returns all detected page-numbered .b64 files in ascending page order.

        Expected names:
            page_001.b64
            page_002.b64

        Also supports:
            page_1.b64
            page-001.b64
            page-1.b64
            page001.b64

        If no page-numbered files are found but .b64 files exist, files are
        assigned page numbers by lexical order as a last-resort fallback.
        """

        b64_dir = Path(b64_dir)
        page_files: dict[int, Path] = {}
        unmatched_b64_files: list[Path] = []

        for b64_file in sorted(b64_dir.glob("*.b64"), key=lambda path: path.name.lower()):
            match = cls.page_file_pattern.match(b64_file.name)

            if not match:
                unmatched_b64_files.append(b64_file)
                continue

            page_number = int(match.group(1))

            # Preserve the first file found for a page number if duplicate naming exists.
            page_files.setdefault(page_number, b64_file)

        if page_files:
            return dict(sorted(page_files.items(), key=lambda item: item[0]))

        # Fallback for directories that contain page images as .b64 files but do not
        # use the page_001.b64 naming convention.
        return {
            index + 1: b64_file
            for index, b64_file in enumerate(sorted(unmatched_b64_files, key=lambda path: path.name.lower()))
        }

    @classmethod
    def find_page_b64_file(cls, b64_dir: Path, page_number: int) -> Path | None:
        """
        Finds a page file using the naming convention from the PDF screenshot script.

        Expected:
            page_001.b64
            page_002.b64

        Also supports:
            page_1.b64
            page-001.b64
            page-1.b64
            page001.b64
        """

        candidates = [
            b64_dir / f"page_{page_number:03d}.b64",
            b64_dir / f"page_{page_number}.b64",
            b64_dir / f"page-{page_number:03d}.b64",
            b64_dir / f"page-{page_number}.b64",
            b64_dir / f"page{page_number:03d}.b64",
            b64_dir / f"page{page_number}.b64",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return cls.list_page_b64_files(b64_dir).get(page_number)

    @staticmethod
    def infer_pdf_file_name(b64_dir: Path, explicit_pdf_file: str | None = None) -> str:
        """
        Infers the original PDF file name from a folder like:

            images/pdf1/b64

        Result:
            pdf1.pdf

        You can override this with pdf_file.
        """

        if explicit_pdf_file:
            return explicit_pdf_file

        b64_dir = b64_dir.resolve()

        if b64_dir.name == "b64":
            pdf_stem = b64_dir.parent.name
        else:
            pdf_stem = b64_dir.name

        if pdf_stem.lower().endswith(".pdf"):
            return pdf_stem

        return f"{pdf_stem}.pdf"

    @staticmethod
    def get_requested_page_range(center_page_number: int, context_radius: int) -> tuple[int, int]:
        """
        Returns the requested extraction window around a center page.

        With center_page_number=n and context_radius=2, this returns n-2 through n+2,
        bounded below by page 1.
        """

        if center_page_number < 1:
            raise ValueError("page_number must be 1-indexed and >= 1")

        if context_radius < 0:
            raise ValueError("context_radius must be >= 0")

        start_page = max(1, center_page_number - context_radius)
        end_page = center_page_number + context_radius

        return start_page, end_page

    @staticmethod
    def normalize_page_selection(page_number: PageSelection = DEFAULT_PAGE_SELECTION) -> int | Literal["all"]:
        """
        Normalizes a page selector.

        Valid inputs:
            "all"     -> all detected pages
            7         -> old center-page mode, page 7 with context window
            "7"       -> old center-page mode, page 7 with context window
        """

        if isinstance(page_number, int):
            if page_number < 1:
                raise ValueError("page_number must be 'all' or a 1-indexed integer >= 1")
            return page_number

        if isinstance(page_number, str):
            normalized = page_number.strip().lower()

            if normalized == "all":
                return "all"

            if normalized.isdigit():
                page_number_int = int(normalized)
                if page_number_int < 1:
                    raise ValueError("page_number must be 'all' or a 1-indexed integer >= 1")
                return page_number_int

        raise ValueError("page_number must be 'all' or a 1-indexed integer")

    @staticmethod
    def build_extraction_prompt(
        pdf_file: str,
        page_selection: int | Literal["all"],
        requested_start_page: int,
        requested_end_page: int,
        included_pages: list[int],
    ) -> str:
        """
        Prompt for visually grounded biomedical evidence extraction.

        In all-pages mode, every available page image is treated as one combined
        evidence chunk for the PDF.

        In center-page mode, the n-2 through n+2 range is treated as one combined
        evidence chunk, preserving the original logic.
        """

        included_pages_text = ", ".join(str(page) for page in included_pages) or "None"
        requested_range_text = f"{requested_start_page} through {requested_end_page}"
        pdf_file_json = json.dumps(pdf_file, ensure_ascii=False)
        included_pages_json = json.dumps(included_pages)

        if page_selection == "all":
            center_page_json = "null"
            center_page_text = "Not applicable; all detected pages are included."
            selection_text = "ALL pages from the supplied PDF image b64 directory"
            chunk_id = "all_pages_combined"
            range_rule = (
                "The attached images represent all detected pages for this PDF. "
                "Treat the complete included page set as one combined evidence chunk."
            )
            split_rule = (
                "Do not split the result by page. Do not return one object per page. "
                "Return one combined object for the entire included PDF page set."
            )
        else:
            center_page_json = str(page_selection)
            center_page_text = str(page_selection)
            selection_text = f"center-page window around page {page_selection}"
            chunk_id = f"pages_{requested_start_page:03d}_to_{requested_end_page:03d}_combined"
            range_rule = (
                f"The intended page window is n-2 through n+2 around center page {page_selection}. "
                "Pages that do not exist or are unavailable are omitted."
            )
            split_rule = (
                "Do not split the result by page. Do not return one object per page. "
                "Return one combined object for the entire included page range."
            )

        return f"""
You are extracting structured biomedical evidence from screenshots of a sepsis-related academic paper.

The attached images are PDF page screenshots.

Target PDF file:
{pdf_file}

Page selection mode:
{selection_text}

Center page used to form the range:
{center_page_text}

Requested extraction page range:
{requested_range_text}

Actually included pages:
{included_pages_text}

Important extraction rule:
{range_rule}
Extract and summarize the relevant biomedical evidence using context from all included pages together.

{split_rule}

You must inspect both ordinary text and visual content, including tables, plots, charts, diagrams, forest plots, ROC curves, Kaplan-Meier plots, captions, labels, legends, and footnotes.

Return ONLY valid JSON.
Do not include markdown.
Do not include commentary.
Do not include explanations outside the JSON.

Return a SINGLE JSON object with exactly this schema:

{{
  "study": "string",
  "population": "string",
  "sample_size": "string",
  "predictor": "string",
  "outcome": "string",
  "timing": "string",
  "method": "string",
  "effect_size": "string",
  "performance": "string",
  "notes": "string",
  "source_info": {{
    "file": {pdf_file_json},
    "center_page": {center_page_json},
    "page_range": {{
      "start": {requested_start_page},
      "end": {requested_end_page}
    }},
    "included_pages": {included_pages_json},
    "chunk": "{chunk_id}"
  }}
}}

Field rules:

1. "study"
   - Use the study citation, author/year, trial name, cohort name, paper section identifier, or a concise combined description if multiple related study identifiers appear.
   - Example: "Gai et al. 2021".
   - If unavailable, use "Not reported".

2. "population"
   - Extract patient group, disease condition, setting, and relevant inclusion context across the full included page set.
   - Example: "Patients with sepsis admitted to ICU".
   - If unavailable, use "Not reported".

3. "sample_size"
   - Extract N, group sizes, cohort size, number of patients, or number of observations.
   - Preserve exact wording when possible.
   - If multiple sample sizes are relevant, include them together in one concise string.
   - Example: "N=72".
   - If unavailable, use "Not reported".

4. "predictor"
   - Extract the predictor, biomarker, clinical score, model feature, exposure, intervention, risk factor, or diagnostic variable.
   - If multiple predictors are relevant, include them together in one concise string.
   - Examples: "APACHE II score", "serum lactate", "SOFA score", "machine learning model".
   - If unavailable, use "Not reported".

5. "outcome"
   - Extract the endpoint, label, target, or clinical outcome.
   - If multiple outcomes are relevant, include them together in one concise string.
   - Examples: "Mortality", "Septic shock", "ICU length of stay", "non-survivor vs survivor".
   - If unavailable, use "Not reported".

6. "timing"
   - Extract when the predictor or outcome was measured.
   - If multiple timings are relevant, include them together in one concise string.
   - Examples: "At ICU admission", "Within 24 hours", "Day 1", "28-day mortality".
   - If unavailable, use "Not reported".

7. "method"
   - Extract study design, statistical method, model type, comparison method, or analysis method.
   - If multiple methods are relevant, include them together in one concise string.
   - Examples: "Case-control comparison", "ROC analysis", "Multivariable logistic regression".
   - If unavailable, use "Not reported".

8. "effect_size"
   - Extract OR, HR, RR, beta coefficient, mean difference, median difference, confidence interval, p-value, or other effect estimate.
   - If multiple effect estimates are relevant, include them together in one concise string.
   - If not shown, use "Not reported".

9. "performance"
   - Extract AUC, AUROC, sensitivity, specificity, accuracy, PPV, NPV, calibration, C-index, F1, precision, recall, or other model/diagnostic performance.
   - If multiple performance values are relevant, include them together in one concise string.
   - If not shown, use "Not reported".

10. "notes"
   - Add concise context needed to interpret the combined extraction.
   - Mention which pages contributed evidence when visible.
   - Mention whether evidence came from text, table, figure, graph, caption, legend, or footnote.
   - If estimating from a visual graph, say "Approximate from figure".
   - Do not invent values.

11. "source_info"
   - "file" must be {pdf_file_json}.
   - "center_page" must be {center_page_json}.
   - "page_range.start" must be {requested_start_page}.
   - "page_range.end" must be {requested_end_page}.
   - "included_pages" must be {included_pages_json}.
   - "chunk" must be "{chunk_id}".

If the included page set contains no extractable relevant evidence, return the same single JSON object but set all non-source fields to "Not reported" and explain briefly in "notes" that no extractable relevant evidence was visible.

Do not guess.
Use "Not reported" for missing fields.
Preserve exact numeric values, units, confidence intervals, p-values, and labels when visible.
""".strip()

    def build_messages(
        self,
        pdf_file: str,
        b64_dir: Path,
        page_number: PageSelection = DEFAULT_PAGE_SELECTION,
        context_radius: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[int], int, int, int | Literal["all"]]:
        """
        Builds OpenRouter multimodal messages with text first, then page images.

        Default:
            page_number="all" -> sends every detected page image in b64_dir.

        Backward-compatible mode:
            page_number=<int> -> sends one range, page_number-context_radius
            through page_number+context_radius. Missing context pages are skipped,
            but the center page must exist.
        """

        b64_dir = Path(b64_dir)
        page_selection = self.normalize_page_selection(page_number)
        effective_context_radius = self.context_radius if context_radius is None else context_radius

        included_pages: list[int] = []
        page_payloads: list[tuple[int, str]] = []

        if page_selection == "all":
            page_file_map = self.list_page_b64_files(b64_dir)

            if not page_file_map:
                raise FileNotFoundError(f"Could not find any .b64 page files in {b64_dir}")

            requested_start_page = min(page_file_map)
            requested_end_page = max(page_file_map)

            for page_num, b64_file in page_file_map.items():
                data_url = self.read_b64_image_as_data_url(b64_file)
                included_pages.append(page_num)
                page_payloads.append((page_num, data_url))
        else:
            requested_start_page, requested_end_page = self.get_requested_page_range(
                center_page_number=page_selection,
                context_radius=effective_context_radius,
            )

            page_numbers_to_try = list(range(requested_start_page, requested_end_page + 1))

            for page_num in page_numbers_to_try:
                b64_file = self.find_page_b64_file(b64_dir, page_num)

                if b64_file is None:
                    if page_num == page_selection:
                        raise FileNotFoundError(
                            f"Could not find center page {page_selection} in {b64_dir}"
                        )
                    continue

                data_url = self.read_b64_image_as_data_url(b64_file)
                included_pages.append(page_num)
                page_payloads.append((page_num, data_url))

        prompt = self.build_extraction_prompt(
            pdf_file=pdf_file,
            page_selection=page_selection,
            requested_start_page=requested_start_page,
            requested_end_page=requested_end_page,
            included_pages=included_pages,
        )

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": prompt,
            }
        ]

        for page_num, data_url in page_payloads:
            if page_selection == "all":
                label = f"PAGE {page_num} IN FULL PDF"
            else:
                label = f"PAGE {page_num} IN COMBINED RANGE {requested_start_page}-{requested_end_page}"

                if page_num == page_selection:
                    label += " (CENTER PAGE)"

            content.append(
                {
                    "type": "text",
                    "text": label,
                }
            )

            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url,
                    },
                }
            )

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]

        return messages, included_pages, requested_start_page, requested_end_page, page_selection

    def call_openrouter(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Sends the multimodal request to OpenRouter.
        """

        effective_api_key = api_key or self.api_key

        if not effective_api_key:
            raise EnvironmentError(
                f"Missing OPENROUTER_API_KEY.\n"
                f"Expected to find it in: {ENV_PATH}\n\n"
                f"Your root/.env file should contain:\n"
                f"OPENROUTER_API_KEY=your_api_key_here\n"
                f"OPENROUTER_MODEL={DEFAULT_MODEL}"
            )

        headers = {
            "Authorization": f"Bearer {effective_api_key}",
            "Content-Type": "application/json",
            "X-Title": "Sepsis Visual PDF Extraction",
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds if timeout_seconds is None else timeout_seconds,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter request failed with status {response.status_code}:\n"
                f"{response.text}"
            )

        return response.json()

    @staticmethod
    def get_message_content(response_json: dict[str, Any]) -> str:
        """
        Extracts assistant message content from an OpenRouter chat completion response.
        """

        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise KeyError(f"Could not find message content in response: {response_json}") from exc

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []

            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif "text" in item:
                        text_parts.append(str(item["text"]))

            return "\n".join(text_parts).strip()

        return str(content)

    @staticmethod
    def strip_json_fences(text: str) -> str:
        """
        Removes ```json fences if the model accidentally returns them.
        """

        text = text.strip()

        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return text.strip()

    @classmethod
    def parse_json_from_model_text(cls, text: str) -> Any:
        """
        Parses JSON from the model response.

        Handles:
        - clean JSON
        - fenced JSON
        - accidental surrounding prose
        """

        cleaned = cls.strip_json_fences(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        object_start = cleaned.find("{")
        object_end = cleaned.rfind("}")

        if object_start != -1 and object_end != -1 and object_end > object_start:
            possible_object = cleaned[object_start : object_end + 1]

            try:
                return json.loads(possible_object)
            except json.JSONDecodeError:
                pass

        array_start = cleaned.find("[")
        array_end = cleaned.rfind("]")

        if array_start != -1 and array_end != -1 and array_end > array_start:
            possible_array = cleaned[array_start : array_end + 1]

            try:
                return json.loads(possible_array)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse model response as JSON:\n{text}")

    @staticmethod
    def stringify_field(value: Any) -> str:
        """
        Converts model output values to clean strings for schema consistency.
        """

        if value is None:
            return "Not reported"

        if isinstance(value, str):
            value = value.strip()
            return value if value else "Not reported"

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)

        return str(value)

    @classmethod
    def _unique_nonempty_strings(cls, values: list[Any]) -> list[str]:
        """
        Converts a list of values into unique, non-empty strings while preserving order.
        """

        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            text = cls.stringify_field(value)

            if not text or text == "Not reported":
                continue

            if text not in seen:
                seen.add(text)
                result.append(text)

        return result

    @classmethod
    def _combine_field_values(cls, values: list[Any]) -> str:
        """
        Combines values from multiple accidental model records into one string.
        """

        unique_values = cls._unique_nonempty_strings(values)

        if not unique_values:
            return "Not reported"

        return "; ".join(unique_values)

    @staticmethod
    def _combined_source_info(
        pdf_file: str,
        page_selection: int | Literal["all"],
        requested_start_page: int,
        requested_end_page: int,
        included_pages: list[int],
    ) -> dict[str, Any]:
        """
        Creates the source_info object for the combined page chunk.
        """

        if page_selection == "all":
            center_page: int | None = None
            chunk = "all_pages_combined"
        else:
            center_page = page_selection
            chunk = f"pages_{requested_start_page:03d}_to_{requested_end_page:03d}_combined"

        return {
            "file": pdf_file,
            "center_page": center_page,
            "page_range": {
                "start": requested_start_page,
                "end": requested_end_page,
            },
            "included_pages": included_pages,
            "chunk": chunk,
        }

    @classmethod
    def normalize_combined_record(
        cls,
        parsed_json: Any,
        pdf_file: str,
        page_selection: int | Literal["all"],
        requested_start_page: int,
        requested_end_page: int,
        included_pages: list[int],
    ) -> CombinedRecord:
        """
        Normalizes model output into ONE combined dictionary for the full page set.

        The prompt asks for a single object. This function is defensive:
        - If the model returns a dict, it normalizes that dict.
        - If the model returns {"records": [...]}, it combines those records into one dict.
        - If the model returns a list, it combines the list into one dict.
        """

        if isinstance(parsed_json, dict):
            if "records" in parsed_json and isinstance(parsed_json["records"], list):
                records = [record for record in parsed_json["records"] if isinstance(record, dict)]
            else:
                records = [parsed_json]
        elif isinstance(parsed_json, list):
            records = [record for record in parsed_json if isinstance(record, dict)]
        else:
            raise ValueError("Parsed JSON must be a dict, a list, or an object containing records.")

        combined_record: CombinedRecord = {}

        if len(records) == 1:
            source_record = records[0]

            for field in REQUIRED_FIELDS:
                if field == "source_info":
                    continue

                combined_record[field] = cls.stringify_field(source_record.get(field, "Not reported"))
        else:
            for field in REQUIRED_FIELDS:
                if field == "source_info":
                    continue

                combined_record[field] = cls._combine_field_values(
                    [record.get(field, "Not reported") for record in records]
                )

            if not records:
                combined_record["notes"] = "No valid extraction records were returned by the model."

        combined_record["source_info"] = cls._combined_source_info(
            pdf_file=pdf_file,
            page_selection=page_selection,
            requested_start_page=requested_start_page,
            requested_end_page=requested_end_page,
            included_pages=included_pages,
        )

        return combined_record

    @staticmethod
    def _file_prefix(
        page_selection: int | Literal["all"],
        requested_start_page: int,
        requested_end_page: int,
    ) -> str:
        if page_selection == "all":
            return "all_pages"

        return f"pages_{requested_start_page:03d}_to_{requested_end_page:03d}"

    def extract_pdf(
        self,
        b64_dir: Path | str,
        page_number: PageSelection = DEFAULT_PAGE_SELECTION,
        pdf_file: str | None = None,
        output_dir: Path | str | None = None,
        context_radius: int | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
        save_raw_response: bool | None = None,
    ) -> CombinedRecord:
        """
        Extract one combined structured evidence dictionary from one PDF's b64 pages.

        Args:
            b64_dir:
                Path to one PDF's b64 folder.
                Example: root/data_extract/visual/images/pdf1/b64

            page_number:
                Default is "all". Sends all detected page images from b64_dir.

                To preserve the old n-2 through n+2 behavior, pass an integer
                center page, e.g. page_number=7.

            pdf_file:
                Optional explicit PDF filename for source_info.
                If omitted, inferred from the parent folder.

            output_dir:
                Where JSON extraction outputs are saved.
                If omitted, uses self.output_dir.

            context_radius:
                Only used when page_number is an integer.
                Default is 2, meaning n-2 through n+2.

            model:
                Optional override for the configured OpenRouter vision model.

            temperature:
                Optional override for model temperature.
                Use 0.0 for deterministic extraction.

            max_tokens:
                Optional override for max output tokens.

            timeout_seconds:
                Optional override for request timeout.

            save_raw_response:
                Saves the full OpenRouter response and raw model text for debugging.

        Returns:
            One combined extraction dictionary for this PDF.
        """

        b64_dir = self.resolve_path_from_cwd_or_script_dir(Path(b64_dir))

        if not b64_dir.exists():
            raise FileNotFoundError(f"b64 directory not found: {b64_dir}")

        if not b64_dir.is_dir():
            raise NotADirectoryError(f"b64_dir must be a directory: {b64_dir}")

        pdf_file_name = self.infer_pdf_file_name(b64_dir, explicit_pdf_file=pdf_file)
        pdf_stem = Path(pdf_file_name).stem

        effective_output_dir = self.output_dir if output_dir is None else self.resolve_path_from_cwd_or_script_dir(Path(output_dir))
        pdf_output_dir = effective_output_dir / pdf_stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)

        messages, included_pages, requested_start_page, requested_end_page, page_selection = self.build_messages(
            pdf_file=pdf_file_name,
            b64_dir=b64_dir,
            page_number=page_number,
            context_radius=context_radius,
        )

        file_prefix = self._file_prefix(
            page_selection=page_selection,
            requested_start_page=requested_start_page,
            requested_end_page=requested_end_page,
        )

        response_json = self.call_openrouter(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )

        model_text = self.get_message_content(response_json)
        effective_save_raw_response = self.save_raw_response if save_raw_response is None else save_raw_response

        if effective_save_raw_response:
            raw_response_path = pdf_output_dir / f"{file_prefix}_raw_openrouter_response.json"
            raw_response_path.write_text(
                json.dumps(response_json, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            raw_text_path = pdf_output_dir / f"{file_prefix}_raw_model_text.txt"
            raw_text_path.write_text(model_text, encoding="utf-8")

        parsed_json = self.parse_json_from_model_text(model_text)

        combined_record = self.normalize_combined_record(
            parsed_json=parsed_json,
            pdf_file=pdf_file_name,
            page_selection=page_selection,
            requested_start_page=requested_start_page,
            requested_end_page=requested_end_page,
            included_pages=included_pages,
        )

        output_json_path = pdf_output_dir / f"{file_prefix}_visual_extract.json"
        output_json_path.write_text(
            json.dumps(combined_record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        metadata_path = pdf_output_dir / f"{file_prefix}_metadata.json"
        metadata = {
            "pdf_file": pdf_file_name,
            "page_selection": page_selection,
            "center_page": None if page_selection == "all" else page_selection,
            "context_radius": self.context_radius if context_radius is None else context_radius,
            "requested_page_range": {
                "start": requested_start_page,
                "end": requested_end_page,
            },
            "included_pages": included_pages,
            "b64_dir": str(b64_dir),
            "model": model or self.model,
            "output_json": str(output_json_path),
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return combined_record

    @staticmethod
    def _normalize_b64_dirs(b64_dirs: Path | str | Sequence[Path | str]) -> list[Path | str]:
        """
        Normalizes one b64 directory or a sequence of b64 directories into a list.
        """

        if isinstance(b64_dirs, (str, Path)):
            return [b64_dirs]

        return list(b64_dirs)

    @staticmethod
    def _normalize_pdf_files(
        pdf_files: str | Sequence[str] | None,
        expected_count: int,
    ) -> list[str | None]:
        """
        Normalizes optional explicit PDF filenames.

        For multiple b64 directories, pass either:
            - None, so each PDF filename is inferred
            - one filename per b64 directory
        """

        if pdf_files is None:
            return [None] * expected_count

        if isinstance(pdf_files, str):
            if expected_count != 1:
                raise ValueError(
                    "When extracting multiple PDFs, pdf_files must contain one filename per b64_dir."
                )
            return [pdf_files]

        pdf_file_list = list(pdf_files)

        if len(pdf_file_list) != expected_count:
            raise ValueError(
                "pdf_files must be None or contain exactly one filename per b64_dir. "
                f"Got {len(pdf_file_list)} filenames for {expected_count} b64 directories."
            )

        return pdf_file_list

    def extract_pdfs(
        self,
        b64_dirs: Path | str | Sequence[Path | str],
        page_number: PageSelection = DEFAULT_PAGE_SELECTION,
        pdf_files: str | Sequence[str] | None = None,
        output_dir: Path | str | None = None,
        context_radius: int | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
        save_raw_response: bool | None = None,
    ) -> list[CombinedRecord]:
        """
        Extract one combined JSON dictionary per PDF.

        Args:
            b64_dirs:
                One b64 directory or a list of b64 directories. Each directory
                should contain that PDF's page_*.b64 image files.

            page_number:
                Default is "all". Sends all detected pages for every PDF.
                Pass an integer to run old center-page window mode for every PDF.

            pdf_files:
                Optional explicit PDF filenames. For multiple PDFs, pass one
                filename per b64_dir.

        Returns:
            List of one combined extraction dictionary per PDF, in the same order
            as b64_dirs.
        """

        b64_dir_list = self._normalize_b64_dirs(b64_dirs)
        pdf_file_list = self._normalize_pdf_files(pdf_files, expected_count=len(b64_dir_list))

        records: list[CombinedRecord] = []

        for b64_dir, pdf_file in zip(b64_dir_list, pdf_file_list, strict=True):
            record = self.extract_pdf(
                b64_dir=b64_dir,
                page_number=page_number,
                pdf_file=pdf_file,
                output_dir=output_dir,
                context_radius=context_radius,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                save_raw_response=save_raw_response,
            )
            records.append(record)

        if len(records) > 1:
            effective_output_dir = self.output_dir if output_dir is None else self.resolve_path_from_cwd_or_script_dir(Path(output_dir))
            effective_output_dir.mkdir(parents=True, exist_ok=True)
            collection_output_path = effective_output_dir / "all_pdfs_visual_extract.json"
            collection_output_path.write_text(
                json.dumps(records, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return records


# Backward-compatible function wrapper for existing imports.
def extract_visual_page_data(
    b64_dir: Path,
    page_number: PageSelection = DEFAULT_PAGE_SELECTION,
    model: str = DEFAULT_MODEL,
    pdf_file: str | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    context_radius: int = DEFAULT_CONTEXT_RADIUS,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    save_raw_response: bool = True,
) -> CombinedRecord:
    """
    Backward-compatible pipeline function.

    Default is now page_number="all". Pass an integer page_number to use the
    original n-2 through n+2 center-page extraction behavior.
    """

    extractor = VisualPDFEvidenceExtractor(
        model=model,
        output_dir=output_dir,
        context_radius=context_radius,
        temperature=temperature,
        max_tokens=max_tokens,
        save_raw_response=save_raw_response,
    )

    return extractor.extract_pdf(
        b64_dir=b64_dir,
        page_number=page_number,
        pdf_file=pdf_file,
    )


# Convenience function for main.py pipelines that pass multiple PDFs at once.
def extract_visual_pdf_data(
    b64_dirs: Path | str | Sequence[Path | str],
    page_number: PageSelection = DEFAULT_PAGE_SELECTION,
    model: str = DEFAULT_MODEL,
    pdf_files: str | Sequence[str] | None = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    context_radius: int = DEFAULT_CONTEXT_RADIUS,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    save_raw_response: bool = True,
) -> list[CombinedRecord]:
    """
    Pipeline-friendly helper that returns one extraction dict per PDF.
    """

    extractor = VisualPDFEvidenceExtractor(
        model=model,
        output_dir=output_dir,
        context_radius=context_radius,
        temperature=temperature,
        max_tokens=max_tokens,
        save_raw_response=save_raw_response,
    )

    return extractor.extract_pdfs(
        b64_dirs=b64_dirs,
        page_number=page_number,
        pdf_files=pdf_files,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract one combined structured sepsis evidence object per PDF using "
            "all b64 page images by default. Pass --page-number <int> to use the "
            "old n-2 through n+2 center-page window."
        )
    )

    parser.add_argument(
        "--b64-dir",
        required=True,
        type=Path,
        nargs="+",
        help=(
            "Path(s) to PDF b64 folder(s), e.g. images/pdf1/b64 images/pdf2/b64. "
            "Each folder should contain page_*.b64 files."
        ),
    )

    parser.add_argument(
        "--page-number",
        type=str,
        default=DEFAULT_PAGE_SELECTION,
        help=(
            "Use 'all' to send all detected pages from each b64 directory. "
            "This is the default. Pass an integer to use center-page window mode."
        ),
    )

    parser.add_argument(
        "--pdf-file",
        type=str,
        nargs="*",
        default=None,
        help=(
            "Optional explicit source PDF filename(s), e.g. Gai_2022.pdf. "
            "For multiple --b64-dir values, provide the same number of names."
        ),
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"OpenRouter vision model. Default: {DEFAULT_MODEL}",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for extraction JSON outputs. Default: {DEFAULT_OUTPUT_DIR}",
    )

    parser.add_argument(
        "--context-radius",
        type=int,
        default=DEFAULT_CONTEXT_RADIUS,
        help=(
            "Pages before and after center page when --page-number is an integer. "
            "Default: 2, meaning n-2 through n+2. Ignored when --page-number all."
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Model temperature. Default: 0.0",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max output tokens. Default: 4096",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="OpenRouter request timeout in seconds. Default: 180",
    )

    parser.add_argument(
        "--no-raw-response",
        action="store_true",
        help="Do not save the full raw OpenRouter response and model text.",
    )

    args = parser.parse_args()

    try:
        extractor = VisualPDFEvidenceExtractor(
            model=args.model,
            output_dir=args.output_dir,
            context_radius=args.context_radius,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
            save_raw_response=not args.no_raw_response,
        )

        records = extractor.extract_pdfs(
            b64_dirs=args.b64_dir,
            page_number=args.page_number,
            pdf_files=args.pdf_file,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(records) == 1:
        print(json.dumps(records[0], indent=2, ensure_ascii=False))
    else:
        print(json.dumps(records, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
