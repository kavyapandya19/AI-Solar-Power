from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Location, PanelConfiguration, SolarPrediction, WeatherData
from core.ml_model import ml_model
from core.weather_service import weather_service
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Set up initial demo data for the solar prediction system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo-predictions',
            type=int,
            default=5,
            help='Number of demo predictions to create',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial demo data...')
        
        # Ensure ML model is trained
        self.stdout.write('Checking ML model...')
        ml_model.load_model()
        self.stdout.write(self.style.SUCCESS('ML model loaded successfully!'))
        
        # Create demo locations
        demo_locations = [
            {'name': 'San Francisco, CA', 'lat': 37.7749, 'lng': -122.4194},
            {'name': 'Phoenix, AZ', 'lat': 33.4484, 'lng': -112.0740},
            {'name': 'Miami, FL', 'lat': 25.7617, 'lng': -80.1918},
            {'name': 'Denver, CO', 'lat': 39.7392, 'lng': -104.9903},
            {'name': 'Seattle, WA', 'lat': 47.6062, 'lng': -122.3321},
        ]
        
        locations = []
        for loc_data in demo_locations:
            location, created = Location.objects.get_or_create(
                latitude=loc_data['lat'],
                longitude=loc_data['lng'],
                defaults={'name': loc_data['name']}
            )
            locations.append(location)
            
            if created:
                self.stdout.write(f'Created location: {location.name}')
        
        # Create demo predictions
        self.stdout.write(f'Creating {options["demo_predictions"]} demo predictions...')
        
        for i in range(options['demo_predictions']):
            location = random.choice(locations)
            
            # Create panel configuration
            panel_config = PanelConfiguration.objects.create(
                surface_area=random.uniform(20, 80),
                tilt_angle=random.uniform(10, 50),
                azimuth_angle=random.uniform(160, 200),  # Mostly south-facing
                panel_efficiency=random.uniform(0.18, 0.22)
            )
            
            # Get weather data
            weather_data = weather_service.get_weather_data(
                location.latitude, location.longitude
            )
            
            # Make prediction
            predicted_output, confidence = ml_model.predict_power_output(
                latitude=location.latitude,
                longitude=location.longitude,
                surface_area=panel_config.surface_area,
                tilt_angle=panel_config.tilt_angle,
                azimuth_angle=panel_config.azimuth_angle,
                panel_efficiency=panel_config.panel_efficiency,
                weather_data=weather_data
            )
            
            # Create prediction record
            timeframe = random.choice(['daily', 'weekly', 'monthly'])
            if timeframe == 'weekly':
                predicted_output *= 7
            elif timeframe == 'monthly':
                predicted_output *= 30
            
            prediction = SolarPrediction.objects.create(
                location=location,
                panel_config=panel_config,
                prediction_date=timezone.now().date(),
                timeframe=timeframe,
                predicted_output=predicted_output,
                confidence_score=confidence,
                weather_data=weather_data
            )
            
            self.stdout.write(
                f'Created prediction {i+1}: {prediction.predicted_output:.2f} kWh ({timeframe})'
            )
        
        self.stdout.write(
            self.style.SUCCESS('Initial demo data setup completed!')
        )
        
        # Display summary
        total_predictions = SolarPrediction.objects.count()
        total_locations = Location.objects.count()
        
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  - Total Locations: {total_locations}')
        self.stdout.write(f'  - Total Predictions: {total_predictions}')
        self.stdout.write(f'  - System is ready for use!')
        
        self.stdout.write(
            self.style.SUCCESS('\nYou can now access the dashboard at http://localhost:8000/')
        )