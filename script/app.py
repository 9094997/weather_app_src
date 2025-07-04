from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import json
import os
import sys
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import math

# Add the score_system directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
score_system_dir = os.path.join(script_dir, 'score_system')
sys.path.append(score_system_dir)

from sunny_score import get_top_sunny_destinations, calculate_destination_sunny_score
from comfort_index import get_top_comfortable_destinations, calculate_destination_comfort_score

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

def load_grid_boundaries():
    """Load grid boundaries data from grid_boundaries.json"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        boundaries_file = os.path.join(script_dir, 'map', 'grid_boundaries.json')
        with open(boundaries_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: grid_boundaries.json not found")
        return {"cell_boundaries": []}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in grid_boundaries.json")
        return {"cell_boundaries": []}

def calculate_distance_miles(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles"""
    try:
        point1 = (lat1, lon1)
        point2 = (lat2, lon2)
        return geodesic(point1, point2).miles
    except:
        return float('inf')

def get_cells_within_radius(center_lat, center_lon, radius_miles, grid_data):
    """Get all grid cells within the specified radius"""
    cells_in_radius = []
    
    for cell in grid_data.get('cell_boundaries', []):
        center = cell.get('center', {})
        cell_lat = center.get('latitude')
        cell_lon = center.get('longitude')
        
        if cell_lat is not None and cell_lon is not None:
            distance = calculate_distance_miles(center_lat, center_lon, cell_lat, cell_lon)
            if distance <= radius_miles:
                cells_in_radius.append(cell)
    
    return cells_in_radius

# Load the weather data and grid boundaries
WEATHER_DATA = load_weather_data()
GRID_BOUNDARIES = load_grid_boundaries()

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
        travel_date = datetime.strptime(data['date'], '%Y-%m-%d')
        start_hour = int(data.get('start_hour', 9))
        end_hour = int(data.get('end_hour', 17))
        max_distance = float(data['distance'])
        
        # Get starting location coordinates
        start_location_data = geolocator.geocode(start_location)
        if not start_location_data:
            return jsonify({"error": "Starting location not found"}), 400
        
        start_coords = (start_location_data.latitude, start_location_data.longitude)
        
        # Get top 10 sunny destinations using the sunny_score module
        sunny_destinations = get_top_sunny_destinations(
            weather_data=WEATHER_DATA,
            target_date=travel_date.date(),
            start_hour=start_hour,
            end_hour=end_hour,
            max_distance=max_distance,
            start_coords=start_coords
        )
        
        # Get top 10 comfortable destinations using the comfort_index module
        comfortable_destinations = get_top_comfortable_destinations(
            weather_data=WEATHER_DATA,
            target_date=travel_date.date(),
            start_hour=start_hour,
            end_hour=end_hour,
            max_distance=max_distance,
            start_coords=start_coords
        )
        
        return jsonify({
            'sunny_destinations': sunny_destinations,
            'comfortable_destinations': comfortable_destinations
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weather-data')
def get_weather_data():
    """Return the current weather data"""
    return jsonify(WEATHER_DATA)

@app.route('/hourly-weather/<int:location_index>/<date>')
def get_hourly_weather(location_index, date):
    """Get hourly weather data for a specific location and date"""
    try:
        # Validate location index
        if location_index < 1 or location_index > len(WEATHER_DATA.get('weather_data', [])):
            return jsonify({"error": "Invalid location index"}), 400
        
        location_data = WEATHER_DATA['weather_data'][location_index - 1]
        
        # Find the forecast for the specified date
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        for forecast in location_data['forecast']:
            forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
            if forecast_date == target_date:
                return jsonify({
                    'location': location_data['location'],
                    'date': forecast['date'],
                    'day_summary': forecast['day_summary'],
                    'astro': forecast['astro'],
                    'hourly': forecast['hourly']
                })
        
        return jsonify({"error": "Weather data not found for the specified date"}), 404
        
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weather-stats/<int:location_index>/<date>')
def get_weather_stats(location_index, date):
    """Get weather statistics for a specific location, date, and time range"""
    try:
        # Get query parameters for time range
        start_hour = int(request.args.get('start_hour', 9))
        end_hour = int(request.args.get('end_hour', 17))
        
        # Validate time range
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            return jsonify({"error": "Invalid time range. Hours must be between 0-23"}), 400
        
        if start_hour >= end_hour:
            return jsonify({"error": "Start hour must be before end hour"}), 400
        
        # Validate location index
        if location_index < 1 or location_index > len(WEATHER_DATA.get('weather_data', [])):
            return jsonify({"error": "Invalid location index"}), 400
        
        location_data = WEATHER_DATA['weather_data'][location_index - 1]
        
        # Find the forecast for the specified date
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        for forecast in location_data['forecast']:
            forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
            if forecast_date == target_date:
                # Use sunny_score module to calculate stats
                sunny_data = calculate_destination_sunny_score(
                    location_data, target_date, start_hour, end_hour
                )
                
                # Use comfort_index module to calculate stats
                comfort_data = calculate_destination_comfort_score(
                    location_data, target_date, start_hour, end_hour
                )
                
                if sunny_data and comfort_data:
                    return jsonify({
                        'location': location_data['location'],
                        'date': forecast['date'],
                        'day_summary': forecast['day_summary'],
                        'sunny_data': sunny_data,
                        'comfort_data': comfort_data
                    })
                else:
                    return jsonify({"error": "No weather data available for the specified time range"}), 404
        
        return jsonify({"error": "Weather data not found for the specified date"}), 404
        
    except ValueError as e:
        return jsonify({"error": f"Invalid input: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weather-icons/<path:filename>')
def serve_weather_icon(filename):
    """Serve weather icons from the icons directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(script_dir, '..', 'icons_and_codes', 'weather_icons')
    return send_from_directory(icons_dir, filename)

@app.route('/grid-boundaries')
def get_grid_boundaries():
    """Return the grid boundaries data"""
    return jsonify(GRID_BOUNDARIES)

@app.route('/cells-in-radius')
def get_cells_in_radius():
    """Get grid cells within a specified radius from a center point"""
    try:
        # Get query parameters
        center_lat = float(request.args.get('lat'))
        center_lon = float(request.args.get('lon'))
        radius_miles = float(request.args.get('radius', 200))
        
        # Get cells within radius
        cells_in_radius = get_cells_within_radius(center_lat, center_lon, radius_miles, GRID_BOUNDARIES)
        
        return jsonify({
            'center': {
                'latitude': center_lat,
                'longitude': center_lon
            },
            'radius_miles': radius_miles,
            'total_cells': len(cells_in_radius),
            'cells': cells_in_radius
        })
        
    except (ValueError, TypeError) as e:
        return jsonify({"error": "Invalid parameters. Please provide lat, lon, and radius"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)