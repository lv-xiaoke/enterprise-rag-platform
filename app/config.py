import os
from pathlib import Path

from dotenv import load_dotenv


# 项目根目录：
# app/config.py 的上一级是 app
# 再上一级就是 mini-rag-backend
BASE_DIR = Path(__file__).resolve().parent.parent
# __file__表示当前python文件的路径，Path则是将普通的路径字符串转为Path对象，方便处理，.resovle() 则是把路径转为完整的绝对路径


# 加载项目根目录下的 .env
load_dotenv(BASE_DIR / ".env")
# `os.getenv()` 只负责读取已经存在的环境变量，而 `.env` 只是一个普通文本文件。需要 `load_dotenv()` 先把文件内容加载进去

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# os.getenv("环境变量名", "默认值")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")