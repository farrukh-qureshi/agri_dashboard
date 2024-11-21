import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from utils.nasa_data import get_historical_data
from utils.visualization import display_weather_insights
import pandas as pd
import os
from datetime import datetime, timedelta

def cleanup_old_files(directory="data", max_age_days=7):
    """Remove files older than max_age_days from the specified directory"""
    try:
        if not os.path.exists(directory):
            return
            
        current_time = datetime.now()
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            # Skip if it's a directory
            if os.path.isdir(filepath):
                continue
                
            file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if current_time - file_modified_time > timedelta(days=max_age_days):
                os.remove(filepath)
                
    except Exception as e:
        st.error(f"Error cleaning up old files: {str(e)}")

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
    cleanup_old_files()
    
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
        if 'latitude' not in st.session_state:
            st.session_state.latitude = 32.6689
            st.session_state.longitude = 71.8107

        latitude = st.session_state.latitude
        longitude = st.session_state.longitude
        zoom_level = 5
        
        # Handle location search
        if search_button and location:
            location_data = search_location(location)
            if location_data:
                st.session_state.latitude = location_data.latitude
                st.session_state.longitude = location_data.longitude
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
            st.session_state.latitude = map_data['last_clicked']['lat']
            st.session_state.longitude = map_data['last_clicked']['lng']
            latitude = st.session_state.latitude
            longitude = st.session_state.longitude
            st.info(f"📌 Selected coordinates: {latitude:.4f}°N, {longitude:.4f}°E")

    with form_col:
        st.subheader("⚙️ Data Configuration")
        
        # Move time range selector outside the form for immediate updates
        time_range = st.radio(
            "📅 Select Time Range",
            options=["Recent Days", "Historical Years"],
            help="Choose between recent daily data or historical yearly data"
        )
        
        with st.form("data_selection_form"):
            st.markdown("**Selected Location:**")
            st.info(f"🌍 Latitude: {latitude:.4f}°N\n\n🌍 Longitude: {longitude:.4f}°E")
            
            # Conditional slider based on time range
            if time_range == "Recent Days":
                time_value = st.slider(
                    "Select number of days",
                    min_value=1,
                    max_value=90,
                    value=30,
                    help="Choose number of days to fetch weather data for"
                )
                time_unit = "days"
            else:
                time_value = st.slider(
                    "Select number of years",
                    min_value=1,
                    max_value=15,
                    value=10,
                    help="Choose number of years to fetch historical weather data for"
                )
                time_unit = "years"
                st.warning("⚠️ Fetching multiple years of data may take several minutes. Please be patient.")
            
            submitted = st.form_submit_button("📥 Fetch Weather Data")
    
    if submitted:
        st.markdown("---")
        st.subheader(f"📊 Weather Data Analysis - Last {time_value} {time_unit}")
        st.markdown(f"*Location: {latitude:.4f}°N, {longitude:.4f}°E*")

        with st.spinner("🔄 Fetching weather data..."):
            try:
                if time_unit == "days":
                    df = get_historical_data(days=time_value, latitude=latitude, longitude=longitude)
                else:
                    df = get_historical_data(days=time_value*365, latitude=latitude, longitude=longitude)
                
                if df is not None and not df.empty:
                    display_weather_insights(df, latitude, longitude, 
                                          days=time_value if time_unit == "days" else time_value*365)
                else:
                    st.error("❌ No data available for the selected location and time period.")
            
            except Exception as e:
                st.error(f"❌ Error fetching weather data: {str(e)}")
                st.info("💡 Please try a different location or time period.")

        

if __name__ == "__main__":
    main() 