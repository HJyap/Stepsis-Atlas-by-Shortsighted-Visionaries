const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3001";

export async function sendChatMessage(prompt) {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || data.detail || "Request failed");
  }

  return data;
}