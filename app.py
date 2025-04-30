```python
# app.py

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from shapely.geometry import shape
from shapely.ops import transform
import pyproj
import requests
import math

# --- CONFIG ---
MAPBOX_TOKEN = "pk.eyJ1IjoiY2FzZXlyYXk0IiwiYSI6ImNtYTRic2JzdTA1bTcya3B5bzZibjZsdGIifQ.JYBfeSWP0uf7CdJjWOnsHg"
# Fallback center: Pequot Lakes, MN
default_lat, default_lon = 46.5547, -94.3559

# --- HELPERS ---

def compute_metrics(polygon_geojson):
    """
    Given a GeoJSON Polygon, project to EPSG:3857 to calculate area and perimeter,
    then convert to square feet and feet.
    """
    # Convert to Shapely geometry
    poly = shape(polygon_geojson)
    # Project to metric (meters)
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(project, poly)
    area_m2 = poly_m.area
    peri_m = poly_m.length
    # Convert to ft² and ft
    area_ft2 = area_m2 * 10.7639
    peri_ft = peri_m * 3.28084
    return area_ft2, peri_ft


def fetch_peak_height(lon, lat, zoom=14):
    """
    Fetch approximate peak elevation via Mapbox Terrain-RGB.
    Decodes the single pixel at the given location for elevation.
    """
    # Calculate tile coordinates
    def deg2num(lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return xtile, ytile

    xt, yt = deg2num(lat, lon, zoom)
    url = f"https://api.mapbox.com/v4/mapbox.terrain-rgb/{zoom}/{xt}/{yt}@2x.pngraw?access_token={MAPBOX_TOKEN}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    from io import BytesIO
    from PIL import Image
    img = Image.open(BytesIO(resp.content))
    # Sample center pixel
    w, h = img.size
    r, g, b = img.getpixel((w//2, h//2))
    # Decode height per Mapbox spec
    height = -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)
    return height  # in meters

# --- UI ---
st.set_page_config(layout="wide", page_title="Roof Measurement")
st.title("🏠 Roof Measurement Prototype")

st.markdown(
    "1. Pan/zoom to your property (default = Pequot Lakes, MN).  
     2. Use the draw tool (top-left) to outline the roof.  
     3. Complete the polygon; area & perimeter will display below.  
     4. Peak height (via Terrain-RGB) shows if available."
)

# Initialize map
m = folium.Map(
    location=[default_lat, default_lon],
    zoom_start=18,
    max_zoom=22,
    control_scale=True
)
# Add tile layers
folium.TileLayer(
    tiles=f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_TOKEN}",
    attr="Mapbox Satellite",
    name="Satellite",
    overlay=False,
    control=True,
    tile_size=512,
    zoom_offset=-1
).add_to(m)
folium.TileLayer("OpenStreetMap", name="OSM", overlay=False, control=True).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
# Enable drawing polygons only
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

# Render map and capture drawn polygon
output = st_folium(m, width=800, height=500, returned_objects=['last_drawn_feature'])
feature = output.get('last_drawn_feature')

if feature and feature.get('geometry', {}).get('type') == 'Polygon':
    area, peri = compute_metrics(feature['geometry'])
    st.success(f"**Area:** {area:,.1f} ft²   **Perimeter:** {peri:,.1f} ft")
    # Peak height
    coords = feature['geometry']['coordinates'][0]
    # pick centroid for height sample
    lon = sum(pt[0] for pt in coords) / len(coords)
    lat = sum(pt[1] for pt in coords) / len(coords)
    height_m = fetch_peak_height(lon, lat)
    if height_m is not None:
        height_ft = height_m * 3.28084
        st.success(f"**Approx. Peak Elevation:** {height_ft:,.1f} ft above sea level")
    else:
        st.info("Peak elevation unavailable.")
else:
    st.info("🔍 Draw a polygon to compute roof metrics.")
```
