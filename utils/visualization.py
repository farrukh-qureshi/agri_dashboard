import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from utils.wind_analysis import display_wind_analysis
import plotly.graph_objects as go
import numpy as np

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
    """Display comprehensive weather insights and visualizations"""
    if df is None or df.empty:
        st.error("❌ No data available for visualization")
        return

    # Create main tabs for different sections
    main_tabs = st.tabs([
        "📊 Overview", 
        "🌡️ Temperature", 
        "💧 Humidity", 
        "🌧️ Precipitation",
        "🌪️ Wind Analysis", 
        "🌾 Agricultural Insights", 
        "📥 Export"
    ])

    with main_tabs[0]:  # Overview Tab
        st.markdown("### 📈 Data Overview")
        
        # Basic metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Hours", f"{len(df):,}")
        with col2:
            completeness = (len(df) / (days*24) * 100)
            st.metric("✅ Data Completeness", f"{completeness:.1f}%")
        with col3:
            st.metric("📅 Date Range", 
                     f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")

        # Overall insights
        st.markdown("### 🔍 Key Weather Insights")
        insights = get_overall_insights(df)
        for insight in insights:
            st.markdown(insight)

        # Combined time series (fixed version)
        st.markdown("### 📈 Combined Parameter Trends")
        
        try:
            # Sample data for large datasets
            max_points = 1000
            if len(df) > max_points:
                df_sample = df.copy()
                df_sample = df_sample.groupby(
                    pd.Grouper(key='Date', freq=f'{len(df)//max_points}h')
                ).mean().reset_index()
            else:
                df_sample = df.copy()

            # Create figure
            fig = go.Figure()

            # Add each parameter
            for param_name, param_info in parameters.items():
                col = param_info['column']
                if col in df_sample.columns:
                    # Normalize the data
                    series = df_sample[col]
                    normalized = (series - series.min()) / (series.max() - series.min())
                    
                    fig.add_trace(
                        go.Scatter(
                            x=df_sample['Date'],
                            y=normalized,
                            name=param_name,
                            line=dict(color=param_info['color'])
                        )
                    )

            # Update layout
            fig.update_layout(
                title="Normalized Parameter Trends",
                xaxis_title="Date",
                yaxis_title="Normalized Values (0-1)",
                showlegend=True,
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error creating combined trends plot: {str(e)}")

    with main_tabs[1]:  # Temperature Tab
        display_parameter_analysis(df, 'Temperature', parameters['Temperature'])
        display_enhanced_temperature_analysis(df)

    with main_tabs[2]:  # Humidity Tab
        display_parameter_analysis(df, 'Humidity', parameters['Humidity'])
        display_enhanced_humidity_analysis(df)

    with main_tabs[3]:  # Precipitation Tab
        display_parameter_analysis(df, 'Precipitation', parameters['Precipitation'])
        display_enhanced_precipitation_analysis(df)

    with main_tabs[4]:  # Wind Analysis Tab
        display_wind_analysis(df)

    with main_tabs[5]:  # Agricultural Insights Tab
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

    with main_tabs[6]:  # Export Tab
        # Data Download Option
        st.markdown("### 📥 Download Data")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"weather_data_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# Add new function to handle parameter analysis
def display_parameter_analysis(df, param_name, param_data):
    """Display analysis for a single parameter"""
    try:
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
            df_hourly = df.copy()
            df_hourly['Hour'] = df_hourly['Date'].dt.hour
            hourly_avg = df_hourly.groupby('Hour')[param_data['column']].mean().reset_index()
            fig_hourly = px.line(hourly_avg, x='Hour', y=param_data['column'],
                                color_discrete_sequence=[param_data['color']],
                                title=f'Daily {param_name} Pattern')
            fig_hourly.update_layout(
                xaxis_title='Hour of Day',
                yaxis_title=f'{param_name} ({param_data["unit"]})'
            )
            st.plotly_chart(fig_hourly, use_container_width=True)
        
        with pattern_col2:
            # Monthly pattern
            df_monthly = df.copy()
            df_monthly['Month'] = df_monthly['Date'].dt.month
            monthly_stats = df_monthly.groupby('Month')[param_data['column']].agg(['mean', 'std']).reset_index()
            monthly_stats['Month'] = pd.to_datetime(monthly_stats['Month'], format='%m').dt.strftime('%B')
            
            fig_monthly = px.bar(monthly_stats, x='Month', y='mean',
                                error_y='std',
                                title=f'Monthly {param_name} Analysis',
                                color_discrete_sequence=[param_data['color']])
            fig_monthly.update_layout(
                xaxis_title='Month',
                yaxis_title=f'Average {param_name} ({param_data["unit"]})'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

    except Exception as e:
        st.error(f"Error in {param_name} analysis: {str(e)}")

def get_overall_insights(df: pd.DataFrame) -> list:
    """Generate comprehensive insights from all weather parameters"""
    insights = []
    
    # Temperature Insights
    temp_stats = df['T2M'].describe()
    insights.append("🌡️ **Temperature Insights:**")
    insights.append(f"- Average temperature: {temp_stats['mean']:.1f}°C")
    insights.append(f"- Temperature range: {temp_stats['min']:.1f}°C to {temp_stats['max']:.1f}°C")
    if temp_stats['max'] > 35:
        insights.append(f"- ⚠️ Heat stress conditions observed ({(df['T2M'] > 35).mean()*100:.1f}% of time)")
    if temp_stats['min'] < 5:
        insights.append(f"- ❄️ Cold stress conditions observed ({(df['T2M'] < 5).mean()*100:.1f}% of time)")

    # Humidity Insights
    humidity_stats = df['RH2M'].describe()
    insights.append("\n💧 **Humidity Insights:**")
    insights.append(f"- Average humidity: {humidity_stats['mean']:.1f}%")
    optimal_humidity = (df['RH2M'] >= 40) & (df['RH2M'] <= 70)
    insights.append(f"- Optimal humidity conditions: {(optimal_humidity.sum() / len(df))*100:.1f}% of time")
    
    # Precipitation Insights
    rain_stats = df['PRECTOTCORR'].describe()
    total_rain = df['PRECTOTCORR'].sum()
    rainy_hours = (df['PRECTOTCORR'] > 0).sum()
    insights.append("\n🌧️ **Precipitation Insights:**")
    insights.append(f"- Total precipitation: {total_rain:.1f} mm")
    insights.append(f"- Rainy hours: {rainy_hours} ({(rainy_hours/len(df))*100:.1f}% of time)")
    insights.append(f"- Maximum hourly precipitation: {rain_stats['max']:.1f} mm/hour")

    # Wind Insights
    wind_stats = df['WS2M'].describe()
    insights.append("\n💨 **Wind Insights:**")
    insights.append(f"- Average wind speed: {wind_stats['mean']:.1f} m/s")
    insights.append(f"- Maximum wind speed: {wind_stats['max']:.1f} m/s")
    # Add dominant wind direction with observed=True
    dominant_direction = df.groupby(
        pd.cut(df['WD2M'], bins=8), 
        observed=True
    )['WD2M'].count().idxmax()
    insights.append(f"- Dominant wind direction: {dominant_direction}")

    return insights

def display_enhanced_temperature_analysis(df):
    """Enhanced temperature analysis"""
    try:
        st.markdown("### 🌡️ Detailed Temperature Analysis")
        
        # Temperature extremes analysis
        extremes_col1, extremes_col2 = st.columns(2)
        with extremes_col1:
            # Calculate daily statistics
            daily_stats = df.groupby(df['Date'].dt.date).agg({
                'T2M': ['min', 'max', 'mean']
            }).reset_index()
            
            # Convert the multi-index columns to single level
            daily_stats.columns = ['Date', 'Min Temp', 'Max Temp', 'Avg Temp']
            daily_stats['Date'] = pd.to_datetime(daily_stats['Date'])
            
            # Create figure with secondary y-axis
            fig_extremes = go.Figure()
            
            # Add traces for min, max, and mean temperatures
            fig_extremes.add_trace(
                go.Scatter(x=daily_stats['Date'], y=daily_stats['Min Temp'],
                          name='Minimum', line=dict(color='blue'))
            )
            fig_extremes.add_trace(
                go.Scatter(x=daily_stats['Date'], y=daily_stats['Max Temp'],
                          name='Maximum', line=dict(color='red'))
            )
            fig_extremes.add_trace(
                go.Scatter(x=daily_stats['Date'], y=daily_stats['Avg Temp'],
                          name='Average', line=dict(color='green'))
            )
            
            # Update layout
            fig_extremes.update_layout(
                title="Daily Temperature Extremes",
                xaxis_title="Date",
                yaxis_title="Temperature (°C)",
                hovermode='x unified'
            )
            st.plotly_chart(fig_extremes, use_container_width=True)
        
        with extremes_col2:
            # Temperature change analysis
            df['temp_change'] = df['T2M'].diff()
            fig_change = px.histogram(
                df, 
                x='temp_change',
                title="Temperature Change Distribution",
                labels={'temp_change': 'Temperature Change (°C/hour)'},
                color_discrete_sequence=['red']
            )
            fig_change.update_layout(
                xaxis_title="Temperature Change (°C/hour)",
                yaxis_title="Count",
                showlegend=False
            )
            st.plotly_chart(fig_change, use_container_width=True)

        # Add daily temperature pattern
        st.markdown("### 📈 Daily Temperature Pattern")
        hourly_col1, hourly_col2 = st.columns(2)
        
        with hourly_col1:
            # Average hourly temperature
            hourly_avg = df.groupby(df['Date'].dt.hour)['T2M'].agg(['mean', 'std']).reset_index()
            fig_hourly = go.Figure()
            
            # Add mean temperature line
            fig_hourly.add_trace(go.Scatter(
                x=hourly_avg['Date'],
                y=hourly_avg['mean'],
                name='Mean Temperature',
                line=dict(color='red'),
                mode='lines'
            ))
            
            # Add standard deviation range
            fig_hourly.add_trace(go.Scatter(
                x=hourly_avg['Date'],
                y=hourly_avg['mean'] + hourly_avg['std'],
                mode='lines',
                line=dict(width=0),
                showlegend=False
            ))
            fig_hourly.add_trace(go.Scatter(
                x=hourly_avg['Date'],
                y=hourly_avg['mean'] - hourly_avg['std'],
                mode='lines',
                line=dict(width=0),
                fillcolor='rgba(255, 0, 0, 0.2)',
                fill='tonexty',
                name='Standard Deviation'
            ))
            
            fig_hourly.update_layout(
                title="Average Daily Temperature Pattern",
                xaxis_title="Hour of Day",
                yaxis_title="Temperature (°C)",
                hovermode='x unified'
            )
            st.plotly_chart(fig_hourly, use_container_width=True)
        
        with hourly_col2:
            # Temperature variability by time of day
            df['hour'] = df['Date'].dt.hour
            temp_variability = df.groupby('hour')['T2M'].agg(['mean', 'std', 'min', 'max']).reset_index()
            
            fig_var = go.Figure()
            fig_var.add_trace(go.Bar(
                x=temp_variability['hour'],
                y=temp_variability['std'],
                name='Temperature Variability',
                marker_color='red'
            ))
            
            fig_var.update_layout(
                title="Temperature Variability by Hour",
                xaxis_title="Hour of Day",
                yaxis_title="Standard Deviation (°C)",
                showlegend=False
            )
            st.plotly_chart(fig_var, use_container_width=True)

    except Exception as e:
        st.error(f"Error in enhanced temperature analysis: {str(e)}")
        st.exception(e)  # This will print the full traceback for debugging

def display_enhanced_humidity_analysis(df):
    """Enhanced humidity analysis"""
    try:
        st.markdown("### 💧 Detailed Humidity Analysis")
        
        # Humidity comfort zones
        comfort_col1, comfort_col2 = st.columns(2)
        with comfort_col1:
            df['comfort_zone'] = pd.cut(df['RH2M'], 
                                      bins=[0, 30, 45, 60, 75, 100],
                                      labels=['Very Dry', 'Dry', 'Comfortable', 
                                            'Humid', 'Very Humid'])
            comfort_dist = df['comfort_zone'].value_counts()
            fig_comfort = px.pie(values=comfort_dist.values,
                               names=comfort_dist.index,
                               title="Humidity Comfort Distribution")
            st.plotly_chart(fig_comfort, use_container_width=True)

    except Exception as e:
        st.error(f"Error in enhanced humidity analysis: {str(e)}")

def display_enhanced_precipitation_analysis(df):
    """Enhanced precipitation analysis"""
    try:
        st.markdown("### 🌧️ Detailed Precipitation Analysis")
        
        # Rainfall intensity categories
        rain_col1, rain_col2 = st.columns(2)
        with rain_col1:
            df['rain_intensity'] = pd.cut(df['PRECTOTCORR'],
                                        bins=[-np.inf, 0, 2.5, 7.6, 50, np.inf],
                                        labels=['No Rain', 'Light', 'Moderate', 
                                              'Heavy', 'Extreme'])
            rain_dist = df['rain_intensity'].value_counts()
            fig_rain = px.pie(values=rain_dist.values,
                            names=rain_dist.index,
                            title="Rainfall Intensity Distribution")
            st.plotly_chart(fig_rain, use_container_width=True)

    except Exception as e:
        st.error(f"Error in enhanced precipitation analysis: {str(e)}")
 