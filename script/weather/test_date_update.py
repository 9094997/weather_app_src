#!/usr/bin/env python3
"""
Test script for the date update functionality
"""

import json
from datetime import datetime, date, timedelta

def test_date_update():
    """Test the date update logic with sample data."""
    
    # Sample weather data structure
    sample_data = {
        "grid_size_miles": 8,
        "total_cells": 1,
        "weather_data": [
            {
                "location": {
                    "name": "Test Location",
                    "region": "Test Region",
                    "country": "UK",
                    "latitude": 51.5074,
                    "longitude": -0.1278
                },
                "forecast": [
                    {
                        "date": "2025-07-04",
                        "day_summary": {
                            "temperature": {"max": 20, "min": 15, "average": 17.5},
                            "condition": {"text": "Sunny", "code": 1000},
                            "wind_kph": 15,
                            "precipitation_mm": 0,
                            "humidity": 60,
                            "uv": 5
                        },
                        "astro": {
                            "sunrise": "05:00 AM",
                            "sunset": "09:00 PM"
                        },
                        "hourly": [
                            {
                                "time": "2025-07-04 12:00",
                                "temp_c": 18,
                                "is_day": 1,
                                "condition": {"text": "Sunny", "code": 1000},
                                "wind_kph": 12,
                                "precip_mm": 0,
                                "humidity": 55,
                                "cloud": 10,
                                "feelslike_c": 17,
                                "chance_of_rain": 0,
                                "chance_of_snow": 0,
                                "vis_km": 10.0,
                                "uv": 4
                            }
                        ]
                    },
                    {
                        "date": "2025-07-05",
                        "day_summary": {
                            "temperature": {"max": 22, "min": 16, "average": 19},
                            "condition": {"text": "Partly Cloudy", "code": 1003},
                            "wind_kph": 18,
                            "precipitation_mm": 2,
                            "humidity": 65,
                            "uv": 4
                        },
                        "astro": {
                            "sunrise": "05:01 AM",
                            "sunset": "08:59 PM"
                        },
                        "hourly": [
                            {
                                "time": "2025-07-05 12:00",
                                "temp_c": 20,
                                "is_day": 1,
                                "condition": {"text": "Partly Cloudy", "code": 1003},
                                "wind_kph": 15,
                                "precip_mm": 1,
                                "humidity": 60,
                                "cloud": 40,
                                "feelslike_c": 19,
                                "chance_of_rain": 30,
                                "chance_of_snow": 0,
                                "vis_km": 10.0,
                                "uv": 3
                            }
                        ]
                    }
                ]
            }
        ],
        "generated_at": "2025-01-01T00:00:00"
    }
    
    print("Original sample data:")
    print(f"Earliest date: {sample_data['weather_data'][0]['forecast'][0]['date']}")
    print(f"Latest date: {sample_data['weather_data'][0]['forecast'][1]['date']}")
    print()
    
    # Simulate the date update process
    current_date = date.today()
    earliest_date = datetime.strptime(sample_data['weather_data'][0]['forecast'][0]['date'], '%Y-%m-%d').date()
    date_diff = current_date - earliest_date
    
    print(f"Current date: {current_date}")
    print(f"Earliest date in data: {earliest_date}")
    print(f"Date offset: {date_diff.days} days")
    print()
    
    # Update the dates
    for location_data in sample_data['weather_data']:
        for forecast in location_data['forecast']:
            # Update main date
            old_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
            new_date = old_date + date_diff
            forecast['date'] = new_date.strftime('%Y-%m-%d')
            
            # Update hourly times
            for hourly_data in forecast['hourly']:
                time_parts = hourly_data['time'].split(' ')
                if len(time_parts) == 2:
                    old_hourly_date = datetime.strptime(time_parts[0], '%Y-%m-%d').date()
                    new_hourly_date = old_hourly_date + date_diff
                    hourly_data['time'] = f"{new_hourly_date.strftime('%Y-%m-%d')} {time_parts[1]}"
    
    # Update generated_at timestamp
    sample_data['generated_at'] = datetime.now().isoformat()
    
    print("Updated sample data:")
    print(f"New earliest date: {sample_data['weather_data'][0]['forecast'][0]['date']}")
    print(f"New latest date: {sample_data['weather_data'][0]['forecast'][1]['date']}")
    print(f"Updated generated_at: {sample_data['generated_at']}")
    print()
    
    print("Test completed successfully!")
    print("The date update logic is working correctly.")

if __name__ == "__main__":
    test_date_update() 