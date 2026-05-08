# File: mcp/rag/embed.py

import json
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

from mcp.rag.init_pinecone import init_pinecone


class Embedder:
    def __init__(
        self,
        chunks_dir: str = "mcp/rag/chunks",
        index_name: str = "llama-text-embed-v2",
    ):
        """Initialize the Embedder with Pinecone configuration."""

        self.project_root = Path(__file__).resolve().parents[2]
        self.chunks_dir = Path(chunks_dir)

        if not self.chunks_dir.is_absolute():
            self.chunks_dir = self.project_root / self.chunks_dir

        self.index_name = index_name

        self.pc, self.index, self.embeddings, self.vector_store = init_pinecone(
            index_name=self.index_name,
            create_if_missing=True,
        )

        self.chunks = self.load_chunks_from_folder()
        print(f"Loaded {len(self.chunks)} chunks from {self.chunks_dir}")

    def load_chunks_from_folder(self):
        """Load all chunk dictionaries from every JSON file in the chunks folder."""

        if not self.chunks_dir.exists():
            raise FileNotFoundError(f"Chunks folder not found: {self.chunks_dir}")

        json_files = sorted(self.chunks_dir.glob("*.json"))

        if not json_files:
            raise FileNotFoundError(f"No JSON files found in: {self.chunks_dir}")

        all_chunks = []

        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            chunk_dicts = self.extract_chunk_dicts(data)

            for chunk in chunk_dicts:
                all_chunks.append(
                    {
                        "json_file": json_file.name,
                        "chunk": chunk,
                    }
                )

            print(f"Loaded {len(chunk_dicts)} chunks from {json_file.name}")

        return all_chunks

    def extract_chunk_dicts(self, data):
        """
        Recursively extract dictionaries that match this structure:

        {
            "chunk_text": "...",
            "metadata": {...}
        }
        """

        chunks = []

        if isinstance(data, dict):
            if "chunk_text" in data and "metadata" in data:
                chunks.append(data)
            else:
                for value in data.values():
                    chunks.extend(self.extract_chunk_dicts(value))

        elif isinstance(data, list):
            for item in data:
                chunks.extend(self.extract_chunk_dicts(item))

        return chunks

    def prepare_documents(self):
        """Convert JSON chunks into LangChain Document objects with metadata."""

        documents = []

        for i, item in enumerate(self.chunks):
            chunk = item["chunk"]
            json_file = item["json_file"]

            text = chunk.get("chunk_text", "")
            chunk_metadata = chunk.get("metadata", {})

            if not text:
                continue

            if not isinstance(chunk_metadata, dict):
                chunk_metadata = {}

            doc_metadata = {
                **chunk_metadata,
                "source_json": json_file,
                "global_chunk_index": i,
            }

            doc = Document(
                page_content=text,
                metadata=doc_metadata,
            )

            documents.append(doc)

        print(f"Prepared {len(documents)} Document objects with metadata.")
        return documents

    def clear_index(self):
        """Delete and recreate the index. Use carefully."""

        if self.pc.has_index(self.index_name):
            self.pc.delete_index(self.index_name)
            print(f"Deleted old index '{self.index_name}'")

        self.pc, self.index, self.embeddings, self.vector_store = init_pinecone(
            index_name=self.index_name,
            create_if_missing=True,
        )

        print(f"Recreated index '{self.index_name}'")

    def upload_documents(self):
        """Upload parsed documents to Pinecone."""

        self.clear_index()

        documents = self.prepare_documents()
        uuids = [str(uuid4()) for _ in range(len(documents))]

        self.vector_store.add_documents(
            documents=documents,
            ids=uuids,
        )

        print(
            f"Uploaded {len(documents)} documents "
            f"to Pinecone index '{self.index_name}'."
        )


if __name__ == "__main__":
    embedder = Embedder(
        chunks_dir="mcp/rag/chunks",
        index_name="llama-text-embed-v2",
    )

    embedder.upload_documents()