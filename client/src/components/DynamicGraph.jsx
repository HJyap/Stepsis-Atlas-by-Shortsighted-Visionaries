import { useRef, useEffect, useState } from "react";
import Plotly from "plotly.js-dist-min";

export default function DynamicGraph({ spec }) {
  const containerRef = useRef(null);
  const [renderError, setRenderError] = useState(null);

  useEffect(() => {
    if (!spec?.data || !containerRef.current) return;
    setRenderError(null);
    try {
      Plotly.react(
        containerRef.current,
        spec.data,
        { autosize: true, ...spec.layout },
        { responsive: true, displaylogo: false }
      );
    } catch (e) {
      setRenderError(String(e));
    }
  }, [spec]);

  useEffect(() => {
    return () => {
      if (containerRef.current) Plotly.purge(containerRef.current);
    };
  }, []);

  if (!spec?.data) {
    return <div style={fallbackStyle}>No graph spec provided.</div>;
  }

  if (renderError) {
    return <div style={fallbackStyle}>Failed to render graph: {renderError}</div>;
  }

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}

const fallbackStyle = {
  width: "100%",
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#888",
  fontFamily: "sans-serif",
};