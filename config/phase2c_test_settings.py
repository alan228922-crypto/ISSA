"""Private file-backed DB for concurrent live-server/browser verification only."""
import copy
import os
from pathlib import Path
from .settings import *

TEST_DB = Path(os.environ['ISSA_UI_TEST_DB']).resolve()
if not str(TEST_DB).startswith('/private/tmp/issa-phase2c-'):
    raise RuntimeError('Use a dedicated Phase2C private test DB path.')
DATABASES = copy.deepcopy(DATABASES)
DATABASES['default']['TEST'] = {'NAME': str(TEST_DB)}
DATABASES['default']['OPTIONS'] = {'timeout': 20, 'transaction_mode': 'IMMEDIATE'}
