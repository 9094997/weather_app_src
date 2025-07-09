# Weather Data Date Updater

This script allows you to update the dates in your `weather_data.json` file to make the earliest date the current date, and adjust all subsequent dates accordingly. This is useful for reusing weather data without making new API calls.

## Files

- `update_weather_dates.py` - Main script to update dates in weather_data.json
- `test_date_update.py` - Test script to verify the functionality works correctly

## How it works

The script:

1. **Loads** the current `weather_data.json` file
2. **Finds** the earliest date in all weather forecasts
3. **Calculates** the difference between the current date and the earliest date
4. **Updates** all dates in the file by adding this difference
5. **Updates** the `generated_at` timestamp to the current time
6. **Creates** a backup of the original file before making changes
7. **Saves** the updated data back to the file

## Usage

### Basic Usage

```bash
cd weather_app_src/script/weather
python update_weather_dates.py
```

### Example Output

```
Weather Data Date Updater
========================================
Processing file: /path/to/weather_data.json

Loading weather data...
Updating dates...
Earliest date in data: 2025-07-04
Current date: 2024-12-19
Date offset: -198 days
Created backup: /path/to/weather_data.json.backup
Updated 150 forecast entries
Updated generated_at timestamp
Successfully updated /path/to/weather_data.json

Date update completed successfully!
The weather data now starts from today's date.
```

## What gets updated

The script updates:

1. **Main forecast dates** - The `date` field in each forecast entry
2. **Hourly data times** - The `time` field in hourly weather data (format: "YYYY-MM-DD HH:MM")
3. **Generated timestamp** - The `generated_at` field in the root of the JSON

## Safety Features

- **Automatic backup**: Creates a `.backup` file before making any changes
- **Validation**: Checks for valid JSON and file existence
- **Confirmation**: Asks for confirmation if dates would be moved to the past
- **Error handling**: Graceful error handling with informative messages

## Testing

You can test the functionality without affecting your real data:

```bash
python test_date_update.py
```

This will run a test with sample data to verify the date update logic works correctly.

## Example: Before and After

### Before (Original Data)
```json
{
  "weather_data": [
    {
      "forecast": [
        {
          "date": "2025-07-04",
          "hourly": [
            {
              "time": "2025-07-04 12:00",
              "temp_c": 18
            }
          ]
        },
        {
          "date": "2025-07-05",
          "hourly": [
            {
              "time": "2025-07-05 12:00",
              "temp_c": 20
            }
          ]
        }
      ]
    }
  ],
  "generated_at": "2025-01-01T00:00:00"
}
```

### After (Updated Data - if run on 2024-12-19)
```json
{
  "weather_data": [
    {
      "forecast": [
        {
          "date": "2024-12-19",
          "hourly": [
            {
              "time": "2024-12-19 12:00",
              "temp_c": 18
            }
          ]
        },
        {
          "date": "2024-12-20",
          "hourly": [
            {
              "time": "2024-12-20 12:00",
              "temp_c": 20
            }
          ]
        }
      ]
    }
  ],
  "generated_at": "2024-12-19T15:30:45.123456"
}
```

## Notes

- The script preserves all weather data (temperatures, conditions, etc.) - only dates are updated
- The relative timing between dates is maintained (e.g., if data was for 3 consecutive days, it will still be 3 consecutive days after updating)
- The script is designed to work with the specific structure of your weather data JSON file
- Always test with the test script first if you're unsure about the functionality

## Troubleshooting

**Error: "File not found"**
- Make sure you're running the script from the correct directory
- Ensure `weather_data.json` exists in the same folder as the script

**Error: "Invalid JSON"**
- Check that your `weather_data.json` file is valid JSON
- Try opening it in a text editor to look for syntax errors

**Warning about dates in the past**
- This happens if the current date is before the earliest date in your data
- The script will ask for confirmation before proceeding
- You can safely proceed if you want to move the dates to the past 