import streamlit as st

def main():
    st.set_page_config(
        page_title="Weather Data Portal",
        page_icon="🌤️",
        layout="wide"
    )

    st.title("🌤️ Weather Data Portal")
    st.markdown("---")

    st.markdown("""
    Welcome to the Weather Data Portal! Choose from the following pages:
    
    - **📊 Analysis**: View detailed weather data analysis and insights
    - **🔮 Predictions**: Generate weather predictions using machine learning
    
    Select a page from the sidebar to get started.
    """)

if __name__ == "__main__":
    main() 