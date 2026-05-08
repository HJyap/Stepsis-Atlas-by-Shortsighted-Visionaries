import { useEffect, useRef, useState } from "react";

function getRowGroupKey(row) {
  return row?.Paper || row?.Study || row?.["Study / Papers"] || "";
}

function getCellValue(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function csvEscape(value) {
  const text = getCellValue(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function formatMetric(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  return String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  const text = String(value);

  if (text.includes("%") || text.toLowerCase().includes("not")) {
    return text;
  }

  return `${text}%`;
}

function formatHours(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  const text = String(value);

  if (text.toLowerCase().includes("not") || text.toLowerCase().includes("h")) {
    return text;
  }

  return `${text}h`;
}

function extractNamedMetric(row, metricName) {
  const combined = [
    row?.["Cohort Characteristics"],
    row?.["Effect / Performance"],
    row?.Population,
  ]
    .filter(Boolean)
    .join(" ");

  const regex = new RegExp(`${metricName}\\s*[:=]?\\s*([0-9]+(?:\\.\\d+)?)`, "i");
  const match = combined.match(regex);

  return match?.[1] ?? "";
}

function buildVisualArticleDetails(row) {
  if (!row) return null;

  return {
    Study: row.Paper || "Extracted article",
    Year: "",
    Region: row.Location || "",
    Population: row.Population || "Not provided",
    N: row["Cohort Size"] || "Not provided",
    StudyType: row["Study Design"] || row["Model / Analysis"] || "Not provided",
    Source:
      row["Record Type"] === "Predictor/Model"
        ? [row.Outcome, row["Model / Analysis"]].filter(Boolean).join(" · ")
        : row["Cohort ID"] || row["Record Type"] || "Visual extraction output",
    SOFA: extractNamedMetric(row, "SOFA") || "Not provided",
    Lactate: extractNamedMetric(row, "Lactate") || "Not provided",
    "28-day Mortality": row["Mortality Rate"] || "Not provided",
    "Antibiotic Timing": "Not provided",
    Confidence: row["Confidence Score"] || "Pending",
    DOI: row.DOI || "Not provided",
    URL: "",
  };
}

export default function MiddlePanel({ data, result, onQuerySend, theme }) {
  const buildMessages = (currentResult) => {
    const msgs = [
      {
        role: "ai",
        text: "Ask about the uploaded articles. I will show a matched answer, source evidence, and a graph only when the articles support it.",
        references: [],
      },
    ];

    if (currentResult.query) {
      msgs.push({ role: "user", text: currentResult.query });
      msgs.push({
        role: "ai",
        text: currentResult.answer,
        status: currentResult.status,
        references: currentResult.references ?? [],
      });
    }

    return msgs;
  };

  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState(buildMessages(result));
  const [selectedArticle, setSelectedArticle] = useState(
    result.references?.[0]?.study ?? result.visualRows?.[0]?.Paper ?? null
  );

  const skipSyncRef = useRef(false);
  const chatContainerRef = useRef(null);

  const hasVisualRows = (result.visualRows ?? []).length > 0;

  const matchedRows = hasVisualRows
    ? result.visualRows
    : result.references?.length
      ? data.filter((row) =>
          result.references.some((ref) => ref.study === row.Study)
        )
      : [];

  const tableColumns = hasVisualRows
    ? result.tableColumns ?? Object.keys(matchedRows[0] ?? {})
    : Object.keys(data[0] ?? {});

  useEffect(() => {
    if (skipSyncRef.current) {
      skipSyncRef.current = false;
      return;
    }

    setMessages(buildMessages(result));
    setSelectedArticle(
      result.references?.[0]?.study ?? result.visualRows?.[0]?.Paper ?? null
    );
  }, [result]);

  useEffect(() => {
    if (!chatContainerRef.current) return;
    chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const submittedQuery = inputValue.trim();

    setMessages((prev) => [
      ...prev,
      { role: "user", text: submittedQuery },
      { role: "ai", text: "Thinking...", status: "thinking" },
    ]);

    skipSyncRef.current = true;
    setInputValue("");

    const result = await onQuerySend(submittedQuery);

    setMessages((prev) => {
      const updated = [...prev];

      updated[updated.length - 1] = {
        role: "ai",
        text: result?.answer ?? "No answer returned.",
        status: result?.status ?? "not_found",
        references: result?.references ?? [],
      };

      return updated;
    });

    setSelectedArticle(
      result?.references?.[0]?.study ?? result?.visualRows?.[0]?.Paper ?? null
    );
  };

  const handleDownloadCSV = () => {
    if (!matchedRows.length || !tableColumns.length) return;

    const csv = [
      tableColumns.map(csvEscape).join(","),
      ...matchedRows.map((row) =>
        tableColumns.map((column) => csvEscape(row[column])).join(",")
      ),
    ].join("\n");

    const element = document.createElement("a");

    element.setAttribute(
      "href",
      "data:text/csv;charset=utf-8," + encodeURIComponent(csv)
    );

    element.setAttribute("download", "sepsis_atlas_matched_results.csv");
    element.style.display = "none";

    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const selectedVisualRow = hasVisualRows
    ? result.visualRows.find((row) => getRowGroupKey(row) === selectedArticle)
    : null;

  const articleDetails = selectedArticle
    ? data.find((entry) => entry.Study === selectedArticle) ??
      buildVisualArticleDetails(selectedVisualRow)
    : null;

  const evidenceCount = hasVisualRows
    ? result.visualRows.length
    : result.references?.length ?? 0;

  return (
    <div className="middle-panel">
      <div className="middle-panel__col middle-panel__col--chat">
        <div style={styles.chatCard(theme)}>
          <h2 style={styles.sectionTitle(theme)}>Article Query</h2>
          <p style={styles.muted(theme)}>
            Ask about the uploaded articles. I will link you directly to the source.
          </p>

          <div ref={chatContainerRef} style={styles.chatContainer}>
            {messages.map((msg, idx) => (
              <div key={idx}>
                <div
                  style={{
                    ...styles.chatMessage,
                    ...(msg.role === "ai"
                      ? styles.chatAI(theme)
                      : styles.chatUser(theme)),
                  }}
                >
                  {msg.text}

                  {msg.role === "ai" && msg.references?.length > 0 ? (
                    <div style={styles.referencesContainer}>
                      <span style={styles.referencesLabel(theme)}>Sources</span>
                      {msg.references.map((ref, refIdx) => (
                        <button
                          key={`${ref.study}-${refIdx}`}
                          onClick={() => setSelectedArticle(ref.study)}
                          style={{
                            ...styles.referenceLink(theme),
                            background:
                              selectedArticle === ref.study
                                ? theme.accent
                                : theme.soft,
                            color:
                              selectedArticle === ref.study
                                ? theme.buttonText
                                : theme.title,
                          }}
                        >
                          {ref.label ?? ref.study} {"->"}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <div style={styles.statusCard(theme)}>
            <div style={styles.statusLabel(theme)}>
              {result.status === "found"
                ? "Matched article evidence"
                : "No article match"}
            </div>
            <div style={styles.statusBody(theme)}>
              {result.status === "found"
                ? hasVisualRows
                  ? `${evidenceCount} extracted evidence rows found. See the Matched Results table below.`
                  : `${evidenceCount} supporting article references found. Click above to view.`
                : "No matching reference was found in the uploaded article set for this question."}
            </div>
          </div>

          <div style={styles.composer}>
            <input
              type="text"
              placeholder="Try a question about the uploaded articles..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              style={styles.input(theme)}
            />

            <button onClick={handleSend} style={styles.sendButton(theme)}>
              Send Question
            </button>
          </div>
        </div>

        <div style={{ ...styles.card(theme), marginTop: "20px" }}>
          <h2 style={styles.sectionTitle(theme)}>Matched Results</h2>

          {result.status === "idle" ? null : matchedRows.length > 0 ? (
            <>
              <div style={styles.tableWrapper}>
                <table style={styles.table(theme)}>
                  <thead>
                    <tr>
                      {tableColumns.map((col) => (
                        <th key={col} style={styles.th(theme)}>
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {matchedRows.map((row, idx) => {
                      const rowGroupKey = getRowGroupKey(row);

                      return (
                        <tr
                          key={row.__row_id ?? `${rowGroupKey}-${idx}`}
                          style={{
                            ...styles.tableRow,
                            backgroundColor:
                              selectedArticle === rowGroupKey
                                ? theme.soft
                                : idx % 2 === 0
                                  ? theme.tableRowAlt ?? theme.soft
                                  : theme.card,
                          }}
                          onClick={() => setSelectedArticle(rowGroupKey)}
                        >
                          {tableColumns.map((column) => (
                            <td key={column} style={styles.td(theme)}>
                              {getCellValue(row[column])}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <button
                onClick={handleDownloadCSV}
                style={styles.downloadButton(theme)}
              >
                Download CSV
              </button>
            </>
          ) : (
            <div style={styles.emptyState(theme)}>
              No extracted results are available because the uploaded articles do not
              support this query.
            </div>
          )}
        </div>
      </div>

      <div className="middle-panel__col">
        <div style={styles.card(theme)}>
          <h2 style={styles.sectionTitle(theme)}>Article Preview</h2>

          {articleDetails ? (
            <>
              <div style={styles.articleHeader(theme)}>
                <h3 style={styles.articleTitle(theme)}>
                  {articleDetails.URL ? (
                    <a
                      href={articleDetails.URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: "inherit",
                        textDecoration: "underline",
                        cursor: "pointer",
                      }}
                    >
                      {articleDetails.Study} ↗
                    </a>
                  ) : (
                    articleDetails.Study
                  )}
                </h3>
                <p style={styles.articleMeta}>
                  {articleDetails.Year ? (
                    <span style={styles.badge(theme)}>{articleDetails.Year}</span>
                  ) : null}
                  {articleDetails.Region ? (
                    <span style={styles.badge(theme)}>
                      {articleDetails.Region}
                    </span>
                  ) : null}
                </p>
              </div>

              <div style={styles.detailsGrid}>
                <div style={styles.detailItem(theme)}>
                  <span style={styles.detailLabel(theme)}>Population</span>
                  <span style={styles.detailValue(theme)}>
                    {articleDetails.Population}
                  </span>
                </div>
                <div style={styles.detailItem(theme)}>
                  <span style={styles.detailLabel(theme)}>Sample Size</span>
                  <span style={styles.detailValue(theme)}>{articleDetails.N}</span>
                </div>
                <div style={styles.detailItem(theme)}>
                  <span style={styles.detailLabel(theme)}>Study Type</span>
                  <span style={styles.detailValue(theme)}>
                    {articleDetails.StudyType ?? "Not provided"}
                  </span>
                </div>
                <div style={styles.detailItem(theme)}>
                  <span style={styles.detailLabel(theme)}>Source</span>
                  <span style={styles.detailValue(theme)}>
                    {articleDetails.Source}
                  </span>
                </div>
              </div>

              <div style={styles.metricsSection}>
                <h4 style={styles.metricsTitle(theme)}>Key Metrics</h4>
                <div style={styles.metricsGrid}>
                  <div style={styles.metricBox(theme)}>
                    <span style={styles.metricLabel(theme)}>SOFA Score</span>
                    <span style={styles.metricBigValue(theme)}>
                      {formatMetric(articleDetails.SOFA)}
                    </span>
                  </div>
                  <div style={styles.metricBox(theme)}>
                    <span style={styles.metricLabel(theme)}>Lactate</span>
                    <span style={styles.metricBigValue(theme)}>
                      {formatMetric(articleDetails.Lactate)}
                    </span>
                  </div>
                  <div style={styles.metricBox(theme)}>
                    <span style={styles.metricLabel(theme)}>Mortality</span>
                    <span style={styles.metricBigValue(theme)}>
                      {formatPercent(articleDetails["28-day Mortality"])}
                    </span>
                  </div>
                  <div style={styles.metricBox(theme)}>
                    <span style={styles.metricLabel(theme)}>
                      Antibiotic Timing
                    </span>
                    <span style={styles.metricBigValue(theme)}>
                      {formatHours(articleDetails["Antibiotic Timing"])}
                    </span>
                  </div>
                </div>
              </div>

              <div style={styles.footerSection(theme)}>
                <div style={styles.confidenceBar}>
                  <span style={styles.confidenceLabel(theme)}>
                    Confidence Score
                  </span>
                  <div style={styles.confidenceDisplay(theme)}>
                    <span style={styles.confidenceValue(theme)}>
                      {articleDetails.Confidence}
                    </span>
                  </div>
                </div>
                <div style={styles.doiSection}>
                  <span style={styles.doiLabel(theme)}>DOI</span>
                  <code style={styles.doiValue(theme)}>
                    {articleDetails.DOI ?? "Not provided"}
                  </code>
                </div>
              </div>

              <div style={styles.highlightBadge(theme)}>
                This article is highlighted in the source evidence
              </div>
            </>
          ) : (
            <div style={styles.emptyArticle(theme)}>
              <p>Select an article from the list to view details</p>
              <p style={styles.smallText(theme)}>
                Click any row in the table or a source link above
              </p>
            </div>
          )}
        </div>
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
  chatCard: (theme) => ({
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
    marginBottom: "8px",
  }),
  muted: (theme) => ({
    color: theme.muted,
    marginBottom: "15px",
    fontSize: "14px",
  }),
  chatContainer: {
    height: "clamp(250px, 35vh, 480px)",
    overflowY: "auto",
    marginBottom: "15px",
    paddingRight: "6px",
  },
  chatMessage: {
    borderRadius: "16px",
    padding: "16px",
    margin: "14px 0",
    maxWidth: "85%",
    whiteSpace: "pre-wrap",
  },
  chatAI: (theme) => ({
    background: theme.soft,
    textAlign: "left",
    color: theme.text,
  }),
  chatUser: (theme) => ({
    background: theme.sourceBg,
    marginLeft: "auto",
    textAlign: "right",
    color: theme.text,
  }),
  referencesContainer: {
    marginTop: "12px",
    paddingTop: "10px",
    borderTop: "1px solid rgba(0,0,0,0.1)",
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
  },
  referencesLabel: (theme) => ({
    width: "100%",
    fontSize: "12px",
    fontWeight: "700",
    color: theme.title,
    textTransform: "uppercase",
  }),
  referenceLink: (theme) => ({
    padding: "8px 12px",
    borderRadius: "8px",
    border: `1px solid ${theme.accent}`,
    background: theme.soft,
    color: theme.title,
    cursor: "pointer",
    fontSize: "12px",
    fontWeight: "600",
  }),
  statusCard: (theme) => ({
    background: theme.soft,
    border: `1px solid ${theme.softBorder}`,
    borderRadius: "16px",
    padding: "14px 16px",
    marginBottom: "15px",
  }),
  statusLabel: (theme) => ({
    color: theme.title,
    fontWeight: "800",
    marginBottom: "6px",
  }),
  statusBody: (theme) => ({
    color: theme.muted,
    lineHeight: "1.5",
  }),
  composer: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  input: (theme) => ({
    width: "100%",
    padding: "12px",
    borderRadius: "8px",
    border: `1px solid ${theme.inputBorder}`,
    fontSize: "14px",
    background: theme.inputBg,
    color: theme.text,
  }),
  sendButton: (theme) => ({
    width: "100%",
    padding: "12px",
    background: theme.accent,
    color: theme.buttonText,
    border: "none",
    borderRadius: "14px",
    fontWeight: "800",
    cursor: "pointer",
  }),
  tableWrapper: {
    overflowX: "auto",
    marginBottom: "15px",
  },
  table: (theme) => ({
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "12px",
    color: theme.text,
  }),
  th: (theme) => ({
    background: theme.tableHeadBg ?? theme.soft,
    padding: "12px",
    textAlign: "left",
    borderBottom: `2px solid ${theme.queryButtonBorder ?? theme.softBorder}`,
    fontWeight: "bold",
    color: theme.queryButtonText ?? theme.text,
    whiteSpace: "nowrap",
  }),
  tableRow: {
    transition: "background-color 0.2s ease",
    cursor: "pointer",
  },
  td: (theme) => ({
    padding: "10px 12px",
    borderBottom: `1px solid ${theme.tableBorder ?? theme.softBorder}`,
    color: theme.text,
    verticalAlign: "top",
  }),
  downloadButton: (theme) => ({
    width: "100%",
    padding: "12px",
    background: theme.accent,
    color: theme.buttonText,
    border: "none",
    borderRadius: "14px",
    fontWeight: "800",
    cursor: "pointer",
  }),
  emptyState: (theme) => ({
    minHeight: "180px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    color: theme.muted,
    background: theme.soft,
    border: `1px dashed ${theme.emptyBorder}`,
    borderRadius: "16px",
    padding: "24px",
    lineHeight: "1.6",
  }),
  articleHeader: (theme) => ({
    marginBottom: "16px",
    paddingBottom: "12px",
    borderBottom: `2px solid ${theme.accent}`,
  }),
  articleTitle: (theme) => ({
    color: theme.title,
    fontSize: "18px",
    fontWeight: "900",
    marginBottom: "8px",
  }),
  articleMeta: {
    display: "flex",
    gap: "8px",
  },
  badge: (theme) => ({
    background: theme.soft,
    border: `1px solid ${theme.accent}`,
    color: theme.title,
    padding: "4px 8px",
    borderRadius: "6px",
    fontSize: "12px",
    fontWeight: "600",
  }),
  detailsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px",
    marginBottom: "16px",
  },
  detailItem: (theme) => ({
    background: theme.sourceBg,
    border: `1px solid ${theme.sourceBorder}`,
    borderRadius: "8px",
    padding: "10px",
  }),
  detailLabel: (theme) => ({
    display: "block",
    fontSize: "11px",
    fontWeight: "700",
    color: theme.title,
    textTransform: "uppercase",
    marginBottom: "4px",
  }),
  detailValue: (theme) => ({
    display: "block",
    fontSize: "13px",
    fontWeight: "600",
    color: theme.text,
  }),
  metricsSection: {
    marginBottom: "16px",
  },
  metricsTitle: (theme) => ({
    fontSize: "14px",
    fontWeight: "700",
    color: theme.title,
    marginBottom: "10px",
    textTransform: "uppercase",
  }),
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
  },
  metricBox: (theme) => ({
    background: theme.soft,
    border: `1px solid ${theme.accent}`,
    borderRadius: "8px",
    padding: "12px",
    textAlign: "center",
  }),
  metricLabel: (theme) => ({
    display: "block",
    fontSize: "11px",
    fontWeight: "700",
    color: theme.title,
    textTransform: "uppercase",
    marginBottom: "4px",
  }),
  metricBigValue: (theme) => ({
    display: "block",
    fontSize: "20px",
    fontWeight: "900",
    color: theme.text,
  }),
  footerSection: (theme) => ({
    marginBottom: "14px",
    paddingBottom: "14px",
    borderBottom: `1px solid ${theme.cardBorder}`,
  }),
  confidenceBar: {
    marginBottom: "10px",
  },
  confidenceLabel: (theme) => ({
    display: "block",
    fontSize: "12px",
    fontWeight: "700",
    color: theme.title,
    marginBottom: "6px",
  }),
  confidenceDisplay: (theme) => ({
    background: theme.soft,
    border: `2px solid ${theme.accent}`,
    borderRadius: "8px",
    padding: "8px",
    textAlign: "center",
  }),
  confidenceValue: (theme) => ({
    fontSize: "16px",
    fontWeight: "900",
    color: theme.title,
  }),
  doiSection: {
    marginTop: "10px",
  },
  doiLabel: (theme) => ({
    display: "block",
    fontSize: "12px",
    fontWeight: "700",
    color: theme.title,
    marginBottom: "4px",
  }),
  doiValue: (theme) => ({
    display: "block",
    fontSize: "11px",
    color: theme.muted,
    background: theme.soft,
    border: `1px solid ${theme.softBorder}`,
    borderRadius: "6px",
    padding: "8px",
    wordBreak: "break-all",
  }),
  highlightBadge: (theme) => ({
    background: theme.soft,
    border: `2px solid ${theme.accent}`,
    borderRadius: "8px",
    padding: "10px",
    textAlign: "center",
    fontSize: "13px",
    fontWeight: "600",
    color: theme.title,
    marginTop: "12px",
  }),
  emptyArticle: (theme) => ({
    minHeight: "400px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    color: theme.muted,
  }),
  smallText: (theme) => ({
    fontSize: "12px",
    color: theme.muted,
    marginTop: "8px",
  }),
};