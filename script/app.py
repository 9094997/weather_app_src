from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import json
import os
import sys
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from functools import lru_cache
from typing import Tuple, Dict, Any, List

# Add the score_system directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
score_system_dir = os.path.join(script_dir, 'score_system')
sys.path.append(score_system_dir)

# Import optimized modules
from weather_calculator import weather_calculator
from spatial_index import spatial_index, distance_cache

app = Flask(__name__)

# Initialize geocoder with a custom user agent
geolocator = Nominatim(user_agent="travel_app")

# Optimized lazy loading with caching
@lru_cache(maxsize=1)
def load_weather_data(file_path=None):
    """Load weather data from weather_data.json with lazy loading and caching"""
    if file_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'weather', 'weather_data.json')
    
    print(f"Loading weather data from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded weather data for {len(data.get('weather_data', []))} locations")
            
            # Build spatial index on first load
            spatial_index.build_index(data)
            return data
    except FileNotFoundError:
        print(f"Error: weather_data.json not found at {file_path}")
        return {"weather_data": []}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        return {"weather_data": []}

@lru_cache(maxsize=1)
def load_grid_boundaries():
    """Load grid boundaries data from grid_boundaries.json with caching"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        boundaries_file = os.path.join(script_dir, 'map', 'grid_boundaries.json')
        with open(boundaries_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded grid boundaries for {len(data.get('cell_boundaries', []))} cells")
            return data
    except FileNotFoundError:
        print(f"Error: grid_boundaries.json not found")
        return {"cell_boundaries": []}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in grid_boundaries.json")
        return {"cell_boundaries": []}

def get_weather_data():
    """Get weather data (cached after first load)"""
    return load_weather_data()

def get_grid_boundaries():
    """Get grid boundaries (cached after first load)"""
    return load_grid_boundaries()

# Helper functions to eliminate duplication
def validate_location_index(location_index):
    """Validate location index and return error response if invalid"""
    weather_data = get_weather_data()
    if location_index < 1 or location_index > len(weather_data.get('weather_data', [])):
        return jsonify({"error": "Invalid location index"}), 400
    return None

def parse_and_validate_date(date_str):
    """Parse date string and return datetime.date object or error response"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date(), None
    except ValueError:
        return None, (jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400)

def find_forecast_for_date(location_data, target_date):
    """Find forecast data for a specific date"""
    for forecast in location_data['forecast']:
        forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
        if forecast_date == target_date:
            return forecast
    return None

def validate_time_range(start_hour, end_hour):
    """Validate time range parameters"""
    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        return jsonify({"error": "Invalid time range. Hours must be between 0-23"}), 400
    
    if start_hour >= end_hour:
        return jsonify({"error": "Start hour must be before end hour"}), 400
    
    return None

def get_cells_within_radius(center_lat, center_lon, radius_miles, grid_data=None):
    """Get all grid cells within the specified radius using optimized spatial lookup"""
    if grid_data is None:
        grid_data = get_grid_boundaries()
    
    cells_in_radius = []
    
    # Use cached distance calculation for better performance
    for cell in grid_data.get('cell_boundaries', []):
        center = cell.get('center', {})
        cell_lat = center.get('latitude')
        cell_lon = center.get('longitude')
        
        if cell_lat is not None and cell_lon is not None:
            # Use cached distance calculation
            distance = distance_cache.get_distance(center_lat, center_lon, cell_lat, cell_lon)
            if distance <= radius_miles:
                cells_in_radius.append(cell)
    
    return cells_in_radius

# Optimized destination finding functions using unified calculator
def get_top_destinations_optimized(target_date, start_hour=9, end_hour=17, max_distance=None, 
                                 start_coords=None, limit=30):
    """
    Get top destinations for both sunny and comfort scores using optimized calculation.
    Replaces separate calls to get_top_sunny_destinations and get_top_comfortable_destinations.
    """
    weather_data = get_weather_data()
    destinations = []
    
    # Use spatial index for fast location filtering if distance constraint exists
    if max_distance and start_coords:
        candidate_locations = spatial_index.get_locations_within_radius(
            start_coords[0], start_coords[1], max_distance
        )
        location_data_list = [(data, distance) for data, distance in candidate_locations]
    else:
        # Process all locations
        location_data_list = [
            (location_data, 0) 
            for location_data in weather_data.get('weather_data', [])
        ]
    
    print(f"Processing {len(location_data_list)} locations for optimization...")
    
    for index, (location_data, distance) in enumerate(location_data_list, 1):
        location = location_data['location']
        
        # Calculate both scores efficiently using unified calculator
        scores_data = weather_calculator.calculate_both_scores(
            location_data, target_date, start_hour, end_hour
        )
        
        if scores_data:
            sunny_data = scores_data['sunny_data']
            comfort_data = scores_data['comfort_data']
            temp_range = scores_data['temperature_range']
            
            destination = {
                'index': index,
                'city': location['name'],
                'region': location['region'],
                'country': location['country'],
                'distance': round(distance, 1) if distance > 0 else None,
                'coordinates': {
                    'lat': location['latitude'],
                    'lon': location['longitude']
                },
                # Sunny score data
                'sunny_score': sunny_data['sunny_score'],
                'sunny_level': sunny_data['sunny_level'],
                'cloud_score': sunny_data['cloud_score'],
                'uv_score': sunny_data['uv_score'],
                'visibility_score': sunny_data['visibility_score'],
                'rain_score': sunny_data['rain_score'],
                'snow_score': sunny_data['snow_score'],
                # Comfort score data
                'comfort_score': comfort_data['comfort_score'],
                'comfort_level': comfort_data['comfort_level'],
                'feels_like_temp_score': comfort_data.get('feels_like_temp_score', 0),
                'humidity_score': comfort_data.get('humidity_score', 0),
                # Shared data
                'time_range': sunny_data['time_range'],
                'min_temp': temp_range['min_temp'],
                'max_temp': temp_range['max_temp'],
                'hourly_summary': scores_data['hourly_summary']  # Count instead of full data
            }
            destinations.append(destination)
    
    return destinations

def get_top_sunny_destinations_optimized(weather_data, target_date, start_hour=9, end_hour=17, 
                                       max_distance=None, start_coords=None):
    """Optimized sunny destinations using unified calculator."""
    destinations = get_top_destinations_optimized(
        target_date, start_hour, end_hour, max_distance, start_coords
    )
    
    # Sort by sunny score and return top 30
    destinations.sort(key=lambda x: x['sunny_score'], reverse=True)
    return destinations[:30]

def get_top_comfortable_destinations_optimized(weather_data, target_date, start_hour=9, end_hour=17,
                                             max_distance=None, start_coords=None):
    """Optimized comfortable destinations using unified calculator."""
    destinations = get_top_destinations_optimized(
        target_date, start_hour, end_hour, max_distance, start_coords
    )
    
    # Sort by comfort score and return top 30
    destinations.sort(key=lambda x: x['comfort_score'], reverse=True)
    return destinations[:30]

# Flask Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/location-suggest')
def location_suggest():
    """Convert user's location input to coordinates"""
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
        
        # Get destinations using optimized unified calculation
        weather_data = get_weather_data()
        
        sunny_destinations = get_top_sunny_destinations_optimized(
            weather_data=weather_data,
            target_date=travel_date.date(),
            start_hour=start_hour,
            end_hour=end_hour,
            max_distance=max_distance,
            start_coords=start_coords
        )
        
        comfortable_destinations = get_top_comfortable_destinations_optimized(
            weather_data=weather_data,
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
def api_get_weather_data():
    """Return the current weather data"""
    return jsonify(get_weather_data())

@app.route('/hourly-weather/<int:location_index>/<date>')
def get_hourly_weather(location_index, date):
    """Get hourly weather data for a specific location and date"""
    try:
        # Validate location index
        validation_error = validate_location_index(location_index)
        if validation_error:
            return validation_error
        
        # Parse and validate date
        target_date, date_error = parse_and_validate_date(date)
        if date_error:
            return date_error
        
        weather_data = get_weather_data()
        location_data = weather_data['weather_data'][location_index - 1]
        
        # Find the forecast for the specified date
        forecast = find_forecast_for_date(location_data, target_date)
        if forecast:
            return jsonify({
                'location': location_data['location'],
                'date': forecast['date'],
                'day_summary': forecast['day_summary'],
                'astro': forecast['astro'],
                'hourly': forecast['hourly']
            })
        
        return jsonify({"error": "Weather data not found for the specified date"}), 404
        
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
        time_range_error = validate_time_range(start_hour, end_hour)
        if time_range_error:
            return time_range_error
        
        # Validate location index
        validation_error = validate_location_index(location_index)
        if validation_error:
            return validation_error
        
        # Parse and validate date
        target_date, date_error = parse_and_validate_date(date)
        if date_error:
            return date_error
        
        weather_data = get_weather_data()
        location_data = weather_data['weather_data'][location_index - 1]
        
        # Find the forecast for the specified date
        forecast = find_forecast_for_date(location_data, target_date)
        if forecast:
            # Use optimized unified calculator
            scores_data = weather_calculator.calculate_both_scores(
                location_data, target_date, start_hour, end_hour
            )
            
            if scores_data:
                sunny_data = scores_data['sunny_data']
                comfort_data = scores_data['comfort_data']
                
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
def api_get_grid_boundaries():
    """Return the grid boundaries data"""
    return jsonify(get_grid_boundaries())

@app.route('/cells-in-radius')
def get_cells_in_radius():
    """Get grid cells within a specified radius from a center point"""
    try:
        # Get query parameters
        center_lat = float(request.args.get('lat'))
        center_lon = float(request.args.get('lon'))
        radius_miles = float(request.args.get('radius', 200))
        
        # Get cells within radius
        cells_in_radius = get_cells_within_radius(center_lat, center_lon, radius_miles)
        
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
        cells_in_radius = get_cells_within_radius(center_lat, center_lon, radius_miles)
        
        # Optimized processing using spatial index and unified calculator
        print(f"Processing {len(cells_in_radius)} cells with optimized algorithms...")
        start_time = time.time()
        
        cells_with_scores = []
        for cell in cells_in_radius:
            cell_center = cell.get('center', {})
            cell_lat = cell_center.get('latitude')
            cell_lon = cell_center.get('longitude')
            
            if cell_lat is None or cell_lon is None:
                continue
            
            # Find the closest weather location using optimized spatial index
            closest_location_data, distance = spatial_index.find_closest_location(cell_lat, cell_lon)
            
            if closest_location_data and distance <= 50:  # Within 50 miles
                # Calculate scores using unified calculator
                scores_data = weather_calculator.calculate_both_scores(
                    closest_location_data, target_date_obj, start_hour, end_hour
                )
                
                if scores_data:
                    if index_type == 'sunny':
                        score = scores_data['sunny_data']['sunny_score']
                        level = scores_data['sunny_data']['sunny_level']
                    else:  # comfort
                        score = scores_data['comfort_data']['comfort_score'] 
                        level = scores_data['comfort_data']['comfort_level']
                    
                    cell_with_score = cell.copy()
                    cell_with_score['weather_score'] = {
                        'score': round(score, 2),
                        'level': level,
                        'index_type': index_type,
                        'closest_location': closest_location_data['location']['name'],
                        'distance_to_station': round(distance, 1)
                    }
                    cells_with_scores.append(cell_with_score)
            else:
                # No nearby weather data
                cell_with_score = cell.copy()
                cell_with_score['weather_score'] = {
                    'score': 0,
                    'level': 'No Data',
                    'index_type': index_type,
                    'closest_location': 'Unknown',
                    'distance_to_station': None
                }
                cells_with_scores.append(cell_with_score)
        
        total_time = time.time() - start_time
        print(f"Optimized processing completed in {total_time:.2f}s for {len(cells_with_scores)} cells")
        
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
    """Return current projection calculation progress"""
    return jsonify({
        'status': 'ready',
        'spatial_index_stats': spatial_index.get_statistics(),
        'cache_stats': {
            'weather_calculator_cache': len(weather_calculator._hourly_cache),
            'distance_cache_size': len(distance_cache.cache)
        }
    })

@app.route('/clear-cache')
def clear_cache():
    """Clear performance caches (useful for development)"""
    # Clear optimized caches
    distance_cache.clear_cache()
    weather_calculator._hourly_cache.clear()
    
    # Clear lazy loading caches
    load_weather_data.cache_clear()
    load_grid_boundaries.cache_clear()
    
    return jsonify({'status': 'Optimized caches cleared successfully'})

if __name__ == '__main__':
    app.run(debug=True)