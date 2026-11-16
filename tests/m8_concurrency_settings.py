"""M8 专用 file-SQLite 测试 DB；不改变应用连接策略。"""
import os
from copy import deepcopy
from config.settings import *  # noqa: F403

DATABASES = deepcopy(DATABASES)  # noqa: F405
DATABASES['default']['TEST'] = {'NAME': os.environ['M8_TEST_DB_PATH']}
