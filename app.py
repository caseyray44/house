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
# Fallback center (Pequot Lakes, MN)
DEFAULT_LON, DEFAULT_LAT = -94.3559, 46.5547

# Initialize run state
if 'run' not in st.session_state:
    st.session_state.run = False

# --- HELPERS ---

def geocode(address):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    resp = requests.get(url, params=params).json()
    feat = resp.get("features", [None])[0]
    if not feat:
        return None, None
    lon, lat = feat["center"]
    return lon, lat


def create_map(lon, lat, zoom_start=18, max_zoom=22):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_start, max_zoom=max_zoom, control_scale=True)
    # Base layers
    styles = {
        'OSM': None,
        'Satellite': 'satellite-v9',
        'Satellite Streets': 'satellite-streets-v11',
        'Streets': 'streets-v11',
        'Light': 'light-v10',
        'Dark': 'dark-v10'
    }
    for name, style in styles.items():
        if style:
            tile_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/tiles/{{z}}/{{x}}/{{y}}@2x"
                f"?access_token={MAPBOX_TOKEN}"
            )
            folium.TileLayer(
                tiles=tile_url,
                name=name,
                control=True,
                overlay=False,
                tile_size=512,
                zoom_offset=-1,
                attr=f"Mapbox {name}"
            ).add_to(m)
        else:
            folium.TileLayer(
                tiles='OpenStreetMap',
                name=name,
                control=True,
                overlay=False
            ).add_to(m)
    Draw(
        export=False,
        draw_options={
            'polyline': False,
            'rectangle': False,
            'circle': False,
            'circlemarker': False,
            'marker': False,
            'polygon': True
        },
        edit_options={'edit': True, 'remove': True}
    ).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def compute_metrics(geom_geojson):
    poly = shape(geom_geojson)
    proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(proj, poly)
    area_m2 = poly_m.area
    perimeter_m = poly_m.length
    return area_m2 * 10.7639, perimeter_m * 3.28084


def fetch_building_height(lon, lat):
    url = f"https://api.mapbox.com/v4/mapbox.mapbox-streets-v8/tilequery/{lon},{lat}.json"
    params = {"layers": "building", "access_token": MAPBOX_TOKEN}
    feats = requests.get(url, params=params).json().get('features', [])
    if feats:
        props = feats[0].get('properties', {})
        height = props.get('height') or props.get('building:levels')
        if height:
            h = float(height)
            if 'levels' in props:
                h *= 3
            return h * 3.28084
    return None

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

# Input controls
left, right = st.columns([1, 3])
with left:
    address = st.text_input("Enter address", "1600 Pennsylvania Ave NW, Washington, DC")
    zoom = st.slider("Zoom level", min_value=15, max_value=22, value=20)
    if st.button("Run"):
        st.session_state.run = True

# Map and drawing
if st.session_state.run:
    lon, lat = geocode(address)
    if lon is None:
        st.warning("⚠️ Geocoding failed. Pan/zoom map manually to your property.")
        lon, lat = DEFAULT_LON, DEFAULT_LAT
    m = create_map(lon, lat, zoom_start=zoom, max_zoom=22)
    right.markdown(
        "**Draw a polygon around the roof plane**: use the toolbar (top-left) and double-click to finish. "
        "Switch layers (top-right) if trees block the view."
    )
    output = right.st_folium(m, width=900, height=600, returned_objects=["last_drawn_feature"])
    feat = output.get("last_drawn_feature")
    if feat and feat.get("geometry", {}).get("type") == "Polygon":
        poly = feat["geometry"]
        area_ft2, peri_ft = compute_metrics(poly)
        st.success(f"**Area:** {area_ft2:,.1f} ft²    **Perimeter:** {peri_ft:,.1f} ft")
        height = fetch_building_height(lon, lat)
        if height:
            st.success(f"**Approx. Height:** {height:.1f} ft")
        else:
            st.warning("Building height not available.")
    else:
        st.info("🎯 Draw a polygon then double-click to compute metrics.")
