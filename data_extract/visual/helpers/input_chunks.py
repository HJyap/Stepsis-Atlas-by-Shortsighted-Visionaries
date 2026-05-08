#data_extract/visual/helpers/input_chunks.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_chunks(input_json: Path) -> list[dict[str, Any]]:
    chunks = json.loads(input_json.read_text(encoding="utf-8"))
    return [chunk for chunk in chunks if isinstance(chunk, dict)]


def source_file_name(chunk: dict[str, Any]) -> str:
    source_file = str(chunk.get("source_file", "")).strip()

    if not source_file:
        raise ValueError("Chunk is missing source_file")

    return Path(source_file).name


def page_as_int(chunk: dict[str, Any]) -> int:
    raw_page = chunk.get("page")
    page = float(str(raw_page).strip())

    if not page.is_integer() or page < 1:
        raise ValueError(f"Invalid page: {raw_page!r}")

    return int(page)


def b64_dir_for_chunk(chunk: dict[str, Any], images_dir: Path) -> Path:
    source_file = source_file_name(chunk)
    source_stem = Path(source_file).stem

    candidates = [
        images_dir / source_file / "b64",
        images_dir / source_stem / "b64",
    ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    tried = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(f"Missing b64 dir. Tried:\n{tried}")