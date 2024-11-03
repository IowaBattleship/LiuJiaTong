import os
import time
import logging

from logging import info

LOGGER_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')

def __check_logger_dir():
    if os.access(LOGGER_DIR, os.F_OK) is False:
        os.mkdir(LOGGER_DIR)
    for filename in os.listdir(LOGGER_DIR):
        filepath = os.path.join(LOGGER_DIR, filename)
        stat = os.stat(filepath)
        if time.time() - stat.st_atime > 600:
            os.remove(filepath)

def init_logger():
    __check_logger_dir()
    logging.basicConfig(
        filename=os.path.join(LOGGER_DIR, str(os.getpid()) + ".log"),
    	level=logging.INFO,
        format='%(message)s'
    )