# File: mcp/rag/rag-tool.py

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from init_pinecone import init_pinecone

ROOT_DIR = Path(__file__).resolve().parents[2]
EXTRACT_INPUT_PATH = ROOT_DIR / "data_extract" / "extract_input.json"
TOP_K = 5

mcp = FastMCP("SepsisDataAnalysis", json_response=True)

_, _, _, vector_store = init_pinecone(
    index_name="llama-text-embed-v2",
    create_if_missing=False,
)


def save_metadata(metadata_list: list[dict[str, Any]]) -> None:
    EXTRACT_INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with EXTRACT_INPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(metadata_list, file, ensure_ascii=False, indent=2)


@mcp.tool()
def retrieve_relevant_data(query: str, top_k: int = TOP_K) -> str:
    """
    Retrieve relevant chunks from Pinecone.

    Returns only chunk text to the LLM/tool caller.
    Saves retrieved metadata separately to data_extract/extract_input.json.
    """
    retrieved = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=top_k,
    )

    chunk_texts: list[str] = []
    metadata_list: list[dict[str, Any]] = []

    for doc, _score in retrieved:
        chunk_texts.append(doc.page_content or "")

        if isinstance(doc.metadata, dict):
            metadata_list.append(dict(doc.metadata))
        else:
            metadata_list.append({})

    save_metadata(metadata_list)

    return "\n\n".join(chunk_texts)


if __name__ == "__main__":
    mcp.settings.host = "localhost"
    mcp.settings.port = 8001
    mcp.run(transport="streamable-http")