import streamlit as st
import plotly.express as px
from utils.nasa_data import get_last_30_days_data
import pandas as pd

def main():
    st.set_page_config(
        page_title="Weather Data Portal",
        page_icon="🌤️",
        layout="wide"
    )

    st.title("📊 Weather Data Portal")
    st.subheader("Temperature and Humidity Data for Last 30 Days")
    st.write("Location: Latitude 32.68°N, Longitude 71.78°E")

    # Load data
    with st.spinner("Fetching weather data..."):
        df = get_last_30_days_data()

    if df is not None:
        # Show data quality metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Hours", len(df))
        with col2:
            st.metric("Data Completeness", f"{(len(df) / (30*24) * 100):.1f}%")
        with col3:
            st.metric("Date Range", f"{df['Date'].min().date()} to {df['Date'].max().date()}")

        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Temperature", "Humidity", "Combined View"])

        with tab1:
            st.subheader("Temperature Trends")
            fig_temp = px.line(
                df,
                x='Date',
                y='T2M',
                title='Temperature Over Time',
                labels={'T2M': 'Temperature (°C)', 'Date': 'Date/Time'}
            )
            st.plotly_chart(fig_temp, use_container_width=True)

            # Daily statistics for temperature
            daily_temp = df.groupby(df['Date'].dt.date)['T2M'].agg(['min', 'max', 'mean'])
            st.subheader("Daily Temperature Statistics")
            st.dataframe(daily_temp.round(2))

        with tab2:
            st.subheader("Humidity Trends")
            fig_humid = px.line(
                df,
                x='Date',
                y='RH2M',
                title='Relative Humidity Over Time',
                labels={'RH2M': 'Relative Humidity (%)', 'Date': 'Date/Time'}
            )
            st.plotly_chart(fig_humid, use_container_width=True)

            # Daily statistics for humidity
            daily_humid = df.groupby(df['Date'].dt.date)['RH2M'].agg(['min', 'max', 'mean'])
            st.subheader("Daily Humidity Statistics")
            st.dataframe(daily_humid.round(2))

        with tab3:
            st.subheader("Combined Temperature and Humidity View")
            fig_combined = px.line(
                df,
                x='Date',
                y=['T2M', 'RH2M'],
                title='Temperature and Humidity Over Time',
                labels={
                    'T2M': 'Temperature (°C)',
                    'RH2M': 'Relative Humidity (%)',
                    'Date': 'Date/Time'
                }
            )
            st.plotly_chart(fig_combined, use_container_width=True)

    else:
        st.error("Failed to fetch weather data. Please try again later.")

if __name__ == "__main__":
    main() 