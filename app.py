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
import os 


try:
    merged_df = pd.read_csv("data/nyc_rent&crime_2015_to_recent.csv", parse_dates=["date"])
    merged_df["ZIP Codes"] = merged_df["ZIP Codes"].apply(lambda x: [str(z) for z in eval(x)] if isinstance(x, str) else [])
    merged_df["date"] = pd.to_datetime(merged_df["date"])
    print("Data loaded successfully.")
except FileNotFoundError:
    print("Error: data/nyc_rent&crime_2015_to_recent.csv not found.")
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

# Map Explorer:
# 1. Map: Display area data based on ZIP Code + Search for nearby places (like supermarkets) with color-coded markers
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
app = dash.Dash(__name__)
app.title = "NYC Rent & Crime Dashboard"
server = app.server # Expose server for production deployment

# === IMPORTANT: Replace "XX" with your actual Google API Key ===
# Ensure the following Google APIs are enabled for your key:
# 1. Geocoding API
# 2. Places API
# 3. Distance Matrix API
# Check your Google Cloud Console for API restrictions and billing setup.

GOOGLE_API_KEY = "YOUR_API_KEY"


# Define colors for different place types
PLACE_COLORS = {
    "supermarket": "blue",
    "hospital": "red",
    "subway_station": "orange",
    "park": "green",
    "school": "purple",
    "library": "brown"
}

# Determine min and max dates for the date picker
if not merged_df.empty:
    min_date_available = merged_df["date"].min().date()
    max_date_available = merged_df["date"].max().date()
    area_names = sorted(merged_df['areaName'].unique()) 
    area_dropdown_options = [{'label': 'Overall NYC', 'value': 'Overall'}] + [{'label': area, 'value': area} for area in area_names if pd.notnull(area)]
else:
    # Default dates if data loading fails or df is empty
    min_date_available = date(2015, 1, 1)
    max_date_available = date.today()
    area_dropdown_options = [{'label': 'Overall NYC', 'value': 'Overall'}]


# === Layout ===
app.layout = html.Div([
    # html.H1("📍 NYC Rent & Crime Explorer", style={"textAlign": "center", "color": "#333", "margin-bottom": "20px"}), 
    # Container for Title and Author to align them vertically
        html.Div([
            html.H1("📍 NYC Rent & Crime Explorer", style={"textAlign": "center", "color": "#333", "margin-bottom": "0"}), 
            html.P("Made by Sunny Chang", style={"textAlign": "center", "color": "#555", "font-size": "0.9em", "margin-top": "5px"})
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
    dcc.Tabs(id="main-tabs", value="tab-eda", children=[
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


            html.Div(id="info_output"), 
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

                # Add Area Name Dropdown 
                 html.Div([ 
                    html.Label("Select Area:", style={"margin-right": "10px", "font-weight": "bold"}),
                    dcc.Dropdown(id="area_dropdown",
                                 options=area_dropdown_options,
                                 value='Overall', # Default value
                                 clearable=False,
                                 style={"width": "250px"}), 
                ], style={"display": "flex", "align-items": "center"}),


                 # Add a button to update charts
                html.Button("Update Charts", id="update_eda_button", n_clicks=0,
                            style={"padding": "10px 20px", "background-color": "#28a745", "color": "white", "border": "none", "border-radius": "5px", "cursor": "pointer", "flex-shrink": 0, "margin-left": "20px"})

            ], className="eda-filters-container"), 

            # Add labels for the filters
            html.Div([
                html.Span("Filter Scope:", style={"fontWeight": "bold", "marginRight": "10px"}),

                html.Span(
                    "Date Range applies to all charts.",
                    style={"color": "#007bff", "marginRight": "15px"}
                ),

                html.Span(
                    "Crime Category applies to crime-related charts only.",
                    style={"marginRight": "15px"}
                ),

                html.Span(
                    "Area selection applies to trend analyses.",
                    style={"color": "#28a745"}
                ),
            ], style={
                "textAlign": "center",
                "marginTop": "10px",
                "fontSize": "0.9em",
                "color": "#555"
            }),


            # Danger Ratio Explanation
            html.Div([
                html.Span("ℹ️ ", style={"fontWeight": "bold", "color": "#007bff"}),
                html.Span("Danger Ratio: ", style={"fontWeight": "bold"}),
                html.Span(
                    "A composite metric that measures crime severity relative to housing cost. "
                    "It is defined as "
                ),
                html.Span(
                    "(Weighted Crime Count ÷ Median Rent)",
                    style={"fontWeight": "bold", "fontStyle": "italic"}
                ),
                html.Span(
                    ". Crime severity is weighted by offense type (Felony = 3, Misdemeanor = 2, Violation = 1). "
                    "Higher values indicate areas where crime intensity is high relative to rental prices, "
                    "suggesting lower safety per dollar spent on housing."
                ),
            ], style={
                "textAlign": "center",
                "marginTop": "15px",
                "marginBottom": "15px",
                "fontSize": "0.95em",
                "color": "#555",
                "padding": "12px",
                "backgroundColor": "#e9ecef",
                "borderRadius": "6px",
                "maxWidth": "1100px",
                "marginLeft": "auto",
                "marginRight": "auto"
            }),

            html.Br(),


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
                    # Chart 7: Median Rent Trend (Overall or by Area) 
                     html.Div(className="graph-container", children=[
                         dcc.Graph(id="rent_danger_scatter", figure={}) # Chart 7: Median Rent Trend (Overall or by Area) - MODIFIED
                     ]),
                    # Chart 8: Average Danger Ratio Trend (Overall or by Area)
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

            ], className="eda-graphs-container"),


        ])
    ], style={"margin": "0 10px"}),

], id="main-app-container") 


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
        latest_date_in_zip = df_zip["date"].max()
        latest_month_start = latest_date_in_zip.replace(day=1)
        df_latest_month = df_zip[df_zip["date"] >= latest_month_start].copy()
        latest_overall_data_point = df_zip.sort_values(by="date", ascending=False).iloc[0]

        summary_elements.extend([
            html.P(f"🏘️ Area: {latest_overall_data_point.get('precinct_area', 'N/A')}"),
            html.P(f"🗓️ Latest Data Date in dataset for ZIP: {latest_date_in_zip.strftime('%Y-%m-%d')}"), # Use latest_date_in_zip
        ])

        # --- Calculate Average Rent for Latest Month ---
        if not df_latest_month.empty and 'median_rent' in df_latest_month.columns and df_latest_month['median_rent'].notna().any():
            avg_rent_latest_month = df_latest_month['median_rent'].mean()
            summary_elements.append(html.P(f"💰 Average Rent (Month: {latest_month_start.strftime('%Y-%m')}): ${avg_rent_latest_month:,.0f}"))
        else:
            summary_elements.append(html.P(f"💰 Average Rent (Month: {latest_month_start.strftime('%Y-%m')}): N/A"))

        # --- Calculate and display crime counts for the latest month ---
        if not df_latest_month.empty:
            crime_counts_latest_month = df_latest_month.groupby("law_cat_cd")["count"].sum().to_dict()
            summary_elements.append(html.P(f"🚨 Total Crime Counts (Month: {latest_month_start.strftime('%Y-%m')}):")) # Confirmed: This is for the latest month with data for this ZIP
            summary_elements.append(html.Ul([
                html.Li(f"FELONY: {crime_counts_latest_month.get('FELONY', 0):,}"),
                html.Li(f"MISDEMEANOR: {crime_counts_latest_month.get('MISDEMEANOR', 0):,}"),
                html.Li(f"VIOLATION: {crime_counts_latest_month.get('VIOLATION', 0):,}"),
            ]))
        else:
             summary_elements.append(html.P(f"🚨 No crime data found for the latest month ({latest_month_start.strftime('%Y-%m')}) in this ZIP."))

        # --- Calculate Average Danger Ratio for Latest Month ---
        if not df_latest_month.empty and 'danger_ratio' in df_latest_month.columns and df_latest_month['danger_ratio'].notna().any():
            avg_danger_latest_month = df_latest_month['danger_ratio'].mean()
            summary_elements.append(html.P(f"💥 Average Danger Ratio (Month: {latest_month_start.strftime('%Y-%m')}): {avg_danger_latest_month:.4f}"))
        else:
            summary_elements.append(html.P(f"💥 Average Danger Ratio (Month: {latest_month_start.strftime('%Y-%m')}): N/A"))

        # --- Add nearby places count (by type) ---
        if types:
            places_summary_list = [
                html.Li(f"{ptype.replace('_', ' ').title()}: {count}")
                for ptype, count in places_count_by_type.items() if count > 0 
            ]
            if places_summary_list: 
                 summary_elements.append(html.P(f"🚶 Places Found Nearby (≤ {time_limit} min walk):"))
                 summary_elements.append(html.Ul(places_summary_list))
            else: 
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
    map_zoom = 12 if lat is not None else current_zoom 

    # --- 5. Return results ---
    return markers, html.Div(summary_elements, className="info-box"), map_center, map_zoom


@app.callback(
    Output("monthly_trend_line", "figure"), 
    Output("crime_area_bar", "figure"),
    Output("crime_rent_scatter", "figure"),
    Output("boxplot_rent_borough", "figure"),
    Output("heatmap_crime_rent", "figure"),
    Output("danger_ratio_area_bar", "figure"), 
    Output("rent_danger_scatter", "figure"),  
    Output("overall_danger_trend", "figure"), 
    Output("choropleth_rent", "figure"), 
    Input("update_eda_button", "n_clicks"),
    State("crime_dropdown", "value"),
    State("date_range_picker", "start_date"),
    State("date_range_picker", "end_date"),
    State("area_dropdown", "value") 
)

def update_eda(n_clicks, category, start_date, end_date, area_name_selected):
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    if merged_df.empty:
        print("Error: merged_df is empty, cannot update EDA charts.")
        empty_plot_title = "No data available"
        return [px.scatter(title=empty_plot_title)] * 9

    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else merged_df["date"].min()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else merged_df["date"].max()

    print(f"\n--- Updating EDA Charts ---")
    print(f"Filtering data for date range: {start_date_obj.strftime('%Y-%m-%d')} to {end_date_obj.strftime('%Y-%m-%d')}")
    print(f"Selected Crime Category: {category}")
    print(f"Selected Area for Trends: {area_name_selected}") 


    filtered_df_date_range = merged_df[
        (merged_df["date"] >= start_date_obj) & (merged_df["date"] <= end_date_obj)
    ].copy()
    print(f"Shape after date filtering: {filtered_df_date_range.shape}")


    if not filtered_df_date_range.empty:
        df_category_date_range = filtered_df_date_range[
            filtered_df_date_range["law_cat_cd"] == category
        ].copy()
    else:
        df_category_date_range = pd.DataFrame() 
    print(f"Shape after date and category ('{category}') filtering: {df_category_date_range.shape}")


    # --- Generate Charts (9 charts total) ---

    # Chart 1: Monthly Crime Trend (Line) — Filtered by Date & Category
    if not df_category_date_range.empty:
        monthly_trend_df = (
            df_category_date_range
            .groupby(pd.Grouper(key="date", freq="ME"))["count"]
            .sum()
            .reset_index()
            .sort_values("date")
        )

        if not monthly_trend_df.empty:
            line_crime_trend = px.line(
                monthly_trend_df,
                x="date",
                y="count",
                title=f"{category} Crime Incidents — Monthly Trend ({start_date} to {end_date})",
                labels={"date": "Date", "count": "Crime Incidents"},
                template="plotly_white"
            )
            line_crime_trend.update_traces(
                line=dict(width=2),
                hovertemplate="Month: %{x|%b %Y}<br>Incidents: %{y:,}<extra></extra>"
            )
            line_crime_trend.update_layout(
                width=700,
                height=400,
                margin=dict(l=100, r=60, t=60, b=50)
            )
        else:
            line_crime_trend = px.scatter(
                title=f"No {category} crime trend data ({start_date} to {end_date})",
                template="plotly_white"
            )
    else:
        line_crime_trend = px.scatter(
            title=f"No {category} crime trend data ({start_date} to {end_date})",
            template="plotly_white"
        )



    # Chart 2: Crime Count by Precinct Area (Bar) — Filtered by Date & Category
    if not df_category_date_range.empty:
        bar_crime_area_df = (
            df_category_date_range
            .groupby("precinct_area", as_index=False)["count"]
            .sum()
            .sort_values("count", ascending=False)
            .head(15)  # Top 15 for readability
        )

        if not bar_crime_area_df.empty:
            bar_crime_area = px.bar(
                bar_crime_area_df,
                x="count",
                y="precinct_area",
                orientation="h",
                title=f"Top 15 {category} Crime by Precinct ({start_date} to {end_date})",
                labels={"precinct_area": "Precinct Area", "count": "Crime Incidents"},
                template="plotly_white"
            )
            bar_crime_area.update_traces(
                hovertemplate="Area: %{y}<br>Incidents: %{x:,}<extra></extra>"
            )
            bar_crime_area.update_layout(
                width=700,
                height=400,
                margin=dict(l=180, r=40, t=60, b=50),
                yaxis=dict(categoryorder="total ascending")
            )
        else:
            bar_crime_area = px.scatter(
                title=f"No {category} crime count data by area ({start_date} to {end_date})",
                template="plotly_white"
            )
    else:
        bar_crime_area = px.scatter(
            title=f"No {category} crime count data by area ({start_date} to {end_date})",
            template="plotly_white"
        )
   

    # Chart 3: Scatter — Crime Count vs Median Rent (Filtered by Date & Category)
    if not df_category_date_range.empty:
        scatter_crime_rent = px.scatter(
            df_category_date_range,
            x="median_rent",
            y="count",
            color="Borough",
            title=f"{category} Crime vs. Median Rent by Borough ({start_date} to {end_date})",
            labels={"median_rent": "Median Rent (USD)", "count": "Crime Incidents"},
            template="plotly_white",
            hover_name="precinct_area"
        )

        scatter_crime_rent.update_traces(
            marker=dict(size=5, opacity=0.6, line=dict(width=0)),
            hovertemplate=(
                "Area: %{hovertext}<br>"
                "Borough: %{marker.color}<br>"
                "Date: %{customdata[0]|%Y-%m-%d}<br>"
                "Median Rent: $%{x:,.0f}<br>"
                "Crime Incidents: %{y:,}<extra></extra>"
            ),
            customdata=df_category_date_range[["date"]].to_numpy()
        )

        scatter_crime_rent.update_layout(
            width=700,
            height=400,
            margin=dict(l=100, r=160, t=60, b=50),
            legend_title_text="Borough"
        )
        scatter_crime_rent.update_xaxes(tickprefix="$")
    else:
        scatter_crime_rent = px.scatter(
            title=f"No {category} crime vs rent data ({start_date} to {end_date})",
            template="plotly_white"
        )


  
    # Chart 4: Box Plot — Rent Distribution by Borough (Date Range)
    if not filtered_df_date_range.empty:
        box_rent = px.box(
            filtered_df_date_range,
            x="Borough",
            y="median_rent",
            title=f"Rent Distribution by Borough ({start_date} to {end_date})",
            labels={
                "Borough": "Borough",
                "median_rent": "Median Rent (USD)"
            },
            template="plotly_white"
        )

        box_rent.update_traces(
            hovertemplate="Borough: %{x}<br>Median Rent: $%{y:,.0f}<extra></extra>"
        )

        box_rent.update_layout(
            width=700,
            height=400,
            margin=dict(l=100, r=40, t=60, b=50)
        )
        box_rent.update_yaxes(tickprefix="$")

    else:
        box_rent = px.scatter(
            title=f"No Rent Distribution data ({start_date} to {end_date})",
            template="plotly_white"
        )
   
    # Chart 5: Heatmap — Avg Danger Ratio by Precinct Area and Month (Date Range)
    if not filtered_df_date_range.empty:
        df_h = filtered_df_date_range.copy()
        df_h["month"] = df_h["date"].dt.to_period("M").dt.to_timestamp()

        heatmap_df_agg = (
            df_h.groupby(["precinct_area", "month"], as_index=False)["danger_ratio"]
            .mean()
            .rename(columns={"danger_ratio": "avg_danger_ratio"})
        )

        if not heatmap_df_agg.empty:
            # Keep top N areas to avoid unreadable axis
            topN = 25
            top_areas = (
                heatmap_df_agg.groupby("precinct_area", as_index=False)["avg_danger_ratio"]
                .mean()
                .sort_values("avg_danger_ratio", ascending=False)
                .head(topN)["precinct_area"]
            )
            heatmap_df_agg = heatmap_df_agg[heatmap_df_agg["precinct_area"].isin(top_areas)]

            pivot = heatmap_df_agg.pivot(index="precinct_area", columns="month", values="avg_danger_ratio")

            heat_danger = px.imshow(
                pivot,
                aspect="auto",
                color_continuous_scale="Reds",
                labels=dict(x="Month", y="Precinct Area", color="Avg Danger Ratio"),
                title=f"Top {topN} Danger Ratio by Precinct and Month ({start_date} to {end_date})",
                template="plotly_white"
            )

            heat_danger.update_layout(
                width=700,
                height=400,
                margin=dict(l=180, r=40, t=60, b=60),
                xaxis=dict(tickformat="%Y-%m")
            )
        else:
            heat_danger = px.scatter(
                title=f"No aggregated data for Heatmap ({start_date} to {end_date})",
                template="plotly_white"
            )
    else:
        heat_danger = px.scatter(
            title=f"No data for Heatmap ({start_date} to {end_date})",
            template="plotly_white"
        )


    # Chart 6: Bar Plot — Average Danger Ratio by Precinct Area (Date Range)
    if not filtered_df_date_range.empty:
        bar_danger_area_df = (
            filtered_df_date_range
            .groupby("precinct_area", as_index=False)["danger_ratio"]
            .mean()
            .sort_values("danger_ratio", ascending=False)
            .head(20)  # Top 20 for readability
        )

        if not bar_danger_area_df.empty:
            bar_danger_area = px.bar(
                bar_danger_area_df,
                x="danger_ratio",
                y="precinct_area",
                orientation="h",
                title=f"Top 20 Precinct by Average Danger Ratio ({start_date} to {end_date})",
                labels={"precinct_area": "Precinct Area", "danger_ratio": "Average Danger Ratio"},
                template="plotly_white"
            )

            bar_danger_area.update_traces(
                hovertemplate="Area: %{y}<br>Avg Danger Ratio: %{x:.3f}<extra></extra>"
            )

            bar_danger_area.update_layout(
                width=700,
                height=400,
                margin=dict(l=180, r=40, t=60, b=50),
                yaxis=dict(categoryorder="total ascending")
            )
        else:
            bar_danger_area = px.scatter(
                title=f"No Danger Ratio data by Area ({start_date} to {end_date})",
                template="plotly_white"
            )
    else:
        bar_danger_area = px.scatter(
            title=f"No Danger Ratio data by Area ({start_date} to {end_date})",
            template="plotly_white"
        )

    # --- Chart 7: Median Rent Trend (Overall or by Area) ---
    if not filtered_df_date_range.empty:
        if area_name_selected in ("Overall", None):
            df7 = filtered_df_date_range
            chart7_title = f"Median Rent Trend (Overall) ({start_date} to {end_date})"
        else:
            df7 = filtered_df_date_range[filtered_df_date_range["areaName"] == area_name_selected].copy()
            chart7_title = f"Median Rent Trend ({area_name_selected}) ({start_date} to {end_date})"

        rent_trend_df_chart7 = (
            df7.groupby(pd.Grouper(key="date", freq="ME"))["median_rent"]
            .median()
            .reset_index()
        )

        if not rent_trend_df_chart7.empty:
            rent_trend_figure = px.line(
                rent_trend_df_chart7,
                x="date",
                y="median_rent",
                title=chart7_title,
                labels={"date": "Date", "median_rent": "Median Rent (USD)"},
                template="plotly_white",
            )
            rent_trend_figure.update_traces(
                line=dict(width=2),
                hovertemplate="Month: %{x|%b %Y}<br>Median Rent: $%{y:,.0f}<extra></extra>"
            )
            rent_trend_figure.update_layout(margin={"l": 100, "r": 40, "t": 60, "b": 50})
            rent_trend_figure.update_yaxes(tickprefix="$")
        else:
            rent_trend_figure = px.scatter(title=f"No rent data ({start_date} to {end_date})", template="plotly_white")
    else:
        rent_trend_figure = px.scatter(title=f"No data for rent trend ({start_date} to {end_date})", template="plotly_white")


    # --- Chart 8: Average Danger Ratio Trend (Overall or by Area) ---
    if not filtered_df_date_range.empty:
        if area_name_selected in ("Overall", None):
            df8 = filtered_df_date_range
            chart8_title = f"Average Danger Ratio Trend (Overall) ({start_date} to {end_date})"
        else:
            df8 = filtered_df_date_range[filtered_df_date_range["areaName"] == area_name_selected].copy()
            chart8_title = f"Average Danger Ratio Trend ({area_name_selected}) ({start_date} to {end_date})"

        danger_trend_df_chart8 = (
            df8.groupby(pd.Grouper(key="date", freq="ME"))["danger_ratio"]
            .mean()
            .reset_index()
        )

        if not danger_trend_df_chart8.empty:
            overall_danger_trend_figure = px.line(
                danger_trend_df_chart8,
                x="date",
                y="danger_ratio",
                title=chart8_title,
                labels={"date": "Date", "danger_ratio": "Average Danger Ratio"},
                template="plotly_white",
            )
            overall_danger_trend_figure.update_traces(
                line=dict(width=2),
                hovertemplate="Month: %{x|%b %Y}<br>Avg Danger Ratio: %{y:.3f}<extra></extra>"
            )
            overall_danger_trend_figure.update_layout(margin={"l": 90, "r": 40, "t": 60, "b": 50})
        else:
            overall_danger_trend_figure = px.scatter(title=f"No danger ratio data ({start_date} to {end_date})", template="plotly_white")
    else:
        overall_danger_trend_figure = px.scatter(title=f"No data for danger ratio trend ({start_date} to {end_date})", template="plotly_white")


    # Chart 9: Choropleth: Latest Median Rent by ZIP Code - Filtered by Date Range
    if not filtered_df_date_range.empty:
        filtered_df_exploded = filtered_df_date_range.explode("ZIP Codes").copy()

        # Clean ZIP
        filtered_df_exploded = filtered_df_exploded.dropna(subset=["ZIP Codes", "date", "median_rent"]).copy()
        filtered_df_exploded["ZIP Codes"] = (
            filtered_df_exploded["ZIP Codes"]
            .astype(str)
            .str.extract(r"(\d+)")[0]
            .str.zfill(5)
        )
        filtered_df_exploded = filtered_df_exploded[filtered_df_exploded["ZIP Codes"].notna()].copy()

        # Latest rent per ZIP within date range (robust)
        if not filtered_df_exploded.empty:
            idx = filtered_df_exploded.groupby("ZIP Codes")["date"].idxmax()
            latest_rent_by_zip_agg = filtered_df_exploded.loc[idx, ["ZIP Codes", "date", "median_rent"]]
        else:
            latest_rent_by_zip_agg = pd.DataFrame({"ZIP Codes": [], "date": [], "median_rent": []})

        geojson_data_url = "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/ny_new_york_zip_codes_geo.min.json"

        choropleth_rent = px.choropleth_map(
            latest_rent_by_zip_agg,
            geojson=geojson_data_url,
            locations="ZIP Codes",
            featureidkey="properties.ZCTA5CE10",
            color="median_rent",
            color_continuous_scale="Blues",
            center={"lat": 40.73, "lon": -73.94},
            zoom=10,
            title=f"Latest Median Rent by ZIP Code ({start_date} to {end_date})",
            labels={"median_rent": "Median Rent (USD)", "ZIP Codes": "ZIP Code"},
            template="plotly_white"
        )

        choropleth_rent.update_traces(
            hovertemplate="ZIP: %{location}<br>Median Rent: $%{z:,.0f}<extra></extra>"
        )

        choropleth_rent.update_layout(margin={"r": 0, "l": 0, "b": 0, "t": 40})

    else:
        choropleth_rent = px.scatter(
            title=f"No data for Choropleth ({start_date} to {end_date})",
            template="plotly_white"
        )

    # Output order: Chart 1, 2, 3, 4, 5, 6, 7, 8, 9
    return (
        line_crime_trend,      
        bar_crime_area,         
        scatter_crime_rent,      
        box_rent,               
        heat_danger,          
        bar_danger_area,        
        rent_trend_figure,      
        overall_danger_trend_figure, 
        choropleth_rent          
    )


# === Run App ===
if __name__ == "__main__":
    # Create assets folder if it doesn't exist 
    assets_folder = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)
        print(f"Created '{assets_folder}' folder.")

    app.run(debug=True, port=8054)