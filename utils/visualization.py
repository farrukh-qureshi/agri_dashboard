import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

def display_weather_insights(df: pd.DataFrame, latitude: float, longitude: float, days: int):
    """
    Display comprehensive weather insights and visualizations
    
    Args:
        df (pd.DataFrame): Weather data DataFrame with columns: Date, T2M, RH2M, WS2M, PRECTOTCORR
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

    # Define parameters and their configurations
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

    # Create tabs for each parameter
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

    # # Correlation Analysis
    # st.markdown("### 🔄 Parameter Correlations")
    # correlation_df = df[[param['column'] for param in parameters.values()]]
    # correlation_df.columns = parameters.keys()
    # fig_corr = px.imshow(correlation_df.corr(),
    #                     title='Correlation Matrix',
    #                     color_continuous_scale='RdBu')
    # st.plotly_chart(fig_corr, use_container_width=True)

    # Data Download Option
    st.markdown("### 📥 Download Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"weather_data_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    ) 