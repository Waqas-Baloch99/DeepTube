from django.urls import path
from . import views

app_name = 'youtubeapp'

urlpatterns = [
    path('', views.index, name='index'),
    path('script_generation/', views.script_generation, name='script_generation'),
    path('generate_script/', views.generate_script, name='generate_script'),
    path('script_history/', views.get_script_history, name='script_history'),
    path('chat/', views.chat_with_deepseek, name='chat_with_deepseek'),
    path('script/<int:script_id>/', views.get_script, name='get_script'),
    path('clear_script_history/', views.clear_script_history, name='clear_script_history'),
]
