import os
from django.core.management import execute_from_command_line
import sys

# Set the environment variable for Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "youtube.settings")

def handler(event, context):
    # Simulate the Django management command for starting the server
    sys.argv = ['manage.py', 'runserver']
    execute_from_command_line(sys.argv)
