export default function LeftPanel({ onQuerySelect, theme }) {
  const queries = [
    "Initial lactate and 28-day mortality",
    "SOFA score and mortality",
    "Antibiotic timing and survival",
    "Septic shock cohorts",
    "Vitamin D and sepsis mortality",
  ];

  return (
    <div style={styles.card(theme)}>
      <h2 style={styles.sectionTitle(theme)}>Example Queries</h2>
      <div style={styles.buttonContainer}>
        {queries.map((label, idx) => (
          <button
            key={idx}
            onClick={() => onQuerySelect(label)}
            style={styles.queryButton(theme)}
            onMouseEnter={(e) => {
              e.target.style.background = theme.queryButtonHoverBg;
              e.target.style.borderColor = theme.queryButtonHoverBorder;
              e.target.style.color = theme.queryButtonHoverText;
            }}
            onMouseLeave={(e) => {
              e.target.style.background = theme.queryButtonBg;
              e.target.style.borderColor = theme.queryButtonBorder;
              e.target.style.color = theme.queryButtonText;
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <hr style={{ margin: "20px 0", borderColor: theme.queryButtonBorder }} />

      <h3 style={{ color: theme.text, marginBottom: "10px" }}>About Sepsis Atlas</h3>
      <p style={styles.muted(theme)}>AI-powered extraction of clinical evidence from sepsis research.</p>
      <p style={styles.muted(theme)}>Every extracted value is linked back to the exact source in the paper.</p>
      <p style={styles.muted(theme)}>If a question is not supported by the uploaded articles, the interface says so clearly instead of showing fake results.</p>
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
    marginBottom: "8px",
  }),
  buttonContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginTop: "14px",
  },
  queryButton: (theme) => ({
    width: "100%",
    background: theme.queryButtonBg,
    color: theme.queryButtonText,
    border: `1px solid ${theme.queryButtonBorder}`,
    borderRadius: "14px",
    padding: "14px",
    fontWeight: "800",
    cursor: "pointer",
    transition: "all 0.3s ease",
    textAlign: "left",
  }),
  muted: (theme) => ({
    color: theme.muted,
    margin: "8px 0",
  }),
};
