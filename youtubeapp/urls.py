from django.urls import path
from . import views  # Ensure views is imported

app_name = 'youtubeapp'  # Ensure app_name is defined

urlpatterns = [
    path('', views.index, name='index'),
    path('script_generation/', views.script_generation, name='script_generation'),
    path('chat/', views.chat_with_groq, name='chat'),
    path('generate_script/', views.generate_script, name='generate_script'),
]
