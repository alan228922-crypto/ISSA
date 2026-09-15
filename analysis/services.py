from django.db import transaction
from analysis.hashing import model_hash
from modeling.snapshot import build_physical_snapshot
from projects.services import can_modify_project
from .models import ModelRevision

class RevisionError(ValueError): pass

def get_or_create_revision(*,project,actor):
    if not can_modify_project(actor,project): raise RevisionError('PROJECT_WRITE_DENIED')
    with transaction.atomic():
        project=type(project).objects.select_for_update().get(pk=project.pk)
        snapshot=build_physical_snapshot(project); digest=model_hash(snapshot)
        latest=ModelRevision.objects.filter(project=project).order_by('-revision_number').first()
        if latest and latest.model_hash==digest and latest.source_draft_version==project.draft_version: return latest,False
        revision=ModelRevision.objects.create(project=project,revision_number=(latest.revision_number if latest else 0)+1,analysis_type=project.analysis_type,source_draft_version=project.draft_version,physical_snapshot_schema_version=snapshot['schema_version'],physical_snapshot_json=snapshot,model_hash=digest,created_by=actor)
        return revision,True
