import asyncio
import json
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
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
EXTRACT_INPUT = ROOT_DIR / "data_extract" / "extract_input.json"
VISUAL_EXTRACTOR = ROOT_DIR / "data_extract" / "visual" / "visual_pdf_evidence_extractor.py"
OUTPUT_DIR = ROOT_DIR / "data_extract" / "visual_extract_output"


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
    1. Call MCP client LLM with prompt
    2. Wait for extract_input.json to be created
    3. Run visual PDF extractor
    4. Collect visual extract output files
    5. Return response with LLM answer + extracted data + confidence score
    """

    try:
        prompt = request.prompt.strip()

        if not prompt:
            return {
                "status": "error",
                "error": "prompt is required",
                "llm_answer": None,
                "visual_extracts": None,
                "confidence_score": 0.0,
            }

        # Step 1: Get LLM answer via MCP client
        print(f"[1/4] Getting LLM response for: {prompt[:50]}...")
        llm_answer = await mcp_run(prompt)

        # Step 2: Wait for extract_input.json to be created
        print("[2/4] Waiting for extract_input.json...")
        await wait_for_file(EXTRACT_INPUT, timeout=30)

        # Step 3: Run visual PDF extractor
        print("[3/4] Running visual PDF extractor...")
        await run_extractor()

        # Step 4: Collect visual extract output
        print("[4/4] Collecting visual extract output...")
        visual_data = load_visual_extracts()

        return {
            "status": "success",
            "llm_answer": llm_answer,
            "visual_extracts": visual_data,
            "confidence_score": 0.85,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "llm_answer": None,
            "visual_extracts": None,
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


async def run_extractor() -> None:
    """Run the visual PDF evidence extractor."""
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(VISUAL_EXTRACTOR)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Extractor failed: {result.stderr}")


def load_visual_extracts() -> dict:
    """
    Load all visual extract JSON files except metadata files.
    """
    extracts = {}

    if not OUTPUT_DIR.exists():
        return extracts

    for json_file in OUTPUT_DIR.glob("*.json"):
        if json_file.name in ["extraction_results.json", "controlled_values.json"]:
            continue

        try:
            paper_name = json_file.stem
            with open(json_file, "r", encoding="utf-8") as f:
                extracts[paper_name] = json.load(f)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return extracts