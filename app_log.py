# Configura el logging
import logging
from datetime import datetime

class app_log:
    filename = 'bot'
    date_format = '%Y-%m-%d %H:%M:%S'

    def write(self,type,msg):
        dt = datetime.now()
        line = dt.strftime(self.date_format)+' - '+type+' - '+msg
        with open(self.filename+'.log', 'a') as file:
            file.write(line + '\n')

    def info(self,msg):
       self.write(type='INFO',msg=msg)

    def warning(self,msg):
       self.write(type='WARNING',msg=msg)

    def error(self,msg):
       self.write(type='ERROR',msg=msg)

    def criticalError(self,msg):
       self.write(type='CRITICAL ERROR',msg=msg)
       exit(msg)
