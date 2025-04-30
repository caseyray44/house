import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import requests
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

# --- CONFIG ---
MAPBOX_TOKEN = "pk.eyJ1IjoiY2FzZXlyYXk0IiwiYSI6ImNtYTRic2JzdTA1bTcya3B5bzZibjZsdGIifQ.JYBfeSWP0uf7CdJjWOnsHg"
DEFAULT_LOCATION = [46.5547, -94.3559]  # Pequot Lakes, MN

# --- HELPERS ---

def compute_metrics(geom):
    poly = shape(geom)
    # project to metric
    proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(proj, poly)
    area_ft2 = poly_m.area * 10.7639
    peri_ft = poly_m.length * 3.28084
    return area_ft2, peri_ft

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

# Instructions
st.write(
    "1. Pan/zoom to your property.\n"
    "2. Use the draw tool (top-left) to trace the roof.\n"
    "3. Complete the polygon; metrics appear below automatically."
)

# Create map
m = folium.Map(
    location=DEFAULT_LOCATION,
    zoom_start=18,
    max_zoom=22,
    control_scale=True
)
# Add Mapbox Satellite layer
tiles = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_TOKEN}"
folium.TileLayer(tiles=tiles, attr="Satellite", name="Satellite", overlay=False, control=True).add_to(m)
# Add OpenStreetMap layer
folium.TileLayer("OpenStreetMap", name="OSM", overlay=False, control=True).add_to(m)
# Add layer control
folium.LayerControl(collapsed=False).add_to(m)
# Enable drawing of polygons only
draw = Draw(
    export=False,
    draw_options={
        'polygon': True,
        'polyline': False,
        'rectangle': False,
        'circle': False,
        'marker': False,
        'circlemarker': False
    },
    edit_options={'edit': True, 'remove': True}
)
draw.add_to(m)

# Render map and capture drawn features
output = st_folium(m, width=800, height=500, returned_objects=['all_drawn_features'])
features = output.get('all_drawn_features') or []
if features:
    feat = features[-1]
    geom = feat.get('geometry')
    if geom and geom.get('type') == 'Polygon':
        area, peri = compute_metrics(geom)
        st.success(f"**Area:** {area:,.1f} ft²    **Perimeter:** {peri:,.1f} ft")
else:
    st.info("🔍 Draw a polygon to compute metrics.")
