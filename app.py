import streamlit as st
 from streamlit_folium import st_folium
 import folium
 from folium.plugins import Draw
 import requests
 from shapely.geometry import shape
 from shapely.ops import transform
 @@ -23,20 +24,33 @@
 
 
 def create_map(lon, lat, zoom=18):
     tiles_url = (
         f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{{z}}/{{x}}/{{y}}"
         f"?access_token={MAPBOX_TOKEN}"
     )
     m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None)
     folium.TileLayer(
         tiles=tiles_url,
         attr="Mapbox Satellite",
         name="Satellite",
         overlay=False,
         control=False,
     ).add_to(m)
     folium.LayerControl().add_to(m)
     folium.plugins.Draw(
     m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True)
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
             tiles = (
                 f"https://api.mapbox.com/styles/v1/mapbox/{style}/tiles/{{z}}/{{x}}/{{y}}"
                 f"?access_token={MAPBOX_TOKEN}"
             )
             folium.TileLayer(
                 tiles=tiles,
                 attr=f"Mapbox {name}",
                 name=name,
                 control=True
             ).add_to(m)
         else:
             folium.TileLayer('OpenStreetMap', name=name, control=True).add_to(m)
 
     # Drawing plugin
     Draw(
         export=False,
         draw_options={
             'polyline': False,
 @@ -47,12 +61,12 @@
         },
         edit_options={'edit': True}
     ).add_to(m)
     folium.LayerControl(collapsed=False).add_to(m)
     return m
 
 
 def compute_metrics(geom_geojson):
     poly = shape(geom_geojson)
     # Project from EPSG:4326 to EPSG:3857 for metric units
     projector = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
     poly_m = transform(projector, poly)
     area_m2 = poly_m.area
 @@ -71,7 +85,6 @@
         props = feats[0].get('properties', {})
         height = props.get('height') or props.get('building:levels')
         if height:
             # If building:levels, assume 3m per level
             if 'levels' in props:
                 height_m = float(height) * 3
             else:
 @@ -84,22 +97,24 @@
 st.title("🏠 Roof Measurement Prototype")
 
 address = st.text_input("Enter address", "1600 Pennsylvania Ave NW, Washington, DC")
 if st.button("Run"):  
 if st.button("Run"):
     lon, lat = geocode(address)
     if lon and lat:
     if lon is not None and lat is not None:
         m = create_map(lon, lat)
         st.markdown("**Draw a polygon around the roof plane**: use the drawing toolbar on the map and double-click to finish.")
         out = st_folium(m, width=800, height=500, returned_objects=["geometries"])
         geoms = out.get("geometries", [])
         if geoms:
             # Take the last polygon drawn
             roof_poly = geoms[-1]
         st.markdown(
             "**Draw a polygon around the roof plane**: use the drawing toolbar (top-left) and double-click to finish."  
             "Toggle base layers via the control (top-right) if trees obscure the view."
         )
         out = st_folium(m, width=800, height=500, returned_objects=["last_drawn_feature"])
         feat = out.get("last_drawn_feature")
         if feat and feat.get("geometry", {}).get("type") == "Polygon":
             roof_poly = feat["geometry"]
             area_ft2, peri_ft = compute_metrics(roof_poly)
             st.success(f"**Area:** {area_ft2:,.1f} ft²  |  **Perimeter:** {peri_ft:,.1f} ft")
             height_ft = fetch_building_height(lon, lat)
             if height_ft:
                 st.success(f"**Approx. Building Height:** {height_ft:.1f} ft")
             else:
                 st.warning("Building height data not available from Mapbox Streets layer.")
         else:
             st.info("Draw a polygon first to compute metrics.")
