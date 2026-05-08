# File: mcp/rag/init_pinecone.py

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from pinecone import Pinecone

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_NAME = "llama-text-embed-v2"
DEFAULT_MODEL = "llama-text-embed-v2"


def init_pinecone(
    index_name: str = DEFAULT_INDEX_NAME,
    create_if_missing: bool = False,
):
    load_dotenv(dotenv_path=ROOT_DIR / ".env")

    pinecone_api_key = os.getenv("PINECONE_API_KEY")

    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY was not found in the root .env file.")

    os.environ["PINECONE_API_KEY"] = pinecone_api_key

    pc = Pinecone(api_key=pinecone_api_key)

    if create_if_missing and not pc.has_index(index_name):
        pc.create_index_for_model(
            name=index_name,
            cloud="aws",
            region="us-east-1",
            embed={
                "model": DEFAULT_MODEL,
                "field_map": {"text": "text"},
            },
        )
        print(f"Created Pinecone index '{index_name}'")

    index = pc.Index(index_name)

    embeddings = PineconeEmbeddings(model=DEFAULT_MODEL)

    vector_store = PineconeVectorStore(
        index=index,
        embedding=embeddings,
    )

    return pc, index, embeddings, vector_store