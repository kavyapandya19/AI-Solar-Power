from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('prediction/<int:prediction_id>/', views.prediction_detail, name='prediction_detail'),
    path('recommendation/<int:recommendation_id>/', views.recommendation_detail, name='recommendation_detail'),
    path('ajax/predict/', views.MakePredictionView.as_view(), name='ajax_predict'),
    path('ajax/recommend/', views.GetRecommendationView.as_view(), name='ajax_recommend'),
    path('download/prediction/<int:prediction_id>/', views.download_report, name='download_report')
]