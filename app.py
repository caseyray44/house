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
DEFAULT_LON, DEFAULT_LAT = -94.3559, 46.5547  # Pequot Lakes center fallback

# --- HELPERS ---

def geocode(address):
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json"
        resp = requests.get(url, params={"access_token": MAPBOX_TOKEN, "limit": 1})
        feat = resp.json().get("features", [None])[0]
        if feat:
            return feat["center"]  # [lon, lat]
    except Exception:
        pass
    return None, None


def create_map(lon, lat, zoom_start=20, max_zoom=22):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_start, max_zoom=max_zoom, control_scale=True)
    # Add base layers
    layers = {
        'OpenStreetMap': None,
        'Satellite': 'satellite-v9',
        'Streets': 'streets-v11',
        'Light': 'light-v10'
    }
    for name, style in layers.items():
        if style:
            url = f"https://api.mapbox.com/styles/v1/mapbox/{style}/tiles/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_TOKEN}"
            folium.TileLayer(tiles=url, name=name, attr=name, control=True, overlay=False, tile_size=512, zoom_offset=-1).add_to(m)
        else:
            folium.TileLayer('OpenStreetMap', name=name, control=True, overlay=False).add_to(m)
    # Drawing plugin
    Draw(export=False, draw_options={'marker': False, 'circle': False, 'circlemarker': False,
                                     'rectangle': False,'polyline': False,'polygon': True},
         edit_options={'edit': True, 'remove': True}).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def compute_metrics(geom):
    poly = shape(geom)
    proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(proj, poly)
    return poly_m.area * 10.7639, poly_m.length * 3.28084


def fetch_building_height(lon, lat):
    try:
        url = f"https://api.mapbox.com/v4/mapbox.mapbox-streets-v8/tilequery/{lon},{lat}.json"
        feats = requests.get(url, params={"layers": "building", "access_token": MAPBOX_TOKEN}).json().get('features', [])
        if feats:
            props = feats[0].get('properties', {})
            h = props.get('height') or props.get('building:levels')
            if h:
                h = float(h) * (3 if 'building:levels' in props else 1)
                return h * 3.28084
    except Exception:
        pass
    return None

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

# Sidebar controls
st.sidebar.header("Map Controls")
address = st.sidebar.text_input("Address (optional)")
zoom = st.sidebar.slider("Zoom level", 15, 22, 20)
st.sidebar.write("Draw directly on the map to measure.")

# Determine center
lon, lat = geocode(address) if address else (None, None)
if lon is None or lat is None:
    st.sidebar.warning("Pan/zoom manually if address not found.")
    lon, lat = DEFAULT_LON, DEFAULT_LAT

# Create and show map
m = create_map(lon, lat, zoom_start=zoom, max_zoom=22)
output = st_folium(m, width=900, height=600, returned_objects=["last_drawn_feature"])
feat = output.get("last_drawn_feature")

if feat and feat.get("geometry", {}).get("type") == "Polygon":
    area, peri = compute_metrics(feat["geometry"])
    st.success(f"**Area:** {area:,.1f} ft²    **Perimeter:** {peri:,.1f} ft")
    height = fetch_building_height(lon, lat)
    if height:
        st.success(f"**Approx. Height:** {height:.1f} ft")
    else:
        st.info("Building height not available.")
else:
    st.info("🎯 Draw a polygon on the map to compute metrics.")
