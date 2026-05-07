import { useEffect, useState } from "react";
import DynamicGraph from "./DynamicGraph";

export default function RightPanel({ data, result, theme }) {
  const [chartType, setChartType] = useState("Lactate vs 28-day Mortality");
  const references = result.references ?? [];
  const graphData =
    result.status === "found"
      ? data.filter((item) => references.some((ref) => ref.study === item.Study))
      : [];
  const [selectedStudy, setSelectedStudy] = useState(
    references[0]?.study ?? data[0]?.Study ?? ""
  );

  useEffect(() => {
    setSelectedStudy(references[0]?.study ?? data[0]?.Study ?? "");
  }, [data, references]);

  const activeStudy =
    graphData.some((d) => d.Study === selectedStudy)
      ? selectedStudy
      : graphData[0]?.Study ?? "";
  const selectedData = graphData.find((d) => d.Study === activeStudy);
  const selectedReference = references.find((ref) => ref.study === activeStudy);

  const getGraphSpec = () => {
    if (result.status !== "found" || graphData.length === 0) {
      return null;
    }

    const baseLayout = {
      title: "Results from Matched Articles",
      paper_bgcolor: theme.card,
      plot_bgcolor: theme.card,
      font: { color: theme.text },
      title_font: { color: theme.title },
      margin: { t: 56, r: 20, b: 56, l: 56 },
    };

    const axisStyle = (title) => ({
      title,
      gridcolor: theme.chartGrid ?? "rgba(15, 118, 110, 0.08)",
      zerolinecolor: theme.chartGrid ?? "rgba(15, 118, 110, 0.08)",
      tickfont: { color: theme.chartAxis ?? theme.text },
      color: theme.chartAxis ?? theme.text,
    });

    if (chartType === "Lactate vs 28-day Mortality") {
      return {
        data: [
          {
            x: graphData.map((d) => d.Lactate),
            y: graphData.map((d) => d["28-day Mortality"]),
            mode: "markers",
            type: "scatter",
            marker: {
              size: graphData.map((d) => d.N / 30),
              color: theme.accent,
              opacity: 0.85,
              line: { color: theme.chartAxis ?? theme.text, width: 1 },
            },
            text: graphData.map((d) => d.Study),
            hovertemplate:
              "<b>%{text}</b><br>Lactate: %{x}<br>Mortality: %{y}%<extra></extra>",
          },
        ],
        layout: {
          ...baseLayout,
          xaxis: axisStyle("Lactate (mmol/L)"),
          yaxis: axisStyle("28-day Mortality (%)"),
        },
      };
    }

    if (chartType === "SOFA vs 28-day Mortality") {
      return {
        data: [
          {
            x: graphData.map((d) => d.SOFA),
            y: graphData.map((d) => d["28-day Mortality"]),
            mode: "markers",
            type: "scatter",
            marker: {
              size: graphData.map((d) => d.N / 30),
              color: theme.accent,
              opacity: 0.85,
              line: { color: theme.chartAxis ?? theme.text, width: 1 },
            },
            text: graphData.map((d) => d.Study),
            hovertemplate:
              "<b>%{text}</b><br>SOFA: %{x}<br>Mortality: %{y}%<extra></extra>",
          },
        ],
        layout: {
          ...baseLayout,
          xaxis: axisStyle("SOFA Score"),
          yaxis: axisStyle("28-day Mortality (%)"),
        },
      };
    }

    return {
      data: [
        {
          x: graphData.map((d) => d.Study),
          y: graphData.map((d) => d["Antibiotic Timing"]),
          type: "bar",
          marker: { color: theme.accent },
          hovertemplate: "<b>%{x}</b><br>Timing: %{y} hours<extra></extra>",
        },
      ],
      layout: {
        ...baseLayout,
        xaxis: axisStyle("Study"),
        yaxis: axisStyle("Time to Antibiotic (hours)"),
      },
    };
  };

  return (
    <div>
      <div style={styles.card(theme)}>
        <h2 style={styles.sectionTitle(theme)}>Graph</h2>

        <div style={styles.selectWrapper}>
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value)}
            style={styles.select(theme)}
          >
            <option>Lactate vs 28-day Mortality</option>
            <option>SOFA vs 28-day Mortality</option>
            <option>Antibiotic Timing vs Mortality</option>
          </select>
          <span style={styles.selectIcon(theme)}>▼</span>
        </div>

        <div style={{ height: "400px", marginTop: "15px" }}>
          {result.status === "found" ? (
            <DynamicGraph spec={getGraphSpec()} />
          ) : (
            <div style={styles.emptyState(theme)}>
              No graph data available for this query.
            </div>
          )}
        </div>
      </div>

      <div style={{ ...styles.card(theme), marginTop: "20px" }}>
        <h2 style={styles.sectionTitle(theme)}>Source Evidence</h2>

        {result.status === "found" ? (
          <>
            <div style={styles.selectWrapper}>
              <select
                value={activeStudy}
                onChange={(e) => setSelectedStudy(e.target.value)}
                style={styles.select(theme)}
              >
                {graphData.map((study) => (
                  <option key={study.Study} value={study.Study}>
                    {study.Study}
                  </option>
                ))}
              </select>
              <span style={styles.selectIcon(theme)}>▼</span>
            </div>

            {selectedData && selectedReference ? (
              <div style={styles.sourceBox(theme)}>
                <div style={styles.evidenceSection(theme)}>
                  <span style={styles.evidenceLabel(theme)}>Article</span>
                  <span style={styles.evidenceValue(theme)}>
                    {selectedData.Study}, {selectedData.Year}
                  </span>
                </div>

                <div style={styles.evidenceSection(theme)}>
                  <span style={styles.evidenceLabel(theme)}>Population</span>
                  <span style={styles.evidenceValue(theme)}>
                    {selectedData.Population}
                  </span>
                </div>

                <div style={styles.evidenceSection(theme)}>
                  <span style={styles.evidenceLabel(theme)}>Reference</span>
                  <span style={styles.evidenceValue(theme)}>
                    {selectedReference.source}
                  </span>
                </div>

                <div style={styles.excerpt(theme)}>
                  <b>Evidence:</b> {selectedReference.excerpt}
                </div>

                <div style={styles.metricsContainer}>
                  <div style={styles.metric(theme)}>
                    <span style={styles.metricLabel(theme)}>SOFA</span>
                    <span style={styles.metricValue(theme)}>{selectedData.SOFA}</span>
                  </div>
                  <div style={styles.metric(theme)}>
                    <span style={styles.metricLabel(theme)}>Lactate</span>
                    <span style={styles.metricValue(theme)}>{selectedData.Lactate}</span>
                  </div>
                  <div style={styles.metric(theme)}>
                    <span style={styles.metricLabel(theme)}>Mortality</span>
                    <span style={styles.metricValue(theme)}>
                      {selectedData["28-day Mortality"]}%
                    </span>
                  </div>
                </div>

                <div style={styles.confidenceBox(theme)}>
                  <span style={styles.confidenceLabel(theme)}>Confidence</span>
                  <span style={styles.confidenceValue(theme)}>
                    {selectedReference.confidence}
                  </span>
                </div>
              </div>
            ) : (
              <div style={styles.emptyState(theme)}>
                No matching reference found in the article set.
              </div>
            )}
          </>
        ) : (
          <div style={styles.emptyState(theme)}>
            No matching reference found in the article set.
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  card: (theme) => ({
    background: theme.card,
    border: `1px solid ${theme.cardBorder}`,
    borderRadius: "20px",
    padding: "22px",
    boxShadow: theme.cardShadow,
  }),
  sectionTitle: (theme) => ({
    color: theme.title,
    fontSize: "22px",
    fontWeight: "900",
    marginBottom: "16px",
  }),
  selectWrapper: {
    position: "relative",
    marginBottom: "15px",
  },
  select: (theme) => ({
    width: "100%",
    padding: "12px 40px 12px 16px",
    borderRadius: "8px",
    border: `2px solid ${theme.accent}`,
    background: theme.inputBg,
    color: theme.text,
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    appearance: "none",
  }),
  selectIcon: (theme) => ({
    position: "absolute",
    right: "12px",
    top: "50%",
    transform: "translateY(-50%)",
    color: theme.accent,
    pointerEvents: "none",
    fontSize: "12px",
  }),
  sourceBox: (theme) => ({
    background: theme.sourceBg,
    border: `1px solid ${theme.sourceBorder}`,
    borderRadius: "12px",
    padding: "18px",
    marginTop: "15px",
  }),
  evidenceSection: (theme) => ({
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "12px",
    marginBottom: "12px",
    paddingBottom: "10px",
    borderBottom: `1px solid ${theme.softBorder}`,
  }),
  evidenceLabel: (theme) => ({
    color: theme.title,
    fontWeight: "700",
    fontSize: "13px",
    textTransform: "uppercase",
  }),
  evidenceValue: (theme) => ({
    color: theme.text,
    fontSize: "14px",
    textAlign: "right",
    flex: 1,
  }),
  excerpt: (theme) => ({
    color: theme.text,
    lineHeight: "1.7",
    marginTop: "8px",
  }),
  metricsContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: "10px",
    marginTop: "16px",
    marginBottom: "12px",
  },
  metric: (theme) => ({
    background: theme.soft,
    border: `1px solid ${theme.softBorder}`,
    borderRadius: "8px",
    padding: "10px",
    textAlign: "center",
  }),
  metricLabel: (theme) => ({
    display: "block",
    color: theme.title,
    fontSize: "11px",
    fontWeight: "700",
    textTransform: "uppercase",
    marginBottom: "4px",
  }),
  metricValue: (theme) => ({
    display: "block",
    color: theme.text,
    fontSize: "16px",
    fontWeight: "800",
  }),
  confidenceBox: (theme) => ({
    background: theme.soft,
    border: `1px solid ${theme.accent}`,
    borderRadius: "8px",
    padding: "12px 14px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: "12px",
  }),
  confidenceLabel: (theme) => ({
    color: theme.title,
    fontWeight: "700",
    fontSize: "13px",
    textTransform: "uppercase",
  }),
  confidenceValue: (theme) => ({
    color: theme.title,
    fontSize: "18px",
    fontWeight: "900",
  }),
  emptyState: (theme) => ({
    height: "100%",
    minHeight: "180px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    color: theme.muted,
    background: theme.soft,
    border: `1px dashed ${theme.emptyBorder}`,
    borderRadius: "18px",
    padding: "24px",
    lineHeight: "1.6",
    marginTop: "15px",
  }),
};
