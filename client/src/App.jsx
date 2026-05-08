import React from "react";
import { sepsisData } from "./data";
import { sendChatMessage } from "./services/api";
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

const VISUAL_TABLE_COLUMNS = [
  "Paper",
  "Record Type",
  "Cohort ID",
  "DOI",
  "Encounter Period",
  "Location",
  "Data Set",
  "Study Design",
  "Population",
  "Cohort",
  "Cohort Size",
  "Cohort Characteristics",
  "Mortality Rate",
  "Mortality Timepoint",
  "Predictors",
  "Predictor Timing",
  "Outcome",
  "Model / Analysis",
  "Effect / Performance",
  "Confidence Score",
];

const NOT_FOUND = {
  status: "not_found",
  query: "",
  answer: "Could not reach the server.",
  references: [],
  visualRows: [],
  tableColumns: VISUAL_TABLE_COLUMNS,
};

function valueOrBlank(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") return "";

  if (typeof value === "number") {
    if (value <= 1) return `${Math.round(value * 100)}%`;
    return `${value}%`;
  }

  return String(value);
}

function getRecordConfidence(record, fallbackConfidence) {
  return formatConfidence(
    record?.confidence_score ??
      record?.confidenceScore ??
      record?.confidence ??
      fallbackConfidence ??
      ""
  );
}

function flattenVisualExtracts(visualExtracts, fallbackConfidence = "") {
  const rows = [];

  Object.entries(visualExtracts ?? {}).forEach(([paperName, paperExtract]) => {
    const cohortRecords = Array.isArray(
      paperExtract?.study_cohort_level_records
    )
      ? paperExtract.study_cohort_level_records
      : [];

    const predictorRecords = Array.isArray(
      paperExtract?.predictor_model_level_records
    )
      ? paperExtract.predictor_model_level_records
      : [];

    const cohortById = new Map();

    cohortRecords.forEach((record) => {
      if (record?.cohort_id) {
        cohortById.set(record.cohort_id, record);
      }
    });

    cohortRecords.forEach((record, index) => {
      rows.push({
        __row_id: `${paperName}-cohort-${index}`,
        Paper: valueOrBlank(record.papers || paperName),
        "Record Type": "Study/Cohort",
        "Cohort ID": valueOrBlank(record.cohort_id),
        DOI: valueOrBlank(record.doi),
        "Encounter Period": valueOrBlank(record.encounters_period),
        Location: valueOrBlank(record.population_location),
        "Data Set": valueOrBlank(record.data_sets),
        "Study Design": valueOrBlank(record.detailed_study_design_description),
        Population: valueOrBlank(record.population_description),
        Cohort: valueOrBlank(record.cohort),
        "Cohort Size": valueOrBlank(record.cohort_size_n),
        "Cohort Characteristics": valueOrBlank(record.cohort_characteristics),
        "Mortality Rate": valueOrBlank(record.mortality_rate_percent),
        "Mortality Timepoint": valueOrBlank(record.mortality_timepoint),
        Predictors: "",
        "Predictor Timing": "",
        Outcome: "",
        "Model / Analysis": "",
        "Effect / Performance": "",
        "Confidence Score": getRecordConfidence(record, fallbackConfidence),
      });
    });

    predictorRecords.forEach((record, index) => {
      const cohortContext = cohortById.get(record?.cohort_id) ?? {};

      rows.push({
        __row_id: `${paperName}-predictor-${index}`,
        Paper: valueOrBlank(cohortContext.papers || paperName),
        "Record Type": "Predictor/Model",
        "Cohort ID": valueOrBlank(record.cohort_id),
        DOI: valueOrBlank(cohortContext.doi),
        "Encounter Period": valueOrBlank(cohortContext.encounters_period),
        Location: valueOrBlank(cohortContext.population_location),
        "Data Set": valueOrBlank(cohortContext.data_sets),
        "Study Design": valueOrBlank(
          cohortContext.detailed_study_design_description
        ),
        Population: valueOrBlank(cohortContext.population_description),
        Cohort: valueOrBlank(cohortContext.cohort),
        "Cohort Size": valueOrBlank(cohortContext.cohort_size_n),
        "Cohort Characteristics": valueOrBlank(
          cohortContext.cohort_characteristics
        ),
        "Mortality Rate": valueOrBlank(cohortContext.mortality_rate_percent),
        "Mortality Timepoint": valueOrBlank(
          cohortContext.mortality_timepoint
        ),
        Predictors: valueOrBlank(record.predictors),
        "Predictor Timing": valueOrBlank(
          record.timing_of_predictor_measurement
        ),
        Outcome: valueOrBlank(record.outcome),
        "Model / Analysis": valueOrBlank(record.model_specification),
        "Effect / Performance": valueOrBlank(
          record.effect_size_performance_and_significance
        ),
        "Confidence Score": getRecordConfidence(record, fallbackConfidence),
      });
    });
  });

  return rows;
}

function buildVisualReferences(visualRows) {
  const referencesByPaper = new Map();

  visualRows.forEach((row) => {
    const paper = row.Paper || "Extracted paper";

    if (referencesByPaper.has(paper)) return;

    referencesByPaper.set(paper, {
      study: paper,
      label: paper,
      source: row["Record Type"] || "Visual extraction output",
      excerpt:
        row["Effect / Performance"] ||
        row.Population ||
        row["Cohort Characteristics"] ||
        "Visual extraction record from uploaded article.",
      confidence: row["Confidence Score"] || "",
    });
  });

  return Array.from(referencesByPaper.values());
}

function buildReferences(matchedStudies) {
  return (matchedStudies ?? [])
    .map(({ study, excerpt }) => {
      const entry = sepsisData.find((d) => d.Study === study);

      return {
        study,
        label: study,
        year: entry?.Year ?? "",
        population: entry?.Population ?? "",
        source: entry?.Source ?? "",
        excerpt: excerpt ?? "",
        lactate: entry?.Lactate ?? null,
        mortality: entry?.["28-day Mortality"] ?? null,
        confidence: entry?.Confidence ?? "",
      };
    })
    .filter((r) => r.study);
}

async function callChat(query) {
  try {
    const data = await sendChatMessage(query);

    const visualRows = flattenVisualExtracts(
      data.visual_extracts,
      data.confidence_score
    );

    const references = visualRows.length
      ? buildVisualReferences(visualRows)
      : buildReferences(data.matched_studies);

    const serverSucceeded = data.status === "success" || data.status === "found";

    return {
      status: serverSucceeded ? "found" : "not_found",
      query,
      answer:
        data.llm_answer ??
        data.answer ??
        data.error ??
        "No answer returned.",
      references,
      visualRows,
      tableColumns: VISUAL_TABLE_COLUMNS,
      rawVisualExtracts: data.visual_extracts ?? {},
      confidenceScore: data.confidence_score ?? "",
    };
  } catch (error) {
    return {
      ...NOT_FOUND,
      query,
      answer: error.message || "Could not reach the server.",
    };
  }
}

export default function App() {
  const [activeResult, setActiveResult] = React.useState({
    status: "idle",
    query: "",
    answer: "",
    references: [],
    visualRows: [],
    tableColumns: VISUAL_TABLE_COLUMNS,
  });

  const [themeName, setThemeName] = React.useState("light");
  const theme = themes[themeName];

  const handleQuerySelect = async (label) => {
    const result = await callChat(label);
    setActiveResult(result);
  };

  const handleQuerySend = async (query) => {
    const result = await callChat(query);
    setActiveResult(result);
    return result;
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
    minHeight: "100dvh",
    color: theme.text,
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