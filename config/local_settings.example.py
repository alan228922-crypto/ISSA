"""本机开发配置示例；复制为local_settings.py，真实密钥只从环境读取。"""
import os
from pathlib import Path
from .settings import *

SECRET_KEY = os.environ['ISSA_SECRET_KEY']
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': Path(os.environ.get('ISSA_DB_PATH', BASE_DIR / 'db.sqlite3'))}}
SESSION_COOKIE_NAME = 'issa_local_session'
CSRF_COOKIE_NAME = 'issa_local_csrf'
