"""
WSGI config for ie project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os, sys

#path a donde esta el manage.py de nuestro proyecto Django
sys.path.append('/home/lbisaro/dj_app/ie/')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ie.settings')

activate_this = '/home/lbisaro/dj_app/ie/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from django.core.wsgi import get_wsgi_application



application = get_wsgi_application()
