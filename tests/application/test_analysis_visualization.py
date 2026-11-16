"""Pure projection over genuine saved Runs; malformed copies are controlled facts."""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.application.test_physical_draft import context
from tests.endpoints.test_analysis_visualization import saved_context, frozen_artifacts


def build(run):
    from analysis.visualization import build_visualization_projection
    return build_visualization_projection(run=run)


def supplied_copy(run):
    """Explicit supplied-fact fixture, never persisted or called a Solver outcome."""
    fields = ['id', 'pk', 'project_id', 'model_revision_id', 'status', 'analysis_type',
              'input_hash', 'input_schema_version', 'result_schema_version',
              'solver_input_json', 'result_json']
    clone = SimpleNamespace(**{k: deepcopy(getattr(run, k)) for k in fields})
    revision = run.model_revision
    clone.model_revision = SimpleNamespace(**{k: deepcopy(getattr(revision, k)) for k in
        ['id', 'pk', 'project_id', 'source_draft_version', 'model_hash',
         'physical_snapshot_schema_version', 'physical_snapshot_json']})
    return clone


@pytest.mark.django_db
def test_saved_run_projection_is_deterministic_and_readonly(saved_context):
    _, project, run, material, _ = saved_context
    before = frozen_artifacts(run)
    # The builder may consume the linked Revision, never current Draft/catalog.
    with CaptureQueriesContext(connection) as queries:
        first = build(run)
        second = build(run)
    assert len(queries) == 0
    assert first == second and first['status'] == 'READY'
    assert first['schema_version'] == 'analysis-visualization-v1'
    assert first['provenance']['analysis_run_id'] == run.pk
    assert first['provenance']['project_id'] == project.pk
    assert first['provenance']['model_revision_id'] == run.model_revision_id
    assert first['provenance']['readonly'] is True
    assert frozen_artifacts(run) == before
    material.E_MPa = 1
    material.save(update_fields=['E_MPa'])
    project.draft_version += 1
    project.save(update_fields=['draft_version'])
    assert build(run) == first
    # Numerical copy is exact, rather than an approximate analytical expectation.
    assert first['reactions'][0]['rx_N'] == run.result_json['support_reactions'][0]['rx_N']
    u = {row['analysis_node_id']: row for row in run.result_json['node_displacements']}
    for row in first['nodes']:
        assert row['displacement'] == {k: u[row['analysis_node_id']][k] for k in ['ux_mm', 'uy_mm']}
    assert first['segments'][0]['axial_force_N'] == run.result_json['member_results'][0]['axial_force_N']
    assert 'state' not in first['segments'][0]  # Existing M9 owns classification.
    assert first['label_source']['analysis_member_mapping'] == {'m1': ['m1:1']}
    assert not any('source_id' in row for row in first['label_source']['physical_members'])
    json.dumps(first, allow_nan=False)


@pytest.mark.django_db
def test_projection_never_calls_solver_or_idealize(saved_context, monkeypatch):
    from analysis import orchestration
    from mechanics.truss2d.solver import Truss2DSolver
    _, _, run, _, _ = saved_context
    def forbidden(*args, **kwargs):
        raise AssertionError('projection attempted mechanics or Draft access')
    monkeypatch.setattr(orchestration, 'idealize', forbidden)
    monkeypatch.setattr(Truss2DSolver, 'solve', forbidden)
    from modeling import snapshot
    monkeypatch.setattr(snapshot, 'build_physical_snapshot', forbidden)
    assert build(run)['status'] == 'READY'


@pytest.mark.django_db
def test_v1_v2_explicit_identity_mapping(saved_context):
    _, _, run, _, _ = saved_context
    view = build(run)
    v2 = run.model_revision.physical_snapshot_schema_version.endswith('v2')
    assert [n['analysis_node_id'] for n in view['nodes']] == (['node:n1', 'node:n2'] if v2 else ['connection:c1', 'connection:c2'])
    assert view['nodes'][0]['source_ref'] == {'kind': 'NODE' if v2 else 'CONNECTION', 'identity': 'n1' if v2 else 'c1', 'endpoint': None}
    assert view['supports'] == [
        {'support_id': 's1', 'analysis_node_id': view['nodes'][0]['analysis_node_id'], 'support_type': 'PINNED', 'restrained_axis': None},
        {'support_id': 's2', 'analysis_node_id': view['nodes'][1]['analysis_node_id'], 'support_type': 'ROLLER', 'restrained_axis': 'Y'}]
    assert view['loads'] == [{'load_id': 'l1', 'analysis_node_id': view['nodes'][1]['analysis_node_id'], 'fx_N': 100.0, 'fy_N': 0.0}]


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['node_displacements', 'support_reactions', 'member_results'])
def test_missing_layer_does_not_destroy_independent_facts(saved_context, field):
    run = supplied_copy(saved_context[2]);run.result_json.pop(field)
    view = build(run)
    cap = {'node_displacements': 'deformation', 'support_reactions': 'reactions', 'member_results': 'axial_forces'}[field]
    assert view['status'] == 'PARTIAL'
    assert view['capabilities'][cap]['status'] == 'UNAVAILABLE'
    assert view['capabilities'][cap]['reason']
    assert view['capabilities']['geometry']['status'] == view['capabilities']['loads']['status'] == 'READY'
    if field != 'support_reactions':assert view['reactions']
    if field == 'node_displacements':assert all(n['displacement'] is None for n in view['nodes'])
    if field == 'member_results':assert all(s['axial_force_N'] is None for s in view['segments'])


@pytest.mark.django_db
@pytest.mark.parametrize('kind', ['missing_graph','duplicate_node','unknown_node','zero_segment','bool_coordinate','nan_coordinate','infinite_coordinate','wrong_mapping','missing_snapshot','wrong_revision','duplicate_segment','bad_endpoint','nonfinite_length'])
def test_bad_graph_or_identity_is_unavailable(saved_context, kind):
    run = supplied_copy(saved_context[2]);g=run.solver_input_json
    if kind=='missing_graph':g.pop('nodes')
    elif kind=='duplicate_node':g['nodes'].append(deepcopy(g['nodes'][0]))
    elif kind=='unknown_node':g['nodes'][0]['id']='unmapped'
    elif kind=='zero_segment':g['members'][0]['node_j']=g['members'][0]['node_i']
    elif kind=='bool_coordinate':g['nodes'][0]['x_mm']=True
    elif kind=='nan_coordinate':g['nodes'][0]['x_mm']=float('nan')
    elif kind=='infinite_coordinate':g['nodes'][0]['x_mm']=float('inf')
    elif kind=='wrong_mapping':g['physical_member_mapping']['m1:1']='nonexistent'
    elif kind=='missing_snapshot':run.model_revision.physical_snapshot_json={}
    elif kind=='wrong_revision':run.model_revision.project_id+=1
    elif kind=='duplicate_segment':g['members'].append(deepcopy(g['members'][0]))
    elif kind=='bad_endpoint':g['members'][0]['node_i']='not-in-graph'
    elif kind=='nonfinite_length':
        for row,x in zip(g['nodes'],[-1e308,1e308]):row['x_mm']=x
        for row,x in zip(run.model_revision.physical_snapshot_json['nodes'],[-1e308,1e308]):row['x_mm']=x
    view=build(run)
    assert view['status']=='UNAVAILABLE'
    assert not view['nodes'] and not view['segments'] and not view['reactions'] and not view['loads']
    assert all(c['status']=='UNAVAILABLE' and c['reason'] for c in view['capabilities'].values())
    json.dumps(view,allow_nan=False)


@pytest.mark.django_db
@pytest.mark.parametrize('field,cap,key', [('node_displacements','deformation','ux_mm'),('support_reactions','reactions','rx_N'),('member_results','axial_forces','axial_force_N')])
@pytest.mark.parametrize('defect',['duplicate','missing','extra','nan','bool','wrong_mapping'])
def test_invalid_optional_result_is_never_zero_filled(saved_context,field,cap,key,defect):
    run=supplied_copy(saved_context[2]);rows=run.result_json[field]
    idkey='analysis_member_id' if field=='member_results' else 'analysis_node_id'
    if defect=='duplicate':rows.append(deepcopy(rows[0]))
    elif defect=='missing':rows.pop()
    elif defect=='extra':rows.append(dict(rows[0],**{idkey:'foreign'}))
    elif defect=='nan':rows[0][key]=float('nan')
    elif defect=='bool':rows[0][key]=False
    elif defect=='wrong_mapping':
        if field=='member_results':rows[0]['physical_member_id']='foreign'
        else:rows[0][idkey]='foreign'
    view=build(run)
    assert view['status']=='PARTIAL' and view['capabilities'][cap]['status']=='UNAVAILABLE'
    assert view['capabilities']['geometry']['status']=='READY'
    json.dumps(view,allow_nan=False)


@pytest.mark.django_db
def test_exact_zero_and_tiny_saved_displacements_are_preserved(saved_context):
    run=supplied_copy(saved_context[2])
    for row in run.result_json['node_displacements']:row.update(ux_mm=0.0,uy_mm=0.0)
    assert build(run)['status']=='READY'
    run.result_json['node_displacements'][0]['ux_mm']=1e-17
    assert build(run)['nodes'][0]['displacement']['ux_mm']==1e-17


@pytest.mark.django_db
@pytest.mark.parametrize('layer',['loads','supports'])
def test_source_rows_must_match_saved_input_not_current_draft(saved_context,layer):
    run=supplied_copy(saved_context[2])
    run.solver_input_json[layer]=[]
    view=build(run);cap='loads' if layer=='loads' else 'reactions'
    assert view['status']=='PARTIAL' and view['capabilities'][cap]['status']=='UNAVAILABLE'
    assert not view['loads'] if layer=='loads' else not view['reactions']


@pytest.mark.django_db
def test_multiple_loads_and_supports_preserve_rows_not_force_sharing(saved_context):
    run=supplied_copy(saved_context[2]);snap=run.model_revision.physical_snapshot_json
    snap['supports'].append(dict(snap['supports'][0],id='s:extra'))
    run.solver_input_json['supports'].append(deepcopy(run.solver_input_json['supports'][0]))
    snap['node_loads'].append(dict(snap['node_loads'][0],id='l:extra',fx_N=-20.0,fy_N=0.5))
    run.solver_input_json['loads'].append(dict(run.solver_input_json['loads'][0],fx_N=-20.0,fy_N=0.5))
    view=build(run)
    assert view['status']=='READY' and len(view['loads'])==2
    assert {l['load_id'] for l in view['loads']}=={'l1','l:extra'}
    assert len(view['reactions'])==2
    assert view['reactions'][0]['support_ids']==['s1','s:extra']
    assert view['reactions'][0]['rx_N']==run.result_json['support_reactions'][0]['rx_N']
    assert all('rx_N' not in row for row in view['supports'])


@pytest.mark.django_db
def test_legacy_delimiter_identity_is_exact_or_unavailable(saved_context):
    run=supplied_copy(saved_context[2]);snap=run.model_revision.physical_snapshot_json
    v2=snap['schema_version'].endswith('v2')
    old=run.solver_input_json['nodes'][0]['id'];identity='joint:START:END'
    if v2:
        snap['nodes'][0]['id']=identity
        snap['physical_members'][0]['start_node_id']=identity
        snap['supports'][0]['node_id']=identity
    else:
        snap['connections'][0]['id']=identity
        snap['supports'][0]['connection_id']=identity
    new=('node:' if v2 else 'connection:')+identity
    for n in run.solver_input_json['nodes']:
        if n['id']==old:n['id']=new
    for edge in run.solver_input_json['members']:
        for k in ['node_i','node_j']:
            if edge[k]==old:edge[k]=new
    for field in ['supports','loads']:
        for row in run.solver_input_json[field]:
            if row['node_id']==old:row['node_id']=new
    for field in ['node_displacements','support_reactions']:
        for row in run.result_json[field]:
            if row['analysis_node_id']==old:row['analysis_node_id']=new
    view=build(run)
    assert view['status']=='READY'
    assert any(n['source_ref']['identity']==identity for n in view['nodes'])
    run.solver_input_json['nodes'][0]['id']='node:joint'  # No prefix splitting/coordinate fallback.
    assert build(run)['status']=='UNAVAILABLE'


@pytest.mark.django_db
def test_intermediate_joint_keeps_saved_segments(context):
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload,v2_project
    owner,project,material,section=context;v2_project(project);payload=v2_payload(material,section)
    payload['nodes'].append({'client_key':'mid','x_mm':400.0,'y_mm':0.0,'label':'中点'})
    payload['member_joint_incidences']=[{'member_client_key':'m1','node_client_key':'mid'}]
    payload['supports'] += [{'client_key':s,'target_node_client_key':n,'support_type':'ROLLER','restrained_axis':'Y'} for s,n in [('s2','n2'),('sm','mid')]]
    payload['node_loads'][0].update(fx_N=100.0,fy_N=0.0)
    save_physical_draft(actor=owner,project=project,payload=payload)
    project.refresh_from_db()
    run=analyze_project(project=project,actor=owner,expected_draft_version=1)
    assert run.status=='SUCCESS'
    view=build(run)
    assert view['status']=='READY' and len(view['nodes'])==3
    assert [(s['analysis_segment_id'],s['start_analysis_node_id'],s['end_analysis_node_id']) for s in view['segments']]==[('m1:1','node:n1','node:mid'),('m1:2','node:mid','node:n2')]
    assert view['label_source']['analysis_member_mapping']=={'m1':['m1:1','m1:2']}


@pytest.mark.django_db
@pytest.mark.parametrize('saved_context', ['v2'], indirect=True)
def test_colocated_distinct_nodes_never_merge(saved_context):
    run=supplied_copy(saved_context[2]);snap=run.model_revision.physical_snapshot_json
    snap['nodes'].append(dict(snap['nodes'][0],id='colocated'))
    snap['physical_members'].append(dict(snap['physical_members'][0],id='m2',start_node_id='colocated'))
    run.solver_input_json['nodes'].append({'id':'node:colocated','x_mm':0.0,'y_mm':0.0})
    run.solver_input_json['members'].append(dict(run.solver_input_json['members'][0],id='m2:1',node_i='node:colocated'))
    run.solver_input_json['physical_member_mapping']['m2:1']='m2'
    run.result_json['node_displacements'].append({'analysis_node_id':'node:colocated','ux_mm':0.0,'uy_mm':0.0})
    run.result_json['member_results'].append(dict(run.result_json['member_results'][0],analysis_member_id='m2:1',physical_member_id='m2'))
    view=build(run)
    assert view['status']=='READY' and len(view['nodes'])==3
    assert {n['source_ref']['identity'] for n in view['nodes']}=={'n1','n2','colocated'}


@pytest.mark.django_db
@pytest.mark.parametrize('saved_context', ['v1'], indirect=True)
def test_v1_free_endpoint_provenance_uses_exact_member_identity(saved_context):
    run=supplied_copy(saved_context[2]);snap=run.model_revision.physical_snapshot_json
    # Controlled historical graph format only, not a newly solved stable structure.
    snap['connections']=[snap['connections'][0]];snap['supports']=[];snap['node_loads']=[]
    for row in run.solver_input_json['nodes']:
        if row['id']=='connection:c2':row['id']='free:m1:END'
    run.solver_input_json['members'][0]['node_j']='free:m1:END'
    run.solver_input_json['supports']=[];run.solver_input_json['loads']=[]
    for row in run.result_json['node_displacements']:
        if row['analysis_node_id']=='connection:c2':row['analysis_node_id']='free:m1:END'
    run.result_json['support_reactions']=[]
    view=build(run)
    assert view['status']=='READY'
    assert view['nodes'][1]['source_ref']=={'kind':'MEMBER_ENDPOINT','identity':'m1','endpoint':'END'}
    run.solver_input_json['nodes'][1]['id']='free:unknown:END'
    assert build(run)['status']=='UNAVAILABLE'


@pytest.mark.django_db
@pytest.mark.parametrize('defect',['source_endpoint_list','units','missing_units'])
def test_malformed_snapshot_never_raises_or_relabels_units(saved_context,defect):
    run=supplied_copy(saved_context[2]);snap=run.model_revision.physical_snapshot_json
    if defect=='source_endpoint_list':snap['physical_members'][0]['start_node_id']=[]
    elif defect=='units':snap['units']['length']='cm'
    else:snap.pop('units')
    assert build(run)['status']=='UNAVAILABLE'


@pytest.mark.django_db
def test_unknown_result_schema_cannot_expose_misinterpreted_numerics(saved_context):
    run=supplied_copy(saved_context[2]);run.result_schema_version='unknown-format'
    view=build(run)
    assert view['status']=='PARTIAL' and view['capabilities']['geometry']['status']=='READY'
    assert all(view['capabilities'][k]['status']=='UNAVAILABLE' for k in ['deformation','reactions','axial_forces'])
    assert all(row['displacement'] is None for row in view['nodes'])


@pytest.mark.django_db
def test_missing_displacement_has_a_specific_availability_reason(saved_context):
    run=supplied_copy(saved_context[2]);run.result_json.pop('node_displacements')
    assert build(run)['capabilities']['deformation']['reason']=='MISSING_SAVED_DISPLACEMENTS'


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['model_hash', 'input_hash'])
@pytest.mark.parametrize('bad', ['', None, False, 123, 'g' * 64, 'a' * 63, float('nan')])
def test_invalid_required_hash_provenance_never_exposes_numeric_graph(saved_context, field, bad):
    """No shared identity anchor means no numeric facts, even if JSON looks valid."""
    run = supplied_copy(saved_context[2])
    target = run.model_revision if field == 'model_hash' else run
    setattr(target, field, bad)
    view = build(run)
    assert view['status'] == 'UNAVAILABLE'
    assert all(cap == {'status': 'UNAVAILABLE', 'reason': 'INVALID_SAVED_PROVENANCE'}
               for cap in view['capabilities'].values())
    for name in ['nodes', 'segments', 'supports', 'loads', 'reactions']:
        assert view[name] == []
    assert view['provenance'][field] is None
    json.dumps(view, allow_nan=False)


@pytest.mark.django_db
def test_integer_coordinate_difference_overflow_is_unavailable(saved_context):
    """Representable JSON integers must not escape the finite-length guard as 500."""
    run = supplied_copy(saved_context[2])
    for row, x in zip(run.solver_input_json['nodes'], [-10**308, 10**308]):
        row['x_mm'] = x
    for row, x in zip(run.model_revision.physical_snapshot_json['nodes'], [-10**308, 10**308]):
        row['x_mm'] = x
    view = build(run)
    assert view['status'] == 'UNAVAILABLE'
    assert view['nodes'] == view['segments'] == []
    json.dumps(view, allow_nan=False)
