import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

# --- CONFIG ---
MAPBOX_TOKEN = "pk.eyJ1IjoiY2FzZXlyYXk0IiwiYSI6ImNtYTRic2JzdTA1bTcya3B5bzZibjZsdGIifQ.JYBfeSWP0uf7CdJjWOnsHg"
DEFAULT_LOCATION = [46.5547, -94.3559]  # Pequot Lakes, MN

# --- HELPERS ---

def compute_metrics(geom):
    poly = shape(geom)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(transformer, poly)
    area_ft2 = poly_m.area * 10.7639
    peri_ft = poly_m.length * 3.28084
    return area_ft2, peri_ft

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

st.markdown("""
1. Pan/zoom to your property.
2. Trace the roof outline with the draw tool (top-left).
3. Finish the polygon; metrics will display below.
"""
)

# Initialize map
draw_map = folium.Map(location=DEFAULT_LOCATION, zoom_start=18, max_zoom=22, control_scale=True)
# Add base layers
tiles = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_TOKEN}"
folium.TileLayer(tiles=tiles, attr="Satellite", name="Satellite", control=True, overlay=False).add_to(draw_map)
folium.TileLayer("OpenStreetMap", name="OSM", control=True, overlay=False).add_to(draw_map)
folium.LayerControl(collapsed=False).add_to(draw_map)
# Enable only polygon drawing
draw = Draw(export=False,
            draw_options={'polygon': True, 'polyline': False, 'rectangle': False, 'circle': False, 'marker': False},
            edit_options={'edit': True, 'remove': True})
draw.add_to(draw_map)

# Render map and capture last drawn feature
output = st_folium(draw_map, width=800, height=500, returned_objects=['last_drawn_feature'])
feature = output.get('last_drawn_feature')

if feature and feature.get('geometry', {}).get('type') == 'Polygon':
    area, peri = compute_metrics(feature['geometry'])
    st.success(f"**Area:** {area:,.1f} ft²    **Perimeter:** {peri:,.1f} ft")
else:
    st.info("🔍 Draw a polygon around the roof to see measurements.")
"
