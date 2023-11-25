FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install -y tzdata

RUN apt-get install -y apt-utils vim curl apache2 apache2-utils 

#Instalar librerias para PostgreSQL
#RUN apt-get -y install gcc musl-dev libghc-persistent-postgresql-dev libffi-dev

RUN apt-get -y install libapache2-mod-wsgi-py3 
RUN apt-get -y install python3-pip 
RUN pip3 install --upgrade pip 
RUN pip3 install django ptvsd 

COPY ./www/config/apache/000-default.conf /etc/apache2/sites-available/000-default.conf 
COPY ./requirements.txt /var/www/html 

ENV PYTHONUNBUFFERED=1

WORKDIR /var/www/html 
RUN pip install -r requirements.txt 

RUN echo 'alias ll="ls -l"' > ~/.bashrc

ADD ./www/ /var/www/html/

RUN chmod 664 /var/www/html/db_sqlite/ 
RUN chmod 775 /var/www/html 
RUN chmod 775 /var/www/html/log 
RUN chown www-data:www-data /var/www/html/db_sqlite/
RUN chown www-data:www-data /var/www/html 
RUN chown www-data:www-data /var/www/html/log 
RUN chmod +x /var/www/html/ie/wsgi.py
EXPOSE 80 8000 3500 

#Setear timezone 
RUN rm /etc/localtime && \ 
    ln -s /usr/share/zoneinfo/America/Buenos_Aires /etc/localtime
#

#Developer
CMD ["python3", "manage.py", "runserver","0.0.0.0:8000"]

#Production
#CMD ["apache2ctl", "-D", "FOREGROUND"]



#Scripts para crear base de datos y migraciones
# RUN python ./manage.py sqlcreate
# RUN python ./manage.py makemigrations
# RUN python ./manage.py makemigrations user
# RUN python ./manage.py makemigrations bot
# RUN python manage.py migrate




