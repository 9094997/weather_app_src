import json
import requests
from datetime import datetime
import os
from typing import Dict, List, Any
import random
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weather.config import OPENWEATHER_API_KEY, REQUEST_TIMEOUT, OUTPUT_FILE

class WeatherDataProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.weatherapi.com/v1/forecast.json"
    
    def get_weather_data(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch weather data from WeatherAPI.com."""
        params = {
            'key': self.api_key,
            'q': f"{lat}, {lon}",
            'days': 7,
            'aqi': 'no',
            'alerts': 'no'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def process_weather_data(self, raw_data: Dict[str, Any], location_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process relevant weather parameters from WeatherAPI.com response."""
        if not raw_data:
            return None
            
        # Get location data
        location = raw_data['location']
            
        processed_data = {
            'location': {
                'name': location['name'],
                'region': location['region'],
                'country': location['country'],
                'latitude': location['lat'],
                'longitude': location['lon']
            },
            'forecast': []
        }
        
        # Add forecast data for next days
        for day in raw_data['forecast']['forecastday']:
            forecast_data = {
                'date': day['date'],
                'temperature': {
                    'max': day['day']['maxtemp_c'],
                    'min': day['day']['mintemp_c'],
                    'average': day['day']['avgtemp_c']
                },
                'condition': {
                    'text': day['day']['condition']['text'],
                    'code': day['day']['condition']['code']
                }
            }
            processed_data['forecast'].append(forecast_data)
        
        return processed_data

def cleanup_weather_data():
    """Clean up the weather data file before starting new data collection."""
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            print(f"Cleaned up existing {OUTPUT_FILE}")
        except Exception as e:
            print(f"Error cleaning up {OUTPUT_FILE}: {str(e)}")

def save_weather_data(weather_data):
    """Save weather data to JSON file"""
    try:
        # Clear the existing file by writing an empty structure
        empty_data = {
            "grid_size_miles": 8,
            "total_cells": 0,
            "weather_data": [],
            "generated_at": datetime.now().isoformat()
        }
        
        with open('weather_data.json', 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=2)
        
        # Now write the new data
        with open('weather_data.json', 'w', encoding='utf-8') as f:
            json.dump(weather_data, f, indent=2)
        print("Weather data saved successfully")
    except Exception as e:
        print(f"Error saving weather data: {str(e)}")

def main():
    # Clean up existing weather data
    cleanup_weather_data()
    
    # Use API key from config
    api_key = OPENWEATHER_API_KEY
    if not api_key:
        raise ValueError("WeatherAPI.com API key not found in config")
    
    # Initialize weather processor
    processor = WeatherDataProcessor(api_key)
    
    # Load locations from JSON file
    try:
        # Update path to point to the map folder
        locations_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'map', 'locations.json')
        print(f"Attempting to read locations file from: {locations_file}")
        
        if not os.path.exists(locations_file):
            print(f"Error: File does not exist at {locations_file}")
            return
            
        with open(locations_file, 'r', encoding='utf-8') as file:
            try:
                locations_data = json.load(file)
                print("Successfully loaded JSON data")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                print(f"Error occurred at line {e.lineno}, column {e.colno}")
                return
                
        if not isinstance(locations_data, dict) or 'cells' not in locations_data:
            print("Error: Invalid JSON structure. Expected a dictionary with 'cells' key")
            return
            
        print(f"Found {len(locations_data['cells'])} locations in the file")
        
    except FileNotFoundError:
        print(f"Error: locations.json file not found at {locations_file}")
        return
    except Exception as e:
        print(f"Error loading locations file: {str(e)}")
        return
    
    # Randomly select 20 locations from the total cells
    total_cells = locations_data['cells']
    selected_cells = random.sample(total_cells, min(100, len(total_cells)))
    
    print(f"Processing weather data for {len(selected_cells)} randomly selected locations...")
    
    # Process weather data for selected locations
    processed_weather_data = []
    
    for index, cell in enumerate(selected_cells, 1):
        print(f"{index:3d} Fetching weather data for coordinates: {cell['latitude']}, {cell['longitude']}")
        raw_weather = processor.get_weather_data(cell['latitude'], cell['longitude'])
        if raw_weather:
            processed_data = processor.process_weather_data(raw_weather, cell)
            if processed_data:
                processed_weather_data.append(processed_data)
    
    # Save processed data to new JSON file
    output_data = {
        'grid_size_miles': locations_data['grid_size_miles'],
        'total_cells': len(selected_cells),
        'weather_data': processed_weather_data,
        'generated_at': datetime.utcnow().isoformat()
    }
    
    # Use the output file path from config
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    with open(output_path, 'w') as file:
        json.dump(output_data, file, indent=2)
    
    print(f"Weather data has been processed and saved to {OUTPUT_FILE}")
    print(f"Successfully processed {len(processed_weather_data)} locations")

if __name__ == "__main__":
    main()