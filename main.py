from fastapi import FastAPI

app = FastAPI()



###################
# ENDPOINTS
###################

@app.get("/")
async def root():
    return {"message": "Server runs on localhost:8000. Use /extract to extract visual evidence from PDFs."}

@app.post("/chat")
async def chat():
    return {"message": "Chat endpoint is not implemented yet."}