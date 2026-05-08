import "dotenv/config";
import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const app = express();
const PORT = 3001;
const PYTHON_API = "http://localhost:8000";

app.use(cors({ origin: "http://localhost:5173" }));
app.use(express.json());

// POST /api/chat — forward to Python backend
app.post("/api/chat", async (req, res) => {
  if (!req.body.prompt?.trim()) {
    return res.status(400).json({ error: "prompt is required" });
  }
  try {
    const response = await fetch(`${PYTHON_API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: "Failed to reach Python backend", detail: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`API gateway running on http://localhost:${PORT}`);
});
