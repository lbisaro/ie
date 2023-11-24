FROM ubuntu

RUN apt-get update
RUN apt-get install -y apt-utils vim curl apache2 apache2-utils 
RUN apt-get -y install python3 libapache2-mod-wsgi-py3 
RUN ln /usr/bin/python3 /usr/bin/python 
RUN apt-get -y install python3-pip 
RUN pip3 install --upgrade pip 
RUN pip3 install django ptvsd 

ADD ./www/config/apache/ienv.conf /etc/apache2/sites-available/000-default.conf 
ADD ./requirements.txt /var/www/html 

ENV PYTHONUNBUFFERED=1

WORKDIR /var/www/html 
RUN pip install -r requirements.txt 

RUN echo 'alias ll="ls -l"' > ~/.bashrc

ADD ./www/ /var/www/html/

RUN chmod 664 /var/www/html/db_sqlite/db.sqlite3 
RUN chmod 775 /var/www/html 
RUN chmod 775 /var/www/html/log 
RUN chown www-data:www-data /var/www/html/db_sqlite/db.sqlite3
RUN chown www-data:www-data /var/www/html 
RUN chown www-data:www-data /var/www/html/log 
EXPOSE 80 7000 8000 3500 

#Setear timezone y sincronizar hora con afip
#ENV TZ=America/Argentina/Buenos_Aires
#RUN rm /etc/localtime && \ 
#    ln -s /usr/share/zoneinfo/America/Buenos_Aires /etc/localtime
#
#CMD ["apache2ctl", "-D", "FOREGROUND"]
CMD ["python", "manage.py", "runserver","0.0.0.0:8000"]


#Scripts para crear base de datos y migraciones
# RUN python ./manage.py sqlcreate
# RUN python ./manage.py makemigrations
# RUN python ./manage.py makemigrations user
# RUN python ./manage.py makemigrations bot
# RUN python manage.py migrate


