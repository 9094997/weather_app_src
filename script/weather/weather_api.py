import json
import requests
from datetime import datetime
import os
from typing import Dict, List, Any

class WeatherDataProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    def kelvin_to_celsius(self, kelvin: float) -> float:
        """Convert Kelvin to Celsius."""
        return round(kelvin - 273.15, 2)
    
    def get_weather_data(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch weather data from OpenWeather API."""
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def process_weather_data(self, raw_data: Dict[str, Any], location_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process relevant weather parameters."""
        if not raw_data:
            return None
            
        processed_data = {
            'latitude': location_info['latitude'],
            'longitude': location_info['longitude'],
            'name': location_info['name'],
            'weather': {
                'temperature': {
                    'average': self.kelvin_to_celsius(raw_data['main']['temp']),
                    'min': self.kelvin_to_celsius(raw_data['main']['temp_min']),
                    'max': self.kelvin_to_celsius(raw_data['main']['temp_max'])
                },
                'wind_speed': raw_data['wind']['speed'],
                'uv_level': self.get_uv_index(location_info['latitude'], location_info['longitude']),
                'condition': raw_data['weather'][0]['main'],
                'condition_description': raw_data['weather'][0]['description']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return processed_data
    
    def get_uv_index(self, lat: float, lon: float) -> float:
        """Fetch UV index data from OpenWeather API."""
        uv_url = f"https://api.openweathermap.org/data/2.5/uvi"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key
        }
        
        try:
            response = requests.get(uv_url, params=params)
            response.raise_for_status()
            return response.json()['value']
        except requests.RequestException:
            return None

def main():
    # Load API key from environment variable
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        raise ValueError("OpenWeather API key not found in environment variables")
    
    # Initialize weather processor
    processor = WeatherDataProcessor(api_key)
    
    # Load locations from JSON file
    try:
        with open('locations.json', 'r') as file:
            locations_data = json.load(file)
    except FileNotFoundError:
        print("Error: locations.json file not found")
        return
    
    # Process weather data for each location
    processed_weather_data = []
    
    for cell in locations_data['cells']:
        raw_weather = processor.get_weather_data(cell['latitude'], cell['longitude'])
        if raw_weather:
            processed_data = processor.process_weather_data(raw_weather, cell)
            if processed_data:
                processed_weather_data.append(processed_data)
    
    # Save processed data to new JSON file
    output_data = {
        'grid_size_miles': locations_data['grid_size_miles'],
        'total_cells': locations_data['total_cells'],
        'weather_data': processed_weather_data,
        'generated_at': datetime.utcnow().isoformat()
    }
    
    with open('weather_forecast.json', 'w') as file:
        json.dump(output_data, file, indent=2)
    
    print(f"Weather data has been processed and saved to weather_forecast.json")

if __name__ == "__main__":
    main()