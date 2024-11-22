import os
import json
import pandas as pd
from datetime import datetime, timedelta
import hashlib

class DataTracker:
    def __init__(self, tracking_file="data/tracking.json"):
        self.tracking_file = tracking_file
        self.tracking_dir = os.path.dirname(tracking_file)
        os.makedirs(self.tracking_dir, exist_ok=True)
        self.load_tracking()

    def load_tracking(self):
        """Load or initialize tracking data"""
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                self.tracking = json.load(f)
        else:
            self.tracking = {}
            self.save_tracking()

    def save_tracking(self):
        """Save tracking data to file"""
        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking, f, indent=2)

    def get_location_key(self, latitude: float, longitude: float) -> str:
        """Generate a unique key for a location"""
        return f"{latitude:.4f}_{longitude:.4f}"

    def add_data_entry(self, latitude: float, longitude: float, 
                      start_date: datetime, end_date: datetime, 
                      filename: str):
        """Add a new data entry to tracking"""
        location_key = self.get_location_key(latitude, longitude)
        
        if location_key not in self.tracking:
            self.tracking[location_key] = {
                "latitude": latitude,
                "longitude": longitude,
                "data_ranges": []
            }
        
        # Add new date range
        self.tracking[location_key]["data_ranges"].append({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filename": filename,
            "downloaded_at": datetime.now().isoformat()
        })
        
        self.save_tracking()

    def find_matching_data(self, latitude: float, longitude: float, 
                         start_date: datetime, end_date: datetime) -> str:
        """Find existing data that covers the requested date range"""
        location_key = self.get_location_key(latitude, longitude)
        
        if location_key not in self.tracking:
            return None
            
        # Check all data ranges for this location
        for data_range in self.tracking[location_key]["data_ranges"]:
            cached_start = datetime.fromisoformat(data_range["start_date"])
            cached_end = datetime.fromisoformat(data_range["end_date"])
            
            # Check if requested range is within cached range
            if cached_start.date() <= start_date.date() and cached_end.date() >= end_date.date():
                filename = data_range["filename"]
                if os.path.exists(filename):
                    return filename
                    
        return None

def get_cached_filename(latitude: float, longitude: float, 
                       start_date: datetime, end_date: datetime) -> str:
    """Generate a filename for the cached data"""
    cache_dir = "data/cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    filename = f"weather_{latitude:.4f}_{longitude:.4f}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    return os.path.join(cache_dir, filename)

def get_cache_key(latitude: float, longitude: float, days: int, start_date: datetime = None, end_date: datetime = None) -> str:
    """Generate a unique cache key based on query parameters"""
    if start_date and end_date:
        params = f"{latitude:.4f}_{longitude:.4f}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    else:
        params = f"{latitude:.4f}_{longitude:.4f}_{days}"
    return hashlib.md5(params.encode()).hexdigest()

def save_cached_data(df: pd.DataFrame, latitude: float, longitude: float, days: int, 
                    cache_dir: str = "data/cache", start_date: datetime = None, 
                    end_date: datetime = None):
    """Save data to cache with metadata"""
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cache_key = get_cache_key(latitude, longitude, days, start_date, end_date)
        
        # Sort DataFrame by date before saving
        df = df.sort_values('Date')
        
        # Save DataFrame
        df_path = os.path.join(cache_dir, f"{cache_key}.csv")
        df.to_csv(df_path, index=False)
        
        # Save metadata with date range
        metadata = {
            "latitude": latitude,
            "longitude": longitude,
            "days": days,
            "timestamp": datetime.now().isoformat(),
            "date_range": {
                "start": df['Date'].min().isoformat(),
                "end": df['Date'].max().isoformat()
            },
            "custom_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "rows": len(df)
        }
        meta_path = os.path.join(cache_dir, f"{cache_key}.json")
        with open(meta_path, 'w') as f:
            json.dump(metadata, f)
            
        return True
    except Exception as e:
        print(f"Error saving cache: {str(e)}")
        return False

def find_matching_cache(latitude: float, longitude: float, start_date: datetime, 
                       end_date: datetime, cache_dir: str = "data/cache") -> tuple:
    """Find any cached data that contains the requested date range"""
    try:
        if not os.path.exists(cache_dir):
            return None, None
            
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                meta_path = os.path.join(cache_dir, filename)
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check if coordinates match
                if (abs(metadata['latitude'] - latitude) < 0.0001 and 
                    abs(metadata['longitude'] - longitude) < 0.0001):
                    
                    # Get cached date range
                    cached_start = datetime.fromisoformat(metadata['date_range']['start'])
                    cached_end = datetime.fromisoformat(metadata['date_range']['end'])
                    
                    # Check if requested range is within cached range
                    if cached_start.date() <= start_date.date() and cached_end.date() >= end_date.date():
                        # Load the corresponding DataFrame
                        df_path = os.path.join(cache_dir, filename.replace('.json', '.csv'))
                        if os.path.exists(df_path):
                            df = pd.read_csv(df_path)
                            df['Date'] = pd.to_datetime(df['Date'])
                            return df, metadata
                            
        return None, None
    except Exception as e:
        print(f"Error finding matching cache: {str(e)}")
        return None, None

def load_cached_data(latitude: float, longitude: float, days: int, 
                    start_date: datetime = None, end_date: datetime = None,
                    max_age_hours: int = 24, cache_dir: str = "data/cache"):
    """Load cached data if available and return with metadata"""
    try:
        # First try to find matching cache for the date range
        if start_date and end_date:
            df, metadata = find_matching_cache(latitude, longitude, start_date, end_date, cache_dir)
            if df is not None:
                # Filter the data to the requested date range
                df = df[
                    (df['Date'].dt.date >= start_date.date()) & 
                    (df['Date'].dt.date <= end_date.date())
                ]
                if not df.empty:
                    return df, metadata
        
        # If no matching cache found, try exact cache key
        cache_key = get_cache_key(latitude, longitude, days, start_date, end_date)
        df_path = os.path.join(cache_dir, f"{cache_key}.csv")
        meta_path = os.path.join(cache_dir, f"{cache_key}.json")
        
        if not (os.path.exists(df_path) and os.path.exists(meta_path)):
            return None, None
            
        # Load metadata
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
            
        # Check cache age
        cache_time = datetime.fromisoformat(metadata['timestamp'])
        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            return None, None
            
        # Load DataFrame
        df = pd.read_csv(df_path)
        df['Date'] = pd.to_datetime(df['Date'])
        
        return df, metadata
    except Exception as e:
        print(f"Error loading cache: {str(e)}")
        return None, None 