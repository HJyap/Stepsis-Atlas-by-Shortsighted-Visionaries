from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str


KNOWN_STUDIES = [
    "Smith et al.", "Garcia et al.", "Patel et al.",
    "Chen et al.", "Johnson et al.", "Baloch et al.",
]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    system_prompt = (
        "You are a clinical research assistant for Sepsis Atlas. "
        "Answer questions about sepsis research based on the available articles.\n\n"
        "The available studies are: " + ", ".join(KNOWN_STUDIES) + ".\n\n"
        "You MUST respond with valid JSON in this exact format:\n"
        '{"answer": "your answer here", "matched_studies": [{"study": "Study Name", "excerpt": "brief relevant finding from this study"}]}\n'
        "Only include studies from the list that are genuinely relevant. "
        "If no studies match, return an empty matched_studies array."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.prompt},
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o",
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=30.0
        )

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")

    if not content:
        return {"status": "not_found", "answer": None, "matched_studies": []}

    try:
        parsed = json.loads(content)
    except Exception:
        return {"status": "found", "answer": content, "matched_studies": []}

    answer = parsed.get("answer")
    matched_studies = parsed.get("matched_studies", [])

    if not answer:
        return {"status": "not_found", "answer": None, "matched_studies": []}

    return {
        "status": "found",
        "answer": answer,
        "matched_studies": matched_studies,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
