import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import requests
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

# --- CONFIG ---
MAPBOX_TOKEN = "pk.eyJ1IjoiY2FzZXlyYXk0IiwiYSI6ImNtYTRic2JzdTA1bDcya3B5bzZibjZsdGIifQ.JYBfeSWP0uf7CdJjWOnsHg"

# --- HELPERS ---

def geocode(address):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    resp = requests.get(url, params=params).json()
    feat = resp.get("features", [None])[0]
    if not feat:
        st.error("❌ Geocoding failed. Check your address.")
        return None, None
    lon, lat = feat["center"]
    return lon, lat


def create_map(lon, lat, zoom_start=20, max_zoom=25):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_start, max_zoom=max_zoom, control_scale=True)
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
            tiles = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/tiles/{{z}}/{{x}}/{{y}}@2x"
                f"?access_token={MAPBOX_TOKEN}"
            )
            folium.TileLayer(
                tiles=tiles,
                attr=f"Mapbox {name}",
                name=name,
                control=True,
                tile_size=512,
                zoom_offset=-1
            ).add_to(m)
        else:
            folium.TileLayer('OpenStreetMap', name=name, control=True).add_to(m)

    # Draw only polygons
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
        edit_options={'edit': True}
    ).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def compute_metrics(geom_geojson):
    poly = shape(geom_geojson)
    # project to metric
    proj = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(proj, poly)
    area_m2 = poly_m.area
    perimeter_m = poly_m.length
    # convert to feet
    return area_m2 * 10.7639, perimeter_m * 3.28084


def fetch_building_height(lon, lat):
    url = f"https://api.mapbox.com/v4/mapbox.mapbox-streets-v8/tilequery/{lon},{lat}.json"
    params = {"layers": "building", "access_token": MAPBOX_TOKEN}
    feats = requests.get(url, params=params).json().get('features', [])
    if feats:
        props = feats[0].get('properties', {})
        height = props.get('height') or props.get('building:levels')
        if height:
            m = float(height)
            # if levels, approximate 3m per story
            if 'levels' in props:
                m *= 3
            return m * 3.28084
    return None

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

address = st.text_input("Enter address", "1600 Pennsylvania Ave NW, Washington, DC")
zoom = st.slider("Zoom level", min_value=15, max_value=25, value=20)
if st.button("Run"):
    lon, lat = geocode(address)
    if lon is not None:
        m = create_map(lon, lat, zoom_start=zoom, max_zoom=25)
        st.markdown(
            "**Draw a polygon around the roof plane:** use the top-left toolbar and double-click to finish. "
            "Switch layers in the top-right control. Zoom in fully for precise corner picks."
        )
        out = st_folium(m, width=900, height=600, returned_objects=["last_drawn_feature"])
        feat = out.get("last_drawn_feature")
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
