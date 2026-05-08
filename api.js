const express = require("express");
const cors = require("cors");

const app = express();

const PORT = process.env.PORT || 3001;
const PYTHON_API = process.env.PYTHON_API || "http://localhost:8000";

app.use(
  cors({
    origin: "http://localhost:5173",
  })
);

app.use(express.json({ limit: "25mb" }));

app.get("/", (_req, res) => {
  res.json({
    message: "Express API gateway is running.",
    chat_endpoint: "/api/chat",
    python_backend: PYTHON_API,
  });
});

app.post("/api/chat", async (req, res) => {
  const prompt = req.body && req.body.prompt;

  if (!prompt || !prompt.trim()) {
    return res.status(400).json({
      status: "error",
      error: "prompt is required",
    });
  }

  try {
    const response = await fetch(`${PYTHON_API}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: prompt.trim(),
      }),
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (err) {
    return res.status(500).json({
      status: "error",
      error: "Failed to reach Python backend",
      detail: err.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`API gateway running on http://localhost:${PORT}`);
});