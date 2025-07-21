"""
Unified Weather Score Calculator
Consolidates sunny_score and comfort_index calculations to eliminate duplication.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache

class WeatherScoreCalculator:
    """Unified calculator for both sunny and comfort scores with caching."""
    
    def __init__(self):
        self._hourly_cache = {}
        self._score_cache = {}
    
    @lru_cache(maxsize=1000)
    def _get_hourly_data_for_date_range(self, location_name: str, target_date_str: str, 
                                       start_hour: int, end_hour: int) -> Optional[List[Dict]]:
        """Cache and return filtered hourly data for a location, date, and time range."""
        cache_key = f"{location_name}_{target_date_str}_{start_hour}_{end_hour}"
        
        if cache_key in self._hourly_cache:
            return self._hourly_cache[cache_key]
        
        return None  # Will be populated by the main calculation functions
    
    def calculate_hourly_averages(self, location_data: Dict, target_date: datetime.date, 
                                start_hour: int = 9, end_hour: int = 17) -> Optional[Dict[str, Any]]:
        """
        Calculate average weather values for a time range.
        This replaces duplicate logic in both score modules.
        """
        target_date_str = target_date.strftime('%Y-%m-%d')
        location_name = location_data['location']['name']
        
        # Check cache first
        cache_key = f"avg_{location_name}_{target_date_str}_{start_hour}_{end_hour}"
        if cache_key in self._hourly_cache:
            return self._hourly_cache[cache_key]
        
        # Find the forecast for the target date
        forecast = None
        for f in location_data['forecast']:
            if f['date'] == target_date_str:
                forecast = f
                break
        
        if not forecast:
            return None
        
        # Filter hourly data for the specified time range
        filtered_hours = []
        for hour_data in forecast['hourly']:
            hour = datetime.strptime(hour_data['time'], '%Y-%m-%d %H:%M').hour
            if start_hour <= hour <= end_hour:
                filtered_hours.append(hour_data)
        
        if not filtered_hours:
            return None
        
        # Calculate all averages at once (more efficient)
        num_hours = len(filtered_hours)
        totals = {
            'cloud': sum(h['cloud'] for h in filtered_hours),
            'uv': sum(h['uv'] for h in filtered_hours),
            'visibility': sum(h['vis_km'] * 1000 for h in filtered_hours),  # Convert to meters
            'rain': sum(h['precip_mm'] for h in filtered_hours),
            'snow': sum(1 for h in filtered_hours if h.get('will_it_snow', 0) > 0),
            'feels_like': sum(h['feelslike_c'] for h in filtered_hours),
            'humidity': sum(h['humidity'] for h in filtered_hours)
        }
        
        # Calculate averages
        averages = {
            'cloud_coverage': totals['cloud'] / num_hours,
            'uv_index': totals['uv'] / num_hours,
            'visibility_m': totals['visibility'] / num_hours,
            'rain_mm': totals['rain'] / num_hours,
            'snow_present': totals['snow'] > 0,
            'feels_like_temp': totals['feels_like'] / num_hours,
            'humidity': totals['humidity'] / num_hours
        }
        
        # Cache the result
        result = {
            'averages': averages,
            'hourly_data': filtered_hours,
            'time_range': f"{start_hour:02d}:00-{end_hour:02d}:00"
        }
        self._hourly_cache[cache_key] = result
        return result
    
    @lru_cache(maxsize=500)
    def calculate_sunny_score(self, cloud: float, uv: float, visibility: float, 
                            rain: float, snow_present: bool) -> Tuple[float, str, Dict]:
        """Calculate sunny score with caching."""
        # Sunny normalization functions (optimized)
        cloud_score = self._normalize_cloud_sunny(cloud)
        uv_score = self._normalize_uv_sunny(uv)
        vis_score = self._normalize_visibility(visibility)
        rain_score = self._normalize_rain_sunny(rain)
        snow_score = 10.0 if not snow_present else 0.0
        
        final_score = round((cloud_score + uv_score + vis_score + rain_score + snow_score) / 5, 2)
        level = self._classify_sunny_level(final_score)
        
        breakdown = {
            'cloud_score': round(cloud_score, 2),
            'uv_score': round(uv_score, 2),
            'visibility_score': round(vis_score, 2),
            'rain_score': round(rain_score, 2),
            'snow_score': round(snow_score, 2)
        }
        
        return final_score, level, breakdown
    
    @lru_cache(maxsize=500)
    def calculate_comfort_score(self, cloud: float, uv: float, visibility: float, 
                              rain: float, snow_present: bool, feels_like: float, 
                              humidity: float) -> Tuple[float, str, Dict]:
        """Calculate comfort score with caching."""
        # Comfort normalization functions (optimized)
        cloud_score = self._normalize_cloud_comfort(cloud)
        uv_score = self._normalize_uv_comfort(uv)
        vis_score = self._normalize_visibility(visibility)
        rain_score = self._normalize_rain_comfort(rain)
        snow_score = 10.0 if not snow_present else 1.0
        feels_score = self._normalize_feels_like_temp(feels_like)
        humidity_score = self._normalize_humidity_comfort(humidity)
        
        final_score = round((cloud_score + uv_score + vis_score + rain_score + 
                           snow_score + feels_score + humidity_score) / 7, 2)
        level = self._classify_comfort_level(final_score)
        
        breakdown = {
            'cloud_score': round(cloud_score, 2),
            'uv_score': round(uv_score, 2),
            'visibility_score': round(vis_score, 2),
            'rain_score': round(rain_score, 2),
            'snow_score': round(snow_score, 2),
            'feels_like_temp_score': round(feels_score, 2),
            'humidity_score': round(humidity_score, 2)
        }
        
        return final_score, level, breakdown
    
    def calculate_both_scores(self, location_data: Dict, target_date: datetime.date,
                            start_hour: int = 9, end_hour: int = 17) -> Dict[str, Any]:
        """
        Calculate both sunny and comfort scores efficiently.
        Replaces separate calls to both score modules.
        """
        # Get hourly averages once (shared calculation)
        hourly_data = self.calculate_hourly_averages(location_data, target_date, start_hour, end_hour)
        if not hourly_data:
            return None
        
        avg = hourly_data['averages']
        
        # Calculate both scores using cached functions
        sunny_score, sunny_level, sunny_breakdown = self.calculate_sunny_score(
            avg['cloud_coverage'], avg['uv_index'], avg['visibility_m'], 
            avg['rain_mm'], avg['snow_present']
        )
        
        comfort_score, comfort_level, comfort_breakdown = self.calculate_comfort_score(
            avg['cloud_coverage'], avg['uv_index'], avg['visibility_m'], 
            avg['rain_mm'], avg['snow_present'], avg['feels_like_temp'], avg['humidity']
        )
        
        # Calculate temperature range
        feels_like_temps = [h['feelslike_c'] for h in hourly_data['hourly_data']]
        
        return {
            'sunny_data': {
                'sunny_score': sunny_score,
                'sunny_level': sunny_level,
                **sunny_breakdown,
                'time_range': hourly_data['time_range']
            },
            'comfort_data': {
                'comfort_score': comfort_score,
                'comfort_level': comfort_level,
                **comfort_breakdown,
                'time_range': hourly_data['time_range']
            },
            'temperature_range': {
                'min_temp': round(min(feels_like_temps), 1),
                'max_temp': round(max(feels_like_temps), 1)
            },
            'hourly_summary': len(hourly_data['hourly_data'])  # Count instead of full data
        }
    
    # Normalization functions (consolidated from both modules)
    def _normalize_cloud_sunny(self, value):
        if value <= 10: return 10.0
        elif value <= 24: return 8 + (10 - 8) * (24 - value) / (24 - 10)
        elif value <= 49: return 5 + (8 - 5) * (49 - value) / (49 - 25)
        elif value <= 90: return 2 + (5 - 2) * (90 - value) / (90 - 50)
        else: return max(0, 0 + (2 - 0) * (100 - value) / (100 - 90))
    
    def _normalize_cloud_comfort(self, value):
        if value <= 10: return 7 + (10 - 7) * (10 - value) / 10
        elif value <= 30: return 9 + (10 - 9) * (30 - value) / 20
        elif value <= 50: return 7 + (9 - 7) * (50 - value) / 20
        elif value <= 80: return 4 + (7 - 4) * (80 - value) / 30
        else: return max(0, 0 + (4 - 0) * (100 - value) / 20)
    
    def _normalize_uv_sunny(self, value):
        if value <= 2: return value * 2
        elif value <= 5: return 4 + (8 - 4) * (value - 2) / (5 - 2)
        elif value <= 7: return 8 + (10 - 8) * (value - 5) / (7 - 5)
        elif value <= 10: return 10.0
        else: return 10.0
    
    def _normalize_uv_comfort(self, value):
        if value <= 2: return 10
        elif value <= 5: return 8 + (10 - 8) * (5 - value) / 3
        elif value <= 7: return 5 + (7 - 5) * (7 - value) / 2
        elif value <= 10: return 3 + (5 - 3) * (10 - value) / 3
        else: return max(0, 0 + (3 - 0) * (12 - min(value, 12)) / 2)
    
    def _normalize_visibility(self, value):
        if value > 30000: return 10.0
        elif value > 10000: return 9 + (10 - 9) * (value - 10000) / (30000 - 10000)
        elif value > 4000: return 3 + (8 - 3) * (value - 4001) / (10000 - 4001)
        elif value > 1000: return 1 + (2 - 1) * (value - 1001) / (4000 - 1001)
        else: return 0.0
    
    def _normalize_rain_sunny(self, value):
        if value == 0.0: return 10.0
        elif value <= 0.9: return 9.0
        elif value <= 10: return max(5, 8 - (value - 1) * (3/9))
        elif value <= 30: return max(1, 5 - (value - 11) * (4/19))
        else: return 0.0
    
    def _normalize_rain_comfort(self, value):
        if value == 0.0: return 10.0
        elif value <= 0.9: return 8 + (9 - 8) * (0.9 - value) / 0.9
        elif value <= 10: return 5 + (8 - 5) * (10 - value) / 9
        elif value <= 30: return 2 + (5 - 2) * (30 - value) / 19
        else: return max(0, 0 + (2 - 0) * (70 - min(value, 70)) / 40)
    
    def _normalize_feels_like_temp(self, value):
        if 20 <= value <= 26: return 10.0
        elif 15 <= value < 20: return 7 + (10 - 7) * (20 - value) / 5
        elif 26 < value <= 30: return 7 + (10 - 7) * (30 - value) / 4
        elif 10 <= value < 15: return 4 + (7 - 3) * (15 - value) / 5
        elif 30 < value <= 35: return 4 + (7 - 4) * (35 - value) / 5
        else:
            if value < 10: return max(0, 0 + (3 - 0) * (10 - value) / 10)
            else: return max(0, 0 + (4 - 0) * (value - 35) / 15)
    
    def _normalize_humidity_comfort(self, value):
        if 40 <= value <= 60: return 10.0
        elif 30 <= value < 40: return 7 + (9 - 7) * (40 - value) / 10
        elif 60 < value <= 70: return 7 + (9 - 7) * (70 - value) / 10
        elif 20 <= value < 30: return 4 + (7 - 4) * (30 - value) / 10
        elif 70 < value <= 80: return 4 + (7 - 4) * (80 - value) / 10
        else:
            if value < 20: return max(0, 0 + (4 - 0) * (20 - value) / 20)
            else: return max(0, 0 + (4 - 0) * (100 - min(value, 100)) / 20)
    
    def _classify_sunny_level(self, score):
        if score >= 9: return 'Very Sunny'
        elif score >= 7: return 'Sunny'
        elif score >= 5: return 'Partly Sunny'
        elif score >= 3: return 'Mostly Cloudy'
        else: return 'Overcast'
    
    def _classify_comfort_level(self, score):
        if score >= 9: return 'Very Comfortable'
        elif score >= 7: return 'Comfortable'
        elif score >= 5: return 'Moderate'
        elif score >= 3: return 'Uncomfortable'
        else: return 'Very Uncomfortable'

# Global instance for caching
weather_calculator = WeatherScoreCalculator() 