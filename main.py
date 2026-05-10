import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add paths for imports
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "llm"))

from mcp_client import run as mcp_run

app = FastAPI()

# Allow frontend / gateway access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
EXTRACT_INPUT = ROOT_DIR / "data_extract" / "extract_input.json"

TEXT_EXTRACT_OUTPUT_DIR = ROOT_DIR / "data_extract" / "text"
VISUAL_EXTRACTOR = ROOT_DIR / "data_extract" / "visual" / "visual_pdf_evidence_extractor.py"
VISUAL_EXTRACT_OUTPUT_DIR = ROOT_DIR / "data_extract" / "visual_extract_output"

COMPARISON_OUTPUT_DIR = ROOT_DIR / "extraction_comparison" / "report" / "dir_run"

IGNORED_JSON_FILES = {
    "controlled_values.json",
    "extraction_results.json",
}


class ChatRequest(BaseModel):
    prompt: str


@app.get("/")
async def root():
    return {
        "message": "Server runs on localhost:8000. Use POST /chat or POST /api/chat."
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    return await handle_chat(request)


@app.post("/api/chat")
async def api_chat(request: ChatRequest):
    return await handle_chat(request)


async def handle_chat(request: ChatRequest):
    """
    Pipeline:
    1. Call MCP client LLM with prompt
    2. Wait for extract_input.json to be created
    3. Run visual PDF extractor
    4. Collect visual extract output files
    5. Run extraction comparison between text and visual outputs
    6. Load mean confidence scores from summary.json for each paper
    7. Return response
    """

    try:
        prompt = request.prompt.strip()

        if not prompt:
            return {
                "status": "error",
                "error": "prompt is required",
                "llm_answer": None,
                "visual_extracts": None,
                "comparison_confidence_scores": None,
                "confidence_score": 0.0,
            }

        # Step 1: Get LLM answer via MCP client
        print(f"[1/6] Getting LLM response for: {prompt[:50]}...")
        llm_answer = await mcp_run(prompt)

        # Step 2: Wait for extract_input.json to be created
        print("[2/6] Waiting for extract_input.json...")
        await wait_for_file(EXTRACT_INPUT, timeout=30)

        # Step 3: Run visual PDF extractor
        print("[3/6] Running visual PDF extractor...")
        await run_visual_extractor()

        # Step 4: Collect visual extract output
        print("[4/6] Collecting visual extract output...")
        visual_data = load_visual_extracts()

        # Step 5: Run extraction comparison
        print("[5/6] Running extraction comparison...")
        await run_extraction_comparison()

        # Step 6: Load per-paper confidence scores
        print("[6/6] Loading comparison confidence scores...")
        comparison_confidence_scores = load_comparison_confidence_scores()

        return {
            "status": "success",
            "llm_answer": llm_answer,
            "visual_extracts": visual_data,
            "comparison_confidence_scores": comparison_confidence_scores,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "llm_answer": None,
            "visual_extracts": None,
            "comparison_confidence_scores": None,
            "confidence_score": 0.0,
        }


async def wait_for_file(file_path: Path, timeout: int = 30) -> None:
    """Wait for a file to be created."""
    start = asyncio.get_event_loop().time()

    while True:
        if file_path.exists():
            return

        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout:
            raise TimeoutError(f"File {file_path} not created within {timeout}s")

        await asyncio.sleep(0.5)


async def run_visual_extractor() -> None:
    """Run the visual PDF evidence extractor."""
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(VISUAL_EXTRACTOR)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Visual extractor failed.\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )


def load_visual_extracts() -> dict:
    """
    Load all visual extract JSON files except metadata files.
    """
    extracts = {}

    if not VISUAL_EXTRACT_OUTPUT_DIR.exists():
        return extracts

    for json_file in sorted(VISUAL_EXTRACT_OUTPUT_DIR.glob("*.json")):
        if json_file.name in IGNORED_JSON_FILES:
            continue

        try:
            paper_name = json_file.stem
            with open(json_file, "r", encoding="utf-8") as f:
                extracts[paper_name] = json.load(f)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return extracts


async def run_extraction_comparison() -> None:
    """
    Run extraction_comparison on:
    - A: root/data_extract/text_extract_output
    - B: root/data_extract/visual_extract_output

    Reports are written to:
    root/extraction_comparison/report/dir_run
    """
    if not TEXT_EXTRACT_OUTPUT_DIR.exists():
        raise FileNotFoundError(f"Text extract output folder not found: {TEXT_EXTRACT_OUTPUT_DIR}")

    if not VISUAL_EXTRACT_OUTPUT_DIR.exists():
        raise FileNotFoundError(f"Visual extract output folder not found: {VISUAL_EXTRACT_OUTPUT_DIR}")

    COMPARISON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(ROOT_DIR)
        if not existing_pythonpath
        else f"{str(ROOT_DIR)}{os.pathsep}{existing_pythonpath}"
    )

    result = await asyncio.to_thread(
        subprocess.run,
        [
            sys.executable,
            "-m",
            "extraction_comparison.main",
            "--dir-a",
            str(TEXT_EXTRACT_OUTPUT_DIR),
            "--dir-b",
            str(VISUAL_EXTRACT_OUTPUT_DIR),
            "--output-dir",
            str(COMPARISON_OUTPUT_DIR),
        ],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Extraction comparison failed.\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )


def load_comparison_confidence_scores() -> dict:
    """
    Load only mean_confidence_score values from each study summary.json.

    Expected folder structure:
    root/extraction_comparison/report/dir_run/Bidart_2024/summary.json

    Returns:
    {
      "Bidart_2024": {
        "cohort_level_mean_confidence_score": 77.65,
        "predictor_level_mean_confidence_score": 0.0
      }
    }
    """
    scores = {}

    if not COMPARISON_OUTPUT_DIR.exists():
        return scores

    for study_dir in sorted(COMPARISON_OUTPUT_DIR.iterdir()):
        if not study_dir.is_dir():
            continue

        summary_file = study_dir / "summary.json"
        if not summary_file.exists():
            continue

        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary = json.load(f)

            cohort_score = (
                summary.get("cohort_level", {})
                .get("mean_confidence_score", 0.0)
            )
            predictor_score = (
                summary.get("predictor_level", {})
                .get("mean_confidence_score", 0.0)
            )

            scores[study_dir.name] = {
                "cohort_level_mean_confidence_score": cohort_score,
                "predictor_level_mean_confidence_score": predictor_score,
            }

        except Exception as e:
            print(f"Error loading confidence score from {summary_file}: {e}")

    return scores