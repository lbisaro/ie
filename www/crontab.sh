SHELL=/bin/bash
cd /home/lbisaro/ie/www
source venv/bin/activate
python --version
python manage.py runscript crontab_bot_1m >> live_run.log