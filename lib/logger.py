import sys
import logging
from pythonjsonlogger import jsonlogger


logger = logging.getLogger('api')
logger.setLevel(logging.INFO)

logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
