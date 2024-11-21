import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta

def create_features(df: pd.DataFrame, target_col: str, seq_length: int):
    """Create time-based features for prediction"""
    df = df.copy()
    
    # Basic time features
    df['hour'] = df['Date'].dt.hour
    df['day'] = df['Date'].dt.day
    df['month'] = df['Date'].dt.month
    df['day_of_week'] = df['Date'].dt.dayofweek
    
    # Rolling features (memory efficient)
    df[f'{target_col}_rolling_mean'] = df[target_col].rolling(window=seq_length, min_periods=1).mean()
    df[f'{target_col}_rolling_std'] = df[target_col].rolling(window=seq_length, min_periods=1).std()
    
    # Lag features (limited to save memory)
    for i in [1, 3, 6, 12, 24]:
        df[f'{target_col}_lag_{i}'] = df[target_col].shift(i)
    
    return df.dropna()

def determine_prediction_params(data_length):
    """Determine prediction parameters based on data length"""
    if data_length < 48:  # Less than 2 days
        return None, None, "Insufficient data for prediction"
    
    # Define parameters based on data length
    if data_length < 168:  # Less than 1 week
        seq_length = 24  # 1 day
        pred_length = 12  # Predict next 12 hours
    elif data_length < 720:  # Less than 1 month
        seq_length = 48  # 2 days
        pred_length = 24  # Predict next day
    else:  # More than 1 month
        seq_length = 72  # 3 days
        pred_length = 48  # Predict next 2 days
    
    return seq_length, pred_length, "OK"

def train_model(X, y):
    """Train Random Forest model with memory-efficient parameters"""
    model = RandomForestRegressor(
        n_estimators=50,  # Reduced number of trees
        max_depth=10,     # Limited depth
        min_samples_split=5,
        n_jobs=2,        # Use both CPU cores
        random_state=42
    )
    model.fit(X, y)
    return model

def calculate_mape(actual, predicted):
    """Calculate Mean Absolute Percentage Error"""
    return np.mean(np.abs((actual - predicted) / actual)) * 100

def predict_weather(df: pd.DataFrame, column: str, model=None, train_only=False):
    """
    Predict weather parameters using Random Forest
    Returns prediction DataFrame and confidence metrics
    """
    if df is None or df.empty:
        return None, None
    
    # Determine prediction parameters
    seq_length, pred_length, status = determine_prediction_params(len(df))
    if status != "OK":
        return None, {"error": status}
    
    try:
        # Create features
        feature_df = create_features(df, column, seq_length)
        
        # Prepare data
        feature_columns = [col for col in feature_df.columns 
                         if col not in [column, 'Date']]
        
        X = feature_df[feature_columns].values
        y = feature_df[column].values
        
        # Train model if not provided
        if model is None:
            model = train_model(X, y)
            if train_only:
                return model, None
        
        # Return if only training is requested
        if train_only:
            return model, None
        
        # Make predictions
        predictions = []
        last_data = feature_df.iloc[-1:].copy()
        
        for i in range(pred_length):
            # Update time features
            next_date = last_data['Date'].iloc[-1] + timedelta(hours=1)
            last_data['Date'] = next_date
            last_data['hour'] = next_date.hour
            last_data['day'] = next_date.day
            last_data['month'] = next_date.month
            last_data['day_of_week'] = next_date.dayofweek
            
            # Make prediction
            pred = model.predict(last_data[feature_columns])[0]
            predictions.append(pred)
            
            # Update lag features
            for lag in [1, 3, 6, 12, 24]:
                last_data[f'{column}_lag_{lag}'] = pred if lag == 1 else last_data[f'{column}_lag_{lag-1}'].iloc[0]
            
            # Update rolling features
            last_data[f'{column}_rolling_mean'] = pred
            last_data[f'{column}_rolling_std'] = 0  # Simplified for prediction
        
        # Calculate confidence metrics
        test_size = min(100, len(df) // 4)
        test_predictions = model.predict(X[-test_size:])
        mape = calculate_mape(y[-test_size:], test_predictions)
        
        # Create prediction DataFrame
        last_date = df['Date'].max()
        future_dates = [last_date + timedelta(hours=i+1) for i in range(len(predictions))]
        pred_df = pd.DataFrame({
            'Date': future_dates,
            f'Predicted_{column}': predictions
        })
        
        confidence_metrics = {
            'mape': mape,
            'prediction_length': pred_length
        }
        
        return pred_df, confidence_metrics
    
    except Exception as e:
        return None, {'error': str(e)}

def predict_rain_probability(df: pd.DataFrame, model=None, train_only=False):
    """
    Predict probability of rain using Random Forest
    Returns DataFrame with rain probabilities
    """
    if df is None or df.empty:
        return None
    
    try:
        # Determine prediction parameters
        seq_length, pred_length, status = determine_prediction_params(len(df))
        if status != "OK":
            return None
        
        # Create binary rain indicator (1 if precipitation > 0.1mm/hour)
        df['Rain_Binary'] = (df['PRECTOTCORR'] > 0.1).astype(float)
        
        # Create features
        feature_df = create_features(df, 'Rain_Binary', seq_length)
        
        # Prepare data
        feature_columns = [col for col in feature_df.columns 
                         if col not in ['Rain_Binary', 'Date', 'PRECTOTCORR']]
        
        X = feature_df[feature_columns].values
        y = feature_df['Rain_Binary'].values
        
        # Train model if not provided
        if model is None:
            model = train_model(X, y)
            if train_only:
                return model, None
        
        # Return if only training is requested
        if train_only:
            return model, None
        
        # Make predictions
        predictions = []
        last_data = feature_df.iloc[-1:].copy()
        
        for i in range(pred_length):
            # Update time features
            next_date = last_data['Date'].iloc[-1] + timedelta(hours=1)
            last_data['Date'] = next_date
            last_data['hour'] = next_date.hour
            last_data['day'] = next_date.day
            last_data['month'] = next_date.month
            last_data['day_of_week'] = next_date.dayofweek
            
            # Make prediction
            pred_prob = model.predict_proba(last_data[feature_columns])[0][1] * 100
            predictions.append(pred_prob)
            
            # Update lag features
            binary_pred = 1.0 if pred_prob > 50 else 0.0
            for lag in [1, 3, 6, 12, 24]:
                last_data[f'Rain_Binary_lag_{lag}'] = binary_pred if lag == 1 else last_data[f'Rain_Binary_lag_{lag-1}'].iloc[0]
            
            # Update rolling features
            last_data['Rain_Binary_rolling_mean'] = binary_pred
            last_data['Rain_Binary_rolling_std'] = 0
        
        # Create prediction DataFrame
        last_date = df['Date'].max()
        future_dates = [last_date + timedelta(hours=i+1) for i in range(len(predictions))]
        pred_df = pd.DataFrame({
            'Date': future_dates,
            'Rain_Probability': predictions
        })
        
        return pred_df
    
    except Exception as e:
        return None 