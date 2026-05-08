import { useState } from "react";
import DynamicGraph from "./DynamicGraph";

export default function RightPanel({ data }) {
  const [chartType, setChartType] = useState("Lactate vs 28-day Mortality");
  const [selectedStudy, setSelectedStudy] = useState(data[0].Study);

  const selectedData = data.find((d) => d.Study === selectedStudy);

  // Create graph specs based on chart type
  const getGraphSpec = () => {
    if (chartType === "Lactate vs 28-day Mortality") {
      return {
        data: [
          {
            x: data.map((d) => d.Lactate),
            y: data.map((d) => d["28-day Mortality"]),
            mode: "markers",
            type: "scatter",
            marker: {
              size: data.map((d) => d.N / 30),
              color: "#0ea5a4",
              opacity: 0.7,
            },
            text: data.map((d) => d.Study),
            hovertemplate:
              "<b>%{text}</b><br>Lactate: %{x}<br>Mortality: %{y}%<extra></extra>",
          },
        ],
        layout: {
          title: "Initial Lactate vs 28-day Mortality",
          xaxis: { title: "Lactate (mmol/L)" },
          yaxis: { title: "28-day Mortality (%)" },
          paper_bgcolor: "white",
          plot_bgcolor: "white",
          font: { color: "#08204a" },
          title_font_color: "#0f766e",
        },
      };
    } else if (chartType === "SOFA vs 28-day Mortality") {
      return {
        data: [
          {
            x: data.map((d) => d.SOFA),
            y: data.map((d) => d["28-day Mortality"]),
            mode: "markers",
            type: "scatter",
            marker: {
              size: data.map((d) => d.N / 30),
              color: "#0ea5a4",
              opacity: 0.7,
            },
            text: data.map((d) => d.Study),
            hovertemplate:
              "<b>%{text}</b><br>SOFA: %{x}<br>Mortality: %{y}%<extra></extra>",
          },
        ],
        layout: {
          title: "SOFA Score vs 28-day Mortality",
          xaxis: { title: "SOFA Score" },
          yaxis: { title: "28-day Mortality (%)" },
          paper_bgcolor: "white",
          plot_bgcolor: "white",
          font: { color: "#08204a" },
          title_font_color: "#0f766e",
        },
      };
    } else if (chartType === "Antibiotic Timing vs Mortality") {
      return {
        data: [
          {
            x: data.map((d) => d.Study),
            y: data.map((d) => d["Antibiotic Timing"]),
            type: "bar",
            marker: { color: "#0ea5a4" },
            hovertemplate: "<b>%{x}</b><br>Timing: %{y} hours<extra></extra>",
          },
        ],
        layout: {
          title: "Antibiotic Timing by Study",
          xaxis: { title: "Study" },
          yaxis: { title: "Time to Antibiotic (hours)" },
          paper_bgcolor: "white",
          plot_bgcolor: "white",
          font: { color: "#08204a" },
          title_font_color: "#0f766e",
        },
      };
    }
  };

  return (
    <div>
      {/* Graph Card */}
      <div style={styles.card}>
        <h2 style={styles.sectionTitle}>Graph</h2>

        <select
          value={chartType}
          onChange={(e) => setChartType(e.target.value)}
          style={styles.select}
        >
          <option>Lactate vs 28-day Mortality</option>
          <option>SOFA vs 28-day Mortality</option>
          <option>Antibiotic Timing vs Mortality</option>
        </select>

        <div style={{ height: "400px", marginTop: "15px" }}>
          <DynamicGraph spec={getGraphSpec()} />
        </div>
      </div>

      {/* Source Evidence Card */}
      <div style={{ ...styles.card, marginTop: "20px" }}>
        <h2 style={styles.sectionTitle}>Source Evidence</h2>

        <select
          value={selectedStudy}
          onChange={(e) => setSelectedStudy(e.target.value)}
          style={styles.select}
        >
          {data.map((d) => (
            <option key={d.Study} value={d.Study}>
              {d.Study}
            </option>
          ))}
        </select>

        <div style={styles.sourceBox}>
          <div>
            <b>Paper:</b> {selectedData.Study}, {selectedData.Year}
          </div>
          <div>
            <b>Population:</b> {selectedData.Population}
          </div>
          <div>
            <b>N:</b> {selectedData.N}
          </div>
          <div>
            <b>Source:</b> {selectedData.Source}
          </div>
          <div style={{ marginTop: "10px" }}>
            <b>Finding:</b> Higher initial lactate levels are associated with
            increased 28-day mortality.
          </div>
          <div>
            <b>Extracted Value:</b> Lactate = {selectedData.Lactate} mmol/L,
            Mortality = {selectedData["28-day Mortality"]}%
          </div>
          <div>
            <b>Confidence:</b> {selectedData.Confidence}
          </div>
        </div>
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
  select: {
    width: "100%",
    padding: "10px",
    borderRadius: "8px",
    border: "1px solid #dbeafe",
    background: "white",
    color: "#08204a",
    fontFamily: "inherit",
    fontSize: "14px",
  },
  sourceBox: {
    background: "#f0fdfa",
    border: "1px solid #99f6e4",
    borderRadius: "18px",
    padding: "18px",
    lineHeight: "1.8",
    marginTop: "15px",
    fontSize: "14px",
  },
};