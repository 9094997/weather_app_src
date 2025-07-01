import pandas as pd
from datetime import datetime


## Please check the comfor_index  file first for an explanation of the formular.

def normalize_cloud_coverage(value):
    if value <= 10:
        return 10.0
    elif value <= 24:
        return 8 + (10 - 8) * (24 - value) / (24 - 10)
    elif value <= 49:
        return 5 + (8 - 5) * (49 - value) / (49 - 25)
    elif value <= 90:
        return 2 + (5 - 2) * (90 - value) / (90 - 50)
    else:
        return max(0, 0 + (2 - 0) * (100 - value) / (100 - 90))

def normalize_uv_index(value):
    if value <= 2:
        return value * 2  # up to 4
    elif value <= 5:
        return 4 + (8 - 4) * (value - 2) / (5 - 2)
    elif value <= 7:
        return 8 + (10 - 8) * (value - 5) / (7 - 5)
    elif value <= 10:
        return 10.0
    else:
        return 10.0

def normalize_visibility(value):
    if value > 30000:
        return 10.0
    elif value > 10000:
        return 9 + (10 - 9) * (value - 10000) / (30000 - 10000)
    elif value > 4000:
        return 3 + (8 - 3) * (value - 4001) / (10000 - 4001)
    elif value > 1000:
        return 1 + (2 - 1) * (value - 1001) / (4000 - 1001)
    else:
        return 0.0

def normalize_rain(value):
      ## the gap between 8 and 9 represent the unwilliness to have rain
    if value == 0.0:
        return 10.0
    elif value <= 0.9:
        return 9.0
    elif value <= 10:
        return max(5, 8 - (value - 1) * (3/9))  # 8 to 5
    elif value <= 30:
        return max(1, 5 - (value - 11) * (4/19))  # 5 to 1
    else:
        return 0.0

def normalize_snow(present):
      ## we need to revisit this logic here, in some rare case what if someone would like a bit of snow? This can be like a easter egg function for the broswer mode. 
    return 10.0 if not present else 0.0

def classify_sunny_level(score):
    if score >= 9:
        return 'Very Sunny'
    elif score >= 7:
        return 'Sunny'
    elif score >= 5:
        return 'Partly Sunny'
    elif score >= 3:
        return 'Mostly Cloudy'
    else:
        return 'Overcast'

def calculate_sunny_score(row):
    cloud = normalize_cloud_coverage(row['cloud_coverage'])
    uv = normalize_uv_index(row['uv_index'])
    vis = normalize_visibility(row['visibility_m'])
    rain = normalize_rain(row['rain_mm'])
    snow = normalize_snow(row['snow_present'])

    final_score = round((cloud + uv + vis + rain + snow) / 5, 2)
    level = classify_sunny_level(final_score)

    return pd.Series({
        'Cloud_Score': round(cloud, 2),
        'UV_Score': round(uv, 2),
        'Visibility_Score': round(vis, 2),
        'Rain_Score': round(rain, 2),
        'Snow_Score': round(snow, 2),
        'Sunny_Score': final_score,
        'Sunny_Level': level
    })

def calculate_destination_sunny_score(location_data, target_date, start_hour=9, end_hour=17):
    """
    Calculate sunny score for a destination on a specific date and time range.
    
    Args:
        location_data: Dictionary containing location and forecast data
        target_date: Target date as datetime.date object
        start_hour: Start hour for time range (default: 9)
        end_hour: End hour for time range (default: 17)
    
    Returns:
        Dictionary with sunny score and breakdown, or None if no data available
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
            
            avg_cloud = total_cloud / len(filtered_hours)
            avg_uv = total_uv / len(filtered_hours)
            avg_visibility = total_visibility / len(filtered_hours)
            avg_rain = total_rain / len(filtered_hours)
            snow_present = total_snow > 0
            
            # Create a row for the sunny score calculation
            row = {
                'cloud_coverage': avg_cloud,
                'uv_index': avg_uv,
                'visibility_m': avg_visibility,
                'rain_mm': avg_rain,
                'snow_present': snow_present
            }
            
            # Calculate sunny score
            scores = calculate_sunny_score(row)
            
            return {
                'sunny_score': scores['Sunny_Score'],
                'sunny_level': scores['Sunny_Level'],
                'cloud_score': scores['Cloud_Score'],
                'uv_score': scores['UV_Score'],
                'visibility_score': scores['Visibility_Score'],
                'rain_score': scores['Rain_Score'],
                'snow_score': scores['Snow_Score'],
                'time_range': f"{start_hour:02d}:00-{end_hour:02d}:00",
                'hourly_data': filtered_hours
            }
    
    return None

def get_top_sunny_destinations(weather_data, target_date, start_hour=9, end_hour=17, max_distance=None, start_coords=None):
    """
    Get top 30 destinations with highest sunny scores.
    
    Args:
        weather_data: Weather data dictionary
        target_date: Target date as datetime.date object
        start_hour: Start hour for time range
        end_hour: End hour for time range
        max_distance: Maximum distance in miles (optional)
        start_coords: Starting coordinates as (lat, lon) tuple (optional)
    
    Returns:
        List of top 30 destinations sorted by sunny score
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
        
        # Calculate sunny score
        sunny_data = calculate_destination_sunny_score(location_data, target_date, start_hour, end_hour)
        
        if sunny_data:
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
                'sunny_score': sunny_data['sunny_score'],
                'sunny_level': sunny_data['sunny_level'],
                'cloud_score': sunny_data['cloud_score'],
                'uv_score': sunny_data['uv_score'],
                'visibility_score': sunny_data['visibility_score'],
                'rain_score': sunny_data['rain_score'],
                'snow_score': sunny_data['snow_score'],
                'time_range': sunny_data['time_range'],
                'hourly_data': sunny_data['hourly_data']
            })
    
    # Sort by sunny score (highest first) and return top 30
    destinations.sort(key=lambda x: x['sunny_score'], reverse=True)
    return destinations[:30]

# # Example batch
# data = [
#     {'location': 'Loc1', 'cloud_coverage': 12, 'uv_index': 6, 'visibility_m': 25000, 'rain_mm': 0.0, 'snow_present': False},
#     {'location': 'Loc2', 'cloud_coverage': 15, 'uv_index': 7, 'visibility_m': 30000, 'rain_mm': 0.0, 'snow_present': False},
#     {'location': 'Loc3', 'cloud_coverage': 8,  'uv_index': 5, 'visibility_m': 15000, 'rain_mm': 0.2, 'snow_present': False},
#     {'location': 'Loc4', 'cloud_coverage': 5,  'uv_index': 8, 'visibility_m': 45000, 'rain_mm': 0.0, 'snow_present': False},
# ]

# df = pd.DataFrame(data)
# results = df.apply(calculate_sunny_score, axis=1)
# df_final = pd.concat([df, results], axis=1)

# print(df_final[['location', 'Sunny_Score', 'Sunny_Level', 'Cloud_Score', 'UV_Score', 'Visibility_Score', 'Rain_Score', 'Snow_Score']])
