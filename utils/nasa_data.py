import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from sklearn.covariance import EllipticEnvelope
from io import StringIO
from utils.cache_utils import save_cached_data, load_cached_data, DataTracker, get_cached_filename

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def clean_weather_data(df):
    """Clean the dataframe by removing outliers and invalid values"""
    # Remove -999 values which indicate missing data
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    numerical_cols = [col for col in numerical_cols if col not in ['Date', 'WD2M']]
    
    # Remove rows where any parameters are missing
    df = df.dropna(subset=numerical_cols)
    
    # Use Robust Covariance Estimation for outlier detection
    outlier_detector = EllipticEnvelope(
        contamination=0.1,
        random_state=42,
        support_fraction=0.8
    )
    
    # Fit and predict outliers
    outlier_labels = outlier_detector.fit_predict(df[numerical_cols])
    df = df[outlier_labels == 1]
    
    # Apply basic physical constraints
    if 'RH2M' in df.columns:
        df = df[df['RH2M'].between(0, 100)]
    if 'T2M' in df.columns:
        df = df[df['T2M'].between(-50, 60)]
    if 'PRECTOTCORR' in df.columns:
        df = df[df['PRECTOTCORR'].between(0, 500)]
    if 'WD2M' in df.columns:
        df = df[df['WD2M'].between(0, 360)]  # Wind direction is in degrees (0-360)
    
    return df

def get_cached_filename(start_date, end_date, latitude, longitude):
    """Generate a filename for cached data"""
    return os.path.join(DATA_DIR, 
        f"weather_data_{start_date}_{end_date}_{latitude}_{longitude}.csv")

def get_weather_data(latitude, longitude, start_date, end_date):
    """Get weather data from NASA POWER API or cached file"""
    cache_file = get_cached_filename(start_date, end_date, latitude, longitude)
    
    # Check if we have recent cached data
    if os.path.exists(cache_file):
        file_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if file_age < 3600:  # 1 hour in seconds
            try:
                df = pd.read_csv(cache_file)
                df['Date'] = pd.to_datetime(df['Date'])
                return df
            except Exception as e:
                print(f"Error reading cached file: {e}")
    
    url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": "T2M,RH2M,WS2M,PRECTOTCORR,WD2M",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "CSV"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        # Find the start of data by looking for 'YEAR' in the header
        lines = response.text.split('\n')
        header_idx = next(i for i, line in enumerate(lines) if 'YEAR' in line)
        
        # Parse CSV starting from the actual data rows
        df = pd.read_csv(StringIO(response.text), skiprows=header_idx)
        
        # Create datetime from individual columns
        df['Date'] = pd.to_datetime(
            df['YEAR'].astype(str) + '-' + 
            df['MO'].astype(str).str.zfill(2) + '-' + 
            df['DY'].astype(str).str.zfill(2) + ' ' + 
            df['HR'].astype(str).str.zfill(2) + ':00:00'
        )
        
        # Drop the individual date/time columns
        df = df.drop(['YEAR', 'MO', 'DY', 'HR'], axis=1)
        
        # Clean the data
        df = clean_weather_data(df)
        
        # Save to cache
        df.to_csv(cache_file, index=False)
        
        return df
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        return None

def get_historical_data(days: int = None, latitude: float = None, longitude: float = None, 
                       start_date: datetime.date = None, end_date: datetime.date = None):
    """Get historical weather data with smart tracking and caching"""
    tracker = DataTracker()
    
    if start_date and end_date:
        # Convert date to datetime for consistent handling
        actual_start_date = datetime.combine(start_date, datetime.min.time())
        actual_end_date = datetime.combine(end_date, datetime.max.time())
        days = (end_date - start_date).days + 1
    else:
        # Use days-based range
        actual_end_date = datetime.now()
        actual_start_date = actual_end_date - timedelta(days=days)

    # Check if we have matching data
    cached_file = tracker.find_matching_data(
        latitude, longitude, actual_start_date, actual_end_date
    )
    
    if cached_file:
        # Load and filter the cached data
        df = pd.read_csv(cached_file)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[
            (df['Date'].dt.date >= actual_start_date.date()) & 
            (df['Date'].dt.date <= actual_end_date.date())
        ]
        return df, True  # True indicates cache hit
    
    # If no cache available, fetch new data
    df = get_weather_data(
        latitude=latitude,
        longitude=longitude,
        start_date=actual_start_date.strftime("%Y%m%d"),
        end_date=actual_end_date.strftime("%Y%m%d")
    )
    
    if df is not None and not df.empty:
        # Save the new data and track it
        filename = get_cached_filename(latitude, longitude, actual_start_date, actual_end_date)
        df.to_csv(filename, index=False)
        tracker.add_data_entry(
            latitude, longitude, 
            actual_start_date, actual_end_date, 
            filename
        )
    
    return df, False  # False indicates new data fetch

# Make sure functions are available for import
__all__ = ['get_historical_data', 'get_weather_data', 'clean_weather_data']