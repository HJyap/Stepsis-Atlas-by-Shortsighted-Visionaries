"""
Sepsis Atlas Backend - FastAPI
Multiple endpoints (like your example)
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime

# ============================================
# Initialize FastAPI app
# ============================================
app = FastAPI(
    title="Sepsis Atlas API",
    description="Medical research article analysis API",
    version="1.0.0"
)

# ============================================
# CORS Configuration
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Data Models
# ============================================

class ChatRequest(BaseModel):
    """Chat request"""
    message: str
    session_id: Optional[str] = None

class ApiResponse(BaseModel):
    """Generic API response"""
    data: Any
    ok: bool = True
    error: Optional[str] = None

# ============================================
# Test Data
# ============================================

ARTICLES_DB = [
    {
        "Study": "Smith et al.",
        "Year": 2021,
        "Population": "Septic shock",
        "N": 320,
        "SOFA": 10.2,
        "Lactate": 4.5,
        "28-day Mortality": 38,
        "Source": "Critical Care Medicine",
        "DOI": "10.1234/ccm.2021",
        "Confidence": "88%",
        "Region": "USA",
        "StudyType": "Prospective cohort"
    },
    {
        "Study": "Chen et al.",
        "Year": 2021,
        "Population": "Hospital-acquired sepsis",
        "N": 412,
        "SOFA": 9.1,
        "Lactate": 4.2,
        "28-day Mortality": 34,
        "Source": "Critical Care",
        "DOI": "10.1186/s13054-021",
        "Confidence": "91%",
        "Region": "China",
        "StudyType": "Multicenter cohort"
    },
    {
        "Study": "Garcia et al.",
        "Year": 2020,
        "Population": "Severe sepsis",
        "N": 310,
        "SOFA": 8.0,
        "Lactate": 3.6,
        "28-day Mortality": 25,
        "Source": "Intensive Care",
        "DOI": "10.1234/ic.2020",
        "Confidence": "86%",
        "Region": "Spain",
        "StudyType": "Retrospective cohort"
    },
    {
        "Study": "Patel et al.",
        "Year": 2022,
        "Population": "Septic shock",
        "N": 275,
        "SOFA": 10.0,
        "Lactate": 4.7,
        "28-day Mortality": 38,
        "Source": "Medical ICU",
        "DOI": "10.1234/micu.2022",
        "Confidence": "89%",
        "Region": "India",
        "StudyType": "Prospective observational"
    },
    {
        "Study": "Johnson et al.",
        "Year": 2018,
        "Population": "Severe sepsis",
        "N": 200,
        "SOFA": 7.0,
        "Lactate": 3.3,
        "28-day Mortality": 22,
        "Source": "ICU Research",
        "DOI": "10.1234/icur.2018",
        "Confidence": "84%",
        "Region": "UK",
        "StudyType": "Case series"
    }
]

TEST_RESPONSES = {
    "lactate": {
        "answer": "Initial lactate levels show strong correlation with 28-day mortality.",
        "relevant_articles": ["Smith et al.", "Chen et al.", "Patel et al."],
        "confidence": 91,
        "evidence": "Evidence found in 3 articles."
    },
    "sofa": {
        "answer": "SOFA score is established predictor of mortality in sepsis.",
        "relevant_articles": ["Garcia et al.", "Johnson et al.", "Chen et al."],
        "confidence": 90,
        "evidence": "Evidence found in 3 articles."
    },
    "default": {
        "answer": "Based on sepsis research articles, found relevant information.",
        "relevant_articles": ["Smith et al.", "Chen et al."],
        "confidence": 75,
        "evidence": "General analysis across articles."
    }
}

# ============================================
# Helper Functions
# ============================================

def match_query_to_response(message: str) -> Dict[str, Any]:
    """Match query to test response"""
    q = message.lower()
    if "lactate" in q:
        return TEST_RESPONSES["lactate"]
    elif "sofa" in q:
        return TEST_RESPONSES["sofa"]
    else:
        return TEST_RESPONSES["default"]

# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/")
def root():
    """Health check"""
    return {
        "message": "Sepsis Atlas API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ============================================
# CHAT ENDPOINTS
# ============================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint - main AI interaction"""
    session_id = request.session_id or str(uuid.uuid4())
    response_data = match_query_to_response(request.message)

    return {
        "session_id": session_id,
        "response": response_data["answer"],
        "relevant_articles": response_data["relevant_articles"],
        "confidence": response_data["confidence"],
        "evidence": response_data["evidence"],
        "token_usage": {"input_tokens": 100, "output_tokens": 150},
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# ARTICLES ENDPOINTS
# ============================================

@app.get("/api/articles")
def get_all_articles():
    """Get all articles"""
    return ApiResponse(data=ARTICLES_DB, ok=True)

@app.get("/api/articles/{article_id}")
def get_article(article_id: str):
    """Get specific article by Study name"""
    article = next((a for a in ARTICLES_DB if a["Study"] == article_id), None)
    
    if not article:
        return ApiResponse(data=None, ok=False, error=f"Article '{article_id}' not found")
    
    return ApiResponse(data=article, ok=True)

@app.get("/api/articles/count")
def count_articles():
    """Get total count of articles"""
    return ApiResponse(
        data={"total": len(ARTICLES_DB), "articles": ARTICLES_DB},
        ok=True
    )

@app.get("/api/articles/by-year/{year}")
def get_articles_by_year(year: int):
    """Get articles from specific year"""
    articles = [a for a in ARTICLES_DB if a["Year"] == year]
    return ApiResponse(data=articles, ok=True)

@app.get("/api/articles/by-region/{region}")
def get_articles_by_region(region: str):
    """Get articles by region"""
    articles = [a for a in ARTICLES_DB if a.get("Region") == region]
    return ApiResponse(data=articles, ok=True)

@app.get("/api/articles/search")
def search_articles(query: str = Query(...)):
    """Search articles by keyword"""
    q = query.lower()
    results = []
    
    for article in ARTICLES_DB:
        found = False
        for value in article.values():
            if q in str(value).lower():
                found = True
                break
        if found:
            results.append(article)
    
    return ApiResponse(data=results, ok=True)

# ============================================
# STATISTICS ENDPOINTS
# ============================================

@app.get("/api/stats/all")
def get_all_statistics():
    """Get all statistics"""
    if not ARTICLES_DB:
        return ApiResponse(data=None, ok=False, error="No articles found")
    
    mortalities = [a["28-day Mortality"] for a in ARTICLES_DB]
    sofas = [a["SOFA"] for a in ARTICLES_DB]
    lactates = [a["Lactate"] for a in ARTICLES_DB]
    
    return ApiResponse(
        data={
            "total_articles": len(ARTICLES_DB),
            "total_patients": sum(a["N"] for a in ARTICLES_DB),
            "mortality": {
                "mean": round(sum(mortalities) / len(mortalities), 2),
                "min": min(mortalities),
                "max": max(mortalities)
            },
            "sofa": {
                "mean": round(sum(sofas) / len(sofas), 2),
                "min": min(sofas),
                "max": max(sofas)
            },
            "lactate": {
                "mean": round(sum(lactates) / len(lactates), 2),
                "min": min(lactates),
                "max": max(lactates)
            }
        },
        ok=True
    )

@app.get("/api/stats/mortality")
def get_mortality_stats():
    """Get mortality statistics"""
    mortalities = [a["28-day Mortality"] for a in ARTICLES_DB]
    
    return ApiResponse(
        data={
            "mean": round(sum(mortalities) / len(mortalities), 2),
            "min": min(mortalities),
            "max": max(mortalities),
            "values": mortalities
        },
        ok=True
    )

@app.get("/api/stats/sofa")
def get_sofa_stats():
    """Get SOFA statistics"""
    sofas = [a["SOFA"] for a in ARTICLES_DB]
    
    return ApiResponse(
        data={
            "mean": round(sum(sofas) / len(sofas), 2),
            "min": min(sofas),
            "max": max(sofas),
            "values": sofas
        },
        ok=True
    )

@app.get("/api/stats/lactate")
def get_lactate_stats():
    """Get lactate statistics"""
    lactates = [a["Lactate"] for a in ARTICLES_DB]
    
    return ApiResponse(
        data={
            "mean": round(sum(lactates) / len(lactates), 2),
            "min": min(lactates),
            "max": max(lactates),
            "values": lactates
        },
        ok=True
    )

@app.get("/api/stats/correlation")
def get_correlation(metric1: str = Query("SOFA"), metric2: str = Query("Lactate")):
    """Get correlation between two metrics"""
    valid_metrics = ["SOFA", "Lactate", "28-day Mortality", "N"]
    
    if metric1 not in valid_metrics or metric2 not in valid_metrics:
        return ApiResponse(data=None, ok=False, error=f"Invalid metric")
    
    values1 = [a[metric1] for a in ARTICLES_DB]
    values2 = [a[metric2] for a in ARTICLES_DB]
    
    n = len(values1)
    mean1 = sum(values1) / n
    mean2 = sum(values2) / n
    
    numerator = sum((values1[i] - mean1) * (values2[i] - mean2) for i in range(n))
    denominator = (sum((v - mean1)**2 for v in values1) * sum((v - mean2)**2 for v in values2))**0.5
    
    correlation = round(numerator / denominator, 2) if denominator > 0 else 0
    
    return ApiResponse(
        data={"metric1": metric1, "metric2": metric2, "correlation": correlation},
        ok=True
    )

# ============================================
# DATA ENDPOINTS
# ============================================

@app.get("/api/data/export/json")
def export_json():
    """Export data as JSON"""
    return ApiResponse(data=ARTICLES_DB, ok=True)

@app.get("/api/data/export/csv")
def export_csv():
    """Export data as CSV"""
    if not ARTICLES_DB:
        return ApiResponse(data=None, ok=False, error="No data to export")
    
    keys = ARTICLES_DB[0].keys()
    csv_data = ",".join(keys) + "\n"
    for article in ARTICLES_DB:
        csv_data += ",".join(str(article[k]) for k in keys) + "\n"
    
    return ApiResponse(data=csv_data, ok=True)

@app.get("/api/data/filter")
def filter_data(field: str = Query(...), operator: str = Query(...), value: str = Query(...)):
    """Filter data by field and operator"""
    results = []
    
    for article in ARTICLES_DB:
        if field not in article:
            continue
        
        article_value = article[field]
        
        try:
            if isinstance(article_value, (int, float)):
                compare_value = float(value)
            else:
                compare_value = value
            
            match = False
            if operator == "eq" and article_value == compare_value:
                match = True
            elif operator == "gt" and article_value > compare_value:
                match = True
            elif operator == "lt" and article_value < compare_value:
                match = True
            
            if match:
                results.append(article)
        except (ValueError, TypeError):
            continue
    
    return ApiResponse(data=results, ok=True)

# ============================================
# CONFIG ENDPOINTS
# ============================================

@app.get("/api/config/metrics")
def get_metrics():
    """Get available metrics"""
    return ApiResponse(
        data=["SOFA", "Lactate", "28-day Mortality", "N"],
        ok=True
    )

@app.get("/api/config/regions")
def get_regions():
    """Get available regions"""
    regions = sorted(list(set(a.get("Region") for a in ARTICLES_DB if a.get("Region"))))
    return ApiResponse(data=regions, ok=True)

@app.get("/api/config/years")
def get_years():
    """Get available years"""
    years = sorted(list(set(a["Year"] for a in ARTICLES_DB)))
    return ApiResponse(data=years, ok=True)

@app.get("/api/config/populations")
def get_populations():
    """Get available populations"""
    populations = sorted(list(set(a["Population"] for a in ARTICLES_DB)))
    return ApiResponse(data=populations, ok=True)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)