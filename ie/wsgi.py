"""
WSGI config for ie project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os, sys
import my_logging as mylog
#path a donde esta el manage.py de nuestro proyecto Django
sys.path.append('/home/lbisaro/dj_app/ie/')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ie.settings')

mylog.info(sys.version_info)
from django.core.wsgi import get_wsgi_application



application = get_wsgi_application()
