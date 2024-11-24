from prophet import Prophet
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np

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

def evaluate_model_performance(forecast_df, actual_df, parameter, start_date):
    """
    Evaluate model performance by comparing predictions with actual values
    
    Args:
        forecast_df: Prophet forecast DataFrame
        actual_df: DataFrame with actual values
        parameter: Name of the parameter being predicted
        start_date: Date from which to start comparison
    """
    try:
        # Get actual values after the start date
        actual_values = actual_df[actual_df['ds'] >= start_date].copy()
        
        if actual_values.empty:
            return None, None
        
        # Merge predictions with actual values
        comparison_df = pd.merge(
            actual_values[['ds', 'y']],
            forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
            on='ds',
            how='inner'
        )
        
        if comparison_df.empty:
            return None, None
            
        # Calculate error metrics
        metrics = {
            'MAPE': np.mean(np.abs((comparison_df['y'] - comparison_df['yhat']) / comparison_df['y'])) * 100,
            'MAE': np.mean(np.abs(comparison_df['y'] - comparison_df['yhat'])),
            'RMSE': np.sqrt(np.mean((comparison_df['y'] - comparison_df['yhat'])**2)),
            'Within CI': np.mean((comparison_df['y'] >= comparison_df['yhat_lower']) & 
                               (comparison_df['y'] <= comparison_df['yhat_upper'])) * 100
        }
        
        # Create comparison plot
        fig = go.Figure()
        
        # Add actual values
        fig.add_trace(go.Scatter(
            x=comparison_df['ds'],
            y=comparison_df['y'],
            name='Actual',
            line=dict(color='black')
        ))
        
        # Add predictions
        fig.add_trace(go.Scatter(
            x=comparison_df['ds'],
            y=comparison_df['yhat'],
            name='Predicted',
            line=dict(color='blue', dash='dash')
        ))
        
        # Add confidence interval
        fig.add_trace(go.Scatter(
            x=comparison_df['ds'],
            y=comparison_df['yhat_upper'],
            fill=None,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=comparison_df['ds'],
            y=comparison_df['yhat_lower'],
            fill='tonexty',
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            fillcolor='rgba(0,0,255,0.2)',
            name='95% Confidence Interval'
        ))
        
        fig.update_layout(
            title=f'{parameter} - Model Performance Evaluation',
            xaxis_title='Date',
            yaxis_title='Value',
            hovermode='x unified'
        )
        
        return metrics, fig
        
    except Exception as e:
        st.error(f"Error in model evaluation: {str(e)}")
        return None, None

def display_weather_predictions(df, parameters):
    """Display predictions for weather parameters"""
    st.markdown("## 🔮 Weather Predictions")
    st.markdown("Forecasting weather parameters for the next 48 hours")

    # Get the date range of available data
    data_start = df['Date'].min()
    data_end = df['Date'].max()
    
    # Automatically set cutoff date to 7 days before the end
    cutoff_datetime = data_end - pd.Timedelta(days=7)
    
    # Split data
    training_data = df[df['Date'] <= cutoff_datetime].copy()
    test_data = df[df['Date'] > cutoff_datetime].copy()
    
    if len(test_data) < 24:  # Require at least 24 hours of test data
        st.warning("⚠️ Insufficient data for evaluation (need at least 24 hours)")
        return
        
    st.info(f"Model evaluation period: {test_data['Date'].min().strftime('%Y-%m-%d')} to {test_data['Date'].max().strftime('%Y-%m-%d')}")

    # Create tabs for different parameters
    tabs = st.tabs(list(parameters.keys()))

    for tab, (param_name, param_info) in zip(tabs, parameters.items()):
        with tab:
            try:
                with st.spinner(f"Generating {param_name.lower()} forecast..."):
                    # Prepare data for Prophet
                    prophet_df = prepare_data_for_prophet(training_data, param_info['column'])
                    
                    # Train model
                    model = train_prophet_model(prophet_df, param_info['column'])
                    
                    # Always do evaluation
                    hours_to_predict = len(test_data)
                    forecast = make_future_predictions(model, hours=hours_to_predict)
                    test_prophet_df = prepare_data_for_prophet(test_data, param_info['column'])
                    metrics, eval_fig = evaluate_model_performance(
                        forecast, test_prophet_df, param_name, cutoff_datetime
                    )
                    
                    if metrics and eval_fig:
                        st.markdown("#### Model Performance Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("MAPE", f"{metrics['MAPE']:.1f}%")
                        col2.metric("MAE", f"{metrics['MAE']:.2f}")
                        col3.metric("RMSE", f"{metrics['RMSE']:.2f}")
                        col4.metric("Within CI", f"{metrics['Within CI']:.1f}%")
                        
                        st.plotly_chart(eval_fig, use_container_width=True)
                    
                    # Make predictions for next 48 hours
                    forecast_future = make_future_predictions(model, hours=48)
                    fig = plot_predictions(prophet_df, forecast_future, param_name, param_info)
                    st.plotly_chart(fig, use_container_width=True)

                    # Display key predictions
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("#### Next 24 Hours")
                        next_24h = forecast_future[['ds', 'yhat']].tail(24).copy()
                        next_24h['ds'] = next_24h['ds'].dt.strftime('%Y-%m-%d %H:00')
                        next_24h.columns = ['Time', param_name]
                        st.dataframe(next_24h, hide_index=True)
                    
                    with col2:
                        st.markdown("#### Key Statistics")
                        future_vals = forecast_future['yhat'].tail(48)
                        st.metric("Maximum", f"{future_vals.max():.1f} {param_info['unit']}")
                        st.metric("Minimum", f"{future_vals.min():.1f} {param_info['unit']}")
                        st.metric("Average", f"{future_vals.mean():.1f} {param_info['unit']}")

            except Exception as e:
                st.error(f"Error generating {param_name.lower()} forecast: {str(e)}")
                st.exception(e)  # This will show the full error traceback 