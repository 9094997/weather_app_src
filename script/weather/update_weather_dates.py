#!/usr/bin/env python3
"""
Weather Data Date Updater

This script updates the dates in weather_data.json to make the earliest date
the current date, and adjusts all subsequent dates accordingly. This allows
the weather data to be reused without making new API calls.

Usage:
    python update_weather_dates.py

The script will:
1. Load the current weather_data.json file
2. Find the earliest date in the data
3. Calculate the difference between the earliest date and current date
4. Update all dates in the file by adding this difference
5. Save the updated data back to the file
"""

import json
import os
from datetime import datetime, date, timedelta
import sys
from typing import Dict, Any, List

def load_weather_data(file_path: str) -> Dict[str, Any]:
    """Load weather data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)

def save_weather_data(data: Dict[str, Any], file_path: str) -> None:
    """Save weather data to JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated {file_path}")
    except Exception as e:
        print(f"Error saving data: {e}")
        sys.exit(1)

def find_earliest_date(weather_data: Dict[str, Any]) -> date:
    """Find the earliest date in the weather data."""
    earliest_date = None
    
    for location_data in weather_data.get('weather_data', []):
        for forecast in location_data.get('forecast', []):
            forecast_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
            if earliest_date is None or forecast_date < earliest_date:
                earliest_date = forecast_date
    
    return earliest_date

def update_dates_in_forecast(forecast: Dict[str, Any], date_offset: timedelta) -> None:
    """Update dates in a forecast entry."""
    # Update the main date
    old_date = datetime.strptime(forecast['date'], '%Y-%m-%d').date()
    new_date = old_date + date_offset
    forecast['date'] = new_date.strftime('%Y-%m-%d')
    
    # Update hourly data times
    for hourly_data in forecast.get('hourly', []):
        if 'time' in hourly_data:
            # Parse the time string (format: "2025-07-04 00:00")
            time_parts = hourly_data['time'].split(' ')
            if len(time_parts) == 2:
                old_hourly_date = datetime.strptime(time_parts[0], '%Y-%m-%d').date()
                new_hourly_date = old_hourly_date + date_offset
                hourly_data['time'] = f"{new_hourly_date.strftime('%Y-%m-%d')} {time_parts[1]}"

def update_weather_dates(weather_data: Dict[str, Any], current_date: date) -> None:
    """Update all dates in the weather data."""
    earliest_date = find_earliest_date(weather_data)
    
    if earliest_date is None:
        print("Error: No dates found in weather data")
        return
    
    print(f"Earliest date in data: {earliest_date}")
    print(f"Current date: {current_date}")
    
    # Calculate the difference between current date and earliest date
    date_diff = current_date - earliest_date
    print(f"Date offset: {date_diff.days} days")
    
    if date_diff.days < 0:
        print("Warning: Current date is before the earliest date in the data")
        print("This will make the dates in the past. Continue? (y/N): ", end="")
        response = input().strip().lower()
        if response != 'y':
            print("Operation cancelled")
            return
    
    # Update dates in all locations
    updated_count = 0
    for location_data in weather_data.get('weather_data', []):
        for forecast in location_data.get('forecast', []):
            update_dates_in_forecast(forecast, date_diff)
            updated_count += 1
    
    print(f"Updated {updated_count} forecast entries")
    
    # Update the generated_at timestamp
    weather_data['generated_at'] = datetime.now().isoformat()
    print("Updated generated_at timestamp")

def main():
    """Main function to update weather dates."""
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    weather_file = os.path.join(script_dir, 'weather_data.json')
    
    print("Weather Data Date Updater")
    print("=" * 40)
    print(f"Processing file: {weather_file}")
    print()
    
    # Load weather data
    print("Loading weather data...")
    weather_data = load_weather_data(weather_file)
    
    # Get current date
    current_date = date.today()
    
    # Update dates
    print("Updating dates...")
    update_weather_dates(weather_data, current_date)
    
    # Save updated data
    print("Saving updated data...")
    save_weather_data(weather_data, weather_file)
    
    print()
    print("Date update completed successfully!")
    print("The weather data now starts from today's date.")

if __name__ == "__main__":
    main() 