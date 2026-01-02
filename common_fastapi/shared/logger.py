import sys, os, logging
from dotenv import load_dotenv # type: ignore
from datetime import date
from logging.handlers import TimedRotatingFileHandler

# 1안)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s') 
# logger = logging.getLogger(__name__) # __name__ : 현재 모듈의 이름(파일 경로)을 나타내는 내장 변수

# 2안)
# logger = logging.getLogger(__name__)
# if not logger.handlers: # 이미 핸들러가 설정되지 않았을 경우에만 추가
#     stream_handler = logging.StreamHandler(sys.stdout)
#     formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
#     stream_handler.setFormatter(formatter)
#     logger.addHandler(stream_handler)
#     logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Reset handlers to avoid duplicate logs

    load_dotenv()
    LOG_PATH = os.getenv("LOG_PATH")
    if LOG_PATH:
        os.makedirs(LOG_PATH, exist_ok=True) # if not os.path.exists(LOG_PATH):
    
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')

    if LOG_PATH:
        file_handler = TimedRotatingFileHandler(filename=os.path.join(LOG_PATH, f"{date.today()}.log"), when="midnight", interval=1, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # logger.info("Logging started.")
