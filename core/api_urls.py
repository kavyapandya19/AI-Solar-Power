from django.urls import path
from .api_views import (
    PredictPowerView, RecommendOptimalView, GenerateReportView, ModelInfoView
)

urlpatterns = [
    path('predict/', PredictPowerView.as_view(), name='predict_power'),
    path('recommend/', RecommendOptimalView.as_view(), name='recommend_optimal'),
    path('report/<int:prediction_id>/', GenerateReportView.as_view(), name='generate_report'),
    path('model/info/', ModelInfoView.as_view(), name='model_info'),
]