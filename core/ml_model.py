import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted #here
import joblib
import os
from django.conf import settings
from .models import WeatherData, SolarPrediction, Location, PanelConfiguration
import logging

logger = logging.getLogger(__name__)

class SolarPowerMLModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.model_path = os.path.join(settings.ML_MODELS_DIR, 'solar_model.joblib')
        self.scaler_path = os.path.join(settings.ML_MODELS_DIR, 'scaler.joblib')
        
    def generate_synthetic_data(self, n_samples=5000):
        """Generate synthetic solar power data for training"""
        np.random.seed(42)
        
        data = []
        for _ in range(n_samples):
            # Location features
            latitude = np.random.uniform(-60, 60)  # Realistic latitude range
            longitude = np.random.uniform(-180, 180)
            
            # Panel features
            surface_area = np.random.uniform(10, 100)  # 10-100 m²
            tilt_angle = np.random.uniform(0, 60)      # 0-60 degrees
            azimuth_angle = np.random.uniform(0, 360)  # 0-360 degrees
            panel_efficiency = np.random.uniform(0.15, 0.25)  # 15-25% efficiency
            
            # Weather features
            solar_irradiance = np.random.uniform(2, 8)  # kWh/m²/day
            temperature = np.random.uniform(-10, 45)    # Celsius
            humidity = np.random.uniform(20, 90)        # Percentage
            wind_speed = np.random.uniform(0, 20)       # m/s
            cloud_cover = np.random.uniform(0, 100)     # Percentage
            
            # Calculate realistic solar power output with some randomness
            # Base calculation with various factors
            irradiance_factor = solar_irradiance / 5  # Normalize around 5 kWh/m²/day
            temp_factor = 1 - (abs(temperature - 25) / 100)  # Optimal around 25°C
            tilt_factor = np.cos(np.radians(abs(tilt_angle - abs(latitude))))  # Optimal tilt ~ latitude
            cloud_factor = (100 - cloud_cover) / 100  # Less clouds = more power
            efficiency_factor = panel_efficiency
            
            # Calculate power output (kWh per day)
            base_power = (surface_area * irradiance_factor * temp_factor * 
                         tilt_factor * cloud_factor * efficiency_factor)
            
            # Add some realistic noise
            power_output = max(0, base_power + np.random.normal(0, base_power * 0.1))
            
            data.append({
                'latitude': latitude,
                'longitude': longitude,
                'surface_area': surface_area,
                'tilt_angle': tilt_angle,
                'azimuth_angle': azimuth_angle,
                'panel_efficiency': panel_efficiency,
                'solar_irradiance': solar_irradiance,
                'temperature': temperature,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'cloud_cover': cloud_cover,
                'power_output': power_output
            })
        
        return pd.DataFrame(data)
    
    def prepare_features(self, data):
        """Prepare features for training"""
        feature_columns = [
            'latitude', 'longitude', 'surface_area', 'tilt_angle', 'azimuth_angle',
            'panel_efficiency', 'solar_irradiance', 'temperature', 'humidity', 
            'wind_speed', 'cloud_cover'
        ]
        
        X = data[feature_columns]
        y = data['power_output']
        
        return X, y
    
    def train_model(self, retrain=False):
        """Train the ML model"""
        logger.info("Starting model training...")
        
        # Generate synthetic data
        df = self.generate_synthetic_data()
        
        # Prepare features
        X, y = self.prepare_features(df)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"Model training completed. MAE: {mae:.2f}, R²: {r2:.3f}")
        
        # Save model and scaler
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        return {'mae': mae, 'r2_score': r2}
    
    def load_model(self):
        """Load pre-trained model"""
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            return True
        except FileNotFoundError:
            logger.warning("Model not found. Training new model...")
            self.train_model()
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def predict_power_output(self, latitude, longitude, surface_area, tilt_angle, 
                           azimuth_angle, panel_efficiency, weather_data):
        """Predict solar power output"""
        # Ensure model is loaded

        try:
            check_is_fitted(self.scaler)
        except Exception:
            self.load_model()
        # Prepare input data
        input_data = pd.DataFrame({
            'latitude': [latitude],
            'longitude': [longitude],
            'surface_area': [surface_area],
            'tilt_angle': [tilt_angle],
            'azimuth_angle': [azimuth_angle],
            'panel_efficiency': [panel_efficiency],
            'solar_irradiance': [weather_data.get('solar_irradiance', 5.0)],
            'temperature': [weather_data.get('temperature', 25.0)],
            'humidity': [weather_data.get('humidity', 50.0)],
            'wind_speed': [weather_data.get('wind_speed', 5.0)],
            'cloud_cover': [weather_data.get('cloud_cover', 30.0)]
        })
        
        # Scale input
        input_scaled = self.scaler.transform(input_data)
        
        # Predict
        prediction = self.model.predict(input_scaled)[0]
        
        # Get confidence (using prediction variance from random forest)
        if hasattr(self.model, 'estimators_'):
            predictions = [tree.predict(input_scaled)[0] for tree in self.model.estimators_]
            confidence = 1 - (np.std(predictions) / np.mean(predictions))
        else:
            confidence = 0.8  # Default confidence
        
        return max(0, prediction), min(1.0, max(0.0, confidence))
    
    def find_optimal_configuration(self, latitude, longitude, surface_area, 
                                 panel_efficiency, weather_data):
        """Find optimal tilt and azimuth angles"""
        best_output = 0
        best_tilt = 0
        best_azimuth = 0
        
        # Test different angles
        tilt_range = range(0, 61, 5)  # 0 to 60 degrees, step 5
        azimuth_range = range(0, 361, 15)  # 0 to 360 degrees, step 15
        
        for tilt in tilt_range:
            for azimuth in azimuth_range:
                output, _ = self.predict_power_output(
                    latitude, longitude, surface_area, tilt, azimuth,
                    panel_efficiency, weather_data
                )
                
                if output > best_output:
                    best_output = output
                    best_tilt = tilt
                    best_azimuth = azimuth
        
        return best_tilt, best_azimuth, best_output

# Initialize global model instance
ml_model = SolarPowerMLModel()