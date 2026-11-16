"""Stable presentation identities and student-only information boundaries."""
import base64
import hashlib
from pathlib import Path

import pytest
from playwright.sync_api import expect

from modeling.services import save_physical_draft
from projects.models import Project
from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core
from tests.browser.test_model_check_recovery import read_draft, open_check

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


@pytest.mark.parametrize('kind,collection,prefix,expected', [
    ('GEOMETRY_NODE', 'nodes', 'node', '节点 N4'),
    ('PHYSICAL_MEMBER', 'physical_members', 'member', '构件 M4'),
    ('SUPPORT', 'supports', 'support', '支座 S4'),
    ('NODE_LOAD', 'node_loads', 'load', '荷载 L4'),
    ('CONNECTION', 'connections', 'connection', '连接 C4'),
])
def test_identity_survives_deletion_reorder_and_snapshot(context, workspace_page, kind, collection, prefix, expected):
    """Break: deriving names from current collection rank or ignoring snapshot id."""
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async ({kind,collection,prefix}) => {
      const {createStudentLabelResolver:resolver}=await import('/static/projects/workspace/labels.js');
      const {studentObjectName}=await import('/static/projects/workspace/incomplete-objects.js');
      const key=prefix+'-4', rows=[1,2,3,4].map(n=>({client_key:prefix+'-'+n,label:''}));
      const states=[rows,rows.filter(r=>!['2','3'].includes(r.client_key.split('-')[1])),[...rows].reverse()];
      return states.flatMap(items=>{
        const draft={[collection]:items}; const snapshot={[collection]:items.map(({client_key,...r})=>({...r,id:client_key}))};
        return [resolver(draft).label(kind,key),studentObjectName(draft,kind,key),resolver(snapshot).label(kind,key)];
      });
    }""", dict(kind=kind, collection=collection, prefix=prefix))
    assert result == [expected] * 9


@pytest.mark.parametrize('key', ['550e8400-e29b-41d4-a716-446655440000', '旧模型/α', 'member-04', 'member-0', 'a'*128, '汉'*64])
def test_nonstandard_identity_digest_and_description(context, workspace_page, key):
    """Break: rank, raw-key, lossy UTF8 hash, or custom label replacing identity."""
    page, _ = open_core(context, workspace_page)
    code = base64.b32encode(hashlib.sha256(key.encode()).digest()).decode()[:10]
    result = page.evaluate("""async key=>{
      const {createStudentLabelResolver:r}=await import('/static/projects/workspace/labels.js');
      return [r({physical_members:[{client_key:key,label:'上弦杆'}]}).label('PHYSICAL_MEMBER',key),
        r({physical_members:[{client_key:'unrelated'}, {client_key:key,label:'上弦杆'}]}).label('PHYSICAL_MEMBER',key)];
    }""", key)
    assert result == [f'上弦杆 · 构件 M·{code}'] * 2


@pytest.mark.parametrize('schema', ['physical-draft-v1', 'physical-draft-v2'])
def test_public_incomplete_delete_history_save_reload_identity(context, workspace_page, schema):
    """Break: names differ across recovery, checks, dialog, history or persistence."""
    owner, original, material, section = context
    project = Project.objects.create(event=original.event, owner_user=owner, name='Stable names', draft_schema_version=schema)
    draft = dict(schema_version=schema, expected_draft_version=0, nodes=[], supports=[], node_loads=[],
                 physical_members=[dict(client_key=f'member-{n}', start_node_client_key=None, end_node_client_key=None,
                     material_id=material.pk, section_id=section.pk, is_active=True, label='上弦杆' if n==4 else '') for n in range(1,5)])
    draft['connections' if schema.endswith('v1') else 'member_joint_incidences'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-draft-object-key="member-4"]').click()
    expect(page.locator('[data-property-identity]')).to_have_text('上弦杆 · 构件 M4')
    page.locator('[data-incomplete-inventory]').evaluate('(e)=>e.open=true')
    for n in [2,3]:
        page.locator(f'[data-incomplete-object-key="member-{n}"]').get_by_role('button', name='删除', exact=True).click()
    expect(page.locator('[data-draft-object-key="member-4"]')).to_contain_text('上弦杆 · 构件 M4')
    page.locator('[data-cad-undo]').click()
    page.locator('[data-cad-redo]').click()
    with page.expect_response('**/model/save/'):
        page.locator('#workspace-save').click()
    expect(page.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    page.reload()
    expect(page.locator('[data-draft-object-key="member-4"]')).to_contain_text('上弦杆 · 构件 M4')
    assert [r['client_key'] for r in read_draft(project)['physical_members']] == ['member-1','member-4']
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/'):
        page.locator('#workspace-model-check').click()
    expect(page.locator('[data-incomplete-check-card]').filter(has_text='构件 M4')).to_contain_text('上弦杆 · 构件 M4')
    evidence = Path(__file__).resolve().parents[2] / '.superpowers/sdd/ux-debt-01/screenshots'
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(evidence / f'stable-incomplete-{schema}.png'), full_page=True)


def test_error_and_unmapped_check_do_not_disclose_internals(context, workspace_page):
    """Break: collapsed machine-code disclosure or untrusted message passthrough."""
    page, _ = open_core(context, workspace_page)
    text = page.evaluate("""async()=>{
      const {renderWorkspaceError}=await import('/static/projects/workspace/errors.js');
      const {presentModelCheckIssue}=await import('/static/projects/workspace/workflow.js');
      const root=document.createElement('section'); document.body.append(root);
      renderWorkspaceError(root,{code:'MACHINE_PRIVATE',message:'raw-private-key schema-secret',details:{id:1234}});
      return {error:root.textContent,hasTechnical:!!root.querySelector('[data-error-technical]'),
        check:presentModelCheckIssue({code:'UNMAPPED_PRIVATE',human_message:'raw-private-key schema-secret'}).explanation};
    }""")
    assert text['hasTechnical'] is False
    for field in ['error','check']:
        assert not any(s in text[field] for s in ['MACHINE_PRIVATE','raw-private-key','schema-secret','技术信息'])
        assert text[field]
    assert '下一步' in text['error']


def test_snapshot_engineering_and_report_hide_ids_keep_values(context, workspace_page):
    """Break: raw mappings/provenance, or replacing historical names with current ones."""
    page, _ = open_core(context, workspace_page)
    result = page.evaluate("""async()=>{
      const {renderReport}=await import('/static/projects/workspace/report.js');
      const {renderEngineeringDetails,showEngineeringDetails}=await import('/static/projects/workspace/results.js');
      const snapshot={nodes:[{id:'node-4',label:'历史节点'}],physical_members:[{id:'member-4',label:'历史构件'}],member_joint_incidences:[]};
      const numbers={node_displacements:[{analysis_node_id:'node:node-4',ux_mm:0.125,uy_mm:-0.25}],support_reactions:[{analysis_node_id:'node:node-4',rx_N:12,ry_N:20}],member_results:[{analysis_member_id:'RAW_SEGMENT',physical_member_id:'member-4',axial_force_N:20,axial_stress_MPa:5,mass_g:7}],total_mass_g:7};
      const report={geometry_connectivity:{...snapshot,analysis_member_mapping:{'member-4':['RAW_SEGMENT']}},
        provenance:{analysis_run_id:987654321,model_revision_id:987654322,model_hash:'RAW_HASH',input_hash:'RAW_INPUT',solver_version:'Truss2D-v1',source_draft_version:1,current_draft_version:2,is_stale:true},
        assumptions:{analysis_type:'TRUSS_2D',kinematics:'SMALL_DISPLACEMENT',joint_model:'PINNED',member_behavior:'AXIAL_ONLY',units:{length:'mm'}},
        node_results:{items:numbers.node_displacements},member_results:{items:numbers.member_results},results_summary:{total_mass_g:7}};
      const root=document.createElement('section'),tech=document.createElement('section');document.body.append(root,tech);
      renderReport(root,{report,completeness:{}},{runNumber:1});
      renderEngineeringDetails(tech,showEngineeringDetails(numbers),true,snapshot);
      return {report:root.textContent,tech:tech.textContent};
    }""")
    for text in result.values():
        assert '历史构件 · 构件 M4' in text
        assert '历史节点 · 节点 N4' in text
        assert '0.125' in text and '20' in text and '5' in text
        assert not any(s in text for s in ['RAW_', '98765432', 'node:node-4', 'member-4', 'TRUSS_2D', 'SMALL_DISPLACEMENT', 'AnalysisRun', 'hash'])


def test_delete_dialog_uses_same_stable_name(context, workspace_page):
    """Break: dialog privately renumbers an affected object."""
    page, _ = open_core(context, workspace_page)
    result=page.evaluate("""async()=>{
      const {confirmDeleteImpact}=await import('/static/projects/workspace/delete-impact-dialog.js');
      const originalDraft={physical_members:[{client_key:'member-4',label:'上弦杆'}]};
      const promise=confirmDeleteImpact({workspace:document.querySelector('#workspace-root'),originalDraft,
        preview:{summary:{related:{PHYSICAL_MEMBER:1},selected:{GEOMETRY_NODE:1},total:{PHYSICAL_MEMBER:1,GEOMETRY_NODE:1}},directAffected:[{kind:'PHYSICAL_MEMBER',clientKey:'member-4'}],newlyUnattached:[]}});
      const dialog=document.querySelector('[data-delete-impact-dialog]'); const text=dialog.textContent;
      dialog.querySelector('[data-delete-impact-choice="cancel"]').click(); await promise;return text;
    }""")
    assert '上弦杆 · 构件 M4' in result


def test_report_reactions_and_v1_free_endpoint_keep_student_meaning(context, workspace_page):
    """Break: dropping report reactions, raw/free endpoint id, or unidentifiable segments."""
    page, _ = open_core(context, workspace_page)
    result=page.evaluate("""async()=>{
      const {renderReport}=await import('/static/projects/workspace/report.js');
      const {renderEngineeringDetails}=await import('/static/projects/workspace/results.js');
      const snapshot={nodes:[{id:'node-4'}],physical_members:[{id:'member-4',start_node_id:'node-4'}],analysis_member_mapping:{'member-4':['opaque-seg-a','opaque-seg-b']}};
      const members=['opaque-seg-a','opaque-seg-b'].map((analysis_member_id,i)=>({analysis_member_id,physical_member_id:'member-4',axial_force_N:i?8:13,axial_stress_MPa:2,mass_g:3}));
      const report={geometry_connectivity:snapshot,provenance:{},node_results:{items:[],support_reactions:[{analysis_node_id:'free:member-4:START',rx_N:123.75,ry_N:234.5}]},member_results:{items:members},results_summary:{}};
      const root=document.createElement('section'),tech=document.createElement('section'); document.body.append(root,tech);
      renderReport(root,{report});
      renderEngineeringDetails(tech,{displacements:[{analysis_node_id:'free:member-4:START',ux_mm:0,uy_mm:0}],reactions:[],members,total_mass_g:6},false,snapshot);
      return {report:root.textContent,tech:tech.textContent};
    }""")
    assert '123.75' in result['report'] and '234.5' in result['report']
    for text in result.values():
        assert '节点 N4' in text
        assert '构件 M4 · 分析段 1' in text and '构件 M4 · 分析段 2' in text
        assert 'opaque-seg' not in text and 'free:' not in text


def test_missing_snapshot_result_has_safe_names_not_raw_fallback(context, workspace_page):
    """Break: fallback paths leak run primary key or raw maximum-displacement ids."""
    page, _=open_core(context,workspace_page)
    result=page.evaluate("""async()=>{
      const {showLevelOne,renderLevelOne}=await import('/static/projects/workspace/results.js');
      const data={source_draft_version:1,result_json:{member_results:[]},level_one:{maximum_displacement:{candidate_analysis_node_ids:['RAW_NODE_KEY'],maximum_displacement_mm:0.5}}};
      const root=document.createElement('section');document.body.append(root);
      renderLevelOne(root,showLevelOne({runId:987654321,historical:false,canLinkCanvas:false,comparisonAvailable:false,members:[],displacement:{available:true,maximumMm:0.5,candidates:[{id:'RAW_NODE_KEY',label:'节点'}]}}));
      return root.textContent;
    }""")
    assert '987654321' not in result and 'RAW_NODE_KEY' not in result
    assert '0.5' in result and '结论' in result


@pytest.mark.parametrize('code,words', [
    ('EDITOR_EXPLICIT_NODE_REQUIRED', ['节点','捕捉']),
    ('EDITOR_UNJOINED_CROSSING_ENDPOINT', ['交点','节点']),
    ('MEMBER_PROPERTIES_REQUIRED', ['材料','截面']),
    ('CAD_INPUT_MALFORMED', ['坐标','长度','角度']),
    ('CAD_COMMAND_CONTEXT', ['节点','构件']),
    ('NODE_MOVE_CONFLICT', ['已有节点','未移动']),
    ('NODE_NOT_ON_MEMBER', ['构件','节点']),
])
def test_known_local_errors_keep_recovery_without_trusting_message(context,workspace_page,code,words):
    """Break: safety fallback destroys existing specific CAD recovery guidance."""
    page,_=open_core(context,workspace_page)
    text=page.evaluate("""async code=>{
      const {renderWorkspaceError}=await import('/static/projects/workspace/errors.js');
      const root=document.createElement('section');document.body.append(root);
      renderWorkspaceError(root,{code,message:'DO_NOT_TRUST_PRIVATE'});return root.textContent;
    }""",code)
    assert 'DO_NOT_TRUST_PRIVATE' not in text and code not in text
    assert all(word in text for word in words)


@pytest.mark.parametrize('schema', ['physical-draft-v1','physical-draft-v2'])
def test_public_historical_results_report_use_own_snapshot(context,workspace_page,schema):
    """Break: main workspace passes current labels into historical result/report renderers."""
    from analysis.orchestration import analyze_project
    from projects.management.commands.seed_demo import _bt01_payload
    owner, original, material, section=context
    project=Project.objects.create(event=original.event,owner_user=owner,name='Historical names',draft_schema_version=schema)
    payload=_bt01_payload(material,section,0,schema)
    payload['physical_members'][0]['label']='历史构件'
    save_physical_draft(actor=owner,project=project,payload=payload)
    project.refresh_from_db()
    run=analyze_project(project=project,actor=owner,expected_draft_version=project.draft_version)
    assert run.status=='SUCCESS'
    page=workspace_page(user=owner,project=project)
    page.locator('[data-draft-object-key="m1"]').click()
    page.locator('[data-property-label]').fill('当前新名称')
    page.locator('[data-property-label]').press('Tab')
    with page.expect_response('**/model/save/'):
        page.locator('#workspace-save').click()
    expect(page.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.pk))
    expect(page.locator('#workspace-results')).to_contain_text('历史构件 · 构件 M·ZIG7FSK2UF')
    report=page.locator('#workspace-report-view')
    expect(report).to_contain_text('历史构件 · 构件 M·ZIG7FSK2UF')
    assert '当前新名称' not in report.text_content()
    assert 'm1:1' not in report.text_content() and 'connection:c1' not in report.text_content()


@pytest.mark.parametrize('code,words', [
    ('UNATTACHED_SUPPORT_NODE',['支座','构件']),
    ('UNATTACHED_LOAD_NODE',['荷载','构件']),
    ('DUPLICATE_NODE_COORDINATE',['节点','同一位置']),
    ('INVALID_MEMBER_INCIDENCE',['构件','节点']),
    ('MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE',['构件','节点','参与']),
])
def test_known_check_explanations_keep_meaning_without_raw_reference(context,workspace_page,code,words):
    """Break: stripping raw issue text also erases the known engineering explanation."""
    page,_=open_core(context,workspace_page)
    text=page.evaluate("""async code=>{
      const {presentModelCheckIssue}=await import('/static/projects/workspace/workflow.js');
      const view=presentModelCheckIssue({code,human_message:'private-client-key'});return view.title+' '+view.explanation;
    }""",code)
    assert 'private-client-key' not in text and code not in text
    assert all(word in text for word in words)


def test_public_unattached_check_names_exact_object_safely(context,workspace_page):
    """Break: ungrouped issues lose their object identity when raw messages are removed."""
    def change(draft):
        draft['nodes'].append(dict(client_key='node-4',x_mm=2000,y_mm=500,label=''))
        draft['supports'][0].update(client_key='support-4',target_node_client_key='node-4')
    page,_,response=open_check(context,workspace_page,change)
    assert 'UNATTACHED_SUPPORT_NODE' in [i['code'] for i in response['issues']]
    card=page.locator('.ux-check-issue').filter(has_text='支座 S4')
    expect(card).to_have_count(1)
    expect(card).to_contain_text('构件')
    assert 'support-4' not in card.text_content()
