import os
from django.core.asgi import get_asgi_application

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube.settings')

# Initialize the ASGI application
app = get_asgi_application()
