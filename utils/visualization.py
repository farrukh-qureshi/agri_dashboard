import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

# Move parameters dictionary to module level
parameters = {
    'Temperature': {
        'column': 'T2M',
        'color': 'red',
        'unit': '°C'
    },
    'Humidity': {
        'column': 'RH2M',
        'color': 'blue',
        'unit': '%'
    },
    'Wind Speed': {
        'column': 'WS2M',
        'color': 'green',
        'unit': 'm/s'
    },
    'Precipitation': {
        'column': 'PRECTOTCORR',
        'color': 'purple',
        'unit': 'mm/hour'
    }
}

def get_temperature_stress_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate temperature stress periods for crops"""
    df = df.copy()
    df['Temp_Status'] = 'Normal'
    df.loc[df['T2M'] > 35, 'Temp_Status'] = 'Heat Stress'
    df.loc[df['T2M'] < 5, 'Temp_Status'] = 'Cold Stress'
    return df

def get_growing_degree_days(df: pd.DataFrame, base_temp=10) -> float:
    """Calculate Growing Degree Days (GDD)"""
    daily_mean = df.groupby(df['Date'].dt.date)['T2M'].mean()
    gdd = daily_mean.apply(lambda x: max(0, x - base_temp))
    return gdd.sum()

def get_crop_recommendations(temp_stats, humidity_stats, rainfall_stats):
    """
    Generate crop recommendations based on weather conditions.
    
    Parameters:
    temp_stats (pd.Series): Temperature statistics from df['T2M'].describe()
    humidity_stats (pd.Series): Humidity statistics from df['RH2M'].describe()
    rainfall_stats (pd.Series): Rainfall statistics from df['PRECTOTCORR'].describe()
    
    Returns:
    list: Recommended crops based on weather parameters.
    """
    recommendations = []

    # Temperature-based recommendations using mean temperature
    mean_temp = temp_stats['mean']
    if 25 <= mean_temp <= 30:
        recommendations.extend(['Cotton', 'Sugarcane'])
    if 21 <= mean_temp <= 27:
        recommendations.append('Maize')
    if 15 <= mean_temp <= 20:
        recommendations.append('Wheat')
    if 20 <= mean_temp <= 27:
        recommendations.append('Rice')
    if 15 <= mean_temp <= 30:
        recommendations.append('Vegetables')

    # Humidity-based filtering using mean humidity
    mean_humidity = humidity_stats['mean']
    if mean_humidity < 30:
        recommendations = [crop for crop in recommendations if crop not in ['Rice', 'Vegetables']]
    elif mean_humidity > 70:
        recommendations = [crop for crop in recommendations if crop not in ['Cotton']]

    # Rainfall-based filtering using mean rainfall
    mean_rainfall = rainfall_stats['mean']
    if mean_rainfall < 0.2:  # Adjusted for mm/hour
        recommendations = [crop for crop in recommendations if crop not in ['Rice', 'Sugarcane']]
    elif mean_rainfall > 0.8:  # Adjusted for mm/hour
        recommendations = [crop for crop in recommendations if crop not in ['Cotton', 'Maize']]

    # Extreme temperature handling
    if temp_stats['max'] > 40:
        recommendations = [crop for crop in recommendations if crop not in ['Vegetables', 'Rice']]
    if temp_stats['min'] < 10:
        recommendations = [crop for crop in recommendations if crop not in ['Maize', 'Cotton']]

    # If no recommendations, suggest drought-resistant crops
    if not recommendations:
        recommendations = ['Sorghum', 'Millet']

    # Deduplicate recommendations and return
    return list(set(recommendations))

def interpret_temperature_pattern(temp_stats, stress_data):
    """Generate detailed temperature pattern interpretation"""
    interpretations = []
    
    # Temperature range interpretation
    if temp_stats['max'] > 40:
        interpretations.append("⚠️ Extreme high temperatures above 40°C indicate severe heat stress "
                             "risk for most crops, especially during flowering stages.")
    
    if temp_stats['min'] < 5:
        interpretations.append("❄️ Low temperatures below 5°C may cause frost damage to sensitive crops. "
                             "Consider frost protection measures.")
    
    # Daily variation
    temp_range = temp_stats['max'] - temp_stats['min']
    if temp_range > 20:
        interpretations.append("📊 Large daily temperature variations (>20°C) may affect crop development "
                             "and stress adaptation mechanisms.")
    
    return interpretations

def display_weather_insights(df: pd.DataFrame, latitude: float, longitude: float, days: int):
    """
    Display comprehensive weather insights and visualizations
    """
    if df is None or df.empty:
        st.error("❌ No data available for visualization")
        return

    # Create main tabs for different sections
    main_tabs = st.tabs(["📊 Overview", "🌾 Agricultural Insights", "📈 Parameter Analysis", "📥 Export"])

    with main_tabs[0]:  # Overview Tab
        # Data Overview Section in 3 columns
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

    with main_tabs[1]:  # Agricultural Insights Tab
        # Calculate necessary statistics
        stress_df = get_temperature_stress_periods(df)
        temp_stats = df['T2M'].describe()
        humidity_stats = df['RH2M'].describe()
        rainfall_stats = df['PRECTOTCORR'].describe()
        
        # Create two columns for agricultural insights
        agri_col1, agri_col2 = st.columns(2)
        
        with agri_col1:
            # Temperature Stress Analysis
            stress_counts = stress_df['Temp_Status'].value_counts()
            fig_stress = px.pie(
                values=stress_counts.values,
                names=stress_counts.index,
                title="Temperature Stress Distribution",
                color_discrete_map={
                    'Normal': 'green',
                    'Heat Stress': 'red',
                    'Cold Stress': 'blue'
                }
            )
            st.plotly_chart(fig_stress, use_container_width=True)
        
        with agri_col2:
            # Growing Conditions Analysis
            gdd = get_growing_degree_days(df)
            daily_max_temp = df.groupby(df['Date'].dt.date)['T2M'].max()
            heat_stress_days = (daily_max_temp > 35).sum()
            optimal_humidity = (df['RH2M'] >= 40) & (df['RH2M'] <= 70)
            optimal_humidity_percent = (optimal_humidity.sum() / len(df)) * 100
            
            st.markdown("**Growing Conditions:**")
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric("📈 Growing Degree Days", f"{gdd:.1f}")
                st.metric("🌡️ Heat Stress Days", f"{heat_stress_days}")
            with metrics_col2:
                st.metric("💧 Optimal Humidity", f"{optimal_humidity_percent:.1f}%")
                
        # Create two columns for recommendations and interpretations
        rec_col1, rec_col2 = st.columns(2)
        
        with rec_col1:
            recommended_crops = get_crop_recommendations(temp_stats, humidity_stats, rainfall_stats)
            st.markdown("**🌾 Recommended Crops:**")
            for crop in recommended_crops:
                st.markdown(f"- {crop}")
                
        with rec_col2:
            temp_interpretations = interpret_temperature_pattern(temp_stats, stress_df)
            st.markdown("**🎯 Key Interpretations:**")
            for interpretation in temp_interpretations:
                st.markdown(f"- {interpretation}")

    with main_tabs[2]:  # Parameter Analysis Tab
        # Create subtabs for each parameter
        param_tabs = st.tabs(['🌡️ Temperature', '💧 Humidity', '💨 Wind', '🌧️ Precipitation'])
        
        for tab, (param_name, param_data) in zip(param_tabs, parameters.items()):
            with tab:
                # Create two columns for charts
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    # Time series plot
                    fig_ts = px.line(df, x='Date', y=param_data['column'],
                                   title=f'{param_name} Over Time',
                                   color_discrete_sequence=[param_data['color']])
                    st.plotly_chart(fig_ts, use_container_width=True)
                
                with chart_col2:
                    # Distribution plot
                    fig_hist = px.histogram(df, x=param_data['column'],
                                          title=f'{param_name} Distribution',
                                          color_discrete_sequence=[param_data['color']])
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                # Create two columns for patterns
                pattern_col1, pattern_col2 = st.columns(2)
                
                with pattern_col1:
                    # Daily pattern
                    df['Hour'] = df['Date'].dt.hour
                    hourly_avg = df.groupby('Hour')[param_data['column']].mean().reset_index()
                    fig_hourly = px.line(hourly_avg, x='Hour', y=param_data['column'],
                                        color_discrete_sequence=[param_data['color']],
                                       title=f'Daily {param_name} Pattern')
                    st.plotly_chart(fig_hourly, use_container_width=True)
                
                with pattern_col2:
                    # Monthly pattern
                    df['Month'] = df['Date'].dt.month
                    monthly_avg = df.groupby('Month')[param_data['column']].agg(['mean', 'std']).reset_index()
                    monthly_avg['Month'] = pd.to_datetime(monthly_avg['Month'], format='%m').dt.strftime('%B')
                    
                    fig_monthly = px.bar(monthly_avg, x='Month', y='mean',
                                       error_y='std',
                                       title=f'Monthly {param_name} Analysis (with Standard Deviation)',
                                       color_discrete_sequence=[param_data['color']])
                    fig_monthly.update_layout(
                        xaxis_title='Month',
                        yaxis_title=f'Average {param_name} ({param_data["unit"]})'
                    )
                    st.plotly_chart(fig_monthly, use_container_width=True)

    # Data Download Option
    st.markdown("### 📥 Download Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"weather_data_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    ) 