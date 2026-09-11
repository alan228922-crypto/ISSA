import pytest
from tests.application.test_physical_draft import context, valid_payload

@pytest.mark.django_db
def test_revision_freezes_snapshot_and_deduplicates(context):
 from modeling.services import save_physical_draft
 from analysis.services import get_or_create_revision
 owner,project,material,section=context; save_physical_draft(actor=owner,project=project,payload=valid_payload(material,section))
 revision,created=get_or_create_revision(project=project,actor=owner); same,created_again=get_or_create_revision(project=project,actor=owner)
 material.E_MPa=999; material.save(); project.geometry_nodes.update(x_mm=42)
 assert created is True and created_again is False and same.id==revision.id
 assert revision.physical_snapshot_json['physical_members'][0]['material']['E_MPa']==2000.0
