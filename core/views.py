from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse , HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import requests
import logging
from .report_generator import ReportGenerator
from .models import SolarPrediction, OptimalConfiguration
from .weather_service import weather_service


report_gen = ReportGenerator()

def dashboard(request):
    """Main dashboard view"""
    recent_predictions = SolarPrediction.objects.select_related(
        'location', 'panel_config'
    ).order_by('-created_at')[:5]
    
    recent_recommendations = OptimalConfiguration.objects.select_related(
        'location'
    ).order_by('-created_at')[:5]
    
    context = {
        'recent_predictions': recent_predictions,
        'recent_recommendations': recent_recommendations,
    }
    
    return render(request, 'core/dashboard.html', context)

def prediction_detail(request, prediction_id):
    """View prediction details"""
    prediction = get_object_or_404(
        SolarPrediction.objects.select_related('location', 'panel_config'),
        id=prediction_id
    )

    # Fetch fresh weather data from API
    try:
        fresh_weather_data = weather_service.get_weather_data(
            prediction.location.latitude,
            prediction.location.longitude
        )
        # Update prediction with fresh weather data
        prediction.weather_data = fresh_weather_data
        prediction.save(update_fields=['weather_data'])
    except Exception as e:
        logger.error(f"Failed to fetch fresh weather data for prediction {prediction_id}: {str(e)}")
        # Use existing weather data if API fails

    # Generate time series data for visualization
    time_series_data = generate_time_series_data(prediction)

    context = {
        'prediction': prediction,
        'time_series_data': json.dumps(time_series_data),
    }

    return render(request, 'core/prediction_detail.html', context)

def recommendation_detail(request, recommendation_id):
    """View recommendation details"""
    recommendation = get_object_or_404(
        OptimalConfiguration.objects.select_related('location', 'current_config'),
        id=recommendation_id
    )
    
    context = {
        'recommendation': recommendation,
    }
    
    return render(request, 'core/recommendation_detail.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class MakePredictionView(View):
    def post(self, request):
        """Handle prediction form submission via AJAX"""
        try:
            data = json.loads(request.body)
            
            # Make API call to prediction endpoint
            api_url = request.build_absolute_uri('/api/predict/')
            response = requests.post(api_url, json=data, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                return JsonResponse({
                    'success': True,
                    'prediction': result,
                    'redirect_url': f"/prediction/{result['id']}/"
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to generate prediction'
                })    
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

@method_decorator(csrf_exempt, name='dispatch')
class GetRecommendationView(View):
    def post(self, request):
        """Handle recommendation form submission via AJAX"""
        try:
            data = json.loads(request.body)
            
            # Make API call to recommendation endpoint
            api_url = request.build_absolute_uri('/api/recommend/')
            response = requests.post(api_url, json=data, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                return JsonResponse({
                    'success': True,
                    'recommendation': result,
                    'redirect_url': f"/recommendation/{result['id']}/"
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to generate recommendation'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

def generate_time_series_data(prediction):
    """Generate time series data for chart visualization"""
    if prediction.timeframe == 'daily':
        times = [f"{h:02d}:00" for h in range(24)]
        base_output = prediction.predicted_output / 24
        outputs = []
        
        for hour in range(24):
            if 6 <= hour <= 18:  # Daylight hours
                solar_factor = abs(12 - hour) / 6
                output_factor = 1 - (solar_factor ** 2) * 0.8
                hourly_output = base_output * output_factor
            else:
                hourly_output = 0
            outputs.append(round(hourly_output, 3))
    
    elif prediction.timeframe == 'weekly':
        times = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_output = prediction.predicted_output / 7
        outputs = []
        
        for day in times:
            variation = 1 + (hash(day) % 20 - 10) / 100
            output = daily_output * variation
            outputs.append(round(output, 2))
    
    else:  # monthly
        times = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        weekly_output = prediction.predicted_output / 4
        outputs = []
        
        for week in times:
            variation = 1 + (hash(week) % 20 - 10) / 100
            output = weekly_output * variation
            outputs.append(round(output, 2))
    
    return {
        'labels': times,
        'data': outputs,
        'timeframe': prediction.timeframe
    }

def download_report(request, prediction_id):
    # Get the prediction object
    prediction = get_object_or_404(SolarPrediction, id=prediction_id)
    
    # Determine the requested format
    format_type = request.GET.get("format", "pdf").lower()
    
    # Initialize ReportGenerator
    report_gen = ReportGenerator()

    file_path = None  # initialize here to avoid UnboundLocalError
    
    try:
        if format_type == "csv":
            file_path, filename = report_gen.generate_csv_report(prediction)
            with open(file_path, 'r') as f:
                response = HttpResponse(f.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        else:  # PDF by default
            file_path, filename = report_gen.generate_pdf_report(prediction)
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass
