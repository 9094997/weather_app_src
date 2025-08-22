import pandas as pd
from datetime import datetime

# -------------------------------
# Normalization functions
# -------------------------------

## here is an instruction of how to read the fomula below:
## for example for the cloud coverage index:

    # elif value <= 50:
    #     return 7 + (9 - 7) * (50 - value) / 20
    
# this paragraph represent the calculation of cloud coverage index between 30% to 50%, the full scrip can be found below. 
# 50 represent 50% cloud coverage, 7 is the lowest score for the cloud coverage range between 10% - 30%, (9-7) is the score range for 10%-30%, 9 is the highest.
# (50-value) measure the distance between the given value and the upper limit of this range, and /20 is the range between 10%-30%, it is the normlisation factor.

# The purpose of this formular is to normalised the weather parameters into an comparable system and find the location of the given value in a pre-set score range


def normalize_cloud_comfort(value):
    ##cloud coverage index
    if value <= 10:
        return 7 + (10 - 7) * (10 - value) / 10 ## too much sun and no cloud is not a good thing, there fore we have the range of 7 to 10
    elif value <= 30:
        return 9 + (10 - 9) * (30 - value) / 20
    elif value <= 50:
        return 7 + (9 - 7) * (50 - value) / 20
    elif value <= 80:
        return 4 + (7 - 4) * (80 - value) / 30
    else:
        return max(0, 0 + (4 - 0) * (100 - value) / 20)

def normalize_uv_comfort(value):
    ##uv index in relation to the comfort index
    if value <= 2:
        return 10
    elif value <= 5:
        return 8 + (10 - 8) * (5 - value) / 3
    elif value <= 7:
        return 5 + (7 - 5) * (7 - value) / 2
    elif value <= 10:
        return 3 + (5 - 3) * (10 - value) / 3
    else:
        return max(0, 0 + (3 - 0) * (12 - min(value,12)) / 2)

def normalize_visibility_comfort(value):
    ## the more the better
    if value > 30000:
        return 10
    elif value > 10000:
        return 8 + (10 - 8) * (value - 10000) / 20000
    elif value > 4000:
        return 5 + (8 - 5) * (value - 4001) / (10000 - 4001)
    elif value > 1000:
        return 2 + (5 - 2) * (value - 1001) / (4000 - 1001)
    else:
        return 0.0

def normalize_rain_comfort(value):
    ## no rain is the best, light rain is accetable
    if value == 0.0:
        return 10.0
    elif value <= 0.9:
        return 8 + (9 - 8) * (0.9 - value) / 0.9
    elif value <= 10:
        return 5 + (8 - 5) * (10 - value) / 9
    elif value <= 30:
        return 2 + (5 - 2) * (30 - value) / 19
    else:
        return max(0, 0 + (2 - 0) * (70 - min(value,70)) / 40)

def normalize_snow_comfort(present):
    ## snow is not properly considerd at the moment, we leave this function to the fucture.
    return 10.0 if not present else 1.0

def normalize_feels_like_temp(value):
    ## this is the most important factor for the comfort index
    if 20 <= value <= 26:
        return 10.0
    elif 15 <= value < 20:
        return 7 + (10 - 7) * (20 - value) / 5
    elif 26 < value <= 30:
        return 7 + (10 - 7) * (30 - value) / 4
    elif 10 <= value < 15:
        return 4 + (7 - 3) * (15 - value) / 5
    elif 30 < value <= 35:
        return 4 + (7 - 4) * (35 - value) / 5
    else:
        if value < 10:
            return max(0, 0 + (3 - 0) * (10 - value) / 10)
        else:
            return max(0, 0 + (4 - 0) * (value - 35) / 15)

def normalize_humidity_comfort(value):
    if 40 <= value <= 60:
        return 10.0
    elif 30 <= value < 40:
        return 7 + (9 - 7) * (40 - value) / 10
    elif 60 < value <= 70:
        return 7 + (9 - 7) * (70 - value) / 10
    elif 20 <= value < 30:
        return 4 + (7 - 4) * (30 - value) / 10
    elif 70 < value <= 80:
        return 4 + (7 - 4) * (80 - value) / 10
    else:
        if value < 20:
            return max(0, 0 + (4 - 0) * (20 - value) / 20)
        else:
            return max(0, 0 + (4 - 0) * (100 - min(value,100)) / 20)

# -------------------------------
# Final classification
# -------------------------------

def classify_comfort_level(score):
    if score >= 9:
        return 'Very Comfortable'
    elif score >= 7:
        return 'Comfortable'
    elif score >= 5:
        return 'Moderate'
    elif score >= 3:
        return 'Uncomfortable'
    else:
        return 'Very Uncomfortable'

# -------------------------------
# Main function for one row
# -------------------------------

def calculate_comfort_score(row):
    cloud = normalize_cloud_comfort(row['cloud_coverage'])
    uv = normalize_uv_comfort(row['uv_index'])
    vis = normalize_visibility_comfort(row['visibility_m'])
    rain = normalize_rain_comfort(row['rain_mm'])
    snow = normalize_snow_comfort(row['snow_present'])
    feels = normalize_feels_like_temp(row['feels_like_temp'])
    humidity = normalize_humidity_comfort(row['humidity'])

    final_score = round((cloud + uv + vis + rain + snow + feels + humidity) / 7, 2)
    level = classify_comfort_level(final_score)

    return pd.Series({
        'Cloud_Score': round(cloud, 2),
        'UV_Score': round(uv, 2),
        'Visibility_Score': round(vis, 2),
        'Rain_Score': round(rain, 2),
        'Snow_Score': round(snow, 2),
        'FeelsLikeTemp_Score': round(feels, 2),
        'Humidity_Score': round(humidity, 2),
        'Comfort_Score': final_score,
        'Comfort_Level': level
    })

# -------------------------------
# Example usage
# -------------------------------

# if __name__ == "__main__":
#     data = [
#         {'location': 'Loc1', 'cloud_coverage': 20, 'uv_index': 5, 'visibility_m': 25000, 'rain_mm': 0.0, 'snow_present': False, 'feels_like_temp': 22, 'humidity': 50},
#         {'location': 'Loc2', 'cloud_coverage': 80, 'uv_index': 1, 'visibility_m': 2000, 'rain_mm': 10.0, 'snow_present': True, 'feels_like_temp': -5, 'humidity': 85},
#         {'location': 'Loc3', 'cloud_coverage': 5,  'uv_index': 7, 'visibility_m': 45000, 'rain_mm': 0.5, 'snow_present': False, 'feels_like_temp': 30, 'humidity': 65},
#     ]

#     df = pd.DataFrame(data)
#     results = df.apply(calculate_comfort_score, axis=1)
#     df_final = pd.concat([df, results], axis=1)

    # print(df_final[['location', 'Comfort_Score', 'Comfort_Level',
    #                 'Cloud_Score', 'UV_Score', 'Visibility_Score',
    #                 'Rain_Score', 'Snow_Score', 'FeelsLikeTemp_Score', 'Humidity_Score']])

def calculate_destination_comfort_score(location_data, target_date, start_hour=9, end_hour=17):
    """
    Calculate comfort score for a destination on a specific date and time range.
    
    Args:
        location_data: Dictionary containing location and forecast data
        target_date: Target date as datetime.date object
        start_hour: Start hour for time range (default: 9)
        end_hour: End hour for time range (default: 17)
    
    Returns:
        Dictionary with comfort score and breakdown, or None if no data available
    """
    # Find the forecast for the target date
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    for forecast in location_data['forecast']:
        if forecast['date'] == target_date_str:
            # Filter hourly data for the specified time range
            filtered_hours = []
            for hour_data in forecast['hourly']:
                hour = datetime.strptime(hour_data['time'], '%Y-%m-%d %H:%M').hour
                if start_hour <= hour <= end_hour:
                    filtered_hours.append(hour_data)
            
            if not filtered_hours:
                return None
            
            # Calculate average values for the time range
            total_cloud = sum(h['cloud'] for h in filtered_hours)
            total_uv = sum(h['uv'] for h in filtered_hours)
            total_visibility = sum(h['vis_km'] * 1000 for h in filtered_hours)  # Convert km to meters
            total_rain = sum(h['precip_mm'] for h in filtered_hours)
            total_snow = sum(1 for h in filtered_hours if h.get('will_it_snow', 0) > 0)
            total_feels_like = sum(h['feelslike_c'] for h in filtered_hours)
            total_humidity = sum(h['humidity'] for h in filtered_hours)
            
            avg_cloud = total_cloud / len(filtered_hours)
            avg_uv = total_uv / len(filtered_hours)
            avg_visibility = total_visibility / len(filtered_hours)
            avg_rain = total_rain / len(filtered_hours)
            snow_present = total_snow > 0
            avg_feels_like = total_feels_like / len(filtered_hours)
            avg_humidity = total_humidity / len(filtered_hours)
            
            # Create a row for the comfort score calculation
            row = {
                'cloud_coverage': avg_cloud,
                'uv_index': avg_uv,
                'visibility_m': avg_visibility,
                'rain_mm': avg_rain,
                'snow_present': snow_present,
                'feels_like_temp': avg_feels_like,
                'humidity': avg_humidity
            }
            
            # Calculate comfort score
            scores = calculate_comfort_score(row)
            
            return {
                'comfort_score': scores['Comfort_Score'],
                'comfort_level': scores['Comfort_Level'],
                'cloud_score': scores['Cloud_Score'],
                'uv_score': scores['UV_Score'],
                'visibility_score': scores['Visibility_Score'],
                'rain_score': scores['Rain_Score'],
                'snow_score': scores['Snow_Score'],
                'feels_like_temp_score': scores['FeelsLikeTemp_Score'],
                'humidity_score': scores['Humidity_Score'],
                'time_range': f"{start_hour:02d}:00-{end_hour:02d}:00",
                'hourly_data': filtered_hours
            }
    
    return None

def remove_duplicate_cities(destinations):
    """
    Remove duplicate cities, keeping the one with the highest comfort score.
    Returns a list with unique cities only.
    """
    city_groups = {}
    
    for dest in destinations:
        # Create a unique key for each city (name + region + country)
        city_key = f"{dest['city']}_{dest['region']}_{dest['country']}"
        
        # If this city doesn't exist yet, or if this entry has a better score
        if city_key not in city_groups or dest['comfort_score'] > city_groups[city_key]['comfort_score']:
            city_groups[city_key] = dest
    
    # Return the deduplicated list
    return list(city_groups.values())

def get_top_comfortable_destinations(weather_data, target_date, start_hour=9, end_hour=17, max_distance=None, start_coords=None):
    """
    Get top 30 destinations with highest comfort scores.
    
    Args:
        weather_data: Weather data dictionary
        target_date: Target date as datetime.date object
        start_hour: Start hour for time range
        end_hour: End hour for time range
        max_distance: Maximum distance in miles (optional)
        start_coords: Starting coordinates as (lat, lon) tuple (optional)
    
    Returns:
        List of top 30 destinations sorted by comfort score
    """
    from geopy.distance import geodesic
    
    destinations = []
    
    for index, location_data in enumerate(weather_data.get('weather_data', []), 1):
        location = location_data['location']
        dest_coords = (location['latitude'], location['longitude'])
        
        # Check distance if specified
        if max_distance and start_coords:
            distance = geodesic(start_coords, dest_coords).miles
            if distance > max_distance:
                continue
        else:
            distance = 0
        
        # Calculate comfort score
        comfort_data = calculate_destination_comfort_score(location_data, target_date, start_hour, end_hour)
        
        if comfort_data:
            # Calculate temperature range from hourly data
            feels_like_temps = [h['feelslike_c'] for h in comfort_data['hourly_data']]
            min_temp = min(feels_like_temps)
            max_temp = max(feels_like_temps)
            
            destinations.append({
                'index': index,
                'city': location['name'],
                'region': location['region'],
                'country': location['country'],
                'distance': round(distance, 1) if distance > 0 else None,
                'coordinates': {
                    'lat': location['latitude'],
                    'lon': location['longitude']
                },
                'comfort_score': comfort_data['comfort_score'],
                'comfort_level': comfort_data['comfort_level'],
                'cloud_score': comfort_data['cloud_score'],
                'uv_score': comfort_data['uv_score'],
                'visibility_score': comfort_data['visibility_score'],
                'rain_score': comfort_data['rain_score'],
                'snow_score': comfort_data['snow_score'],
                'feels_like_temp_score': comfort_data['feels_like_temp_score'],
                'humidity_score': comfort_data['humidity_score'],
                'time_range': comfort_data['time_range'],
                'hourly_data': comfort_data['hourly_data'],
                'min_temp': round(min_temp, 1),
                'max_temp': round(max_temp, 1)
            })
    
    # Remove duplicate cities before sorting and limiting to top 30
    unique_destinations = remove_duplicate_cities(destinations)
    
    # Sort by comfort score (highest first) and return top 30
    unique_destinations.sort(key=lambda x: x['comfort_score'], reverse=True)
    return unique_destinations[:30]
