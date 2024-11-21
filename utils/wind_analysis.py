import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st

def categorize_wind_speed(speed):
    """Categorize wind speed into standard categories (Beaufort scale simplified)"""
    if speed < 0.5:
        return "Calm"
    elif speed < 1.5:
        return "Light Air"
    elif speed < 3.3:
        return "Light Breeze"
    elif speed < 5.5:
        return "Gentle Breeze"
    elif speed < 7.9:
        return "Moderate Breeze"
    elif speed < 10.7:
        return "Fresh Breeze"
    else:
        return "Strong+"

def create_wind_rose(df):
    """Create a wind rose plot using Plotly"""
    # Create wind direction bins (16 directions)
    dir_bins = np.arange(-11.25, 370, 22.5)
    dir_labels = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    
    # Assign direction labels
    df['Direction_label'] = pd.cut(df['WD2M'], bins=dir_bins, labels=dir_labels, include_lowest=True)
    
    # Categorize wind speeds
    df['Speed_category'] = df['WS2M'].apply(categorize_wind_speed)
    
    # Calculate frequency for each direction and speed category
    wind_freq = pd.crosstab(df['Direction_label'], df['Speed_category'], normalize='index') * 100
    
    # Create wind rose using Plotly
    fig = go.Figure()
    
    colors = px.colors.sequential.Viridis[::-1]  # Reverse Viridis color scale
    
    for i, speed_cat in enumerate(reversed(wind_freq.columns)):
        fig.add_trace(go.Barpolar(
            r=wind_freq[speed_cat],
            theta=wind_freq.index,
            name=speed_cat,
            marker_color=colors[i],
            marker_line_color="white",
            marker_line_width=0.5,
        ))
    
    fig.update_layout(
        title="Wind Rose Diagram",
        font_size=12,
        polar=dict(
            radialaxis=dict(
                ticksuffix="%",
                angle=45,
                dtick=20,
            ),
        ),
        showlegend=True,
        legend_title="Wind Speed Categories",
    )
    
    return fig

def analyze_wind_patterns(df):
    """Analyze wind patterns and return insights"""
    insights = []
    
    # Average wind speed
    avg_speed = df['WS2M'].mean()
    insights.append(f"Average wind speed: {avg_speed:.1f} m/s")
    
    # Dominant wind direction
    dominant_direction = df['WD2M'].mode().iloc[0]
    cardinal_direction = get_cardinal_direction(dominant_direction)
    insights.append(f"Dominant wind direction: {cardinal_direction} ({dominant_direction:.0f}°)")
    
    # Wind speed distribution
    calm_winds = (df['WS2M'] < 0.5).mean() * 100
    strong_winds = (df['WS2M'] > 10.7).mean() * 100
    insights.append(f"Calm conditions: {calm_winds:.1f}% of the time")
    insights.append(f"Strong winds: {strong_winds:.1f}% of the time")
    
    return insights

def get_cardinal_direction(degrees):
    """Convert degrees to cardinal direction"""
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = round(degrees / (360 / len(directions))) % len(directions)
    return directions[index]

def display_wind_analysis(df):
    """Display comprehensive wind analysis in Streamlit"""
    st.markdown("## 🌪️ Wind Analysis")
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        # Wind Rose Plot
        wind_rose = create_wind_rose(df)
        st.plotly_chart(wind_rose, use_container_width=True)
    
    with col2:
        # Wind Speed vs Direction Scatter Plot
        scatter = px.scatter(df, x='WD2M', y='WS2M', 
                           title='Wind Speed vs Direction',
                           labels={'WD2M': 'Wind Direction (degrees)',
                                 'WS2M': 'Wind Speed (m/s)'},
                           color='WS2M',
                           color_continuous_scale='Viridis')
        st.plotly_chart(scatter, use_container_width=True)
    
    # Display insights
    st.markdown("### 📊 Wind Pattern Insights")
    insights = analyze_wind_patterns(df)
    for insight in insights:
        st.markdown(f"- {insight}")
    
    # Temporal patterns
    st.markdown("### ⏰ Temporal Wind Patterns")
    temp_col1, temp_col2 = st.columns(2)
    
    with temp_col1:
        # Hourly wind speed pattern
        df['Hour'] = df['Date'].dt.hour
        hourly_avg = df.groupby('Hour')['WS2M'].mean().reset_index()
        fig_hourly = px.line(hourly_avg, x='Hour', y='WS2M',
                           title='Average Wind Speed by Hour',
                           labels={'WS2M': 'Wind Speed (m/s)',
                                 'Hour': 'Hour of Day'})
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    with temp_col2:
        # Monthly wind speed pattern
        df['Month'] = df['Date'].dt.month
        monthly_avg = df.groupby('Month')['WS2M'].agg(['mean', 'std']).reset_index()
        monthly_avg['Month'] = pd.to_datetime(monthly_avg['Month'], format='%m').dt.strftime('%B')
        
        fig_monthly = px.bar(monthly_avg, x='Month', y='mean',
                           error_y='std',
                           title='Monthly Wind Speed Analysis',
                           labels={'mean': 'Average Wind Speed (m/s)',
                                 'Month': 'Month'})
        st.plotly_chart(fig_monthly, use_container_width=True) 