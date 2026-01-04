import dash
from dash import html, dcc, Input, Output, State
import dash_leaflet as dl
from dash_leaflet import CircleMarker
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os # Import os module to check for assets folder


# Load cleaned data
try:
    # Use parse_dates directly in read_csv for efficiency
    merged_df = pd.read_csv("data/nyc_rent&crime_2015_to_recent.csv", parse_dates=["date"])
    # Safely evaluate the ZIP Codes column, handling potential NaNs or non-string types before eval
    # Also convert resulting list elements to strings to avoid potential issues later
    merged_df["ZIP Codes"] = merged_df["ZIP Codes"].apply(lambda x: [str(z) for z in eval(x)] if isinstance(x, str) else [])
    # Ensure date column is explicitly datetime, although parse_dates should handle this
    merged_df["date"] = pd.to_datetime(merged_df["date"])
    print("Data loaded successfully.")
except FileNotFoundError:
    print("Error: data/nyc_rent&crime_2015_to_recent.csv not found.")
    # Create an empty DataFrame to allow the app to start, albeit without data
    merged_df = pd.DataFrame({
        "index": [], "addr_pct_cd": [], "date": [], "law_cat_cd": [], "count": [],
        "precinct_area": [], "areaName": [], "Borough": [], "areaType": [],
        "median_rent": [], "Neighborhood": [], "ZIP Codes": [], "danger_ratio": []
    })
except Exception as e:
    print(f"Error loading or processing data file: {e}")
    # Create an empty DataFrame on other errors
    merged_df = pd.DataFrame({
        "index": [], "addr_pct_cd": [], "date": [], "law_cat_cd": [], "count": [],
        "precinct_area": [], "areaName": [], "Borough": [], "areaType": [],
        "median_rent": [], "Neighborhood": [], "ZIP Codes": [], "danger_ratio": []
    })


# --- Integrated Dash Application with Charts ---
# Total Charts/Components: 1 Map Explorer + 9 EDA Charts = 10
#
# Map Explorer:
# 1. Map: Display area data based on ZIP Code + Search for nearby places (like supermarkets) with color-coded markers
#
# EDA Charts (Triggered by "Update Charts" button, Filterable by Date Range and/or Crime Category, Area Name for Chart 8):
# 2. Crime vs Rent Scatter Plot (Crime Count) - Filterable by Date Range & Category
# 3. Bar Plot by Precinct (Crime Count) - Filterable by Date Range & Category
# 4. Crime Count over Time (Monthly Trend by Category) - Filterable by Date Range & Category
# 5. Box Plot: Rent Distribution by Borough - Filterable by Date Range
# 6. Heatmap: Crime-to-Rent Ratio (Danger Index) - Filterable by Date Range
# 7. NEW: Bar Plot: Average Danger Ratio by Precinct Area - Filterable by Date Range
# 8. NEW: Scatter Plot: Median Rent vs. Average Danger Ratio - Filterable by Date Range
# 9. NEW: Line Plot: Average Danger Ratio Trend (Overall or by Area) - Filterable by Date Range & Area Name
# 10. Choropleth: Latest Median Rent by ZIP Code - Filterable by Date Range (uses data across all categories)

# Initialize Dash app - Dash automatically looks for assets folder
# Dash reads CSS files from the 'assets' folder automatically when the app is initialized.
# You don't need to explicitly import or load them in the Python code.
# Just place your style.css file inside the 'assets' folder.
app = dash.Dash(__name__)
app.title = "NYC Rent & Crime Dashboard"
server = app.server # Expose server for production deployment

# === IMPORTANT: Replace "XX" with your actual Google API Key ===
# Ensure the following Google APIs are enabled for your key:
# 1. Geocoding API
# 2. Places API
# 3. Distance Matrix API
# Check your Google Cloud Console for API restrictions and billing setup.
GOOGLE_API_KEY = "AIzaSyAYGK5ln7RhqgcViyZqEUcLoIXLLeFeFtM"

# Define colors for different place types
PLACE_COLORS = {
    "supermarket": "blue",
    "hospital": "red",
    "subway_station": "orange",
    "park": "green",
    "school": "purple",
    "library": "brown"
}

# Determine min and max dates for the date picker (handle empty dataframe case)
if not merged_df.empty:
    min_date_available = merged_df["date"].min().date()
    max_date_available = merged_df["date"].max().date()
    # Get unique area names for the dropdown
    area_names = sorted(merged_df['areaName'].unique()) # Sort for professional look
    area_dropdown_options = [{'label': 'Overall NYC', 'value': 'Overall'}] + [{'label': area, 'value': area} for area in area_names if pd.notnull(area)]
else:
    # Default dates if data loading fails or df is empty
    min_date_available = date(2015, 1, 1)
    max_date_available = date.today()
    area_dropdown_options = [{'label': 'Overall NYC', 'value': 'Overall'}]


# === Layout ===
app.layout = html.Div([
    # html.H1("📍 NYC Rent & Crime Explorer", style={"textAlign": "center", "color": "#333", "margin-bottom": "20px"}), # Removed padding-top as it's in CSS
    # Container for Title and Author to align them vertically
        html.Div([
            html.H1("📍 NYC Rent & Crime Explorer", style={"textAlign": "center", "color": "#333", "margin-bottom": "0"}), # Remove bottom margin from H1
            html.P("Made by Sunny", style={"textAlign": "center", "color": "#555", "font-size": "0.9em", "margin-top": "5px"}) # Add author info
        ], style={"display": "flex", "flex-direction": "column", "align-items": "center", "justify-content": "center"}),
        html.Div([
            html.A(
                "📄 View Final Report (PDF)",
                href="/assets/Sunny_Chang_Final_Report_FRE6191.pdf",
                target="_blank",
                style={
                    "textDecoration": "none",
                    "color": "white",
                    "backgroundColor": "#1f77b4",
                    "padding": "10px 20px",
                    "borderRadius": "5px",
                    "display": "inline-block",
                    "fontWeight": "bold"
                }
            )
        ], style={"marginBottom": "30px"}),
    dcc.Tabs(id="main-tabs", value="tab-map", children=[
        dcc.Tab(label="📌 Map Explorer", value="tab-map", children=[
            html.Div([
                dcc.Input(id="zip_input", type="text", placeholder="Enter ZIP...", debounce=True,
                          style={"padding": "10px", "border-radius": "5px", "border": "1px solid #ccc", "flex-grow": 1, "min-width": "120px"}),
                dcc.Dropdown(id="travel_dropdown", value=15, clearable=False,
                             options=[{"label": f"{i} min walk", "value": i} for i in range(5, 61, 5)],
                             style={"width": "180px", "padding": "0 10px", "flex-shrink": 0}),
                dcc.Dropdown(id="place_type", value=["supermarket"], multi=True,
                             options=[{"label": x.replace('_', ' ').title(), "value": x}
                                      for x in PLACE_COLORS.keys()],
                             style={"width": "280px", "flex-shrink": 0}),
                html.Button("Search", id="search_btn", n_clicks=0,
                            style={"padding": "10px 20px", "background-color": "#007bff", "color": "white", "border": "none", "border-radius": "5px", "cursor": "pointer", "flex-shrink": 0})
            ], style={"display": "flex", "gap": "10px", "padding": "15px", "justify-content": "center", "flex-wrap": "wrap", "background-color": "#f9f9f9", "border-bottom": "1px solid #eee"}),

            # POI Color Legend
            html.Div([
                html.Span("POI Colors:", style={"margin-right": "10px", "font-weight": "bold"}),
                *[html.Span(f" {place.replace('_', ' ').title()} ",
                             style={"background-color": color, "color": "white" if color in ["blue", "red", "purple", "brown"] else "black",
                                    "padding": "3px 8px", "margin-right": "8px", "border-radius": "3px", "font-size": "0.9em", "display": "inline-block"})
                  for place, color in PLACE_COLORS.items()]
            ], style={"textAlign": "center", "margin": "15px 0"}),


            html.Div(id="info_output"), # Removed inline style, moved to CSS
            dl.Map(id="map", center=[40.73, -73.94], zoom=12, children=[
                dl.TileLayer(),
                dl.LayerGroup(id="marker_layer")
            ], style={'width': '100%', 'height': '650px', 'margin': '20px auto', 'border-radius': '5px', 'border': '1px solid #ccc'})
        ]),

        dcc.Tab(label="📊 EDA Dashboard", value="tab-eda", children=[
            html.Div([ # EDA Controls and Filters
                html.Div([ # Container for Crime Category Dropdown
                    html.Label("Select Crime Category:", style={"margin-right": "10px", "font-weight": "bold"}),
                    dcc.Dropdown(id="crime_dropdown", value="FELONY", clearable=False,
                                 options=[{"label": cat, "value": cat} for cat in merged_df["law_cat_cd"].unique()] if not merged_df.empty else [],
                                 style={"width": "200px"}),
                ], style={"display": "flex", "align-items": "center"}),

                html.Div([ # Container for Date Range Picker
                     html.Label("Select Date Range:", style={"margin-right": "10px", "font-weight": "bold"}),
                     dcc.DatePickerRange(
                        id='date_range_picker',
                        min_date_allowed=min_date_available,
                        max_date_allowed=max_date_available,
                        start_date=min_date_available,
                        end_date=max_date_available,
                        display_format='YYYY-MM-DD',
                        style={"font-size": "0.9em"}
                    ),
                ], style={"display": "flex", "align-items": "center"}),

                # Add Area Name Dropdown for Rent Trend Chart (Chart 7)
                 html.Div([ # Container for Area Name Dropdown
                    html.Label("Select Area:", style={"margin-right": "10px", "font-weight": "bold"}),
                    dcc.Dropdown(id="area_dropdown",
                                 options=area_dropdown_options,
                                 value='Overall', # Default value
                                 clearable=False,
                                 style={"width": "250px"}), # Adjust width as needed
                ], style={"display": "flex", "align-items": "center"}),


                 # Add a button to update charts
                html.Button("Update Charts", id="update_eda_button", n_clicks=0,
                            style={"padding": "10px 20px", "background-color": "#28a745", "color": "white", "border": "none", "border-radius": "5px", "cursor": "pointer", "flex-shrink": 0, "margin-left": "20px"})

            ], className="eda-filters-container"), # Use a class for the filters container

             # Add labels for the filters
            html.Div([
                html.Span("Chart Filters:", style={"font-weight": "bold", "margin-right": "10px"}),
                html.Span("Date Range applies to ALL charts.", className="filter-label", style={"color": "#007bff"}), # Highlight date range
                html.Span("|  Crime Category applies to: ", style={"margin-left": "15px", "font-weight": "bold"}),
                html.Span("Crime/Rent Scatter (Chart 3),", className="filter-label"), # Updated description for Chart 3 (Crime Count vs Rent)
                html.Span("Bar by Precinct (Chart 2),", className="filter-label"),
                html.Span("Monthly Trend of Crime Count (Chart 1).", className="filter-label"),
                html.Span("|  Area selection applies to:", style={"margin-left": "15px", "font-weight": "bold"}),
                html.Span(" Rent Trend (Chart 7), Dager Ratio Trend (Chart 8).", className="filter-label", style={"color": "#ff232"}), # Highlight Area filter


            ], style={"textAlign": "center", "margin-top": "10px", "font-size": "0.9em", "color": "#555"}),

            # === Danger Ratio Calculation Description for Layout ===
            html.Div([
                 html.Span("ℹ️ ", style={'fontWeight': 'bold', 'color': '#007bff'}), # Info icon
                 html.Span("Danger Ratio Explanation: ", style={'fontWeight': 'bold'}),
                 html.Span("This metric quantifies crime severity relative to the cost of living. It is computed as the "),
                 html.Span("(Weighted Crime Count) / (Median Rent)", style={'fontWeight': 'bold', 'fontStyle': 'italic'}),
                 html.Span(". Weighted Crime Count is calculated by assigning severity weights to crime types: FELONYs are weighted by 3, MISDEMEANORs by 2, and VIOLATIONs by 1. A higher Danger Ratio indicates an area where crime is relatively higher compared to the median rental price, suggesting a potentially lower safety index per dollar spent on housing."),
             ], style={'textAlign': 'center', 'marginTop': '15px', 'marginBottom': '15px', 'fontSize': '0.95em', 'color': '#555', 'padding': '10px', 'backgroundColor': '#e9ecef', 'borderRadius': '5px'}),

             # Basic style for filter labels
            html.Br(), # Add a line break for spacing


            # Container for the graphs with the desired 2x4 + 1 layout
            html.Div([
                # Row 1: Chart 1 and Chart 2
                html.Div(className="graph-row", children=[
                    html.Div(className="graph-container", children=[
                        dcc.Graph(id="monthly_trend_line", figure={}) # Chart 1: Crime Count Trend
                    ]),
                    html.Div(className="graph-container", children=[
                        dcc.Graph(id="crime_area_bar", figure={}) # Chart 2: Crime Count by Area
                    ]),
                ]),
                # Row 2: Chart 3 and Chart 4
                html.Div(className="graph-row", children=[
                    html.Div(className="graph-container", children=[
                        dcc.Graph(id="crime_rent_scatter", figure={}) # Chart 3: Crime vs Rent Scatter
                    ]),
                    html.Div(className="graph-container", children=[
                        dcc.Graph(id="boxplot_rent_borough", figure={}) # Chart 4: Rent Distribution by Borough
                    ]),
                ]),
                # Row 3: Chart 5 and Chart 6
                html.Div(className="graph-row", children=[
                     html.Div(className="graph-container", children=[
                         dcc.Graph(id="heatmap_crime_rent", figure={}) # Chart 5: Danger Ratio Heatmap
                     ]),
                     html.Div(className="graph-container", children=[
                         dcc.Graph(id="danger_ratio_area_bar", figure={}) # Chart 6: Average Danger Ratio by Area
                     ]),
                ]),
                # Row 4: Chart 7 and Chart 8
                html.Div(className="graph-row", children=[
                    # --- Chart 7 (MODIFIED): Median Rent Trend (Overall or by Area) ---
                     html.Div(className="graph-container", children=[
                         dcc.Graph(id="rent_danger_scatter", figure={}) # Chart 7: Median Rent Trend (Overall or by Area) - MODIFIED
                     ]),
                    # --- Chart 8 (ORIGINAL): Average Danger Ratio Trend (Overall or by Area) ---
                    html.Div(className="graph-container", children=[
                         dcc.Graph(id="overall_danger_trend", figure={}) # Chart 8: Average Danger Ratio Trend (Overall or by Area) - KEPT ORIGINAL
                     ]),
                ]),
                # Row 5: Chart 9 (Choropleth Map) - Centered and Larger
                html.Div(className="graph-row", children=[ # Still use graph-row to maintain gap and centering
                     html.Div(className="choropleth-container", children=[
                         dcc.Graph(id="choropleth_rent", figure={}, style={"height": "100%", "width": "100%"}) # Chart 9 (Map): Latest Median Rent Choropleth
                     ]),
                ]),

            ], className="eda-graphs-container"), # Main wrapper container


        ])
    ], style={"margin": "0 10px"}),

], id="main-app-container") # Give the main div an ID if needed for CSS targeting

# === Modified Index String (Removed inline CSS) ===
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


# === Callbacks ===

@app.callback(
    Output("marker_layer", "children"),
    Output("info_output", "children"),
    Output("map", "center"),
    Output("map", "zoom"),
    Input("search_btn", "n_clicks"),
    State("zip_input", "value"),
    State("travel_dropdown", "value"),
    State("place_type", "value"),
    State("map", "center"),
    State("map", "zoom")
)
def update_map(n, zip_code, time_limit, types, current_center, current_zoom):
    if not n or not zip_code:
        return dash.no_update, html.P("Enter ZIP Code, select place types, and click Search to explore."), dash.no_update, dash.no_update

    if merged_df.empty:
         print("❌ Data failed to load. Map data unavailable.")
         return [], html.P("❌ Data failed to load. Map data unavailable."), current_center, current_zoom

    lat, lon = None, None
    markers = []
    api_errors = []

    # --- 1. Geocode zip code ---
    try:
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zip_code}, NY, USA&key={GOOGLE_API_KEY}"
        geo_req = requests.get(geo_url)
        geo_req.raise_for_status()
        geo = geo_req.json()

        if geo.get("status") == "OK" and geo.get("results"):
            loc = geo["results"][0]["geometry"]["location"]
            lat, lon = loc["lat"], loc["lng"]
            print(f"Geocoded {zip_code} to: {lat}, {lon}")
            zip_marker_popup = html.Div(f"Searched ZIP: {zip_code}")
            zip_marker = dl.Marker(position=[lat, lon], children=dl.Popup(id="zip-popup-content", children=zip_marker_popup))
            markers.append(zip_marker)
        else:
             status = geo.get("status", "Unknown error")
             error_message = geo.get("error_message", "")
             err_msg = f"❌ Geocoding failed for {zip_code}. Status: {status}. Message: {error_message}. Check ZIP or API key."
             print(err_msg)
             api_errors.append(err_msg)
             return [], html.P(err_msg), current_center, current_zoom

    except requests.exceptions.RequestException as e:
         err_msg = f"❌ Network error during Geocoding for {zip_code}: {e}"
         print(err_msg)
         api_errors.append(err_msg)
         return [], html.P(err_msg), current_center, current_zoom
    except Exception as e:
         err_msg = f"❌ Unexpected error during Geocoding for {zip_code}: {e}"
         print(err_msg)
         api_errors.append(err_msg)
         return [], html.P(err_msg), current_center, current_zoom

    # --- 2. Search for nearby places ---
    # Initialize dictionary to store counts for each place type
    places_count_by_type = {ptype: 0 for ptype in types} if types else {}
    place_markers = []

    if lat is not None and lon is not None and types:
        print(f"Searching for types: {types} near {lat},{lon} within {time_limit} mins walk...")
        for place_type in types:
            if place_type not in PLACE_COLORS:
                 print(f"Warning: No color defined for place type: {place_type}, skipping.")
                 continue

            try:
                places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=2000&type={place_type}&key={GOOGLE_API_KEY}"
                places_req = requests.get(places_url)
                places_req.raise_for_status()
                places_result = places_req.json()

                if places_result.get("status") == "OK" and places_result.get("results"):
                    all_nearby_places = places_result.get("results", [])
                    print(f"Found {len(all_nearby_places)} potential '{place_type}' places nearby.")

                    for p in all_nearby_places:
                        place_name = p.get("name", "N/A")
                        if p.get("geometry") and p["geometry"].get("location"):
                            dest = p["geometry"]["location"]
                            dest_lat, dest_lng = dest.get("lat"), dest.get("lng")

                            if dest_lat is not None and dest_lng is not None:
                                try:
                                    dist_url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={lat},{lon}&destinations={dest_lat},{dest_lng}&mode=walking&key={GOOGLE_API_KEY}"
                                    dur_req = requests.get(dist_url)
                                    dur_req.raise_for_status()
                                    dur_result = dur_req.json()

                                    if (dur_result.get("status") == "OK" and
                                        dur_result.get("rows") and
                                        dur_result["rows"][0].get("elements") and
                                        dur_result["rows"][0]["elements"][0].get("status") == "OK" and
                                        dur_result["rows"][0]["elements"][0].get("duration")):

                                        mins = dur_result["rows"][0]["elements"][0]["duration"]["value"] / 60
                                        if mins <= time_limit:
                                            # Increment count for this specific place type
                                            if place_type in places_count_by_type:
                                                places_count_by_type[place_type] += 1

                                            place_markers.append(dl.CircleMarker(
                                                center=[dest_lat, dest_lng],
                                                radius=6,
                                                color=PLACE_COLORS[place_type],
                                                fillColor=PLACE_COLORS[place_type],
                                                fillOpacity=0.9,
                                                children=[
                                                    dl.Tooltip(f"{place_name}"),
                                                    dl.Popup(f"{place_name}<br>{mins:.1f} min walk")
                                                ]))

                                    elif dur_result.get("status") != "OK":
                                         err_msg = f"Distance Matrix API Error for '{place_name}'. Status: {dur_result.get('status', 'Unknown')}. Message: {dur_result.get('error_message','')}"
                                         print(err_msg)
                                    elif dur_result["rows"][0]["elements"][0].get("status") != "OK":
                                         el_status = dur_result["rows"][0]["elements"][0].get("status")
                                         print(f"Distance Matrix element status for '{place_name}': {el_status}. Could not calculate walking time.")

                                except requests.exceptions.RequestException as e_dist:
                                     print(f"Network error during Distance Matrix for '{place_name}': {e_dist}")
                                except Exception as e_dist_proc:
                                     print(f"Error processing Distance Matrix result for '{place_name}': {e_dist_proc}")

                            else:
                                print(f"Skipping place '{place_name}' due to missing/invalid coordinates.")
                        else:
                            print(f"Skipping place '{place_name}' due to missing geometry/location.")

                elif places_result.get("status") == "ZERO_RESULTS":
                    print(f"No '{place_type}' places found nearby via Places API.")
                else:
                    status = places_result.get("status", "Unknown error")
                    error_message = places_result.get("error_message", "")
                    err_msg = f"Places API Error for type '{place_type}'. Status: {status}. Message: {error_message}"
                    print(err_msg)
                    api_errors.append(err_msg)

            except requests.exceptions.RequestException as e_places:
                 err_msg = f"Network error during Places API search for '{place_type}': {e_places}"
                 print(err_msg)
                 api_errors.append(err_msg)
            except Exception as e_places_proc:
                 err_msg = f"Unexpected error during Places API processing for '{place_type}': {e_places_proc}"
                 print(err_msg)
                 api_errors.append(err_msg)

        markers = place_markers + markers

    # --- 3. Filter data for the entered ZIP code ---
    def zip_match(row_zips):
         if isinstance(row_zips, list):
             return str(zip_code) in row_zips
         return False

    df_zip = merged_df[merged_df["ZIP Codes"].apply(zip_match)].copy()

    # --- 4. Prepare summary information ---
    summary_elements = [html.P(f"📍 ZIP: {zip_code}")]

    if api_errors:
        summary_elements.append(html.Details([
            html.Summary("⚠️ API Errors Encountered (click to expand)"),
            html.Ul([html.Li(err) for err in api_errors])
        ], style={'color': 'red', 'marginBottom': '10px'}))

    if df_zip.empty:
        summary_elements.append(html.P("No crime or rent data available for this ZIP Code in the dataset."))
        # If no data for ZIP, still show place counts if search was done
        if types:
            places_summary_list = [
                html.Li(f"{ptype.replace('_', ' ').title()}: {count}")
                for ptype, count in places_count_by_type.items()
            ]
            if places_summary_list:
                 summary_elements.append(html.P(f"🚶 Places Found Nearby (≤ {time_limit} min walk):"))
                 summary_elements.append(html.Ul(places_summary_list))
            else:
                 summary_elements.append(html.P(f"🚶 No places found for selected types within {time_limit} min walk."))

    else:
        # Find the latest date *in the filtered data for this specific ZIP*
        latest_date_in_zip = df_zip["date"].max()
        # Determine the start of the month for the latest date
        latest_month_start = latest_date_in_zip.replace(day=1)

        # Filter data for the latest month *within this ZIP's data*
        # This df contains all records (potentially multiple crime types) for the latest month
        df_latest_month = df_zip[df_zip["date"] >= latest_month_start].copy()

        # Get the *first* record corresponding to the absolute latest date for this ZIP
        # This is mainly for precinct_area, as rent/danger might vary slightly even on the same date if data source changes
        latest_overall_data_point = df_zip.sort_values(by="date", ascending=False).iloc[0]

        summary_elements.extend([
            html.P(f"🏘️ Area: {latest_overall_data_point.get('precinct_area', 'N/A')}"),
            html.P(f"🗓️ Latest Data Date in dataset for ZIP: {latest_date_in_zip.strftime('%Y-%m-%d')}"), # Use latest_date_in_zip
        ])

        # --- Calculate Average Rent for Latest Month ---
        if not df_latest_month.empty and 'median_rent' in df_latest_month.columns and df_latest_month['median_rent'].notna().any():
            # Calculate the mean of 'median_rent' for all entries in the latest month
            avg_rent_latest_month = df_latest_month['median_rent'].mean()
            summary_elements.append(html.P(f"💰 Average Rent (Month: {latest_month_start.strftime('%Y-%m')}): ${avg_rent_latest_month:,.0f}"))
        else:
            summary_elements.append(html.P(f"💰 Average Rent (Month: {latest_month_start.strftime('%Y-%m')}): N/A"))

        # --- Calculate and display crime counts for the latest month ---
        if not df_latest_month.empty:
            # Sum counts for each category within the latest month (Correctly implemented)
            crime_counts_latest_month = df_latest_month.groupby("law_cat_cd")["count"].sum().to_dict()
            summary_elements.append(html.P(f"🚨 Total Crime Counts (Month: {latest_month_start.strftime('%Y-%m')}):")) # Confirmed: This is for the latest month with data for this ZIP
            summary_elements.append(html.Ul([
                html.Li(f"FELONY: {crime_counts_latest_month.get('FELONY', 0):,}"),
                html.Li(f"MISDEMEANOR: {crime_counts_latest_month.get('MISDEMEANOR', 0):,}"),
                html.Li(f"VIOLATION: {crime_counts_latest_month.get('VIOLATION', 0):,}"),
            ]))
        else:
             # This case might be rare if df_zip wasn't empty, but good to handle
             summary_elements.append(html.P(f"🚨 No crime data found for the latest month ({latest_month_start.strftime('%Y-%m')}) in this ZIP."))

        # --- Calculate Average Danger Ratio for Latest Month ---
        if not df_latest_month.empty and 'danger_ratio' in df_latest_month.columns and df_latest_month['danger_ratio'].notna().any():
             # Calculate the mean of 'danger_ratio' for all entries in the latest month
            avg_danger_latest_month = df_latest_month['danger_ratio'].mean()
            summary_elements.append(html.P(f"💥 Average Danger Ratio (Month: {latest_month_start.strftime('%Y-%m')}): {avg_danger_latest_month:.4f}"))
        else:
            summary_elements.append(html.P(f"💥 Average Danger Ratio (Month: {latest_month_start.strftime('%Y-%m')}): N/A"))

        # --- Add nearby places count (by type) ---
        if types:
            places_summary_list = [
                # Format each type and its count
                html.Li(f"{ptype.replace('_', ' ').title()}: {count}")
                for ptype, count in places_count_by_type.items() if count > 0 # Optionally only show types with count > 0
            ]
            if places_summary_list: # Only add the section if any places were found
                 summary_elements.append(html.P(f"🚶 Places Found Nearby (≤ {time_limit} min walk):"))
                 summary_elements.append(html.Ul(places_summary_list))
            else: # Handle case where types were selected but none found in time limit
                 summary_elements.append(html.P(f"🚶 No places found for selected types within {time_limit} min walk."))
        else:
             summary_elements.append(html.P("🚶 No place types selected for nearby search."))

    # Update the ZIP marker's popup content
    for i, marker in enumerate(markers):
         if isinstance(marker, dl.Marker) and hasattr(marker, 'children') and isinstance(marker.children, dl.Popup):
              markers[i] = dl.Marker(position=[lat, lon], children=dl.Popup(html.Div(summary_elements)))
              break

    # Determine final map center and zoom
    map_center = [lat, lon] if lat is not None else current_center
    # Increase zoom level slightly for better focus on the ZIP code area
    map_zoom = 12 if lat is not None else current_zoom # Zoom increased to 13

    # --- 5. Return results ---
    # Use class "info-box" for potential CSS styling
    return markers, html.Div(summary_elements, className="info-box"), map_center, map_zoom


@app.callback(
    Output("monthly_trend_line", "figure"), # Order changed to match output definition
    Output("crime_area_bar", "figure"),
    Output("crime_rent_scatter", "figure"),
    Output("boxplot_rent_borough", "figure"),
    Output("heatmap_crime_rent", "figure"),
    Output("danger_ratio_area_bar", "figure"), # Chart 6 output
    Output("rent_danger_scatter", "figure"),  # Chart 7 output (Now Rent Trend)
    Output("overall_danger_trend", "figure"), # Chart 8 output (Danger Ratio Trend)
    Output("choropleth_rent", "figure"), # Chart 9 output
    # Input is now the button click
    Input("update_eda_button", "n_clicks"),
    # States are the filter values
    State("crime_dropdown", "value"),
    State("date_range_picker", "start_date"),
    State("date_range_picker", "end_date"),
    State("area_dropdown", "value") # State for Area Name dropdown (used by Chart 7 and 8)
)
# Callback to update EDA charts based on button click and State filter values
# Now returns 9 figures
def update_eda(n_clicks, category, start_date, end_date, area_name_selected):
    # Prevent update on initial page load (button not clicked)
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    # Handle case where data might not be loaded
    if merged_df.empty:
        print("Error: merged_df is empty, cannot update EDA charts.")
        # Return empty plots with informative titles if data is not available (9 empty plots)
        empty_plot_title = "No data available"
        # Ensure 9 empty figures are returned to match the 9 outputs
        return [px.scatter(title=empty_plot_title)] * 9


    # Convert date strings from DatePickerRange to datetime objects
    # Use available min/max dates as fallback if picker values are None initially (shouldn't happen with default values)
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else merged_df["date"].min()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else merged_df["date"].max()

    print(f"\n--- Updating EDA Charts ---")
    print(f"Filtering data for date range: {start_date_obj.strftime('%Y-%m-%d')} to {end_date_obj.strftime('%Y-%m-%d')}")
    print(f"Selected Crime Category: {category}")
    print(f"Selected Area for Trends: {area_name_selected}") # Updated print message


    # Filter the entire dataset by the selected date range
    filtered_df_date_range = merged_df[
        (merged_df["date"] >= start_date_obj) & (merged_df["date"] <= end_date_obj)
    ].copy()

    print(f"Shape after date filtering: {filtered_df_date_range.shape}")


    # Filter data ONLY for the selected crime category and date range (used for crime-count specific charts)
    # Ensure filtered_df_date_range is not empty before filtering by category
    if not filtered_df_date_range.empty:
        df_category_date_range = filtered_df_date_range[
            filtered_df_date_range["law_cat_cd"] == category
        ].copy()
    else:
        df_category_date_range = pd.DataFrame() # Create empty dataframe if date filtered is empty

    print(f"Shape after date and category ('{category}') filtering: {df_category_date_range.shape}")


    # --- Generate Charts (9 charts total) ---

    # Chart 1: Monthly Crime Trend by Category (Line) - Filtered by Date & Category
    # Ensure monthly_trend_df is not empty before plotting
    if not df_category_date_range.empty:
        monthly_trend_df = df_category_date_range.groupby(pd.Grouper(key='date', freq='M'))["count"].sum().reset_index()
        print(f"Shape of monthly_trend_df: {monthly_trend_df.shape}")
        if not monthly_trend_df.empty: # Check if grouped data is also not empty
            line_crime_trend = px.line(monthly_trend_df, x="date", y="count", title=f"📈 {category} Crime Count Monthly Trend ({start_date} to {end_date})",
                           labels={"date": "Date", "count": "Crime Count"},
                           template="plotly_white"
                           ).update_layout(margin={"t":40})
        else:
            print("Grouped monthly_trend_df is empty for Chart 1, returning empty plot.")
            line_crime_trend = px.scatter(title=f"📈 No {category} Crime Trend data ({start_date} to {end_date})", template="plotly_white")
    else:
         print("df_category_date_range is empty for Chart 1, returning empty plot.")
         line_crime_trend = px.scatter(title=f"📈 No {category} Crime Trend data ({start_date} to {end_date})", template="plotly_white")


    # Chart 2: Bar Plot by Precinct (Crime Count) - Filtered by Date & Category
    # Ensure bar_df is not empty before plotting
    if not df_category_date_range.empty:
        bar_crime_area_df = df_category_date_range.groupby("precinct_area")["count"].sum().reset_index().sort_values("count", ascending=False)
        print(f"Shape of bar_crime_area_df: {bar_crime_area_df.shape}")
        if not bar_crime_area_df.empty: # Check if grouped data is also not empty
             bar_crime_area = px.bar(bar_crime_area_df, x="precinct_area", y="count", title=f"🔍 {category} Crime Count by Precinct Area ({start_date} to {end_date})",
                         labels={"precinct_area": "Precinct Area", "count": "Crime Count"},
                         template="plotly_white"
                         )
             # Rotate x-axis labels
             bar_crime_area.update_layout(
                 margin={"t":40},
                 xaxis={"tickangle": 45, "automargin": True} # Rotate x-axis labels
             )
        else:
             print("Grouped bar_crime_area_df is empty for Chart 2, returning empty plot.")
             bar_crime_area = px.scatter(title=f"🔍 No {category} Crime Count data by Area ({start_date} to {end_date})", template="plotly_white")
    else:
         print("df_category_date_range is empty for Chart 2, returning empty plot.")
         bar_crime_area = px.scatter(title=f"🔍 No {category} Crime Count data by Area ({start_date} to {end_date})", template="plotly_white")


    # Chart 3: Crime vs Rent Scatter Plot (Crime Count) - Filtered by Date & Category
    if not df_category_date_range.empty:
        print(f"Shape of scatter_crime_rent source: {df_category_date_range.shape}")
        scatter_crime_rent = px.scatter(df_category_date_range, x="median_rent", y="count", color="Borough",
                         title=f"💥 {category} Crime Count vs Median Rent by Borough ({start_date} to {end_date})",
                         hover_data={"precinct_area": True, "date": True, "count": True, "median_rent": ":,.0f", "Borough": True},
                         labels={"median_rent": "Median Rent ($)", "count": "Crime Count"},
                         template="plotly_white"
                         ).update_layout(margin={"t":40})
    else:
         print("df_category_date_range is empty for Chart 3, returning empty plot.")
         scatter_crime_rent = px.scatter(title=f"💥 No {category} Crime vs Rent data ({start_date} to {end_date})", template="plotly_white")


    # Chart 4: Box Plot: Rent Distribution by Borough - Filtered by Date Range (uses data across all categories in date range)
    if not filtered_df_date_range.empty:
        print(f"Shape of box_rent source: {filtered_df_date_range.shape}")
        box_rent = px.box(filtered_df_date_range, x="Borough", y="median_rent", title=f"🧊 Rent Distribution by Borough ({start_date} to {end_date})",
                 labels={"Borough": "Borough", "median_rent": "Median Rent ($)"},
                 template="plotly_white"
                 ).update_layout(margin={"t":40})
    else:
         print("filtered_df_date_range is empty for Chart 4, returning empty plot.")
         box_rent = px.scatter(title=f"🧊 No Rent Distribution data ({start_date} to {end_date})", template="plotly_white")


    # Chart 5: Heatmap: Average Crime-to-Rent Danger Index by Area and Month - Filtered by Date Range (uses data across all categories)
    if not filtered_df_date_range.empty:
        filtered_df_date_range_heatmap = filtered_df_date_range.copy()
        filtered_df_date_range_heatmap['month_year'] = filtered_df_date_range_heatmap['date'].dt.strftime('%Y-%m')
        # Ensure there's data after grouping before creating heatmap_df_agg
        if not filtered_df_date_range_heatmap.empty: # Check if the dataframe for heatmap is not empty
            heatmap_df_agg = filtered_df_date_range_heatmap.groupby(["precinct_area", "month_year"])["danger_ratio"].mean().reset_index()
            print(f"Shape of heatmap_df_agg: {heatmap_df_agg.shape}")
            if not heatmap_df_agg.empty: # Check if grouped data is also not empty
                 heatmap_df_agg['month_year'] = pd.to_datetime(heatmap_df_agg['month_year']).dt.strftime('%Y-%m') # Ensure format for plotting
                 heatmap_df_agg = heatmap_df_agg.sort_values(by=['month_year', 'precinct_area'])

                 heat_danger = px.density_heatmap(heatmap_df_agg, x="precinct_area", y="month_year", z="danger_ratio",
                                        title=f"🔥 Average Crime-to-Rent Danger Index by Area and Month ({start_date} to {end_date})",
                                        labels={"precinct_area": "Precinct Area", "month_year": "Month-Year", "danger_ratio": "Average Danger Ratio"},
                                        color_continuous_scale="Reds",
                                        template="plotly_white"
                                        )
                 # Rotate x-axis labels
                 heat_danger.update_layout(
                     margin={"t":40},
                     xaxis={"tickangle": 45, "automargin": True} # Rotate x-axis labels
                 )

                 if len(heatmap_df_agg["month_year"].unique()) > 12:
                      heat_danger.update_layout(yaxis={"dtick": "M6", "automargin": True})
                 else:
                      heat_danger.update_layout(yaxis={"dtick": "M1", "automargin": True})
            else:
                 print("Aggregated heatmap_df_agg is empty for Chart 5, returning empty plot.")
                 heat_danger = px.scatter(title=f"🔥 No aggregated data for Heatmap ({start_date} to {end_date})", template="plotly_white")
        else:
             print("filtered_df_date_range_heatmap is empty for Chart 5, returning empty plot.")
             heat_danger = px.scatter(title=f"🔥 No filtered data for Heatmap ({start_date} to {end_date})", template="plotly_white")
    else:
        print("filtered_df_date_range is empty for Chart 5, returning empty plot.")
        heat_danger = px.scatter(title=f"🔥 No data for Heatmap ({start_date} to {end_date})", template="plotly_white")


    # Chart 6 (NEW): Bar Plot: Average Danger Ratio by Precinct Area - Filtered by Date Range (uses data across all categories)
    # Ensure filtered_df_date_range is not empty before plotting
    if not filtered_df_date_range.empty:
        bar_danger_area_df = filtered_df_date_range.groupby("precinct_area")["danger_ratio"].mean().reset_index().sort_values("danger_ratio", ascending=False)
        print(f"Shape of bar_danger_area_df: {bar_danger_area_df.shape}")
        if not bar_danger_area_df.empty: # Check if grouped data is also not empty
             bar_danger_area = px.bar(bar_danger_area_df, x="precinct_area", y="danger_ratio", title=f"📊 Average Danger Ratio by Precinct Area ({start_date} to {end_date})",
                           labels={"precinct_area": "Precinct Area", "danger_ratio": "Average Danger Ratio"},
                           template="plotly_white"
                           )
             # Rotate x-axis labels
             bar_danger_area.update_layout(
                 margin={"t":40},
                 xaxis={"tickangle": 45, "automargin": True} # Rotate x-axis labels
             )
        else:
            print("Grouped bar_danger_area_df is empty for Chart 6, returning empty plot.")
            bar_danger_area = px.scatter(title=f"📊 No Danger Ratio data by Area ({start_date} to {end_date})", template="plotly_white")
    else:
         print("filtered_df_date_range is empty for Chart 6, returning empty plot.")
         bar_danger_area = px.scatter(title=f"📊 No Danger Ratio data by Area ({start_date} to {end_date})", template="plotly_white")


    # --- Chart 7 (MODIFIED): Line Plot: Median Rent Trend (Overall or by Area) ---
    # This chart now shows the Median Rent trend over time, filtered by the selected Area.
    # It replaces the original "Average Rent vs. Average Danger Ratio" scatter plot.
    if not filtered_df_date_range.empty:
        if area_name_selected == 'Overall' or area_name_selected is None:
            # Calculate overall median rent trend
            # Group by month and calculate the median of 'median_rent'
            rent_trend_df_chart7 = filtered_df_date_range.groupby(pd.Grouper(key='date', freq='M'))["median_rent"].median().reset_index()
            chart7_title = f"💰 Overall Median Rent Trend ({start_date} to {end_date})" # Dynamic Title
            print(f"Chart 7: Calculating overall median rent trend. Shape: {rent_trend_df_chart7.shape}")
        else:
            # Filter by area and calculate median rent trend
            df_area_filtered_chart7 = filtered_df_date_range[filtered_df_date_range['areaName'] == area_name_selected].copy() # Use copy to avoid SettingWithCopyWarning
            print(f"Chart 7: Filtering rent trend by area '{area_name_selected}'. Shape: {df_area_filtered_chart7.shape}")
            if not df_area_filtered_chart7.empty:
                 # Group by month and calculate the median of 'median_rent' for the selected area
                 rent_trend_df_chart7 = df_area_filtered_chart7.groupby(pd.Grouper(key='date', freq='M'))["median_rent"].median().reset_index()
                 chart7_title = f"💰 Median Rent Trend for {area_name_selected} ({start_date} to {end_date})" # Dynamic Title
                 print(f"Chart 7: Grouped rent trend for '{area_name_selected}'. Shape: {rent_trend_df_chart7.shape}")
            else:
                 rent_trend_df_chart7 = pd.DataFrame() # Empty if no data for the area
                 chart7_title = f"💰 No Median Rent Trend data for {area_name_selected} ({start_date} to {end_date})" # Dynamic Title
                 print(f"Chart 7: No data after filtering for area '{area_name_selected}'.")


        if not rent_trend_df_chart7.empty: # Check if grouped data is also not empty
            # Use px.line for time series plot
            rent_trend_figure = px.line(rent_trend_df_chart7, x="date", y="median_rent", title=chart7_title, # Use dynamic title
                                 labels={"date": "Date", "median_rent": "Median Rent ($)"}, # Updated y-axis label
                                 template="plotly_white"
                                 ).update_layout(margin={"t":40})
        else:
            print("Chart 7: rent_trend_df_chart7 is empty, returning empty plot.")
            rent_trend_figure = px.scatter(title=chart7_title, template="plotly_white") # Use dynamic title

    else:
         print("Chart 7: filtered_df_date_range is empty for rent trend source, returning empty plot.")
         rent_trend_figure = px.scatter(title=f"💰 No data for Median Rent Trend ({start_date} to {end_date})", template="plotly_white") # Fallback static title

    # --- End of Chart 7 (MODIFIED) ---


    # --- Chart 8 (ORIGINAL): Line Plot: Average Danger Ratio Trend (Overall or by Area) ---
    # This chart remains the Average Danger Ratio Trend over time, filtered by the selected Area.
    # It was previously Chart 9 in my *incorrect* modification, now corrected back to Chart 8.
    if not filtered_df_date_range.empty:
        if area_name_selected == 'Overall' or area_name_selected is None:
            # Calculate overall trend
            overall_danger_trend_df_chart8 = filtered_df_date_range.groupby(pd.Grouper(key='date', freq='M'))["danger_ratio"].mean().reset_index()
            chart8_title = f"📊 Overall Average Danger Ratio Trend ({start_date} to {end_date})" # Dynamic Title
            print(f"Chart 8: Calculating overall danger ratio trend. Shape: {overall_danger_trend_df_chart8.shape}")
        else:
            # Filter by area and calculate trend
            df_area_filtered_chart8 = filtered_df_date_range[filtered_df_date_range['areaName'] == area_name_selected].copy() # Use copy to avoid SettingWithCopyWarning
            print(f"Chart 8: Filtering danger ratio trend by area '{area_name_selected}'. Shape: {df_area_filtered_chart8.shape}")
            if not df_area_filtered_chart8.empty:
                 overall_danger_trend_df_chart8 = df_area_filtered_chart8.groupby(pd.Grouper(key='date', freq='M'))["danger_ratio"].mean().reset_index()
                 chart8_title = f"📊 Average Danger Ratio Trend for {area_name_selected} ({start_date} to {end_date})" # Dynamic Title
                 print(f"Chart 8: Grouped danger ratio trend for '{area_name_selected}'. Shape: {overall_danger_trend_df_chart8.shape}")
            else:
                 overall_danger_trend_df_chart8 = pd.DataFrame() # Empty if no data for the area
                 chart8_title = f"📊 No Danger Ratio Trend data for {area_name_selected} ({start_date} to {end_date})" # Dynamic Title
                 print(f"Chart 8: No data after filtering for area '{area_name_selected}'.")


        if not overall_danger_trend_df_chart8.empty: # Check if grouped data is also not empty
            # Use px.line for time series plot
            overall_danger_trend_figure = px.line(overall_danger_trend_df_chart8, x="date", y="danger_ratio", title=chart8_title, # Use dynamic title
                                 labels={"date": "Date", "danger_ratio": "Average Danger Ratio"},
                                 template="plotly_white"
                                 ).update_layout(margin={"t":40})
        else:
            print("Chart 8: overall_danger_trend_df_chart8 is empty, returning empty plot.")
            overall_danger_trend_figure = px.scatter(title=chart8_title, template="plotly_white") # Use dynamic title

    else:
         print("Chart 8: filtered_df_date_range is empty for danger ratio trend source, returning empty plot.")
         overall_danger_trend_figure = px.scatter(title=f"📊 No data for Danger Ratio Trend ({start_date} to {end_date})", template="plotly_white") # Fallback static title
    # --- End of Chart 8 (ORIGINAL) ---


    # Chart 9: Choropleth: Latest Median Rent by ZIP Code - Filtered by Date Range (uses data across all categories)
    if not filtered_df_date_range.empty:
        # Explode ZIP Codes to have one row per ZIP code
        filtered_df_exploded = filtered_df_date_range.explode("ZIP Codes").copy()
        # Ensure ZIP Codes are strings and drop rows with empty ZIP Codes after explode
        filtered_df_exploded["ZIP Codes"] = filtered_df_exploded["ZIP Codes"].astype(str)
        filtered_df_exploded = filtered_df_exploded[filtered_df_exploded["ZIP Codes"] != ''].copy()

        print(f"Shape after exploding ZIP Codes: {filtered_df_exploded.shape}")
        # print(filtered_df_exploded.head())

        # Get the latest rent for each unique ZIP code *within the selected date range*
        if not filtered_df_exploded.empty:
             latest_rent_by_zip_agg = filtered_df_exploded.sort_values("date", ascending=False).groupby("ZIP Codes").first().reset_index()
        else:
             latest_rent_by_zip_agg = pd.DataFrame({"ZIP Codes": [], "median_rent": []}) # Empty df if no data after explode/filter

        geojson_data_url = "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/ny_new_york_zip_codes_geo.min.json"

        choropleth_rent = px.choropleth_mapbox(
            latest_rent_by_zip_agg,
            geojson=geojson_data_url,
            locations="ZIP Codes",
            featureidkey="properties.ZCTA5CE10",
            color="median_rent",
            mapbox_style="carto-positron",
            center={"lat": 40.73, "lon": -73.94},
            zoom=10, title=f"🗺️ Latest Median Rent by ZIP Code ({start_date} to {end_date})",
            color_continuous_scale="Blues",
            labels={"median_rent": "Median Rent ($)", "ZIP Codes": "ZIP Code"},
            hover_data={"ZIP Codes": True, "median_rent": ":$,.0f"},
            template="plotly_white"
        )
        choropleth_rent.update_layout(margin={"r":0,"l":0,"b":0,"t":40})
    else:
         choropleth_rent = px.scatter(title=f"🗺️ No data for Choropleth ({start_date} to {end_date})", template="plotly_white")


    # Return the generated figures - Ensure the order matches the Output definition
    # Output order: Chart 1, 2, 3, 4, 5, 6, 7 (Rent Trend), 8 (Danger Ratio Trend), 9 (Choropleth)
    return (
        line_crime_trend,        # Chart 1
        bar_crime_area,          # Chart 2
        scatter_crime_rent,      # Chart 3
        box_rent,                # Chart 4
        heat_danger,             # Chart 5
        bar_danger_area,         # Chart 6
        rent_trend_figure,       # Chart 7 (MODIFIED: Rent Trend)
        overall_danger_trend_figure, # Chart 8 (ORIGINAL: Danger Ratio Trend)
        choropleth_rent          # Chart 9
    )


# === Run App ===
if __name__ == "__main__":
    # Create assets folder if it doesn't exist (optional, good for first run)
    assets_folder = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)
        print(f"Created '{assets_folder}' folder.")

    app.run(debug=True, port=8054)