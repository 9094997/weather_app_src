from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import json
import os
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

app = Flask(__name__)

# Initialize geocoder with a custom user agent
geolocator = Nominatim(user_agent="travel_app")

def load_weather_data():
    """Load weather data from weather_data.json"""
    try:
        # Get the absolute path to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        weather_file = os.path.join(script_dir, 'weather', 'weather_data.json')
        with open(weather_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: weather_data.json not found at {weather_file}")
        return {"weather_data": []}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in weather_data.json")
        return {"weather_data": []}

def load_categorised_weather():
    """Load categorised weather data"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        weather_file = os.path.join(script_dir, '..', 'icons_and_codes', 'categorised_weather.json')
        with open(weather_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: categorised_weather.json not found at {weather_file}")
        return {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in categorised_weather.json")
        return {}

# Load the weather data
WEATHER_DATA = load_weather_data()
CATEGORISED_WEATHER = load_categorised_weather()

def get_weather_category(condition_code):
    """Get the weather category for a given condition code"""
    for category, conditions in CATEGORISED_WEATHER.items():
        for condition in conditions:
            if condition['code'] == condition_code:
                return category, condition['icon']
    return None, None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/location-suggest')
#this function take user's location input and convert it to coordinates
def location_suggest():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    try:
        # Search for locations using Nominatim
        locations = geolocator.geocode(
            query,
            exactly_one=False,
            limit=5,
            addressdetails=True,
            country_codes=['gb']  # Limit to UK
        )
        
        if not locations:
            return jsonify([])
        
        suggestions = []
        for loc in locations:
            if loc.address:
                suggestions.append({
                    'display_name': loc.address,
                    'lat': loc.latitude,
                    'lon': loc.longitude
                })
        
        return jsonify(suggestions)
    
    except GeocoderTimedOut:
        return jsonify({"error": "Service temporarily unavailable"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    
    try:
        # Get user inputs
        start_location = data['from']
        desired_weather = data['weather']
        travel_date = datetime.strptime(data['date'], '%Y-%m-%d')
        max_distance = float(data['distance'])
        
        # Get starting location coordinates
        start_location_data = geolocator.geocode(start_location)
        if not start_location_data:
            return jsonify({"error": "Starting location not found"}), 400
        
        start_coords = (start_location_data.latitude, start_location_data.longitude)
        
        # Find matching destinations from weather data
        matches = []
        for index, location_data in enumerate(WEATHER_DATA.get('weather_data', []), 1):
            location = location_data['location']
            dest_coords = (location['latitude'], location['longitude'])
            distance = geodesic(start_coords, dest_coords).miles
            
            # Check if any forecast day matches the travel date
            for forecast in location_data['forecast']:
                forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d')
                if forecast_date.date() == travel_date.date():
                    # Get weather category and icon for the condition code
                    weather_category, icon_code = get_weather_category(forecast['condition']['code'])
                    
                    # Check if the weather category matches the desired weather
                    if weather_category == desired_weather and distance <= max_distance:
                        matches.append({
                            'index': index,
                            'city': location['name'],
                            'region': location['region'],
                            'country': location['country'],
                            'distance': round(distance, 1),
                            'coordinates': {
                                'lat': location['latitude'],
                                'lon': location['longitude']
                            },
                            'weather': {
                                'condition': forecast['condition']['text'],
                                'temperature': forecast['temperature'],
                                'icon_code': icon_code
                            }
                        })
                    break
        
        return jsonify(matches)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weather-data')
def get_weather_data():
    """Return the current weather data"""
    return jsonify(WEATHER_DATA)

@app.route('/weather-icons/<path:filename>')
def serve_weather_icon(filename):
    """Serve weather icons from the icons directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(script_dir, '..', 'icons_and_codes', 'weather_icons')
    return send_from_directory(icons_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)