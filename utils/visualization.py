import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

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
    """Generate crop recommendations based on weather conditions"""
    recommendations = []
    
    # Temperature-based recommendations
    if 20 <= temp_stats['mean'] <= 30:
        recommendations.extend(['Cotton', 'Maize', 'Sugarcane'])
    elif 15 <= temp_stats['mean'] <= 25:
        recommendations.extend(['Wheat', 'Rice', 'Vegetables'])
    
    # Filter based on extreme temperatures
    if temp_stats['max'] > 40:
        recommendations = [crop for crop in recommendations 
                         if crop not in ['Vegetables', 'Rice']]
    
    return recommendations

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

    # Calculate stress periods first
    stress_df = get_temperature_stress_periods(df)
    
    # Calculate key statistics
    temp_stats = df['T2M'].describe()
    humidity_stats = df['RH2M'].describe()
    rainfall_stats = df['PRECTOTCORR'].describe()
    
    # Calculate additional metrics
    daily_max_temp = df.groupby(df['Date'].dt.date)['T2M'].max()
    heat_stress_days = (daily_max_temp > 35).sum()
    optimal_humidity = (df['RH2M'] >= 40) & (df['RH2M'] <= 70)
    optimal_humidity_percent = (optimal_humidity.sum() / len(df)) * 100
    temp_range = temp_stats['max'] - temp_stats['min']

    # Enhanced Agricultural Insights Section
    st.markdown("### 🌾 Agricultural Insights")
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
        
        # Display stress statistics
        st.markdown("**Temperature Stress Summary:**")
        total_hours = len(df)
        for status, count in stress_counts.items():
            percentage = (count / total_hours) * 100
            if status == 'Heat Stress':
                st.warning(f"🌡️ {status}: {percentage:.1f}% of time ({count:,} hours)")
            elif status == 'Cold Stress':
                st.info(f"❄️ {status}: {percentage:.1f}% of time ({count:,} hours)")
            else:
                st.success(f"✅ {status}: {percentage:.1f}% of time ({count:,} hours)")

    with agri_col2:
        # Growing Conditions Analysis
        gdd = get_growing_degree_days(df)
        
        st.markdown("**Growing Conditions:**")
        st.metric("📈 Growing Degree Days (Base 10°C)", f"{gdd:.1f}")
        st.metric("🌡️ Days with Heat Stress", f"{heat_stress_days} days")
        st.metric("💧 Time in Optimal Humidity Range", f"{optimal_humidity_percent:.1f}%")
        
        # Crop Risk Assessment
        risk_level = "Low"
        risk_color = "green"
        risk_factors = []
        
        if heat_stress_days > 5:
            risk_factors.append("Extended periods of high temperature")
            risk_level = "High"
            risk_color = "red"
        if optimal_humidity_percent < 40:
            risk_factors.append("Sub-optimal humidity conditions")
            risk_level = "Medium" if risk_level == "Low" else "High"
            risk_color = "orange" if risk_level == "Medium" else "red"
        
        st.markdown(f"**Crop Risk Assessment:** :{risk_color}[{risk_level} Risk]")
        if risk_factors:
            st.markdown("Risk Factors:")
            for factor in risk_factors:
                st.markdown(f"- {factor}")
        else:
            st.success("✅ Favorable growing conditions")

    # Get interpretations
    temp_interpretations = interpret_temperature_pattern(temp_stats, stress_df)
    
    # Display enhanced insights
    st.markdown("#### 🎯 Key Agricultural Interpretations")
    
    # Temperature Insights
    st.markdown("**Temperature Impact Analysis:**")
    for interpretation in temp_interpretations:
        st.markdown(f"- {interpretation}")
    
    # Growing Season Analysis
    growing_season = "Favorable" if (
        optimal_humidity_percent > 40 and 
        heat_stress_days < 60 and 
        15 <= temp_stats['mean'] <= 30
    ) else "Challenging"
    
    st.markdown(f"**🌱 Growing Season Assessment:** {growing_season}")
    
    # Crop Recommendations
    recommended_crops = get_crop_recommendations(temp_stats, humidity_stats, rainfall_stats)
    if recommended_crops:
        st.markdown("**🌾 Suitable Crops Based on Conditions:**")
        for crop in recommended_crops:
            st.markdown(f"- {crop}")
    
    # Risk Management Suggestions
    st.markdown("**⚠️ Risk Management Suggestions:**")
    if heat_stress_days > 5:
        st.markdown("""
        - Consider heat-tolerant crop varieties
        - Implement shade management techniques
        - Adjust irrigation scheduling to early morning or evening
        - Monitor soil moisture levels closely
        """)
    
    if optimal_humidity_percent < 40:
        st.markdown("""
        - Install drip irrigation systems
        - Use mulching to conserve soil moisture
        - Consider drought-resistant crop varieties
        """)
    
    # Create tabs for each parameter
    parameters = {
        'Temperature': {
            'column': 'T2M',
            'unit': '°C',
            'icon': '🌡️',
            'color': 'red'
        },
        'Humidity': {
            'column': 'RH2M',
            'unit': '%',
            'icon': '💧',
            'color': 'blue'
        },
        'Wind Speed': {
            'column': 'WS2M',
            'unit': 'm/s',
            'icon': '💨',
            'color': 'green'
        },
        'Precipitation': {
            'column': 'PRECTOTCORR',
            'unit': 'mm/hour',
            'icon': '🌧️',
            'color': 'purple'
        }
    }

    tabs = st.tabs([f"{param['icon']} {name}" for name, param in parameters.items()])

    for tab, (param_name, param_config) in zip(tabs, parameters.items()):
        with tab:
            col1, col2 = st.columns(2)
            
            with col1:
                # Time series plot
                fig_ts = px.line(df, x='Date', y=param_config['column'],
                               title=f'{param_name} Variation Over Time',
                               color_discrete_sequence=[param_config['color']])
                fig_ts.update_layout(yaxis_title=f'{param_name} ({param_config["unit"]})')
                st.plotly_chart(fig_ts, use_container_width=True)
                
                # Statistics
                stats = df[param_config['column']].describe()
                st.markdown(f"**{param_name} Statistics:**")
                st.write(f"Average: {stats['mean']:.1f} {param_config['unit']}")
                st.write(f"Maximum: {stats['max']:.1f} {param_config['unit']}")
                st.write(f"Minimum: {stats['min']:.1f} {param_config['unit']}")

            with col2:
                # Distribution plot
                fig_hist = px.histogram(df, x=param_config['column'],
                                      title=f'{param_name} Distribution',
                                      nbins=30,
                                      color_discrete_sequence=[param_config['color']])
                fig_hist.update_layout(
                    xaxis_title=f'{param_name} ({param_config["unit"]})',
                    yaxis_title='Frequency'
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            # Daily patterns
            st.markdown("### 📊 Daily Patterns")
            df['Hour'] = df['Date'].dt.hour
            hourly_avg = df.groupby('Hour')[param_config['column']].mean().reset_index()
            fig_hourly = px.line(hourly_avg, x='Hour', y=param_config['column'],
                               title=f'Average {param_name} by Hour of Day',
                               color_discrete_sequence=[param_config['color']])
            fig_hourly.update_layout(
                xaxis_title='Hour of Day',
                yaxis_title=f'Average {param_name} ({param_config["unit"]})'
            )
            st.plotly_chart(fig_hourly, use_container_width=True)

            # Monthly Analysis
            st.markdown("### 📅 Monthly Patterns")
            df['Month'] = df['Date'].dt.month
            monthly_avg = df.groupby('Month')[param_config['column']].agg(['mean', 'std']).reset_index()
            monthly_avg['Month'] = pd.to_datetime(monthly_avg['Month'], format='%m').dt.strftime('%B')
            
            fig_monthly = px.bar(monthly_avg, x='Month', y='mean',
                               error_y='std',
                               title=f'Monthly {param_name} Analysis (with Standard Deviation)',
                               color_discrete_sequence=[param_config['color']])
            fig_monthly.update_layout(
                xaxis_title='Month',
                yaxis_title=f'Average {param_name} ({param_config["unit"]})'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

            # Extreme Events Analysis
            st.markdown("### ⚠️ Extreme Events")
            percentile_95 = df[param_config['column']].quantile(0.95)
            percentile_5 = df[param_config['column']].quantile(0.05)
            
            extreme_events = df[
                (df[param_config['column']] > percentile_95) |
                (df[param_config['column']] < percentile_5)
            ].copy()
            
            if not extreme_events.empty:
                extreme_events['Event_Type'] = extreme_events[param_config['column']].apply(
                    lambda x: 'High' if x > percentile_95 else 'Low'
                )
                
                fig_extreme = px.scatter(
                    extreme_events,
                    x='Date',
                    y=param_config['column'],
                    color='Event_Type',
                    title=f'Extreme {param_name} Events (5th and 95th percentiles)',
                    color_discrete_map={'High': 'red', 'Low': 'blue'}
                )
                st.plotly_chart(fig_extreme, use_container_width=True)
                
                # Summary of extreme events
                st.markdown("**Extreme Events Summary:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"High events (>95th percentile): {(extreme_events['Event_Type'] == 'High').sum()}")
                    st.write(f"95th percentile: {percentile_95:.1f} {param_config['unit']}")
                with col2:
                    st.write(f"Low events (<5th percentile): {(extreme_events['Event_Type'] == 'Low').sum()}")
                    st.write(f"5th percentile: {percentile_5:.1f} {param_config['unit']}")

            # Parameter-specific interpretations in each tab
            st.markdown("#### 📊 Parameter Interpretation")
            
            if param_name == "Temperature":
                daily_stats = df.groupby(df['Date'].dt.date)[param_config['column']].agg(['max', 'min', 'mean'])
                daily_range = daily_stats['max'] - daily_stats['min']
                avg_daily_range = daily_range.mean()
                
                daily_max_temp = daily_stats['max']
                temp_stress_days = (daily_max_temp > 35).sum()
                frost_days = (daily_stats['min'] < 2).sum()

                st.markdown(f"""
                - **Daily Pattern:** Average daily temperature variation is {avg_daily_range:.1f}°C
                - **Extreme Conditions:**
                    - Heat stress observed on {temp_stress_days} days
                    - Frost risk observed on {frost_days} days
                - **Crop Impact:** 
                    - {"High risk of heat damage during peak summer" if temp_stats['max'] > 40 else "Moderate heat stress risk"}
                    - {"Risk of cold damage during winter" if temp_stats['min'] < 5 else "Low risk of frost damage"}
                - **Management:** 
                    - {"Consider protective measures during peak temperatures" if temp_stats['max'] > 35 else "Temperature range is generally suitable for crop growth"}
                    - {"Use frost protection during winter" if frost_days > 0 else "No frost protection needed"}
                """)
            
            elif param_name == "Humidity":
                optimal_range = (df['RH2M'] >= 40) & (df['RH2M'] <= 70)
                optimal_percent = (optimal_range.sum() / len(df)) * 100
                high_humidity = (df['RH2M'] > 80).sum() / len(df) * 100
                
                st.markdown(f"""
                - **Crop Growth:** {
                    "Favorable humidity conditions" if optimal_percent > 60
                    else "Sub-optimal humidity levels may affect crop growth"
                }
                - **Disease Risk:** 
                    - {high_humidity:.1f}% of time with high humidity (>80%)
                    - {"High risk of fungal diseases" if high_humidity > 20 else "Moderate to low disease pressure"}
                - **Management:** 
                    - {"Implement disease prevention measures" if high_humidity > 20 else "Standard disease monitoring recommended"}
                    - {"Consider humidity management in greenhouses" if optimal_percent < 40 else "Natural humidity levels are generally adequate"}
                """)
            
            elif param_name == "Wind Speed":
                high_wind = (df['WS2M'] > 8).sum() / len(df) * 100
                avg_wind = df['WS2M'].mean()
                
                st.markdown(f"""
                - **General Pattern:** Average wind speed is {avg_wind:.1f} m/s
                - **Strong Winds:** {high_wind:.1f}% of time with high winds (>8 m/s)
                - **Crop Impact:** 
                    - {"Risk of mechanical damage to crops" if high_wind > 10 else "Generally favorable wind conditions"}
                    - {"May affect spraying operations" if high_wind > 5 else "Suitable for most agricultural operations"}
                - **Management:**
                    - {"Consider windbreaks or protective structures" if high_wind > 10 else "Standard wind protection adequate"}
                    - {"Plan spraying operations carefully" if high_wind > 5 else "Normal spraying operations possible"}
                """)
            
            elif param_name == "Precipitation":
                monthly_rainfall = df.groupby(df['Date'].dt.month)['PRECTOTCORR'].sum()
                total_rainfall = monthly_rainfall.sum()
                rainy_days = (df.groupby(df['Date'].dt.date)['PRECTOTCORR'].sum() > 0).sum()
                
                st.markdown(f"""
                - **Annual Pattern:** 
                    - Total rainfall: {total_rainfall:.1f}mm
                    - Rainy days: {rainy_days} days
                - **Distribution:** {
                    "Well-distributed" if monthly_rainfall.std() < monthly_rainfall.mean()
                    else "Highly variable between months"
                }
                - **Irrigation Needs:** {
                    "Consider supplemental irrigation" if total_rainfall < 500
                    else "Rainfall generally sufficient for crop growth"
                }
                - **Management:**
                    - {"Implement water conservation measures" if total_rainfall < 500 else "Focus on drainage management"}
                    - {"Consider drought-resistant varieties" if total_rainfall < 400 else "Standard varieties suitable"}
                """)

    # Data Download Option
    st.markdown("### 📥 Download Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"weather_data_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    ) 