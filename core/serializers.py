from rest_framework import serializers
from .models import Location, PanelConfiguration, SolarPrediction, OptimalConfiguration

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'created_at']

class PanelConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelConfiguration
        fields = ['id', 'surface_area', 'tilt_angle', 'azimuth_angle', 'panel_efficiency', 'created_at']

class PredictionInputSerializer(serializers.Serializer):
    # Location data
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    location_name = serializers.CharField(max_length=200, required=False)
    
    # Panel configuration
    surface_area = serializers.FloatField(min_value=0.1)
    tilt_angle = serializers.FloatField(min_value=0, max_value=90)
    azimuth_angle = serializers.FloatField(min_value=0, max_value=360)
    panel_efficiency = serializers.FloatField(min_value=0.01, max_value=1.0, default=0.2)
    
    # Prediction timeframe
    timeframe = serializers.ChoiceField(choices=['daily', 'weekly', 'monthly'], default='daily')

class SolarPredictionSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    panel_config = PanelConfigurationSerializer(read_only=True)
    
    class Meta:
        model = SolarPrediction
        fields = ['id', 'location', 'panel_config', 'prediction_date', 'timeframe', 
                 'predicted_output', 'confidence_score', 'weather_data', 'created_at']

class OptimalConfigurationSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    current_config = PanelConfigurationSerializer(read_only=True)
    
    class Meta:
        model = OptimalConfiguration
        fields = ['id', 'location', 'optimal_tilt', 'optimal_azimuth', 'max_predicted_output',
                 'current_config', 'improvement_percentage', 'created_at']

class RecommendationInputSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    location_name = serializers.CharField(max_length=200, required=False)
    surface_area = serializers.FloatField(min_value=0.1)
    panel_efficiency = serializers.FloatField(min_value=0.01, max_value=1.0, default=0.2)
    current_tilt = serializers.FloatField(min_value=0, max_value=90, required=False)
    current_azimuth = serializers.FloatField(min_value=0, max_value=360, required=False)