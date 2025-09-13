import os
import csv
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.conf import settings
from django.utils import timezone
import tempfile
import base64
from io import BytesIO

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        styles = {}
        
        styles['CustomTitle'] = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        
        styles['CustomHeading'] = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkgreen
        )
        
        return styles
    
    def _create_time_series_chart(self, prediction):
        """Create time series chart for the prediction"""
        # Generate time series data (same logic as API)
        if prediction.timeframe == 'daily':
            times = [f"{h:02d}:00" for h in range(24)]
            base_output = prediction.predicted_output / 24
            outputs = []
            
            for hour in range(24):
                if 6 <= hour <= 18:
                    solar_factor = abs(12 - hour) / 6
                    output_factor = 1 - (solar_factor ** 2) * 0.8
                    hourly_output = base_output * output_factor
                else:
                    hourly_output = 0
                outputs.append(hourly_output)
        
        elif prediction.timeframe == 'weekly':
            times = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            daily_output = prediction.predicted_output / 7
            outputs = [daily_output * (1 + (hash(day) % 20 - 10) / 100) for day in times]
        
        else:  # monthly
            times = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
            weekly_output = prediction.predicted_output / 4
            outputs = [weekly_output * (1 + (hash(week) % 20 - 10) / 100) for week in times]
        
        # Create plot
        plt.figure(figsize=(12, 6))
        plt.plot(times, outputs, marker='o', linewidth=2, markersize=6)
        plt.title(f'Solar Power Output - {prediction.timeframe.title()} Prediction', fontsize=16, fontweight='bold')
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Power Output (kWh)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def generate_pdf_report(self, prediction):
        """Generate PDF report for a prediction"""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        filename = f"solar_prediction_report_{prediction.id}_{timezone.now().strftime('%Y%m%d')}.pdf"
        
        # Create document
        doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
        elements = []
        
        # Title
        title = Paragraph("Solar Power Generation Prediction Report", self.custom_styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Basic information table
        basic_info = [
            ['Report Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Prediction ID:', str(prediction.id)],
            ['Timeframe:', prediction.timeframe.title()],
            ['Prediction Date:', prediction.prediction_date.strftime('%Y-%m-%d')],
        ]
        
        basic_table = Table(basic_info)
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(basic_table)
        elements.append(Spacer(1, 20))
        
        # Location Information
        location_heading = Paragraph("Location Information", self.custom_styles['CustomHeading'])
        elements.append(location_heading)
        
        location_info = [
            ['Location Name:', prediction.location.name],
            ['Latitude:', f"{prediction.location.latitude}°"],
            ['Longitude:', f"{prediction.location.longitude}°"],
        ]
        
        location_table = Table(location_info)
        location_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(location_table)
        elements.append(Spacer(1, 15))
        
        # Panel Configuration
        panel_heading = Paragraph("Panel Configuration", self.custom_styles['CustomHeading'])
        elements.append(panel_heading)
        
        panel_info = [
            ['Surface Area:', f"{prediction.panel_config.surface_area} m²"],
            ['Tilt Angle:', f"{prediction.panel_config.tilt_angle}°"],
            ['Azimuth Angle:', f"{prediction.panel_config.azimuth_angle}°"],
            ['Panel Efficiency:', f"{prediction.panel_config.panel_efficiency:.1%}"],
        ]
        
        panel_table = Table(panel_info)
        panel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(panel_table)
        elements.append(Spacer(1, 15))
        
        # Prediction Results
        results_heading = Paragraph("Prediction Results", self.custom_styles['CustomHeading'])
        elements.append(results_heading)
        
        results_info = [
            ['Predicted Output:', f"{prediction.predicted_output:.2f} kWh"],
            ['Confidence Score:', f"{prediction.confidence_score:.1%}" if prediction.confidence_score else "N/A"],
            ['Weather Source:', prediction.weather_data.get('source', 'N/A')],
        ]
        
        results_table = Table(results_info)
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightyellow),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(results_table)
        elements.append(Spacer(1, 20))
        
        # Weather Conditions
        if prediction.weather_data:
            weather_heading = Paragraph("Weather Conditions", self.custom_styles['CustomHeading'])
            elements.append(weather_heading)
            
            weather_info = [
                ['Solar Irradiance:', f"{prediction.weather_data.get('solar_irradiance', 'N/A')} kWh/m²/day"],
                ['Temperature:', f"{prediction.weather_data.get('temperature', 'N/A')}°C"],
                ['Humidity:', f"{prediction.weather_data.get('humidity', 'N/A')}%"],
                ['Wind Speed:', f"{prediction.weather_data.get('wind_speed', 'N/A')} m/s"],
                ['Cloud Cover:', f"{prediction.weather_data.get('cloud_cover', 'N/A')}%"],
            ]
            
            weather_table = Table(weather_info)
            weather_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightcyan),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(weather_table)
            elements.append(Spacer(1, 20))
        
        # Add chart
        try:
            chart_path = self._create_time_series_chart(prediction)
            chart_image = Image(chart_path, width=6*inch, height=3*inch)
            elements.append(chart_image)
        except Exception as e:
            # If chart generation fails, add text note
            chart_note = Paragraph("Chart generation failed.", self.styles['Normal'])
            elements.append(chart_note)
        
        # Build PDF
        doc.build(elements)

        # Clean up temporary chart file
        os.unlink(chart_path)
        
        return temp_file.name, filename
    
    def generate_csv_report(self, prediction):
        """Generate CSV report for a prediction"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        filename = f"solar_prediction_data_{prediction.id}_{timezone.now().strftime('%Y%m%d')}.csv"
        
        writer = csv.writer(temp_file)
        
        # Write header information
        writer.writerow(['Solar Power Prediction Report'])
        writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])  # Empty row
        
        # Basic information
        writer.writerow(['Basic Information'])
        writer.writerow(['Prediction ID', prediction.id])
        writer.writerow(['Timeframe', prediction.timeframe])
        writer.writerow(['Prediction Date', prediction.prediction_date])
        writer.writerow(['Predicted Output (kWh)', prediction.predicted_output])
        writer.writerow(['Confidence Score', prediction.confidence_score or 'N/A'])
        writer.writerow([])
        
        # Location information
        writer.writerow(['Location Information'])
        writer.writerow(['Name', prediction.location.name])
        writer.writerow(['Latitude', prediction.location.latitude])
        writer.writerow(['Longitude', prediction.location.longitude])
        writer.writerow([])
        
        # Panel configuration
        writer.writerow(['Panel Configuration'])
        writer.writerow(['Surface Area (m²)', prediction.panel_config.surface_area])
        writer.writerow(['Tilt Angle (°)', prediction.panel_config.tilt_angle])
        writer.writerow(['Azimuth Angle (°)', prediction.panel_config.azimuth_angle])
        writer.writerow(['Panel Efficiency', prediction.panel_config.panel_efficiency])
        writer.writerow([])
        
        # Weather data
        if prediction.weather_data:
            writer.writerow(['Weather Conditions'])
            writer.writerow(['Solar Irradiance (kWh/m²/day)', prediction.weather_data.get('solar_irradiance', 'N/A')])
            writer.writerow(['Temperature (°C)', prediction.weather_data.get('temperature', 'N/A')])
            writer.writerow(['Humidity (%)', prediction.weather_data.get('humidity', 'N/A')])
            writer.writerow(['Wind Speed (m/s)', prediction.weather_data.get('wind_speed', 'N/A')])
            writer.writerow(['Cloud Cover (%)', prediction.weather_data.get('cloud_cover', 'N/A')])
            writer.writerow(['Weather Source', prediction.weather_data.get('source', 'N/A')])
        
        temp_file.close()
        
        return temp_file.name, filename