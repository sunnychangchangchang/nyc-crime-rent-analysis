# NYC Rent & Crime Analysis Dashboard

**Interactive Data Science Project | Python, Dash, Plotly, Pandas**

This project analyzes the relationship between **housing affordability and crime patterns in New York City** from 2015 to 2024.  It combines exploratory data analysis, geospatial visualization, and an interactive dashboard to support data-driven urban insights.



## 📌 Project Overview

- **Objective:**  
  Examine how crime severity relates to median rent levels across NYC neighborhoods, precincts, and ZIP codes.

- **Key Questions:**
  - How do crime trends evolve over time by category?
  - Are higher-rent areas associated with lower crime severity?
  - Which precincts exhibit disproportionately high crime relative to rent?
  - How does accessibility to amenities vary by ZIP code?

- **Outcome:**  
  A fully interactive **Dash dashboard** that allows users to explore trends across **time, geography, crime category, and area**.



## 🎥 Dashboard Demo

> The GIF below demonstrates real-time interaction, filtering, and map exploration.

![Dashboard Demo](https://raw.githubusercontent.com/sunnychangchangchang/nyc-crime-rent-analysis/master/assets/screenshots/dashboard_demo.gif)

## ✨ Key Features

### 1. Interactive EDA Dashboard
- Dynamic filtering by:
  - Date range
  - Crime category (Felony / Misdemeanor / Violation)
  - Geographic area
- Responsive multi-panel layout with synchronized updates

### 2. Advanced Visual Analytics
- Time series analysis of crime and rent trends
- Box plots for rent distribution by borough
- Heatmaps for crime-to-rent “Danger Ratio”
- Scatter analysis of crime vs. housing cost
- Choropleth map of median rent by ZIP code

### 3. Geospatial Map Explorer
- ZIP-based search with:
  - Nearby amenities (supermarkets, hospitals, transit, parks, etc.)
  - Walking-time distance filtering
- Google Maps APIs integration (Geocoding, Places, Distance Matrix)



## Methodology
### Danger Ratio (Core Metric)

To normalize crime intensity by cost of living, a **Danger Ratio** is defined as:

**Danger Ratio = Weighted Crime Count / Median Rent**

**Crime Severity Weights**
- Felony: 3  
- Misdemeanor: 2  
- Violation: 1  

This metric captures relative crime exposure per dollar of rent, enabling
a normalized comparison of safety versus housing cost across NYC areas.



## 🛠️ Tech Stack

**Languages & Libraries**
- Python
- Pandas, NumPy
- Plotly, Dash
- Dash Leaflet
- Google Maps APIs

**Visualization**
- Interactive dashboards (Dash)
- Geospatial mapping
- Time series & distribution analysis




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
```


## 📄 Report

A full written analysis is available here: [NYC_Rent_Crime_Analysis_Report (PDF)](assets/Sunny_Chang_Final_Report_FRE6191.pdf)



## 🔗 Related Work

This project has a complementary visualization-focused implementation using **D3.js**:

- **NYC Rent & Crime Analysis (D3 / Observable)**  
  [Link to Observable notebook](https://observablehq.com/@nyuinfovis/nye-crime-rent-analysis)

The two projects use the **same dataset and research question**, but differ in:
- **This repo:** Data science workflow, analytics, dashboard engineering  
- **Observable project:** Custom visual encoding and front-end visualization design


## 🚀 Running the Dashboard Locally

To run the interactive dashboard on your local machine:

```bash
git clone https://github.com/your-username/nyc-rent-crime-analysis.git
cd nyc-rent-crime-analysis
pip install -r requirements.txt
python app.py
```

Then open your browser at:
```text
http://localhost:8054
```

> Note: Google Maps functionality requires a valid API key with Geocoding, Places, and Distance Matrix APIs enabled.


## Author

**Sunny Chang**  
Data Science | Analytics | Visualization  

If you have feedback or would like to discuss this project, feel free to reach out.
