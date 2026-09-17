from django.db import transaction
from analysis.hashing import model_hash
from modeling.snapshot import build_physical_snapshot
from projects.services import can_modify_project
from .models import ModelRevision


# ============================================================
# 檔案閱讀指南
#
# 這個檔案負責把可變的 Project 草稿，固定成可以追蹤的 ModelRevision。
# Revision 會保存當時的 Physical Snapshot 和 hash，供 AnalysisRun 指向同一版輸入。
# 這裡不執行桁架求解；它只處理模型版本、快照和資料庫保存。
# ============================================================

class RevisionError(ValueError): pass

def get_or_create_revision(*,project,actor):
    # ========================================================
    # 函數用途：取得目前 Project 對應的正式模型版本。
    #
    # 輸入是 Project 和提出操作的使用者；輸出是 (revision, 是否新建)。
    # 先把 ORM 草稿轉成固定 Snapshot，再用 hash 判斷是否可以重用最新 Revision。
    # 這個版本會被後續 AnalysisRun 使用，讓分析結果不會跟著學生之後的編輯改變。
    # ========================================================
    # 只有模型內容或草稿版本改變時才建立新的 Revision，避免同一模型重複保存。
    if not can_modify_project(actor,project): raise RevisionError('PROJECT_WRITE_DENIED')
    with transaction.atomic():
        # 鎖定 Project，讓建立 Snapshot 和讀取 draft_version 在同一個資料庫交易中完成。
        project=type(project).objects.select_for_update().get(pk=project.pk)
        # Snapshot 是草稿在這一刻的固定資料；hash 是這份 Snapshot 的內容指紋。
        snapshot=build_physical_snapshot(project); digest=model_hash(snapshot)
        # latest 是這個 Project 最近建立的 Revision，用來判斷是否已有相同版本可重用。
        latest=ModelRevision.objects.filter(project=project).order_by('-revision_number').first()
        if latest and latest.model_hash==digest and latest.source_draft_version==project.draft_version: return latest,False
        # 沒有可重用的版本時，建立一筆新的資料庫紀錄，保存快照、版本號和建立者。
        revision=ModelRevision.objects.create(project=project,revision_number=(latest.revision_number if latest else 0)+1,analysis_type=project.analysis_type,source_draft_version=project.draft_version,physical_snapshot_schema_version=snapshot['schema_version'],physical_snapshot_json=snapshot,model_hash=digest,created_by=actor)
        return revision,True
