import { useState } from "react";

export default function MiddlePanel({ data, onQuerySend }) {
  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Hi! Ask me a sepsis research question. I will return structured data, graphs, and source evidence.",
    },
    {
      role: "user",
      text: "What is the relationship between initial lactate and 28-day mortality?",
    },
    {
      role: "ai",
      text: "I found relevant studies. The graph and source evidence are shown on the right.",
    },
  ]);
  const [inputValue, setInputValue] = useState("");

  const handleSend = () => {
    if (!inputValue.trim()) return;

    setMessages([...messages, { role: "user", text: inputValue }]);
    onQuerySend(inputValue);
    setInputValue("");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: "I found relevant studies. The graph and source evidence are shown on the right.",
        },
      ]);
    }, 1000);
  };

  const handleDownloadCSV = () => {
    const csv = [
      Object.keys(data[0]).join(","),
      ...data.map((row) => Object.values(row).join(",")),
    ].join("\n");

    const element = document.createElement("a");
    element.setAttribute(
      "href",
      "data:text/csv;charset=utf-8," + encodeURIComponent(csv)
    );
    element.setAttribute("download", "sepsis_atlas_data.csv");
    element.style.display = "none";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div>
      {/* Chat Card */}
      <div style={styles.card}>
        <h2 style={styles.sectionTitle}>Clinical Research Chat</h2>
        <p style={styles.muted}>Ask any clinical question about sepsis research.</p>

        <div style={styles.chatContainer}>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                ...styles.chatMessage,
                ...(msg.role === "ai" ? styles.chatAI : styles.chatUser),
              }}
            >
              {msg.text}
            </div>
          ))}
        </div>

        <input
          type="text"
          placeholder="Ask a clinical sepsis question..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          style={styles.input}
        />

        <button onClick={handleSend} style={styles.sendButton}>
          Send Question
        </button>
      </div>

      {/* Data Table Card */}
      <div style={{ ...styles.card, marginTop: "20px" }}>
        <h2 style={styles.sectionTitle}>Extracted Data</h2>

        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                {Object.keys(data[0]).map((col) => (
                  <th key={col} style={styles.th}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx} style={idx % 2 === 0 ? { background: "#f8fbff" } : {}}>
                  {Object.values(row).map((val, i) => (
                    <td key={i} style={styles.td}>
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button onClick={handleDownloadCSV} style={styles.downloadButton}>
          ⬇️ Download CSV
        </button>
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: "white",
    border: "1px solid #dbeafe",
    borderRadius: "20px",
    padding: "22px",
    boxShadow: "0 12px 35px rgba(2,132,199,0.08)",
  },
  sectionTitle: {
    color: "#0f766e",
    fontSize: "22px",
    fontWeight: "900",
    marginBottom: "8px",
  },
  muted: {
    color: "#55708f",
    marginBottom: "15px",
  },
  chatContainer: {
    maxHeight: "250px",
    overflowY: "auto",
    marginBottom: "15px",
  },
  chatMessage: {
    borderRadius: "16px",
    padding: "16px",
    margin: "14px 0",
    maxWidth: "85%",
  },
  chatAI: {
    background: "#eef6ff",
    textAlign: "left",
  },
  chatUser: {
    background: "#e6fffb",
    marginLeft: "auto",
    textAlign: "right",
  },
  input: {
    width: "100%",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ddd",
    marginBottom: "10px",
    fontFamily: "inherit",
    fontSize: "14px",
  },
  sendButton: {
    width: "100%",
    padding: "12px",
    background: "#0ea5a4",
    color: "white",
    border: "none",
    borderRadius: "14px",
    fontWeight: "800",
    cursor: "pointer",
  },
  tableWrapper: {
    overflowX: "auto",
    marginBottom: "15px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "12px",
  },
  th: {
    background: "#f0f9ff",
    padding: "12px",
    textAlign: "left",
    borderBottom: "2px solid #bfdbfe",
    fontWeight: "bold",
    color: "#0f3d75",
  },
  td: {
    padding: "10px 12px",
    borderBottom: "1px solid #e0f2fe",
  },
  downloadButton: {
    width: "100%",
    padding: "12px",
    background: "#0ea5a4",
    color: "white",
    border: "none",
    borderRadius: "14px",
    fontWeight: "800",
    cursor: "pointer",
  },
};