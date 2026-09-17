"""CSV 开户服务只在处理期间使用队长学号，绝不将其写入数据库或审计。"""
import csv
from io import StringIO
from os.path import basename
from django.core import signing
from django.db import transaction
from accounts.models import User
from .authorization import can_create_role,can_manage_event
from .models import BulkImportBatch,CompetitionEvent,EventMembership


class ProvisioningError(Exception):
    """面向调用方的稳定机器码错误。"""


def _error(code):
    raise ProvisioningError(code)


def _validate(actor,event,rows,requested_role):
    # 預覽和確認使用同一套檢查；確認時會再檢查一次，避免預覽後資料或權限已改變。
    if not can_create_role(actor,event,requested_role):
        _error('ROLE_NOT_ALLOWED')
    if not can_manage_event(actor,event):
        _error('EVENT_NOT_AUTHORIZED')
    if event.status==CompetitionEvent.Status.PURGED:
        _error('EVENT_PURGED')
    if event.status==CompetitionEvent.Status.ACTIVE:
        _error('PROVISIONING_STATUS_POLICY_GAP')
    if event.status!=CompetitionEvent.Status.DRAFT:
        _error('EVENT_STATUS_NOT_ALLOWED')
    errors=[]
    seen=set()
    for row in rows:
        number=row.get('team_number','').strip()
        captain=row.get('captain_student_id','').strip()
        if not number.isdigit() or not 1<=int(number)<=99:
            errors.append('INVALID_TEAM_NUMBER')
            continue
        if not captain:
            errors.append('MISSING_CAPTAIN_STUDENT_ID')
        if number in seen:
            errors.append('DUPLICATE_TEAM_NUMBER')
        seen.add(number)
        username=f'{event.competition_date:%Y%m%d}{int(number):02d}'
        if User.objects.filter(username=username).exists():
            errors.append('USERNAME_COLLISION')
        if EventMembership.objects.filter(event=event,user__username=username,is_active=True).exists():
            errors.append('PARTICIPATION_CONFLICT')
    return sorted(set(errors))


def preview_team_import(actor,event,source_filename,csv_text,requested_role=User.Role.USER):
    # 預覽 token 只暫時保存確認所需的資料；學號不會寫入長期保存的審計紀錄。
    rows=list(csv.DictReader(StringIO(csv_text)))
    errors=_validate(actor,event,rows,requested_role)
    display=[{'team_number':row.get('team_number','').strip(),'username':f'{event.competition_date:%Y%m%d}{int(row.get("team_number","0")):02d}' if row.get('team_number','').strip().isdigit() else ''} for row in rows]
    token=signing.dumps({'event_id':event.id,'rows':rows,'filename':basename(source_filename),'requested_role':requested_role},salt='team-import')
    return {'rows':display,'errors':errors,'token':token,'audit':{'source_filename':basename(source_filename),'row_count':len(rows),'error_codes':errors}}


def confirm_team_import(actor,event,token):
    # 確認時會一次建立所有帳戶和成員關係；中途失敗時，整批資料都不會留下。
    try:
        data=signing.loads(token,salt='team-import',max_age=600)
    except signing.BadSignature:
        _error('INVALID_PREVIEW_TOKEN')
    if data['event_id']!=event.id:
        _error('EVENT_MISMATCH')
    rows=data['rows']
    try:
        errors=_validate(actor,event,rows,data['requested_role'])
    except ProvisioningError as exc:
        BulkImportBatch.objects.create(actor=actor,event=event,source_filename=data['filename'],row_count=len(rows),success=False,validation_error_codes=[str(exc)])
        raise
    if errors:
        BulkImportBatch.objects.create(actor=actor,event=event,source_filename=data['filename'],row_count=len(rows),success=False,validation_error_codes=errors)
        _error(errors[0])
    with transaction.atomic():
        for row in rows:
            username=f'{event.competition_date:%Y%m%d}{int(row["team_number"]):02d}'
            user=User(username=username,role=User.Role.USER,must_change_password=True)
            user.set_password(row['captain_student_id'])
            user.save()
            EventMembership.objects.create(user=user,event=event,membership_type=EventMembership.Type.PARTICIPANT)
        BulkImportBatch.objects.create(actor=actor,event=event,source_filename=data['filename'],row_count=len(rows),success=True,created_account_count=len(rows))
    return {'created_count':len(rows)}
