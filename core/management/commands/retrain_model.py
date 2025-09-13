from django.core.management.base import BaseCommand
from django.utils import timezone
from core.ml_model import ml_model
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Retrain the solar power prediction ML model with updated data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retrain even if model exists',
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=5000,
            help='Number of synthetic samples to generate for training',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting ML model retraining...')
        )
        
        try:
            # Train the model
            start_time = timezone.now()
            
            self.stdout.write('Generating synthetic training data...')
            
            # Generate synthetic data and train
            results = ml_model.train_model(retrain=options['force'])
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Model retraining completed successfully in {duration:.2f} seconds!'
                )
            )
            
            self.stdout.write(f"Training Results:")
            self.stdout.write(f"  - Mean Absolute Error: {results['mae']:.2f}")
            self.stdout.write(f"  - R² Score: {results['r2_score']:.3f}")
            
            # Test the model with a sample prediction
            self.stdout.write('\nTesting model with sample prediction...')
            
            test_weather = {
                'solar_irradiance': 5.5,
                'temperature': 25.0,
                'humidity': 50.0,
                'wind_speed': 8.0,
                'cloud_cover': 30.0
            }
            
            test_output, test_confidence = ml_model.predict_power_output(
                latitude=37.7749,  # San Francisco
                longitude=-122.4194,
                surface_area=50.0,
                tilt_angle=30.0,
                azimuth_angle=180.0,
                panel_efficiency=0.20,
                weather_data=test_weather
            )
            
            self.stdout.write(
                f"Sample prediction: {test_output:.2f} kWh (confidence: {test_confidence:.1%})"
            )
            
            self.stdout.write(
                self.style.SUCCESS('Model is operational and ready for predictions!')
            )
            
        except Exception as e:
            logger.error(f"Model retraining failed: {e}")
            self.stdout.write(
                self.style.ERROR(f'Model retraining failed: {str(e)}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('Retraining process completed successfully!')
        )