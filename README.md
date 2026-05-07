# Sepsis Atlas by Shortsighted Visionaries

This repository contains a minimal, implementation-ready blueprint for the Sepsis Atlas Hackathon challenge: converting unstructured sepsis papers into structured, verifiable, analysis-ready evidence tables.

## Problem We Solve

Manual literature extraction is too slow and too brittle for high-throughput clinical R&D.  
Our pipeline turns raw PDF studies into harmonized datasets with explicit provenance, so every extracted value can be traced back to source text.

## End-to-End Pipeline

1. **Ingestion**
   - Input: raw study PDFs + metadata (title, DOI, year).
   - Output: immutable document package with checksum.
2. **Parsing & Segmentation**
   - Extract text, tables, figure captions, section boundaries.
   - Preserve page/paragraph coordinates for citation traceability.
3. **Clinical Information Extraction**
   - Identify study characteristics (population, interventions, outcomes).
   - Extract key sepsis variables such as:
     - demographics (age, sex, sample size),
     - severity markers (SOFA/APACHE/lactate),
     - treatment timelines (antibiotic timing, vasopressors),
     - outcomes (28-day mortality, ICU LOS).
4. **Normalization & Harmonization**
   - Standardize units, naming, and time axes across studies.
   - Map synonyms to canonical variables.
5. **Verification Layer (Source Grounding)**
   - Each value stores provenance:
     - document id,
     - page number,
     - text span (start/end offset),
     - extraction confidence.
   - Low-confidence rows are flagged for human review.
6. **Analysis-Ready Output**
   - Produce tidy tables (CSV/Parquet) suitable for downstream stats/ML.
   - Support query-time aggregation across studies.

## Core Data Contract

Minimum row schema for extracted evidence:

| column | description |
|---|---|
| study_id | unique study identifier (e.g., DOI hash) |
| cohort | cohort arm/group label |
| variable_name | canonical variable key (e.g., `initial_lactate_mmol_l`) |
| variable_value | numeric/categorical value |
| unit | normalized unit |
| timepoint | relative timing (e.g., baseline, 6h, day 28) |
| outcome | reported endpoint (if applicable) |
| page | source page in PDF |
| quote | exact supporting text |
| confidence | model confidence score |

## Query-to-Table Behavior

Given a question like:
> “What is the relationship between initial lactate level and 28-day mortality in septic shock?”

the system returns a **structured table**, for example:

| study_id | n | initial_lactate_mmol_l | mortality_28d_pct | effect_measure | page |
|---|---:|---:|---:|---|---:|
| study_A | 164 | 4.8 | 38.4 | OR 1.22 per mmol/L | 6 |
| study_B | 92 | 3.9 | 27.2 | HR 1.15 per mmol/L | 4 |

No free-text-only answer is accepted; every value must be source-grounded.

## Why This Meets the Challenge

- **Automated pipeline construction:** handles PDFs through extraction to standardized dataframes.
- **Direct business relevance:** removes a known evidence-synthesis bottleneck in sepsis R&D.
- **Expert-auditable outputs:** provenance and confidence make outputs verifiable by clinical reviewers.

## Deliverables in Scope

- Reproducible extraction pipeline architecture.
- Standardized evidence table format.
- Citation-grounded outputs suitable for expert audit and downstream analysis.
