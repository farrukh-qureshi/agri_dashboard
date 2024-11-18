import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import json

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def clean_weather_data(df):
    """Clean the dataframe by removing outliers and invalid values"""
    # Remove -999 values which indicate missing data
    df = df.replace(-999, pd.NA)
    
    # Remove rows where any of the main parameters are missing
    df = df.dropna(subset=['T2M', 'RH2M', 'WS2M'])
    
    # Remove statistical outliers (values outside 3 standard deviations)
    for column in ['T2M', 'RH2M', 'WS2M']:
        mean = df[column].mean()
        std = df[column].std()
        df = df[df[column].between(mean - 3*std, mean + 3*std)]
    
    # Ensure humidity is between 0 and 100
    df = df[df['RH2M'].between(0, 100)]
    
    # Ensure temperature is within reasonable range (-50°C to 60°C)
    df = df[df['T2M'].between(-50, 60)]
    
    return df

def get_cached_filename(start_date, end_date, latitude, longitude):
    """Generate a filename for cached data"""
    return os.path.join(DATA_DIR, 
        f"weather_data_{start_date}_{end_date}_{latitude}_{longitude}.csv")

def get_weather_data(latitude, longitude, start_date, end_date):
    """Get weather data from NASA POWER API or cached file"""
    cache_file = get_cached_filename(start_date, end_date, latitude, longitude)
    
    # Check if we have recent cached data (less than 1 hour old)
    if os.path.exists(cache_file):
        file_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if file_age < 3600:  # 1 hour in seconds
            try:
                df = pd.read_csv(cache_file)
                df['Date'] = pd.to_datetime(df['Date'])
                return df
            except Exception as e:
                print(f"Error reading cached file: {e}")
    
    url = f"https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": "T2M,RH2M,WS2M",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "JSON"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        parameter_data = data['properties']['parameter']
        df = pd.DataFrame()
        for key, value in parameter_data.items():
            df[key] = list(value.values())
        df['Date'] = list(parameter_data['T2M'].keys())
        
        # Convert the date string to datetime properly
        df['Date'] = df['Date'].apply(lambda x: 
            datetime.strptime(str(x), '%Y%m%d%H'))
        
        # Clean the data
        df = clean_weather_data(df)
        
        # Save to cache
        df.to_csv(cache_file, index=False)
        
        return df
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        return None

def get_last_30_days_data():
    """Get data for the last 30 days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    return get_weather_data(
        latitude=32.68,
        longitude=71.78,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d")
    ) 