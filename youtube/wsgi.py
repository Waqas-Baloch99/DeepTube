import os
import django
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

# Set up the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "youtube.settings")

# Initialize Django application
django.setup()

# Run migrations (this will apply any pending migrations to the database)
call_command('migrate', interactive=False)

# Initialize WSGI application
application = get_wsgi_application()

# Vercel specific requirement
app = application
