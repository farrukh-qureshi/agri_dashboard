from prophet import Prophet
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def prepare_data_for_prophet(df, parameter):
    """Prepare data for Prophet model"""
    # Prophet requires columns named 'ds' and 'y'
    prophet_df = df.copy()
    prophet_df = prophet_df[['Date', parameter]].rename(columns={
        'Date': 'ds',
        parameter: 'y'
    })
    return prophet_df

def train_prophet_model(df, parameter):
    """Train Prophet model for given parameter"""
    # Initialize and train Prophet model
    model = Prophet(
        daily_seasonality=True,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
    )
    
    # Add hourly seasonality
    model.add_seasonality(
        name='hourly',
        period=24,
        fourier_order=5
    )
    
    model.fit(df)
    return model

def make_future_predictions(model, hours=48):
    """Generate future predictions"""
    # Create future dataframe
    future = model.make_future_dataframe(
        periods=hours,
        freq='H',
        include_history=True
    )
    
    # Make predictions
    forecast = model.predict(future)
    return forecast

def plot_predictions(historical_df, forecast_df, parameter, parameter_info):
    """Create interactive plot with historical data and predictions"""
    fig = go.Figure()

    # Add historical data
    fig.add_trace(go.Scatter(
        x=historical_df['ds'],
        y=historical_df['y'],
        name='Historical',
        line=dict(color=parameter_info['color'])
    ))

    # Add predictions
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'].tail(48),  # Show only future predictions
        y=forecast_df['yhat'].tail(48),
        name='Prediction',
        line=dict(color=parameter_info['color'], dash='dash')
    ))

    # Add confidence interval
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'].tail(48),
        y=forecast_df['yhat_upper'].tail(48),
        fill=None,
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=forecast_df['ds'].tail(48),
        y=forecast_df['yhat_lower'].tail(48),
        fill='tonexty',
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        fillcolor=f'rgba{tuple(list(hex_to_rgb(parameter_info["color"])) + [0.2])}',
        name='95% Confidence'
    ))

    fig.update_layout(
        title=f'{parameter} Forecast (Next 48 Hours)',
        xaxis_title='Date',
        yaxis_title=f'{parameter} ({parameter_info["unit"]})',
        hovermode='x unified'
    )

    return fig

def hex_to_rgb(hex_color):
    """Convert hex color to RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def display_weather_predictions(df, parameters):
    """Display predictions for weather parameters"""
    st.markdown("## 🔮 Weather Predictions")
    st.markdown("Forecasting weather parameters for the next 48 hours")

    # Create tabs for different parameters
    tabs = st.tabs(list(parameters.keys()))

    for tab, (param_name, param_info) in zip(tabs, parameters.items()):
        with tab:
            try:
                with st.spinner(f"Generating {param_name.lower()} forecast..."):
                    # Prepare data
                    prophet_df = prepare_data_for_prophet(df, param_info['column'])
                    
                    # Train model
                    model = train_prophet_model(prophet_df, param_info['column'])
                    
                    # Make predictions
                    forecast = make_future_predictions(model)
                    
                    # Plot results
                    fig = plot_predictions(prophet_df, forecast, param_name, param_info)
                    st.plotly_chart(fig, use_container_width=True)

                    # Display key predictions
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Next 24 Hours")
                        next_24h = forecast[['ds', 'yhat']].tail(24).copy()
                        next_24h['ds'] = next_24h['ds'].dt.strftime('%Y-%m-%d %H:00')
                        next_24h.columns = ['Time', param_name]
                        st.dataframe(next_24h, hide_index=True)
                    
                    with col2:
                        st.markdown("### Key Statistics")
                        future_vals = forecast['yhat'].tail(48)
                        st.metric("Maximum", f"{future_vals.max():.1f} {param_info['unit']}")
                        st.metric("Minimum", f"{future_vals.min():.1f} {param_info['unit']}")
                        st.metric("Average", f"{future_vals.mean():.1f} {param_info['unit']}")

            except Exception as e:
                st.error(f"Error generating {param_name.lower()} forecast: {str(e)}") 