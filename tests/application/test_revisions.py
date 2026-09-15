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


@pytest.mark.django_db
def test_revision_reuse_is_scoped_to_source_draft_version(context):
 from modeling.services import save_physical_draft
 from analysis.services import get_or_create_revision

 owner, project, material, section = context
 save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section))
 first, first_created = get_or_create_revision(project=project, actor=owner)
 same_draft, same_draft_created = get_or_create_revision(project=project, actor=owner)

 project.refresh_from_db()
 save_physical_draft(actor=owner, project=project, payload=valid_payload(material, section, version=project.draft_version))
 second, second_created = get_or_create_revision(project=project, actor=owner)

 assert first_created is True
 assert same_draft_created is False
 assert same_draft.id == first.id
 assert (first.source_draft_version, second.source_draft_version) == (1, 2)
 assert second_created is True
 assert second.id != first.id
 assert (first.revision_number, second.revision_number) == (1, 2)
 assert second.model_hash == first.model_hash
 assert second.physical_snapshot_json == first.physical_snapshot_json
