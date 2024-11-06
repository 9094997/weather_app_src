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
    "Paris": {
        "lat": 48.8566, 
        "lon": 2.3522,
        "weather": {"Nov": {"avg_temp": 10, "conditions": ["Rainy", "Cloudy"]},
                   "Dec": {"avg_temp": 6, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]}},
        "description": "City of Light, home to iconic landmarks like the Eiffel Tower and Louvre"
    },
    "Nice": {
        "lat": 43.7102, 
        "lon": 7.2620,
        "weather": {"Nov": {"avg_temp": 15, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 12, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 11, "conditions": ["Sunny", "Rainy"]}},
        "description": "Beautiful coastal city with Mediterranean beaches and vibrant culture"
    },
    "Lyon": {
        "lat": 45.7578, 
        "lon": 4.8320,
        "weather": {"Nov": {"avg_temp": 11, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 7, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 6, "conditions": ["Cloudy", "Rainy"]}},
        "description": "Gastronomic capital of France with historic Renaissance architecture"
    },
    "Marseille": {
        "lat": 43.2965, 
        "lon": 5.3698,
        "weather": {"Nov": {"avg_temp": 14, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 11, "conditions": ["Sunny", "Rainy"]},
                   "Jan": {"avg_temp": 10, "conditions": ["Sunny", "Rainy"]}},
        "description": "Historic port city with vibrant culture and beautiful calanques"
    },
    "Bordeaux": {
        "lat": 44.8378, 
        "lon": -0.5792,
        "weather": {"Nov": {"avg_temp": 12, "conditions": ["Rainy", "Cloudy"]},
                   "Dec": {"avg_temp": 9, "conditions": ["Rainy", "Cloudy"]},
                   "Jan": {"avg_temp": 8, "conditions": ["Rainy", "Cloudy"]}},
        "description": "World-famous wine region with elegant 18th-century architecture"
    },
    "Toulouse": {
        "lat": 43.6047, 
        "lon": 1.4442,
        "weather": {"Nov": {"avg_temp": 13, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 9, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 8, "conditions": ["Cloudy", "Rainy"]}},
        "description": "The 'Pink City' known for aerospace industry and historic center"
    },
    "Strasbourg": {
        "lat": 48.5734, 
        "lon": 7.7521,
        "weather": {"Nov": {"avg_temp": 9, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 4, "conditions": ["Cloudy", "Rainy"]}},
        "description": "European capital with German-French cultural blend and Christmas markets"
    },
    "Montpellier": {
        "lat": 43.6108, 
        "lon": 3.8767,
        "weather": {"Nov": {"avg_temp": 14, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 11, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 10, "conditions": ["Sunny", "Rainy"]}},
        "description": "Dynamic university city with Mediterranean lifestyle"
    },
    "Nantes": {
        "lat": 47.2184, 
        "lon": -1.5536,
        "weather": {"Nov": {"avg_temp": 11, "conditions": ["Rainy", "Cloudy"]},
                   "Dec": {"avg_temp": 8, "conditions": ["Rainy", "Cloudy"]},
                   "Jan": {"avg_temp": 7, "conditions": ["Rainy", "Cloudy"]}},
        "description": "Creative city known for mechanical animals and castle"
    },
    "Lille": {
        "lat": 50.6292, 
        "lon": 3.0573,
        "weather": {"Nov": {"avg_temp": 9, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 6, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]}},
        "description": "Northern cultural hub with Flemish influence and grand plaza"
    },
    "Rennes": {
        "lat": 48.1173, 
        "lon": -1.6778,
        "weather": {"Nov": {"avg_temp": 11, "conditions": ["Rainy", "Cloudy"]},
                   "Dec": {"avg_temp": 8, "conditions": ["Rainy", "Cloudy"]},
                   "Jan": {"avg_temp": 7, "conditions": ["Rainy", "Cloudy"]}},
        "description": "Breton capital with medieval heritage and student life"
    },
    "Reims": {
        "lat": 49.2583, 
        "lon": 4.0317,
        "weather": {"Nov": {"avg_temp": 9, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 6, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]}},
        "description": "Champagne capital with stunning Gothic cathedral"
    },
    "Saint-Tropez": {
        "lat": 43.2727, 
        "lon": 6.6406,
        "weather": {"Nov": {"avg_temp": 15, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 12, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 11, "conditions": ["Sunny", "Cloudy"]}},
        "description": "Glamorous coastal resort town with beautiful beaches"
    },
    "Annecy": {
        "lat": 45.8992, 
        "lon": 6.1294,
        "weather": {"Nov": {"avg_temp": 10, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 4, "conditions": ["Cloudy", "Rainy"]}},
        "description": "Alpine town with pristine lake and medieval canals"
    },
    "Biarritz": {
        "lat": 43.4832, 
        "lon": -1.5586,
        "weather": {"Nov": {"avg_temp": 13, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 10, "conditions": ["Rainy", "Cloudy"]},
                   "Jan": {"avg_temp": 9, "conditions": ["Rainy", "Cloudy"]}},
        "description": "Elegant seaside town famous for surfing and beaches"
    },
    "Avignon": {
        "lat": 43.9493, 
        "lon": 4.8055,
        "weather": {"Nov": {"avg_temp": 13, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 9, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 8, "conditions": ["Sunny", "Cloudy"]}},
        "description": "Historic papal city with famous bridge and festival"
    },
    "Cannes": {
        "lat": 43.5528, 
        "lon": 7.0174,
        "weather": {"Nov": {"avg_temp": 15, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 12, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 11, "conditions": ["Sunny", "Cloudy"]}},
        "description": "Glamorous film festival city with luxury shopping"
    },
    "Dijon": {
        "lat": 47.3220, 
        "lon": 5.0415,
        "weather": {"Nov": {"avg_temp": 10, "conditions": ["Cloudy", "Rainy"]},
                   "Dec": {"avg_temp": 6, "conditions": ["Cloudy", "Rainy"]},
                   "Jan": {"avg_temp": 5, "conditions": ["Cloudy", "Rainy"]}},
        "description": "Historic Burgundy capital known for mustard and wine"
    },
    "La Rochelle": {
        "lat": 46.1591, 
        "lon": -1.1520,
        "weather": {"Nov": {"avg_temp": 12, "conditions": ["Rainy", "Cloudy"]},
                   "Dec": {"avg_temp": 9, "conditions": ["Rainy", "Cloudy"]},
                   "Jan": {"avg_temp": 8, "conditions": ["Rainy", "Cloudy"]}},
        "description": "Historic port city with famous aquarium and towers"
    },
    "Antibes": {
        "lat": 43.5813, 
        "lon": 7.1250,
        "weather": {"Nov": {"avg_temp": 15, "conditions": ["Sunny", "Cloudy"]},
                   "Dec": {"avg_temp": 12, "conditions": ["Sunny", "Cloudy"]},
                   "Jan": {"avg_temp": 11, "conditions": ["Sunny", "Cloudy"]}},
        "description": "Charming coastal town between Nice and Cannes with old town and port"
    }
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