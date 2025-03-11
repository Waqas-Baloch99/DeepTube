from django.urls import path
from . import views  # Ensure views is imported

app_name = 'youtubeapp'  # Ensure app_name is defined

urlpatterns = [
    path('', views.index, name='index'),  # Ensure these are correct
    path('script-generation/', views.script_genertation, name='script_generation'),
]
