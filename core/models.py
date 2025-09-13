from django.db import models
from django.utils import timezone
import json

class Location(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"

class PanelConfiguration(models.Model):
    surface_area = models.FloatField(help_text="Panel surface area in m²")
    tilt_angle = models.FloatField(help_text="Tilt angle in degrees")
    azimuth_angle = models.FloatField(help_text="Azimuth angle in degrees")
    panel_efficiency = models.FloatField(default=0.2, help_text="Panel efficiency (0.0-1.0)")
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Panel: {self.surface_area}m² - Tilt: {self.tilt_angle}° - Azimuth: {self.azimuth_angle}°"

class WeatherData(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    date = models.DateField()
    solar_irradiance = models.FloatField(help_text="Solar irradiance in kWh/m²/day")
    temperature = models.FloatField(help_text="Temperature in Celsius")
    humidity = models.FloatField(help_text="Humidity percentage")
    wind_speed = models.FloatField(help_text="Wind speed in m/s")
    cloud_cover = models.FloatField(help_text="Cloud cover percentage")
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['location', 'date']
    
    def __str__(self):
        return f"{self.location.name} - {self.date}"

class SolarPrediction(models.Model):
    TIMEFRAME_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    panel_config = models.ForeignKey(PanelConfiguration, on_delete=models.CASCADE)
    prediction_date = models.DateField()
    timeframe = models.CharField(max_length=10, choices=TIMEFRAME_CHOICES)
    predicted_output = models.FloatField(help_text="Predicted power output in kWh")
    confidence_score = models.FloatField(null=True, blank=True)
    weather_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Prediction: {self.predicted_output:.2f} kWh - {self.timeframe}"

class OptimalConfiguration(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    optimal_tilt = models.FloatField()
    optimal_azimuth = models.FloatField()
    max_predicted_output = models.FloatField()
    current_config = models.ForeignKey(PanelConfiguration, on_delete=models.CASCADE, null=True)
    improvement_percentage = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Optimal for {self.location.name}: Tilt {self.optimal_tilt}°, Azimuth {self.optimal_azimuth}°"

class PredictionReport(models.Model):
    prediction = models.ForeignKey(SolarPrediction, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=10, choices=[('csv', 'CSV'), ('pdf', 'PDF')])
    file_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.report_type.upper()} Report - {self.prediction.id}"