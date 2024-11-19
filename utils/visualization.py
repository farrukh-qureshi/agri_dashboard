import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

def display_weather_insights(df: pd.DataFrame, latitude: float, longitude: float, days: int):
    """
    Display comprehensive weather insights and visualizations
    
    Args:
        df (pd.DataFrame): Weather data DataFrame with columns: Date, T2M (temperature), RH2M (humidity)
        latitude (float): Location latitude
        longitude (float): Location longitude
        days (int): Number of days of data
    """
    
    if df is None or df.empty:
        st.error("❌ No data available for visualization")
        return

    # Data Overview Section
    st.markdown("### 📈 Data Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Hours", f"{len(df):,}")
    with col2:
        completeness = (len(df) / (days*24) * 100)
        st.metric("✅ Data Completeness", f"{completeness:.1f}%")
    with col3:
        st.metric("📅 Date Range", 
                 f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")

    # Temperature Analysis
    st.markdown("### 🌡️ Temperature Analysis")
    temp_col1, temp_col2 = st.columns(2)
    
    with temp_col1:
        # Temperature line plot
        fig_temp = px.line(df, x='Date', y='T2M',
                          title='Temperature Variation Over Time')
        fig_temp.update_layout(yaxis_title='Temperature (°C)')
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Temperature statistics
        temp_stats = df['T2M'].describe()
        st.markdown("**Temperature Statistics:**")
        st.write(f"Average: {temp_stats['mean']:.1f}°C")
        st.write(f"Maximum: {temp_stats['max']:.1f}°C")
        st.write(f"Minimum: {temp_stats['min']:.1f}°C")

    with temp_col2:
        # Temperature histogram
        fig_temp_hist = px.histogram(df, x='T2M',
                                   title='Temperature Distribution',
                                   nbins=30)
        fig_temp_hist.update_layout(xaxis_title='Temperature (°C)',
                                  yaxis_title='Frequency')
        st.plotly_chart(fig_temp_hist, use_container_width=True)

    # Humidity Analysis
    st.markdown("### 💧 Humidity Analysis")
    hum_col1, hum_col2 = st.columns(2)
    
    with hum_col1:
        # Humidity line plot
        fig_hum = px.line(df, x='Date', y='RH2M',
                         title='Humidity Variation Over Time')
        fig_hum.update_layout(yaxis_title='Relative Humidity (%)')
        st.plotly_chart(fig_hum, use_container_width=True)
        
        # Humidity statistics
        hum_stats = df['RH2M'].describe()
        st.markdown("**Humidity Statistics:**")
        st.write(f"Average: {hum_stats['mean']:.1f}%")
        st.write(f"Maximum: {hum_stats['max']:.1f}%")
        st.write(f"Minimum: {hum_stats['min']:.1f}%")

    with hum_col2:
        # Humidity histogram
        fig_hum_hist = px.histogram(df, x='RH2M',
                                  title='Humidity Distribution',
                                  nbins=30)
        fig_hum_hist.update_layout(xaxis_title='Relative Humidity (%)',
                                 yaxis_title='Frequency')
        st.plotly_chart(fig_hum_hist, use_container_width=True)

    # Temperature vs Humidity Analysis
    st.markdown("### 🔄 Temperature vs Humidity")
    fig_scatter = px.scatter(df, x='T2M', y='RH2M',
                           title='Temperature vs Humidity Correlation',
                           trendline="ols")
    fig_scatter.update_layout(xaxis_title='Temperature (°C)',
                            yaxis_title='Relative Humidity (%)')
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Daily Patterns
    st.markdown("### 📊 Daily Patterns")
    pattern_col1, pattern_col2 = st.columns(2)
    
    with pattern_col1:
        # Average temperature by hour
        df['Hour'] = df['Date'].dt.hour
        hourly_temp = df.groupby('Hour')['T2M'].mean().reset_index()
        fig_hourly_temp = px.line(hourly_temp, x='Hour', y='T2M',
                                title='Average Temperature by Hour of Day')
        fig_hourly_temp.update_layout(xaxis_title='Hour of Day',
                                    yaxis_title='Average Temperature (°C)')
        st.plotly_chart(fig_hourly_temp, use_container_width=True)

    with pattern_col2:
        # Average humidity by hour
        hourly_hum = df.groupby('Hour')['RH2M'].mean().reset_index()
        fig_hourly_hum = px.line(hourly_hum, x='Hour', y='RH2M',
                               title='Average Humidity by Hour of Day')
        fig_hourly_hum.update_layout(xaxis_title='Hour of Day',
                                   yaxis_title='Average Humidity (%)')
        st.plotly_chart(fig_hourly_hum, use_container_width=True)

    # Data Download Option
    st.markdown("### 📥 Download Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"weather_data_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    ) 