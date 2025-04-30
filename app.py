# Roof Measurement Prototype

**User need:**
> A simple web app where you can pan/zoom to any property, draw the roof outline by clicking corners, and instantly get:
> 1. **Total roof area** (ft²)  
> 2. **Total perimeter** (ft)  
> 3. **Approximate highest elevation** (ft)

---

## App design

### Tech stack
- **Streamlit** for UI and rapid deployment  
- **Folium** with **Leaflet Draw** plugin for interactive map & drawing  
- **Streamlit-Folium** integration to embed the map  
- **Shapely** & **PyProj** for geometry calculations  
- **Mapbox Satellite tiles** (via tile URL + access token) for high-resolution imagery  

### File structure
```
roof-measurement-proto/
├── app.py
├── requirements.txt
└── README.md
```

#### requirements.txt
```
streamlit
folium
streamlit-folium
shapely
pyproj
```

### app.py outline
```python
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

# --- CONFIG ---
MAPBOX_TOKEN = "<YOUR_TOKEN>"
DEFAULT_LOCATION = [<lat>, <lon>]  # e.g. center of your area or fallback

# --- HELPERS ---
def compute_metrics(geojson_polygon):
    # project to metric CRS, compute area & length, convert to ft²/ft
    pass

def fetch_peak_height(lon, lat):
    # optional: call Mapbox Terrain-RGB API, decode elevation, return max
    pass

# --- UI ---
st.set_page_config(layout="wide")
st.title("🏠 Roof Measurement Prototype")

st.write("Pan/zoom to your roof, draw the polygon, get instant area, perimeter, height.")

# build folium map: add Satellite + OSM layers, add Draw(polygon-only)
m = folium.Map(location=DEFAULT_LOCATION, zoom_start=18)
# add tile layers & Draw plugin...

# embed map and capture drawn polygon
output = st_folium(m, width=800, height=600, returned_objects=['last_drawn_feature'])
poly = output.get('last_drawn_feature')

if poly:
    area, peri = compute_metrics(poly['geometry'])
    st.success(f"Area: {area:.1f} ft² | Perimeter: {peri:.1f} ft")
    height = fetch_peak_height(...)
    if height:
        st.success(f"Approx. peak height: {height:.1f} ft")
```

---

**Next steps:**
1. Fill in the helper functions with actual code.  
2. Deploy `app.py` on Streamlit Cloud.  
3. Test by drawing on a sample roof and verifying metrics.  
