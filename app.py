import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from utils.nasa_data import get_historical_data
from utils.visualization import display_weather_insights
import pandas as pd

def init_map(lat, lon, zoom=5):
    """Initialize folium map with markers and styling"""
    m = folium.Map(location=[lat, lon], zoom_start=zoom)
    # Add click functionality
    m.add_child(folium.LatLngPopup())
    # Add default marker
    folium.Marker(
        [lat, lon],
        popup="Current Selection",
        icon=folium.Icon(color="red", icon="info-sign"),
    ).add_to(m)
    return m

def search_location(query):
    """Search location with error handling"""
    try:
        geolocator = Nominatim(user_agent="weather_app")
        location_data = geolocator.geocode(query, timeout=10)
        if location_data:
            return location_data
        return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        st.error(f"Error searching location: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Weather Data Portal",
        page_icon="🌤️",
        layout="wide"
    )

    st.title("📊 Weather Data Portal")
    st.markdown("---")

    # Create columns for map and form
    map_col, form_col = st.columns([1, 1])
    
    with map_col:
        st.subheader("📍 Location Selection")
        
        # Search functionality
        location = st.text_input(
            "Search Location",
            placeholder="Enter city, region, or country (e.g., Lahore, Pakistan)"
        )
        search_button = st.button("🔍 Search")
        
        # Initialize default coordinates (Pakistan)
        latitude = 30.3753
        longitude = 69.3451
        zoom_level = 5
        
        # Handle location search
        if search_button and location:
            location_data = search_location(location)
            if location_data:
                latitude = location_data.latitude
                longitude = location_data.longitude
                zoom_level = 12
                st.success(f"📍 Found: {location_data.address}")
        
        # Initialize and display map
        m = init_map(latitude, longitude, zoom_level)
        map_data = st_folium(
            m,
            width=400,
            height=400,
            returned_objects=["last_clicked"]
        )
        
        # Update coordinates from map click
        if map_data['last_clicked']:
            latitude = map_data['last_clicked']['lat']
            longitude = map_data['last_clicked']['lng']
            st.info(f"📌 Selected coordinates: {latitude:.4f}°N, {longitude:.4f}°E")

    with form_col:
        st.subheader("⚙️ Data Configuration")
        with st.form("data_selection_form"):
            st.markdown("**Selected Location:**")
            st.info(f"🌍 Latitude: {latitude:.4f}°N\n\n🌍 Longitude: {longitude:.4f}°E")
            
            days = st.slider(
                "📅 Select time period",
                min_value=1,
                max_value=90,
                value=30,
                help="Choose number of days to fetch weather data for"
            )
            
            submitted = st.form_submit_button("📥 Fetch Weather Data")
    
    if submitted:
        st.markdown("---")
        st.subheader(f"📊 Weather Data Analysis - Last {days} Days")
        st.markdown(f"*Location: {latitude:.4f}°N, {longitude:.4f}°E*")

        with st.spinner("🔄 Fetching weather data..."):
            try:
                df = get_historical_data(days=days, latitude=latitude, longitude=longitude)
                if df is not None and not df.empty:
                    # Call the visualization function
                    display_weather_insights(df, latitude, longitude, days)
                else:
                    st.error("❌ No data available for the selected location and time period.")
            
            except Exception as e:
                st.error(f"❌ Error fetching weather data: {str(e)}")
                st.info("💡 Please try a different location or time period.")

if __name__ == "__main__":
    main() 