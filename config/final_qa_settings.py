"""Final QA only: isolated private file SQLite, no product configuration changes."""
import copy, os
from pathlib import Path
from .settings import *
QA_DIR = Path(os.environ['ISSA_FINAL_QA_DIR']).resolve()
if not str(QA_DIR).startswith('/private/tmp/issa-ui-final-'):
    raise RuntimeError('Dedicated Final QA private directory required')
DATABASES = copy.deepcopy(DATABASES)
DATABASES['default']['NAME'] = QA_DIR / 'system.sqlite3'
DATABASES['default']['TEST'] = {'NAME': str(QA_DIR / (os.environ.get('ISSA_FINAL_SUITE', 'test') + '.sqlite3'))}
DATABASES['default']['OPTIONS'] = {'timeout':20}
if os.environ.get('ISSA_FINAL_SUITE') == 'browser':
    DATABASES['default']['OPTIONS']['transaction_mode'] = 'IMMEDIATE'
