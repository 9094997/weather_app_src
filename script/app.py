from flask import Flask, render_template, request, jsonify
from datetime import datetime
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time

app = Flask(__name__)

# Initialize geocoder with a custom user agent
geolocator = Nominatim(user_agent="travel_app")

# Sample destination database
DESTINATIONS = {
    "Paris": {"lat": 48.8566, "lon": 2.3522, 
              "weather": {"Nov": {"avg_temp": 10, "conditions": ["Rainy", "Cloudy"]}},
              "description": "City of Light"},
    "Nice": {"lat": 43.7102, "lon": 7.2620, 
             "weather": {"Nov": {"avg_temp": 15, "conditions": ["Sunny", "Cloudy"]}},
             "description": "Beautiful coastal city"},
    "Bordeaux": {"lat": 44.8378, "lon": -0.5792, 
                 "weather": {"Nov": {"avg_temp": 12, "conditions": ["Rainy", "Cloudy"]}},
                 "description": "Wine country capital"},
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/location-suggest')
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
            country_codes=['fr']  # Limit to France
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
        
        # Find matching destinations
        matches = []
        for city, info in DESTINATIONS.items():
            dest_coords = (info['lat'], info['lon'])
            distance = geodesic(start_coords, dest_coords).miles
            
            if (distance <= max_distance and
                desired_weather in info['weather'][travel_date.strftime('%b')]['conditions']):
                matches.append({
                    'city': city,
                    'distance': round(distance, 1),
                    'description': info['description'],
                    'coordinates': {
                        'lat': info['lat'],
                        'lon': info['lon']
                    }
                })
        
        return jsonify(matches)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)