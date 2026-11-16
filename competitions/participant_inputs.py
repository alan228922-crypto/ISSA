"""仅在处理栈中解析凭证；输出只包含服务端可用 hash。"""
import csv
from io import StringIO
import re

from django.contrib.auth.hashers import make_password
from django.views.decorators.debug import sensitive_variables

from accounts.models import User

MAX_CSV_BYTES = 1024 * 1024


@sensitive_variables()
def create_target(event, fields):
    if type(fields) is not dict or set(fields) != {'team_number', 'captain_student_id'}:
        raise ValueError('INVALID_PROVISIONING_ROW')
    number, captain = fields['team_number'], fields['captain_student_id']
    if type(number) is not str or not re.fullmatch('[0-9]{1,2}', number.strip()):
        raise ValueError('INVALID_PROVISIONING_ROW')
    number = int(number.strip())
    if not 1 <= number <= 99 or type(captain) is not str or not 1 <= len(captain.strip()) <= 128:
        raise ValueError('INVALID_PROVISIONING_ROW')
    username = f'{event.competition_date:%Y%m%d}{number:02d}'
    if User.objects.filter(username=username).exists():
        raise ValueError('ACCOUNT_ALREADY_EXISTS')
    return {'username': username, 'password_hash': make_password(captain.strip()), 'expected': None}


@sensitive_variables()
def csv_targets(event, csv_text):
    try:
        if type(csv_text) is not str or len(csv_text.encode('utf-8')) > MAX_CSV_BYTES:
            raise ValueError('INVALID_PROVISIONING_ROW')
        reader = csv.DictReader(StringIO(csv_text.lstrip('\ufeff')), strict=True)
        columns = reader.fieldnames
        required = {'team_number', 'captain_student_id'}
        if not columns or len(columns) != len(set(columns)) or not required <= set(columns) or set(columns) - required - {'optional_team_name'}:
            raise ValueError('INVALID_PROVISIONING_ROW')
        rows = list(reader)
        if not 1 <= len(rows) <= 99:
            raise ValueError('INVALID_PROVISIONING_ROW')
        targets, seen = [], set()
        for row in rows:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('INVALID_PROVISIONING_ROW')
            target = create_target(event, {key: row[key] for key in required})
            if target['username'] in seen:
                raise ValueError('DUPLICATE_INPUT')
            seen.add(target['username'])
            targets.append(target)
        return targets, []
    except (ValueError, csv.Error, UnicodeError) as exc:
        code = str(exc)
        return [], [code if code in {'INVALID_PROVISIONING_ROW', 'ACCOUNT_ALREADY_EXISTS', 'DUPLICATE_INPUT'} else 'INVALID_PROVISIONING_ROW']
