from django.contrib import admin
from .models import Location, PanelConfiguration, WeatherData, SolarPrediction, OptimalConfiguration, PredictionReport

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'latitude', 'longitude', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at']

@admin.register(PanelConfiguration)
class PanelConfigurationAdmin(admin.ModelAdmin):
    list_display = ['surface_area', 'tilt_angle', 'azimuth_angle', 'panel_efficiency', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']

@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ['location', 'date', 'solar_irradiance', 'temperature', 'cloud_cover', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['location__name']
    readonly_fields = ['created_at']

@admin.register(SolarPrediction)
class SolarPredictionAdmin(admin.ModelAdmin):
    list_display = ['id', 'location', 'timeframe', 'predicted_output', 'confidence_score', 'created_at']
    list_filter = ['timeframe', 'prediction_date', 'created_at']
    search_fields = ['location__name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('location', 'panel_config')

@admin.register(OptimalConfiguration)
class OptimalConfigurationAdmin(admin.ModelAdmin):
    list_display = ['location', 'optimal_tilt', 'optimal_azimuth', 'max_predicted_output', 'improvement_percentage', 'created_at']
    list_filter = ['created_at']
    search_fields = ['location__name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('location', 'current_config')

@admin.register(PredictionReport)
class PredictionReportAdmin(admin.ModelAdmin):
    list_display = ['prediction', 'report_type', 'created_at']
    list_filter = ['report_type', 'created_at']
    readonly_fields = ['created_at']