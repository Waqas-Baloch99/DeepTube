from django.urls import path
from . import views

app_name = 'youtubeapp'

urlpatterns = [
    path('', views.home, name='home'),
    path('chat/', views.index, name='index'),  # Chat functionality merged here
    path('clear-chat-history/', views.clear_chat_history, name='clear_chat_history'),
    path('youtube_analytics/', views.youtube_analytics, name='youtube_analytics'),
    path('script_generation/', views.script_generation, name='script_generation'),
    path('generate_script/', views.generate_script, name='generate_script'),
    path('script_history/', views.get_script_history, name='script_history'),
    path('script/<int:script_id>/', views.get_script, name='get_script'),
    path('clear_script_history/', views.clear_script_history, name='clear_script_history'),
    path('contact/', views.contact_view, name='contact'),
    path('update_region/', views.update_region, name='update_region'),
]
