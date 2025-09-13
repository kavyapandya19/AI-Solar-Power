import requests
import random
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.openweather_api_key = settings.OPENWEATHER_API_KEY
        logger.info(f"OpenWeather API Key loaded: {bool(self.openweather_api_key)}")

    
    def get_mock_weather_data(self, latitude, longitude):
        """Generate mock weather data for demonstration"""
        # Generate realistic mock data based on latitude
        base_temp = 25 - (abs(latitude) * 0.5)  # Temperature decreases with latitude
        
        return {
            'solar_irradiance': random.uniform(3.0, 7.5),  # kWh/m²/day
            'temperature': base_temp + random.uniform(-10, 15),  # Celsius
            'humidity': random.uniform(30, 80),  # Percentage
            'wind_speed': random.uniform(1, 15),  # m/s
            'cloud_cover': random.uniform(10, 70),  # Percentage
            'source': 'mock_data'
        }
    
    def get_openweather_data(self, latitude, longitude):
        """Fetch weather data from OpenWeatherMap API"""
        if not self.openweather_api_key:
            logger.warning("OpenWeatherMap API key not configured, using mock data")
            return self.get_mock_weather_data(latitude, longitude)
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.openweather_api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Convert OpenWeatherMap data to our format
            return {
                'solar_irradiance': self._estimate_solar_irradiance(data),
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'cloud_cover': data['clouds']['all'],
                'source': 'openweathermap'
            }
        
        except requests.RequestException as e:
            logger.error(f"Error fetching OpenWeatherMap data: {e}")
            return self.get_mock_weather_data(latitude, longitude)
    
    def get_nasa_power_data(self, latitude, longitude):
        """Fetch solar data from NASA POWER API"""
        try:
            # NASA POWER API for solar radiation data
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            url = "https://power.larc.nasa.gov/api/temporal/daily/point"
            params = {
                'parameters': 'ALLSKY_SFC_SW_DWN,T2M,RH2M,WS10M,CLRSKY_SFC_SW_DWN',
                'community': 'RE',
                'longitude': longitude,
                'latitude': latitude,
                'start': start_date,
                'end': end_date,
                'format': 'JSON'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Get most recent data
            properties = data['properties']['parameter']
            latest_date = max(properties['ALLSKY_SFC_SW_DWN'].keys())
            
            return {
                'solar_irradiance': properties['ALLSKY_SFC_SW_DWN'][latest_date],
                'temperature': properties['T2M'][latest_date],
                'humidity': properties['RH2M'][latest_date],
                'wind_speed': properties['WS10M'][latest_date],
                'cloud_cover': self._estimate_cloud_cover(
                    properties['ALLSKY_SFC_SW_DWN'][latest_date],
                    properties['CLRSKY_SFC_SW_DWN'][latest_date]
                ),
                'source': 'nasa_power'
            }
        
        except Exception as e:
            logger.error(f"Error fetching NASA POWER data: {e}")
            return self.get_openweather_data(latitude, longitude)
    
    def _estimate_solar_irradiance(self, openweather_data):
        """Estimate solar irradiance from OpenWeatherMap data"""
        # Simple estimation based on cloud cover and time of day
        cloud_cover = openweather_data['clouds']['all']
        clear_sky_irradiance = 6.0  # Average clear sky irradiance kWh/m²/day
        
        # Reduce irradiance based on cloud cover
        irradiance = clear_sky_irradiance * (1 - cloud_cover / 100 * 0.8)
        return max(1.0, irradiance)
    
    def _estimate_cloud_cover(self, all_sky_radiation, clear_sky_radiation):
        """Estimate cloud cover from radiation difference"""
        if clear_sky_radiation <= 0:
            return 50  # Default value
        
        ratio = all_sky_radiation / clear_sky_radiation
        cloud_cover = (1 - ratio) * 100
        return max(0, min(100, cloud_cover))
    
    def get_weather_data(self, latitude, longitude, source='auto'):
        if source == 'openweather':
            return self.get_openweather_data(latitude, longitude)
        elif source == 'nasa':
            return self.get_nasa_power_data(latitude, longitude)
        elif source == 'mock':
            return self.get_mock_weather_data(latitude, longitude)
        else:  # AUTO
            data = self.get_openweather_data(latitude, longitude)
            if data["source"] == "mock_data":  
                data = self.get_nasa_power_data(latitude, longitude)
                if data["source"] == "openweathermap":  # NASA failed → fell back to OpenWeather again
                    return self.get_mock_weather_data(latitude, longitude)
            return data




# Global weather service instance
weather_service = WeatherService()