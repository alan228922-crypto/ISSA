import pytest

from tests.application.test_physical_draft import context

pytestmark = pytest.mark.django_db


@pytest.fixture
def shared_resources(context):
    from materials.models import Strip
    from modeling.models import PhysicalMember
    from projects.models import Project
    owner, project, material, section = context
    project.event.status = 'ACTIVE'
    project.event.save()
    from tests.endpoints.test_event_landing import make_event
    closed = make_event(name='历史赛事', code='M7-HISTORY')
    closed.status = 'FINISHED_GRACE'
    closed.save()
    readonly = Project.objects.create(owner_user=owner, event=closed, name='历史模型')
    PhysicalMember.objects.create(project=readonly, client_key='member-4', material=material, section=section)
    strip = Strip.objects.create(owner_user=owner, material=material, name='条材', width_mm=2, thickness_mm=1)
    section.definition_json['strip_id'] = strip.pk
    section.save()
    return owner, project, material, section, strip, readonly


def resource_state():
    from materials.models import Material, Section, Strip, ResourceDeletionAudit
    from modeling.models import PhysicalMember
    from projects.models import Project
    return [list(model.objects.values().order_by('pk')) for model in (
        Material, Section, Strip, PhysicalMember, Project, ResourceDeletionAudit)]


@pytest.mark.parametrize('status', ['FINISHED_GRACE', 'PURGED'])
@pytest.mark.parametrize('operation', ['delete_material', 'delete_section', 'update_section', 'rebind_strip', 'update_material'])
def test_direct_mutation_cannot_touch_readonly_referenced_resources(shared_resources, status, operation):
    from materials import services
    owner, _, material, section, strip, readonly = shared_resources
    readonly.event.status = status
    readonly.event.save()
    before = resource_state()
    with pytest.raises(services.SectionServiceError):
        if operation.startswith('delete'):
            services.delete_resource(actor=owner, resource=material if operation.endswith('material') else section)
        elif operation == 'update_section':
            services.update_section(actor=owner, section=section, name='新名称', definition=section.definition_json)
        elif operation == 'update_material':
            services.update_material(actor=owner, material=material, fields={'name':'新材料'})
        else:
            services.rebind_strip_material(actor=owner, strip=strip, material_id=None)
    assert resource_state() == before


@pytest.mark.parametrize('kind', ['material', 'section'])
def test_active_context_cannot_delete_or_edit_readonly_referenced_resource(shared_resources, client, kind):
    owner, active, material, section, _, _ = shared_resources
    client.force_login(owner)
    before = resource_state()
    obj = material if kind == 'material' else section
    base = f'/projects/{active.pk}/{kind}s/{obj.pk}'
    assert client.post(f'{base}/delete/').status_code == 403
    fields = {'name':'新名称','E_MPa':'3500','source_type':'MEASURED','width_mm':'3','height_mm':'4','density_g_per_mm3':'0.001'}
    assert client.post(f'{base}/edit/', fields).status_code == 403
    assert resource_state() == before


def test_active_unshared_resource_management_stays_unchanged(context):
    from materials.services import delete_resource, update_section
    owner, _, material, section = context
    updated = update_section(actor=owner, section=section, name='可修改', definition=section.definition_json)
    assert updated.name == '可修改'
    receipt = delete_resource(actor=owner, resource=material)
    assert receipt.object_counts_json == {'members':0, 'strips':0}


def test_indirect_strip_reference_protects_material_without_direct_member_reference(shared_resources):
    from materials.services import delete_resource, SectionServiceError
    from modeling.models import PhysicalMember
    owner, _, material, _, _, readonly = shared_resources
    PhysicalMember.objects.filter(project=readonly).update(material=None)
    before = resource_state()
    with pytest.raises(SectionServiceError, match='PROJECT_WRITE_DENIED'):
        delete_resource(actor=owner, resource=material)
    assert resource_state() == before
