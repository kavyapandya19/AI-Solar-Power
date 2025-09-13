from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import Location, PanelConfiguration, SolarPrediction, OptimalConfiguration
from .serializers import (
    PredictionInputSerializer, SolarPredictionSerializer, 
    OptimalConfigurationSerializer, RecommendationInputSerializer
)
from .ml_model import ml_model
from .weather_service import weather_service
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class PredictPowerView(APIView):
    def post(self, request):
        """Predict solar power output based on location and panel configuration"""
        serializer = PredictionInputSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Get or create location
            location, _ = Location.objects.get_or_create(
                latitude=data['latitude'],
                longitude=data['longitude'],
                defaults={'name': data.get('location_name', f"Location {data['latitude']}, {data['longitude']}")}
            )
            
            # Create panel configuration
            panel_config = PanelConfiguration.objects.create(
                surface_area=data['surface_area'],
                tilt_angle=data['tilt_angle'],
                azimuth_angle=data['azimuth_angle'],
                panel_efficiency=data['panel_efficiency']
            )
            
            # Get weather data
            weather_data = weather_service.get_weather_data(
                data['latitude'], data['longitude']
            )
            
            # Predict power output
            predicted_output, confidence = ml_model.predict_power_output(
                latitude=data['latitude'],
                longitude=data['longitude'],
                surface_area=data['surface_area'],
                tilt_angle=data['tilt_angle'],
                azimuth_angle=data['azimuth_angle'],
                panel_efficiency=data['panel_efficiency'],
                weather_data=weather_data
            )
            
            # Adjust output based on timeframe
            timeframe = data['timeframe']
            if timeframe == 'weekly':
                predicted_output *= 7
            elif timeframe == 'monthly':
                predicted_output *= 30
            
            # Save prediction
            prediction = SolarPrediction.objects.create(
                location=location,
                panel_config=panel_config,
                prediction_date=timezone.now().date(),
                timeframe=timeframe,
                predicted_output=predicted_output,
                confidence_score=confidence,
                weather_data=weather_data
            )
            
            # Generate time series data for visualization
            time_series_data = self._generate_time_series(prediction, weather_data)
            
            response_data = SolarPredictionSerializer(prediction).data
            response_data['time_series'] = time_series_data
            response_data['weather_info'] = weather_data
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}")
            return Response(
                {'error': 'Failed to generate prediction'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_time_series(self, prediction, weather_data):
        """Generate time series data for charts"""
        if prediction.timeframe == 'daily':
            # Hourly data for 24 hours
            hours = list(range(24))
            base_output = prediction.predicted_output / 24
            
            # Simulate solar radiation curve
            time_series = []
            for hour in hours:
                if 6 <= hour <= 18:  # Daylight hours
                    # Solar curve - peak at noon
                    solar_factor = abs(12 - hour) / 6  # Distance from noon
                    output_factor = 1 - (solar_factor ** 2) * 0.8
                    hourly_output = base_output * output_factor
                else:
                    hourly_output = 0
                
                time_series.append({
                    'time': f"{hour:02d}:00",
                    'output': round(hourly_output, 3)
                })
        
        elif prediction.timeframe == 'weekly':
            # Daily data for 7 days
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            daily_output = prediction.predicted_output / 7
            
            time_series = []
            for day in days:
                # Add some variation
                variation = 1 + (hash(day) % 20 - 10) / 100  # ±10% variation
                output = daily_output * variation
                
                time_series.append({
                    'time': day,
                    'output': round(output, 2)
                })
        
        else:  # monthly
            # Weekly data for 4 weeks
            weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
            weekly_output = prediction.predicted_output / 4
            
            time_series = []
            for week in weeks:
                variation = 1 + (hash(week) % 20 - 10) / 100
                output = weekly_output * variation
                
                time_series.append({
                    'time': week,
                    'output': round(output, 2)
                })
        
        return time_series

class RecommendOptimalView(APIView):
    def post(self, request):
        """Recommend optimal tilt and azimuth angles"""
        serializer = RecommendationInputSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Get or create location
            location, _ = Location.objects.get_or_create(
                latitude=data['latitude'],
                longitude=data['longitude'],
                defaults={'name': data.get('location_name', f"Location {data['latitude']}, {data['longitude']}")}
            )
            
            # Get weather data
            weather_data = weather_service.get_weather_data(
                data['latitude'], data['longitude']
            )
            
            # Find optimal configuration
            optimal_tilt, optimal_azimuth, max_output = ml_model.find_optimal_configuration(
                latitude=data['latitude'],
                longitude=data['longitude'],
                surface_area=data['surface_area'],
                panel_efficiency=data['panel_efficiency'],
                weather_data=weather_data
            )
            
            # Calculate improvement - use provided current config or default
            current_config = None
            current_tilt = data.get('current_tilt', 30)  # Default tilt 30 degrees
            current_azimuth = data.get('current_azimuth', 180)  # Default azimuth south

            current_config = PanelConfiguration.objects.create(
                surface_area=data['surface_area'],
                tilt_angle=current_tilt,
                azimuth_angle=current_azimuth,
                panel_efficiency=data['panel_efficiency']
            )

            current_output, _ = ml_model.predict_power_output(
                latitude=data['latitude'],
                longitude=data['longitude'],
                surface_area=data['surface_area'],
                tilt_angle=current_tilt,
                azimuth_angle=current_azimuth,
                panel_efficiency=data['panel_efficiency'],
                weather_data=weather_data
            )

            if current_output > 0:
                improvement_percentage = ((max_output - current_output) / current_output) * 100
            else:
                improvement_percentage = 0.0
            
            # Save optimal configuration
            optimal_config = OptimalConfiguration.objects.create(
                location=location,
                optimal_tilt=optimal_tilt,
                optimal_azimuth=optimal_azimuth,
                max_predicted_output=max_output,
                current_config=current_config,
                improvement_percentage=improvement_percentage
            )
            
            return Response(
                OptimalConfigurationSerializer(optimal_config).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error in recommendation: {str(e)}")
            return Response(
                {'error': 'Failed to generate recommendation'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GenerateReportView(APIView):
    def get(self, request, prediction_id):
        """Generate and download report for a prediction"""
        try:
            prediction = SolarPrediction.objects.select_related(
                'location', 'panel_config'
            ).get(id=prediction_id)
        except SolarPrediction.DoesNotExist:
            raise Http404("Prediction not found")
        
        report_type = request.GET.get('format', 'pdf').lower()
        
        if report_type not in ['pdf', 'csv']:
            return Response(
                {'error': 'Invalid format. Use pdf or csv'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            report_generator = ReportGenerator()
            
            if report_type == 'pdf':
                file_path, filename = report_generator.generate_pdf_report(prediction)
                content_type = 'application/pdf'
            else:
                file_path, filename = report_generator.generate_csv_report(prediction)
                content_type = 'text/csv'
            
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
                
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return Response(
                {'error': 'Failed to generate report'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ModelInfoView(APIView):
    def get(self, request):
        """Get information about the ML model"""
        try:
            # Check if model exists
            model_exists = ml_model.load_model()
            
            return Response({
                'model_loaded': model_exists,
                'model_type': 'Random Forest Regressor',
                'features': [
                    'latitude', 'longitude', 'surface_area', 'tilt_angle', 
                    'azimuth_angle', 'panel_efficiency', 'solar_irradiance', 
                    'temperature', 'humidity', 'wind_speed', 'cloud_cover'
                ],
                'last_trained': 'N/A',  # Could be enhanced to track training time
                'status': 'operational'
            })
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return Response(
                {'error': 'Failed to get model information'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )