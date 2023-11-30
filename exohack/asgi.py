import os
import django
from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exohack.settings')
django.setup()
print("HERE ASGI")
application = get_default_application()