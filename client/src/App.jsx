import React from "react";
import { sepsisData } from "./data";
import { articleResults, getArticleResultFromQuery } from "./testData";
import LeftPanel from "./components/LeftPanel";
import MiddlePanel from "./components/MiddlePanel";
import RightPanel from "./components/RightPanel";
import "./style.css";

const themes = {
  light: {
    background: "linear-gradient(135deg, #f7fbff 0%, #eef8fb 100%)",
    text: "#08204a",
    title: "#0f766e",
    card: "#ffffff",
    cardBorder: "#dbeafe",
    cardShadow: "0 12px 35px rgba(2,132,199,0.08)",
    muted: "#55708f",
    soft: "#f8fafc",
    softBorder: "#dbeafe",
    emptyBorder: "#bfdbfe",
    inputBg: "#ffffff",
    inputBorder: "#d1d5db",
    accent: "#0ea5a4",
    buttonText: "#ffffff",
    queryButtonBg: "#ffffff",
    queryButtonBorder: "#bfdbfe",
    queryButtonText: "#0f3d75",
    queryButtonHoverBg: "#ecfeff",
    queryButtonHoverBorder: "#5eead4",
    queryButtonHoverText: "#0f766e",
    tableHeadBg: "#f0f9ff",
    tableRowAlt: "#f8fbff",
    tableBorder: "#e0f2fe",
    sourceBg: "#f0fdfa",
    sourceBorder: "#99f6e4",
  },
  dark: {
    background:
      "linear-gradient(180deg, #14110c 0%, #0b0a08 55%, #080808 100%)",
    text: "#f7f2e7",
    title: "#e0b13f",
    card: "rgba(19, 16, 12, 0.92)",
    cardBorder: "#4a3920",
    cardShadow: "0 18px 40px rgba(0,0,0,0.45)",
    muted: "#b8b0a1",
    soft: "#16120d",
    softBorder: "#56411f",
    emptyBorder: "#6e5526",
    inputBg: "#0f0d0a",
    inputBorder: "#6b5222",
    accent: "#e0b13f",
    buttonText: "#16110a",
    queryButtonBg: "#12100d",
    queryButtonBorder: "#5b4620",
    queryButtonText: "#f4ecdc",
    queryButtonHoverBg: "#1a1510",
    queryButtonHoverBorder: "#e0b13f",
    queryButtonHoverText: "#e0b13f",
    tableHeadBg: "#1a1510",
    tableRowAlt: "#110e0b",
    tableBorder: "#43331c",
    sourceBg: "#15110c",
    sourceBorder: "#7b5c20",
    chartGrid: "rgba(224, 177, 63, 0.14)",
    chartAxis: "#f4ecdc",
  },
};

export default function App() {
  const [activeResult, setActiveResult] = React.useState(
    articleResults.lactate_mortality
  );
  const [themeName, setThemeName] = React.useState("light");
  const theme = themes[themeName];

  const handleQuerySelect = (queryKey) => {
    setActiveResult(articleResults[queryKey] ?? articleResults.not_found);
  };

  const handleQuerySend = (query) => {
    setActiveResult(getArticleResultFromQuery(query));
  };

  return (
    <div
      data-theme={themeName}
      className="app-container"
      style={styles.container(theme, themeName === "dark")}
    >
      <div style={styles.header}>
        <h1 style={styles.title(theme)}>Sepsis Atlas</h1>
        <button
          type="button"
          onClick={() =>
            setThemeName((current) => (current === "light" ? "dark" : "light"))
          }
          style={styles.themeToggle(theme)}
        >
          {themeName === "light" ? "Dark Mode" : "Light Mode"}
        </button>
      </div>

      <div className="app-layout">
        <div className="app-column">
          <LeftPanel onQuerySelect={handleQuerySelect} theme={theme} />
        </div>

        <div className="app-column">
          <MiddlePanel
            data={sepsisData}
            result={activeResult}
            onQuerySend={handleQuerySend}
            theme={theme}
          />
        </div>

        <div className="app-column">
          <RightPanel data={sepsisData} result={activeResult} theme={theme} />
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: (theme, isDark) => ({
    background: theme.background,
    backgroundImage: isDark
      ? "linear-gradient(rgba(224, 177, 63, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(224, 177, 63, 0.06) 1px, transparent 1px), linear-gradient(180deg, #14110c 0%, #0b0a08 55%, #080808 100%)"
      : theme.background,
    backgroundSize: isDark ? "52px 52px, 52px 52px, auto" : "auto",
    minHeight: "100vh",
    color: theme.text,
    margin: 0,
    width: "100%",
    transition: "background 0.2s ease, color 0.2s ease",
  }),
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "16px",
    marginBottom: "30px",
    flexWrap: "wrap",
  },
  title: (theme) => ({
    color: theme.title,
    fontSize: "32px",
    fontWeight: "bold",
    margin: 0,
  }),
  themeToggle: (theme) => ({
    background: theme.accent,
    color: theme.buttonText,
    border: "none",
    borderRadius: "999px",
    padding: "12px 18px",
    fontWeight: "800",
    cursor: "pointer",
  }),
};
