import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from utils.nasa_data import get_historical_data
from utils.prediction import display_weather_predictions
import pandas as pd
from datetime import datetime, timedelta

# Define PARAMETERS dictionary
PARAMETERS = {
    'Temperature': {
        'column': 'T2M',
        'color': '#FF4B4B',
        'unit': '°C'
    },
    'Humidity': {
        'column': 'RH2M',
        'color': '#4B4BFF',
        'unit': '%'
    },
    'Precipitation': {
        'column': 'PRECTOTCORR',
        'color': '#9D4BFF',
        'unit': 'mm/hour'
    },
    'Wind Speed': {
        'column': 'WS2M',
        'color': '#4BFF4B',
        'unit': 'm/s'
    }
}

def init_map(lat, lon, zoom=5):
    """Initialize folium map with markers and styling"""
    m = folium.Map(location=[lat, lon], zoom_start=zoom)
    m.add_child(folium.LatLngPopup())
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
    # Initialize session state
    if 'latitude' not in st.session_state:
        st.session_state.latitude = 32.6689
        st.session_state.longitude = 71.8107

    st.title("🔮 Weather Predictions")
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
        st.subheader("⚙️ Prediction Settings")
        
        # Time range selector with custom date option
        time_range = st.radio(
            "📅 Select Training Data Range",
            options=["Recent Days", "Historical Years", "Custom Date Range"],
            help="Choose between recent daily data, historical yearly data, or custom date range"
        )
        
        with st.form("prediction_form"):
            st.markdown("**Selected Location:**")
            st.info(f"🌍 Latitude: {latitude:.4f}°N\n\n🌍 Longitude: {longitude:.4f}°E")
            
            # Conditional inputs based on time range selection
            if time_range == "Recent Days":
                days = st.slider(
                    "Select number of days for training",
                    min_value=30,
                    max_value=90,
                    value=60,
                    help="More historical data might improve prediction accuracy"
                )
                time_value = days
                time_unit = "days"
            elif time_range == "Historical Years":
                time_value = st.slider(
                    "Select number of years",
                    min_value=1,
                    max_value=15,
                    value=5,
                    help="Choose number of years for historical training data"
                )
                time_unit = "years"
                st.warning("⚠️ Fetching multiple years of data may take several minutes.")
            else:  # Custom Date Range
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=datetime.now() - timedelta(days=60),
                        max_value=datetime.now().date(),
                        help="Select start date for training data"
                    )
                with col2:
                    end_date = st.date_input(
                        "End Date",
                        value=datetime.now().date(),
                        max_value=datetime.now().date(),
                        min_value=start_date,
                        help="Select end date for training data"
                    )
                
                if start_date > end_date:
                    st.error("Error: End date must be after start date")
                time_unit = "custom"
            
            submitted = st.form_submit_button("🔮 Generate Predictions")

    if submitted:
        st.markdown("---")
        
        # Set title based on time range
        if time_range == "Custom Date Range":
            st.subheader(f"🔮 Weather Predictions ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        else:
            st.subheader(f"🔮 Weather Predictions - Last {time_value} {time_unit}")
            
        st.markdown(f"*Location: {latitude:.4f}°N, {longitude:.4f}°E*")

        with st.spinner("🔄 Fetching data and generating predictions..."):
            try:
                # Fetch historical data based on selected time range
                if time_range == "Custom Date Range":
                    days = (end_date - start_date).days + 1
                    df, is_cached = get_historical_data(
                        latitude=latitude,
                        longitude=longitude,
                        start_date=start_date,
                        end_date=end_date
                    )
                else:
                    days = time_value if time_unit == "days" else time_value * 365
                    df, is_cached = get_historical_data(
                        days=days,
                        latitude=latitude,
                        longitude=longitude
                    )
                
                if df is not None and not df.empty:
                    if is_cached:
                        st.success("📦 Using cached data")
                    else:
                        st.success("🌐 Successfully fetched new data")
                    st.success(f"✅ Data loaded successfully ({len(df)} records)")
                    
                    # Display predictions with automatic evaluation
                    display_weather_predictions(
                        df=df, 
                        parameters=PARAMETERS
                    )
                else:
                    st.error("❌ No data available for the selected location")
                    
            except Exception as e:
                st.error(f"❌ Error generating predictions: {str(e)}")
                st.info("💡 Please try a different location or time period")

if __name__ == "__main__":
    main()