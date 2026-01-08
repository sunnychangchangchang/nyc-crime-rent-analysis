# NYC Rent & Crime Analysis Dashboard

An end-to-end **data science project** analyzing the relationship between **housing costs and crime patterns in New York City**, combining data cleaning, feature engineering, exploratory analysis, and an interactive dashboard built with Dash.

This project emphasizes **analytical thinking, metric design, and insight communication**, rather than pure web development.

---

## 🎥 Interactive Dashboard Demo

![Dashboard Demo](assets/screenshots/dashboard_demo.gif)

> The dashboard allows users to explore crime trends, rent distributions, and a custom-designed **Danger Ratio** metric across time, geography, and crime categories.

---

## 📌 Project Motivation

New York City presents significant variation in both rental prices and crime intensity.  
This project aims to answer questions such as:

- How do crime levels evolve over time across different precincts?
- Is higher rent always associated with lower crime?
- Which areas show disproportionately high crime relative to housing cost?
- How does this relationship change over time?

The goal is to **transform raw public data into interpretable metrics and actionable insights**.

---

## 📊 Key Features

- **Custom Danger Ratio Metric**  
  \[
  \text{Danger Ratio} = \frac{\text{Weighted Crime Count}}{\text{Median Rent}}
  \]
  - FELONY = 3  
  - MISDEMEANOR = 2  
  - VIOLATION = 1  

- **Interactive EDA Dashboard (Dash)**
  - Crime trends over time
  - Crime vs. rent scatter analysis
  - Rent distribution by borough
  - Heatmaps of danger ratio by area and month
  - Choropleth map of latest median rent by ZIP code

- **Geospatial Analysis**
  - ZIP-code-level aggregation
  - Precinct-level comparisons
  - Map-based exploration

- **Reproducible Analysis Notebook**
  - Data cleaning & preprocessing
  - Feature engineering
  - Aggregation logic validation

---

## 🧠 Analytical Focus (What This Project Demonstrates)

- Data cleaning and normalization across heterogeneous sources
- Metric design for combining socioeconomic and crime data
- Time-series aggregation and comparison
- Geospatial reasoning (ZIP, precinct, borough levels)
- Translating analysis into **decision-friendly visualizations**

This project was designed to reflect **real-world data science workflows**, not classroom-only exercises.

---

## 🗂 Repository Structure

```text
.
├── app.py                         # Dash dashboard application
├── nyc-rent-crime-analysis.ipynb  # EDA & data processing notebook
├── NYC_Rent_Crime_Analysis_Report.pdf       # Full written analysis & methodology
├── assets/
│   └── screenshots/
│       ├── dashboard_demo.gif
│       ├── dashboard_overview.png
│       ├── map_explorer.png
│       └── danger_ratio_heatmap.png