from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import json
import os
import sys
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import numpy as np
from functools import lru_cache
from typing import Tuple, Dict, Any, List
import time
import threading

# Add the score_system directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
score_system_dir = os.path.join(script_dir, 'score_system')
sys.path.append(score_system_dir)

from sunny_score import get_top_sunny_destinations, calculate_destination_sunny_score
from comfort_index import get_top_comfortable_destinations, calculate_destination_comfort_score

app = Flask(__name__)

# Initialize geocoder with a custom user agent
geolocator = Nominatim(user_agent="travel_app")

# Global cache for performance optimization
_distance_cache = {}
_score_cache = {}
_closest_location_cache = {}

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
    """Calculate distance between two points in miles - optimized version"""
    try:
        # Use faster haversine calculation instead of geodesic
        return haversine_distance_miles(lat1, lon1, lat2, lon2)
    except:
        return float('inf')

def get_cells_within_radius(center_lat, center_lon, radius_miles, grid_data):
    """Get all grid cells within the specified radius using fast distance calculation"""
    cells_in_radius = []
    
    for cell in grid_data.get('cell_boundaries', []):
        center = cell.get('center', {})
        cell_lat = center.get('latitude')
        cell_lon = center.get('longitude')
        
        if cell_lat is not None and cell_lon is not None:
            # Use fast haversine distance instead of geodesic
            distance = haversine_distance_miles(center_lat, center_lon, cell_lat, cell_lon)
            if distance <= radius_miles:
                cells_in_radius.append(cell)
    
    return cells_in_radius


def auto_refresh():
    """Background function that runs the weather monitor and checks time"""
    while True:
        current_time = datetime.now()
        global WEATHER_DATA
        
        if current_time.hour == 3 and current_time.minute == 10:
            print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Weather data reloaded at 3:10 AM")
            WEATHER_DATA = load_weather_data()
        else:
            # Print statement every 3 hours (0, 3, 6, 9, 12, 15, 18, 21)
            if current_time.hour % 3 == 0 and current_time.minute == 0:
                print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Weather data check - next reload at 3:10 AM")
        
        time.sleep(60)  # Check every minute


# Load the weather data and grid boundaries
WEATHER_DATA = load_weather_data()
GRID_BOUNDARIES = load_grid_boundaries()

# Start the background weather monitor thread
weather_monitor_thread = threading.Thread(target=auto_refresh, daemon=True)
weather_monitor_thread.start()


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

@app.route('/project-weather-index')
def project_weather_index():
    """Calculate real weather scores for grid cells within radius"""
    try:
        # Get query parameters
        center_lat = float(request.args.get('lat'))
        center_lon = float(request.args.get('lon'))
        radius_miles = float(request.args.get('radius', 200))
        index_type = request.args.get('index_type', 'sunny')  # 'sunny' or 'comfort'
        target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        start_hour = int(request.args.get('start_hour', 9))
        end_hour = int(request.args.get('end_hour', 17))
        
        # Validate parameters
        if index_type not in ['sunny', 'comfort']:
            return jsonify({"error": "index_type must be 'sunny' or 'comfort'"}), 400
        
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            return jsonify({"error": "Invalid time range. Hours must be between 0-23"}), 400
        
        if start_hour >= end_hour:
            return jsonify({"error": "Start hour must be before end hour"}), 400
        
        # Parse target date
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        # Get cells within radius
        cells_in_radius = get_cells_within_radius(center_lat, center_lon, radius_miles, GRID_BOUNDARIES)
        
        # Step 1: Find closest weather location for each cell (vectorized)
        print(f"Processing {len(cells_in_radius)} cells...")
        start_time = time.time()
        
        cells_with_locations = []
        for cell in cells_in_radius:
            cell_center = cell.get('center', {})
            cell_lat = cell_center.get('latitude')
            cell_lon = cell_center.get('longitude')
            
            if cell_lat is None or cell_lon is None:
                continue
            
            # Find the closest weather data location (cached)
            closest_location_data, distance = find_closest_weather_location_fast(cell_lat, cell_lon, LOCATION_INDEX)
            
            # Skip cells that are too far from any weather station (>50 miles)
            if closest_location_data and distance <= 50:
                cells_with_locations.append({
                    'cell': cell,
                    'location_data': closest_location_data,
                    'distance': distance
                })
            else:
                # Add cell with no data for very distant cells
                cells_with_locations.append({
                    'cell': cell,
                    'location_data': None,
                    'distance': float('inf')
                })
        
        location_time = time.time() - start_time
        print(f"Location lookup completed in {location_time:.2f}s")
        
        # Step 2: Batch calculate scores (grouped by weather location to avoid redundancy)
        start_time = time.time()
        cells_with_scores = batch_calculate_scores(cells_with_locations, index_type, target_date_obj, start_hour, end_hour)
        
        score_time = time.time() - start_time
        print(f"Score calculation completed in {score_time:.2f}s for {len(cells_with_scores)} cells")
        
        return jsonify({
            'center': {
                'latitude': center_lat,
                'longitude': center_lon
            },
            'radius_miles': radius_miles,
            'index_type': index_type,
            'target_date': target_date,
            'time_range': f"{start_hour:02d}:00-{end_hour:02d}:00",
            'total_cells': len(cells_with_scores),
            'cells': cells_with_scores
        })
        
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid parameters: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/projection-progress')
def projection_progress():
    """Return current projection calculation progress (for future use with WebSockets)"""
    return jsonify({
        'status': 'ready',
        'cache_stats': {
            'distance_cache_size': len(_distance_cache),
            'location_cache_size': len(_closest_location_cache),
            'score_cache_size': len(_score_cache)
        }
    })

@app.route('/clear-cache')
def clear_cache():
    """Clear performance caches (useful for development)"""
    global _distance_cache, _closest_location_cache, _score_cache
    _distance_cache.clear()
    _closest_location_cache.clear()
    _score_cache.clear()
    
    # Clear LRU caches
    cached_distance_miles.cache_clear()
    cached_weather_score.cache_clear()
    
    return jsonify({'status': 'Cache cleared successfully'})

def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Fast haversine distance calculation in miles.
    Much faster than geodesic for our use case.
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    # Radius of earth in miles
    r = 3956
    return c * r

@lru_cache(maxsize=10000)
def cached_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Cached version of distance calculation"""
    cache_key = f"{lat1:.4f},{lon1:.4f},{lat2:.4f},{lon2:.4f}"
    if cache_key in _distance_cache:
        return _distance_cache[cache_key]
    
    distance = haversine_distance_miles(lat1, lon1, lat2, lon2)
    _distance_cache[cache_key] = distance
    return distance

def build_location_index(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a spatial index of weather locations for fast lookup.
    Returns a dict with location data and coordinates for quick access.
    """
    location_index = {
        'locations': [],
        'coordinates': [],
        'data': []
    }
    
    for idx, location_data in enumerate(weather_data.get('weather_data', [])):
        location = location_data['location']
        lat, lon = location['latitude'], location['longitude']
        
        location_index['locations'].append(location)
        location_index['coordinates'].append((lat, lon))
        location_index['data'].append(location_data)
    
    return location_index

def find_closest_weather_location_fast(target_lat: float, target_lon: float, location_index: Dict[str, Any]) -> Tuple[Any, float]:
    """
    Fast closest location finder using pre-built index and vectorized calculations.
    Returns (location_data, distance) or (None, float('inf'))
    """
    cache_key = f"{target_lat:.4f},{target_lon:.4f}"
    if cache_key in _closest_location_cache:
        return _closest_location_cache[cache_key]
    
    if not location_index['coordinates']:
        return None, float('inf')
    
    # Vectorized distance calculation using numpy
    coords = np.array(location_index['coordinates'])
    target = np.array([target_lat, target_lon])
    
    # Calculate distances to all locations at once
    distances = np.array([
        haversine_distance_miles(target_lat, target_lon, lat, lon)
        for lat, lon in coords
    ])
    
    # Find the closest
    min_idx = np.argmin(distances)
    closest_location = location_index['data'][min_idx]
    min_distance = distances[min_idx]
    
    # Cache the result
    _closest_location_cache[cache_key] = (closest_location, min_distance)
    return closest_location, min_distance

@lru_cache(maxsize=1000)
def cached_weather_score(location_name: str, target_date: str, start_hour: int, end_hour: int, index_type: str) -> Tuple[float, str]:
    """
    Cached weather score calculation to avoid recalculating for the same location/parameters.
    """
    cache_key = f"{location_name}_{target_date}_{start_hour}_{end_hour}_{index_type}"
    if cache_key in _score_cache:
        return _score_cache[cache_key]
    
    # This should not be called - just a fallback
    return 0.0, 'No Data'

def batch_calculate_scores(cells_with_locations: List[Dict], index_type: str, target_date_obj, start_hour: int, end_hour: int) -> List[Dict]:
    """
    Batch calculate scores for multiple cells, grouping by weather location to minimize redundant calculations.
    """
    # Group cells by their closest weather location
    location_groups = {}
    for cell_info in cells_with_locations:
        cell, location_data, distance = cell_info['cell'], cell_info['location_data'], cell_info['distance']
        location_name = location_data['location']['name'] if location_data else 'Unknown'
        
        if location_name not in location_groups:
            location_groups[location_name] = {
                'location_data': location_data,
                'cells': [],
                'distance': distance
            }
        location_groups[location_name]['cells'].append(cell)
    
    # Calculate score once per location group
    results = []
    for location_name, group in location_groups.items():
        location_data = group['location_data']
        distance = group['distance']
        
        if location_data:
            # Calculate score once for this location
            if index_type == 'sunny':
                score_data = calculate_destination_sunny_score(
                    location_data, target_date_obj, start_hour, end_hour
                )
                score = score_data['sunny_score'] if score_data else 0
                level = score_data['sunny_level'] if score_data else 'No Data'
            else:  # comfort
                score_data = calculate_destination_comfort_score(
                    location_data, target_date_obj, start_hour, end_hour
                )
                score = score_data['comfort_score'] if score_data else 0
                level = score_data['comfort_level'] if score_data else 'No Data'
            
            # Apply this score to all cells in this group
            for cell in group['cells']:
                cell_with_score = cell.copy()
                cell_with_score['weather_score'] = {
                    'score': round(score, 2),
                    'level': level,
                    'index_type': index_type,
                    'closest_location': location_name,
                    'distance_to_station': round(distance, 1) if distance != float('inf') else None
                }
                results.append(cell_with_score)
        else:
            # No weather data available
            for cell in group['cells']:
                cell_with_score = cell.copy()
                cell_with_score['weather_score'] = {
                    'score': 0,
                    'level': 'No Data',
                    'index_type': index_type,
                    'closest_location': 'Unknown',
                    'distance_to_station': None
                }
                results.append(cell_with_score)
    
    return results

# Build location index on startup for fast lookups
LOCATION_INDEX = build_location_index(WEATHER_DATA)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True)
