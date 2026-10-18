from django.urls import path
from .views import *


urlpatterns = [
    path('', index, name="school_index"),
    path('api/stress-marks/', SchoolAPIStressMarksView.as_view(), name='api_stress_marks'),
    path('api/paronyms/', SchoolAPIParonymsView.as_view(), name='api_paronyms'),
]
