# Configura el logging
import logging

logging.basicConfig(filename='bot.log', filemode='a',
                    format='%(asctime)s %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

def info(msg):
    logging.info(msg, exc_info=False)

def error(msg):
    logging.error(msg, exc_info=False)

def criticalError(msg):
    logging.error(msg, exc_info=False)
    exit(msg)

def warning(msg):
    logging.warning(msg, exc_info=False)