import streamlit as st
from utils.visualization import display_weather_insights, display_agricultural_analysis, display_weather_parameters, display_data_export

def main():
    st.set_page_config(page_title="Weather Analysis Dashboard", layout="wide")
    
    # Initialize session state if not exists
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Overview"
    
    # Sidebar navigation
    st.sidebar.markdown("## 📊 Navigation")
    navigation = st.sidebar.radio(
        "Select Section",
        ["Overview", "Agricultural Analysis", "Weather Parameters", "Data Export"],
        key="navigation",
        on_change=update_page
    )
    
    # Load or get your data here
    df = load_data()  # Your data loading function
    latitude = your_latitude  # Your latitude value
    longitude = your_longitude  # Your longitude value
    days = your_days  # Your days value
    
    # Display the appropriate page based on navigation
    if st.session_state.current_page == "Overview":
        display_weather_insights(df, latitude, longitude, days)
    elif st.session_state.current_page == "Agricultural Analysis":
        display_agricultural_analysis(df)
    elif st.session_state.current_page == "Weather Parameters":
        display_weather_parameters(df)
    elif st.session_state.current_page == "Data Export":
        display_data_export(df)

def update_page():
    st.session_state.current_page = st.session_state.navigation

if __name__ == "__main__":
    main() 