from flask import Flask, render_template, request, jsonify
from datetime import datetime
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

app = Flask(__name__)

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

@app.route('/geocode')
def geocode():
    location = request.args.get('location')
    if not location:
        return jsonify({"error": "No location provided"}), 400
    
    geolocator = Nominatim(user_agent="travel_app")
    try:
        location_data = geolocator.geocode(location)
        if location_data:
            return jsonify({
                "coordinates": {
                    "lat": location_data.latitude,
                    "lon": location_data.longitude
                }
            })
        return jsonify({"error": "Location not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    
    # Get user inputs
    start_location = data['from']
    desired_weather = data['weather']
    travel_date = datetime.strptime(data['date'], '%Y-%m-%d')
    max_distance = float(data['distance'])
    
    # Initialize geocoder
    geolocator = Nominatim(user_agent="travel_app")
    
    try:
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
            
            # Check if destination matches criteria
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