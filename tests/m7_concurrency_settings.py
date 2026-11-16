"""仅用于 M7 文件型 SQLite 并发验证，不改变应用配置。"""
import os
from copy import deepcopy
from config.settings import *  # noqa: F403

DATABASES = deepcopy(DATABASES)  # noqa: F405
DATABASES['default']['TEST'] = {'NAME': os.environ['M7_TEST_DB_PATH']}
