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
        st.error("Geocoding failed. Check your address.")
        return None, None
    lon, lat = feat["center"]
    return lon, lat


def create_map(lon, lat, zoom_start=18, max_zoom=22):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_start, max_zoom=max_zoom, control_scale=True)
    # Base layer options
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
            tiles_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/tiles/{{z}}/{{x}}/{{y}}@2x"  # retina
                f"?access_token={MAPBOX_TOKEN}"
            )
            folium.TileLayer(
                tiles=tiles_url,
                attr=f"Mapbox {name}",
                name=name,
                control=True,
                tile_size=512,
                zoom_offset=-1
            ).add_to(m)
        else:
            folium.TileLayer('OpenStreetMap', name=name, control=True).add_to(m)

    # Drawing plugin (only polygon)
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
    projector = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    poly_m = transform(projector, poly)
    area_m2 = poly_m.area
    perimeter_m = poly_m.length
    # Convert to feet
    area_ft2 = area_m2 * 10.7639
    perimeter_ft = perimeter_m * 3.28084
    return area_ft2, perimeter_ft


def fetch_building_height(lon, lat):
    url = f"https://api.mapbox.com/v4/mapbox.mapbox-streets-v8/tilequery/{lon},{lat}.json"
    params = {"layers": "building", "access_token": MAPBOX_TOKEN}
    feats = requests.get(url, params=params).json().get('features', [])
    if feats:
        props = feats[0].get('properties', {})
        height = props.get('height') or props.get('building:levels')
        if height:
            if 'levels' in props:
                height_m = float(height) * 3
            else:
                height_m = float(height)
            return height_m * 3.28084
    return None

# --- APP ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

address = st.text_input("Enter address", "1600 Pennsylvania Ave NW, Washington, DC")
if st.button("Run"):
    lon, lat = geocode(address)
    if lon is not None and lat is not None:
        m = create_map(lon, lat, zoom_start=20, max_zoom=22)
        st.markdown(
            "**Draw a polygon around the roof plane**: use the drawing toolbar (top-left) and double-click to finish. "
            "Use the layer control (top-right) to switch imagery if needed. Zoom in closely for precise corner placement."
        )
        out = st_folium(m, width=800, height=600, returned_objects=["all_drawn_features"])
        feats = out.get("all_drawn_features") or []
        if feats and feats[-1].get("geometry", {}).get("type") == "Polygon":
            roof_poly = feats[-1]["geometry"]
            area_ft2, peri_ft = compute_metrics(roof_poly)
            st.success(f"**Area:** {area_ft2:,.1f} ft²  |  **Perimeter:** {peri_ft:,.1f} ft")
            height_ft = fetch_building_height(lon, lat)
            if height_ft:
                st.success(f"**Approx. Building Height:** {height_ft:.1f} ft")
            else:
                st.warning("Building height data not available from Mapbox Streets layer.")
        else:
            st.info("Draw a polygon first to compute metrics.")
