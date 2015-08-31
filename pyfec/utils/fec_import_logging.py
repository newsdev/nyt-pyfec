import logging, sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from pyfec import settings

""" Set up a logger.

from utils.fec_logging import fec_logger

my_logger=fec_logger()
my_logger.info('my_logger.info')
my_logger.warn('my_logger.warn')
my_logger.error('my_logger.error')
my_logger.critical('my_logger.critical')

-

2012-04-17 13:24:46,745 INFO my_logger.info
2012-04-17 13:24:46,745 WARNING my_logger.warn
2012-04-17 13:24:46,745 ERROR my_logger.error
2012-04-17 13:24:46,745 CRITICAL my_logger.critical

"""
def fec_logger():
    logger = logging.getLogger("fec_import")
    h = logging.FileHandler(settings.LOG_DIRECTORY + "/" + LOG_NAME + '.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    h.setFormatter(formatter)
    logger.addHandler(h) 
    logger.setLevel(logging.ERROR)
    return logger
