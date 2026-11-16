"""Task7: real public Saved Runs; controlled transport barriers are explicitly separate."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.endpoints.test_analysis_visualization import saved_context, frozen_artifacts
from tests.browser.test_m9_public_teaching_loop import public_page, draw_triangle, analyze, reflect
from tests.browser.test_m9_reflection_handoff import active_m9_run, two_active_runs, db_read
from tests.browser.test_m9_run_context import m9_page, m9_run
from tests.browser.av01_harness import projection_fixture
from tests.browser.test_av01_layers_evidence import choose_evidence, hit_object, clock_hover

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]
EVIDENCE=Path('.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots')


def ready_plot(page):
    expect(page.locator('[data-av01-root]')).to_have_attribute('data-av01-availability','READY')
    expect(page.locator('[data-av01-canvas]')).to_be_visible()
    # SVG horizontal/vertical lines have a zero-area bounding box in Playwright,
    # even when their stroke is painted. Check the visible surface and painted
    # extent; real viewport screenshots below provide the visual evidence.
    # Same visible-paint assertion, waiting for the actual post-reattach frame.
    page.wait_for_function('()=>{const el=document.querySelector(\'[data-av01-original-segment]\');if(!el)return false;const r=el.getBoundingClientRect();return (r.width>0||r.height>0)&&getComputedStyle(el).stroke!=="none"&&Number(el.getAttribute("stroke-width"))>0}')


def select_public(page,run_id):
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run_id))
    page.locator('[data-ux-stage-target="understanding"]').click()


def capture_public(page,name):
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    page.locator('[data-av01-canvas]').scroll_into_view_if_needed()
    page.screenshot(path=str(EVIDENCE/(name+'.png')),full_page=False)
    page.screenshot(path=str(EVIDENCE/(name+'-overview.png')),full_page=True)
    (EVIDENCE/(name+'.json')).write_text(json.dumps({'viewport':page.viewport_size,'url':page.url,'stage':'understanding','scope':'real authenticated public Results, genuine saved Run','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()},indent=2))


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_visualization_keeps_m9_navigation_and_reflection_contract(public_page,width,height):
    page,owner,project=public_page;page.set_viewport_size({'width':width,'height':height})
    draw_triangle(page);run=analyze(page);ready_plot(page)
    assert page.locator('[data-av01-original-segment]').count()==3
    assert page.locator('[data-av01-root] [data-cad-node-grip], [data-av01-root] input[type=text]').count()==0
    for name in ['结论','预测对比','为什么','技术数据']:
        expect(page.get_by_role('tab',name=name,exact=True)).to_have_count(1)
        page.get_by_role('tab',name=name,exact=True).click()
    page.get_by_role('tab',name='结论',exact=True).click();ready_plot(page)
    expect(page.locator('[data-av01-layer=forceStates]')).to_be_enabled()
    page.locator('[data-av01-layer=deformation]').check()
    page.get_by_role('button',name='适合视窗',exact=True).click()
    assert page.locator('[data-av01-deformed-segment]').count()==3
    assert '变形' in page.locator('[data-av01-scale]').text_content()
    choose_evidence(page,'ANALYSIS_SEGMENT','member-1:1')
    assert 'N' in page.locator('[data-av01-evidence]').inner_text()
    assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth')
    capture_public(page,f'task7-results-{width}x{height}')
    reflect(page,'Phase3：仍由学生保存这次分析的反思。')
    expect(page.locator('#workspace-run-select')).to_have_value(str(run))
    page.reload();select_public(page,run);ready_plot(page)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('[data-ux-summary-target="reflection"]').click()
    expect(page.locator('#workspace-reflection [name="next_iteration_intent"]')).to_have_value('Phase3：仍由学生保存这次分析的反思。')


def test_public_v1_v2_evidence_is_readonly_and_saved_run_bound(saved_context,workspace_page):
    owner,project,run,_,_=saved_context
    before=frozen_artifacts(run)
    page=workspace_page(user=owner,project=project);select_public(page,run.pk);ready_plot(page)
    choose_evidence(page,'SUPPORT','s1')
    expect(page.locator('[data-av01-evidence]')).to_contain_text('-100 N')
    page.locator('[data-av01-evidence] [data-av01-exact] summary').click()
    assert 'node:' not in page.locator('[data-av01-evidence]').inner_text()
    assert page.locator('[data-av01-object-list] button').count()==5
    assert db_read(lambda:frozen_artifacts(run))==before


@pytest.mark.parametrize('part',['comparison','explanation'])
def test_numeric_layers_survive_unavailable_teaching_facts(active_m9_run,workspace_page,part):
    owner,project,run=active_m9_run
    page=workspace_page(user=owner,project=project)
    page.route(f'**/analyses/{run.pk}/{part}/',lambda route:route.fulfill(status=503,json={'ok':False,'error':{'code':'INTERNAL_ERROR'}}))
    select_public(page,run.pk);ready_plot(page)
    expect(page.locator('[data-av01-layer=reactions]')).to_be_enabled()
    expect(page.locator('[data-av01-layer=loads]')).to_be_enabled()
    expect(page.locator('[data-av01-layer=forceStates]')).to_be_disabled()
    expect(page.locator('[data-av01-layer=deformation]')).to_be_disabled()
    assert page.locator('[data-av01-maximum]').count()==0
    assert page.locator('[data-av01-reaction]').count()>0


@pytest.mark.parametrize('field',['project_id','model_revision_id','model_hash','input_hash'])
def test_numeric_projection_must_match_the_independent_data_anchor(active_m9_run,workspace_page,field):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    def wrong(route):
        response=route.fetch();body=response.json();body['visualization']['provenance'][field]='f'*64 if field.endswith('hash') else 999999
        route.fulfill(response=response,json=body)
    page.route(f'**/analyses/{run.pk}/visualization/',wrong)
    select_public(page,run.pk)
    expect(page.locator('[data-av01-root]')).to_have_attribute('data-av01-availability','UNAVAILABLE')
    expect(page.locator('[data-av01-status]')).to_contain_text('暂不可用')
    assert not page.locator('[data-av01-original-segment]').count()
    expect(page.locator('[data-result-conclusion]')).to_be_visible()


def test_failed_initial_data_reveal_prohibits_visualization(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);requests=[]
    page.on('request',lambda r:requests.append(r.url) if r.url.endswith('/visualization/') else None)
    page.route(f'**/analyses/{run.pk}/data/',lambda r:r.fulfill(status=403,json={'ok':False,'error':{'code':'PROJECT_READ_DENIED'}}))
    select_public(page,run.pk)
    expect(page.locator('#workspace-error')).to_be_visible()
    assert requests==[] and not page.locator('[data-av01-original-segment]').count()


def test_optional_visualization_network_failure_keeps_m9_text_and_retries_same_run(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    pattern=f'**/analyses/{run.pk}/visualization/'
    page.route(pattern,lambda r:r.fulfill(status=503,json={'ok':False,'error':{'code':'INTERNAL_ERROR'}}))
    select_public(page,run.pk)
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    expect(page.locator('[data-av01-retry]')).to_be_visible()
    expect(page.locator('[data-av01-status]')).to_contain_text('重试')
    page.unroute(pattern);page.locator('[data-av01-retry]').click();ready_plot(page)
    expect(page.locator('#workspace-run-select')).to_have_value(str(run.pk))
    expect(page.locator('[data-result-conclusion]')).to_be_visible()


def test_denial_during_retry_clears_every_protected_result_surface(active_m9_run,workspace_page):
    from competitions.models import CompetitionEvent
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    pattern=f'**/analyses/{run.pk}/visualization/'
    page.route(pattern,lambda r:r.fulfill(status=503,json={'ok':False,'error':{'code':'INTERNAL_ERROR'}}))
    select_public(page,run.pk);expect(page.locator('[data-result-conclusion]')).to_be_visible();expect(page.locator('[data-av01-retry]')).to_be_visible()
    db_read(lambda:CompetitionEvent.objects.filter(pk=project.event_id).update(status='PURGED'))
    page.unroute(pattern);page.locator('[data-av01-retry]').click()
    expect(page.locator('[data-av01-status]')).to_contain_text('无权')
    assert not page.locator('[data-av01-original-segment],[data-teaching-member],[data-av01-object-list] button').count()
    assert not page.locator('#workspace-reflection textarea,[data-engineering-content] table,#workspace-report-view table').count()


def test_results_keyboard_context_menu_and_grips_cannot_mutate_workspace(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);select_public(page,run.pk);ready_plot(page)
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    svg=page.locator('[data-av01-canvas]');svg.focus()
    before=page.locator('#workspace-canvas').evaluate('(el)=>el.innerHTML');status=page.locator('#workspace-save-status').inner_text();posts=[]
    page.on('request',lambda r:posts.append(r.url) if r.method=='POST' else None)
    for command in ['CO','M','RO','ST','LEN']:
        page.keyboard.type(command);page.keyboard.press('Enter')
    for key in ['Escape','Shift','Space','Delete','Backspace']:page.keyboard.press(key)
    page.locator('[data-av01-layer=loads]').focus();was=page.locator('[data-av01-layer=loads]').is_checked();page.keyboard.press('Space')
    assert page.locator('[data-av01-layer=loads]').is_checked()!=was
    assert page.locator('[data-av01-layer=loads]').evaluate('(el)=>el===document.activeElement')
    svg.click(button='right')
    assert page.locator('[data-cad-context-menu]').count()==0
    assert not page.locator('[data-av01-root] [data-cad-node-grip]').count()
    assert page.locator('#workspace-canvas').evaluate('(el)=>el.innerHTML')==before
    assert page.locator('#workspace-save-status').inner_text()==status and posts==[]
    ids=page.locator('svg [id]').evaluate_all('(els)=>els.map(el=>el.id)');assert len(ids)==len(set(ids))
    assert page.locator('svg').count()>=2


@pytest.mark.parametrize('role',['MANAGER','DEVELOPER','GRACE'])
def test_readonly_roles_can_inspect_without_private_reflection(active_m9_run,workspace_page,role):
    from accounts.models import User
    from competitions.models import EventMembership
    from django.test import Client
    owner,project,run=active_m9_run;client=Client();client.force_login(owner)
    assert client.get(f'/projects/{project.pk}/analyses/{run.pk}/data/').status_code==200
    assert client.post(f'/projects/{project.pk}/analyses/{run.pk}/reflection/',{'original_reasoning':'学生私人草稿密文'},content_type='application/json').status_code==201
    if role=='GRACE':project.event.status='FINISHED_GRACE';project.event.save();viewer=owner
    else:
        viewer=User.objects.create_user('av01-'+role.lower(),role=role)
        if role=='MANAGER':EventMembership.objects.create(user=viewer,event=project.event,membership_type=EventMembership.Type.MANAGER)
    page=workspace_page(user=viewer,project=project);select_public(page,run.pk);ready_plot(page)
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    choose_evidence(page,'ANALYSIS_NODE',run.solver_input_json['nodes'][0]['id'])
    assert '原始 X' in page.locator('[data-av01-evidence]').inner_text()
    page.locator('[data-ux-stage-target="summary"]').click();page.locator('[data-ux-summary-target="reflection"]').click()
    assert page.locator('#workspace-reflection textarea:not(:disabled)').count()==0
    assert page.locator('#workspace-reflection').get_by_role('button',name='保存草稿',exact=True).count()==0
    assert page.locator('#workspace-reflection').get_by_role('button',name='完成反思',exact=True).count()==0
    if role!='GRACE':assert '学生私人草稿密文' not in page.locator('#workspace-reflection').inner_text()


def test_hidden_results_reopen_resize_and_hover_lifecycle(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);select_public(page,run.pk);ready_plot(page)
    page.locator('[data-av01-layer=deformation]').check();page.get_by_role('button',name='适合视窗',exact=True).click()
    alpha=page.locator('[data-av01-scale]').get_attribute('data-alpha')
    for size in [{'width':1024,'height':768},{'width':1440,'height':900},{'width':1280,'height':800}]:
        page.get_by_role('tab',name='为什么',exact=True).click();page.set_viewport_size(size)
        page.get_by_role('tab',name='结论',exact=True).click();ready_plot(page)
        assert page.locator('[data-av01-scale]').get_attribute('data-alpha')==alpha
        rect=page.locator('[data-av01-canvas]').bounding_box();assert rect['width']>200 and rect['height']>0
    # Use paused virtual time for preview lifecycle; data itself is a genuine saved Run.
    segment_id=run.solver_input_json['members'][0]['id'];clock_hover(page,'ANALYSIS_SEGMENT',segment_id);page.clock.run_for(400)
    expect(page.locator('[data-av01-hover]')).to_be_visible()
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(EVIDENCE/'task7-results-hover-1280x800.png'),full_page=False)
    (EVIDENCE/'task7-results-hover-1280x800.json').write_text(json.dumps({'viewport':page.viewport_size,'scope':'real public Results/genuine Saved Run; paused test clock for hover lifecycle','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()},indent=2))
    page.get_by_role('tab',name='技术数据',exact=True).click();assert not page.locator('[data-av01-hover]').is_visible()
    page.clock.run_for(1000);assert not page.locator('[data-av01-hover]').is_visible()


# Controlled transport barriers below exercise the actual run-context implementation,
# not fabricated public Solver evidence. The fake GET intentionally ignores abort
# so stale callback guards are tested even when transport cancellation is ineffective.
CONTEXT_SETUP=r'''async ({projection,defer=[],overrides={}})=>{
  const {createRunContext}=await import('/static/projects/workspace/run-context.js');
  const pending=new Map(),requests=[],events=[],selected=[];window.transport={pending,requests,events,selected,overrides};
  const ok=(body,status=200)=>({response:{ok:status>=200&&status<300,status},body:{ok:status>=200&&status<300,...body}});
  const runs=[11,12].map(id=>({analysis_run_id:id,status:'SUCCESS',model_revision_id:7,source_draft_version:2,is_stale:false}));
  const reply=(kind,id)=>{
    const override=overrides[kind+':'+id];if(override)return ok(override.body,override.status);
    const p=structuredClone(projection);p.provenance.analysis_run_id=id;
    if(kind==='data')return ok({analysis_run_id:id,model_revision_id:7,source_draft_version:2,model_hash:'a'.repeat(64),input_hash:'b'.repeat(64),input_schema_version:'truss2d-input-v1',result_schema_version:'truss2d-result-v1',status:'SUCCESS',failure_code:null,diagnostics:{},result_json:{schema_version:'truss2d-result-v1',node_displacements:[],support_reactions:[],member_results:[]}});
    if(kind==='visualization')return ok({visualization:p});
    if(kind==='comparison')return ok({comparison:{project_id:1,analysis_run_id:id,comparison_available:false,reason:'NO_PREDICTION'}});
    if(kind==='explanation')return ok({explanation:{project_id:1,analysis_run_id:id,explanation_available:false,blocks:[]}});
    if(kind==='report')return ok({report:{metadata:{project_id:1,analysis_run_id:id,model_revision_id:7,source_draft_version:2},geometry_connectivity:projection.label_source}});
    if(kind==='reflection')return ok({error:{code:'REFLECTION_NOT_FOUND'}},404);
    return ok({analysis_run_id:id});
  };
  const counts=new Map();
  const get=async url=>{
    requests.push(url);if(url==='/runs')return ok({runs});
    const [,kind,idString]=url.split('/'),id=Number(idString),key=kind+':'+id,count=(counts.get(key)||0)+1;counts.set(key,count);
    if(defer.includes(key+':'+count))return new Promise((resolve,reject)=>pending.set(key+':'+count,{resolve,reject,reply:()=>reply(kind,id)}));
    return reply(kind,id);
  };
  const urls={runs:'/runs',resultTemplate:'/data/{run_id}',comparisonTemplate:'/comparison/{run_id}',explanationTemplate:'/explanation/{run_id}',reportTemplate:'/report/{run_id}',reasoningTemplate:'/reasoning/{run_id}',reflectionTemplate:'/reflection/{run_id}',visualizationTemplate:'/visualization/{run_id}'};
  const c=createRunContext({projectId:1,urls,select:document.createElement('select'),get,onSelect:p=>selected.push(p?.metadata.analysis_run_id||null),onVisualization:event=>events.push(event)});
  window.transport.c=c;await c.refreshRuns();return {hasRetry:typeof c.retryVisualization==='function'};
}'''


def setup_context(page,**kwargs):
    result=page.evaluate(CONTEXT_SETUP,{'projection':projection_fixture(),**kwargs})
    assert result['hasRetry'],'Task7 visualization lifecycle/retry missing from existing run context'


def start_context(page,id=11):
    page.evaluate('(id)=>{transport.selection=transport.c.selectRun(id).catch(error=>{transport.error=error.code||String(error)})}',id)


def await_event(page,kind,run=11):
    page.wait_for_function('([kind,run])=>transport.events.some(e=>e.kind===kind&&e.runId===run)',arg=[kind,run],timeout=5000)


def test_optional_visualization_starts_after_data_without_waiting_for_teaching(m9_page):
    setup_context(m9_page,defer=['comparison:11:1']);start_context(m9_page);await_event(m9_page,'READY')
    observed=m9_page.evaluate('()=>({requests:transport.requests,selected:transport.selected,event:transport.events.find(e=>e.kind==="READY")})')
    assert observed['selected'][-1] is None
    assert observed['requests'].index('/data/11')<observed['requests'].index('/visualization/11')
    assert observed['event']['expectedContext']=={'projectId':1,'runId':11,'revisionId':7,'sourceDraftVersion':2,'modelHash':'a'*64,'inputHash':'b'*64,'inputSchemaVersion':'truss2d-input-v1','resultSchemaVersion':'truss2d-result-v1'}
    m9_page.evaluate('()=>{const p=transport.pending.get("comparison:11:1");p.resolve(p.reply())}')
    m9_page.evaluate('()=>transport.selection')


@pytest.mark.parametrize('aba',[False,True])
@pytest.mark.parametrize('late',['success','network','denial'])
def test_projection_late_success_error_and_aba_are_discarded(m9_page,aba,late):
    setup_context(m9_page,defer=['visualization:11:1']);start_context(m9_page)
    m9_page.wait_for_function('()=>transport.pending.has("visualization:11:1")')
    m9_page.evaluate('()=>transport.c.selectRun(12)');await_event(m9_page,'READY',12)
    if aba:m9_page.evaluate('()=>transport.c.selectRun(11)');m9_page.wait_for_function('()=>transport.events.some(e=>e.kind==="READY"&&e.runId===11)')
    before=m9_page.evaluate('()=>({events:transport.events.length,selected:transport.selected.length,token:transport.c.state().selectionToken})')
    m9_page.evaluate('''late=>{const p=transport.pending.get('visualization:11:1');if(late==='network')p.reject(new Error('old network'));else if(late==='denial')p.resolve({response:{ok:false,status:403},body:{ok:false,error:{code:'PROJECT_READ_DENIED'}}});else p.resolve(p.reply());}''',late)
    m9_page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    after=m9_page.evaluate('()=>({events:transport.events.length,selected:transport.selected.length,token:transport.c.state().selectionToken})')
    assert after==before


@pytest.mark.parametrize('denial',[False,True])
def test_same_run_retry_distinguishes_denial_and_network_error(m9_page,denial):
    setup_context(m9_page);start_context(m9_page);await_event(m9_page,'READY');m9_page.evaluate('()=>transport.selection')
    m9_page.evaluate('''denial=>{transport.overrides['visualization:11']={status:denial?403:503,body:{error:{code:denial?'PROJECT_READ_DENIED':'INTERNAL_ERROR'}}};return transport.c.retryVisualization()}''',denial)
    await_event(m9_page,'DENIED' if denial else 'ERROR')
    state=m9_page.evaluate('()=>({payload:transport.c.state().payload?.metadata.analysis_run_id||null,selected:transport.selected.at(-1),dataCalls:transport.requests.filter(x=>x==="/data/11").length})')
    assert state['dataCalls']==1
    if denial:assert state['payload'] is None and state['selected'] is None
    else:
        assert state['payload']==11
        m9_page.evaluate("()=>{delete transport.overrides['visualization:11'];return transport.c.retryVisualization()}")
        assert m9_page.evaluate('()=>transport.events.at(-1).kind')=='READY'


def test_late_initial_data_cannot_establish_an_old_anchor(m9_page):
    setup_context(m9_page,defer=['data:11:1']);start_context(m9_page)
    m9_page.wait_for_function('()=>transport.pending.has("data:11:1")')
    m9_page.evaluate('()=>transport.c.selectRun(12)');await_event(m9_page,'READY',12)
    m9_page.evaluate('()=>{const p=transport.pending.get("data:11:1");p.resolve(p.reply())}')
    m9_page.evaluate('()=>transport.selection')
    assert '/visualization/11' not in m9_page.evaluate('()=>transport.requests')
    assert m9_page.evaluate('()=>transport.events.filter(e=>e.kind==="READY").map(e=>e.runId)')==[12]


def test_required_access_denial_clears_an_already_ready_numeric_view(m9_page):
    setup_context(m9_page,defer=['comparison:11:1']);start_context(m9_page);await_event(m9_page,'READY')
    m9_page.evaluate('()=>transport.pending.get("comparison:11:1").resolve({response:{ok:false,status:403},body:{ok:false,error:{code:"PROJECT_READ_DENIED"}}})')
    m9_page.evaluate('()=>transport.selection');await_event(m9_page,'DENIED')
    assert m9_page.evaluate('()=>transport.selected.at(-1)') is None


def test_public_historical_plot_and_inspector_keep_a_after_changed_b(public_page):
    from tests.browser.test_cad_core_journey import save_reload
    page,_,project=public_page;draft=draw_triangle(page);first=analyze(page);ready_plot(page)
    base=page.url.split('/projects/')[0]+f'/projects/{project.pk}/analyses/'
    before=page.context.request.get(f'{base}{first}/visualization/').json()
    saved=before['visualization'];segment=saved['segments'][0]
    choose_evidence(page,'ANALYSIS_SEGMENT',segment['analysis_segment_id'])
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator(f'[data-draft-object-key="{draft["physical_members"][0]["client_key"]}"]').click()
    page.locator('[data-property-label]').fill('仅新草稿的构件描述');page.locator('[data-property-label]').press('Tab')
    page.locator(f'[data-draft-object-key="{draft["node_loads"][0]["client_key"]}"]').click()
    page.locator('[data-property-fy]').fill('-40');page.locator('[data-property-fy]').press('Tab');save_reload(page)
    second=analyze(page);ready_plot(page);assert second!=first
    select_public(page,first);ready_plot(page)
    assert '仅新草稿的构件描述' not in page.locator('[data-av01-root]').inner_text()
    choose_evidence(page,'ANALYSIS_SEGMENT',segment['analysis_segment_id'])
    panel=page.locator('[data-av01-evidence]');panel.locator('[data-av01-exact] summary').click()
    raw=panel.locator('[data-av01-exact] [data-av01-field=N] [data-av01-value]').inner_text()
    assert float(raw.split()[0])==segment['axial_force_N']
    assert page.context.request.get(f'{base}{first}/visualization/').json()==before
    select_public(page,second);ready_plot(page);select_public(page,first);ready_plot(page)
    assert not page.locator('[data-av01-object-list] [aria-pressed=true]').count()
    assert not page.locator('[data-av01-layer=deformation]').is_checked()


def test_results_keyboard_guard_preserves_existing_prediction_space_pan(active_m9_run,workspace_page):
    owner,project,_=active_m9_run;page=workspace_page(user=owner,project=project)
    page.locator('[data-ux-stage-target="prediction"]').click()
    canvas=page.locator('#workspace-canvas');canvas.focus();box=canvas.bounding_box()
    x=box['x']+box['width']/2;y=box['y']+box['height']/2
    before=canvas.locator('[data-world-layer]').get_attribute('transform');dirty=page.locator('#workspace-save-status').inner_text()
    page.keyboard.down('Space');page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y+20);page.mouse.up();page.keyboard.up('Space')
    assert canvas.locator('[data-world-layer]').get_attribute('transform')!=before
    assert page.locator('#workspace-save-status').inner_text()==dirty


def test_late_teaching_keeps_numeric_selection_layers_tab_and_keyboard_focus(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);held=[]
    pattern=f'**/analyses/{run.pk}/explanation/'
    page.route(pattern,lambda route:held.append((route,route.fetch())))
    with page.expect_request(pattern):select_public(page,run.pk)
    ready_plot(page)
    expect(page.locator('[data-av01-layer=deformation]')).to_be_disabled()
    page.locator('[data-av01-layer=reactions]').uncheck()
    first=run.solver_input_json['nodes'][0]['id'];choose_evidence(page,'ANALYSIS_NODE',first)
    page.get_by_role('tab',name='技术数据',exact=True).click()
    held[0][0].fulfill(response=held[0][1])
    expect(page.locator('[data-result-conclusion]')).to_have_count(1)
    expect(page.get_by_role('tab',name='技术数据',exact=True)).to_have_attribute('aria-selected','true')
    assert page.get_by_role('tab',name='技术数据',exact=True).evaluate('(el)=>el===document.activeElement')
    page.get_by_role('tab',name='结论',exact=True).click();ready_plot(page)
    assert not page.locator('[data-av01-layer=reactions]').is_checked()
    assert page.locator('[data-av01-object-list] [aria-pressed=true]').count()==1
    expect(page.locator('[data-av01-layer=deformation]')).to_be_enabled()


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_results_mount_uses_full_width_and_preserves_build_layout(active_m9_run,workspace_page,width,height):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    page.set_viewport_size({'width':width,'height':height})
    build_columns=page.locator('.workspace-layout').evaluate('(el)=>getComputedStyle(el).gridTemplateColumns')
    select_public(page,run.pk);ready_plot(page)
    panel=page.locator('#workspace-workflow-panel').bounding_box();layout=page.locator('.workspace-layout').bounding_box()
    assert abs(panel['width']-layout['width'])<4
    page.locator('[data-ux-stage-target="build"]').click()
    assert page.locator('.workspace-layout').evaluate('(el)=>getComputedStyle(el).gridTemplateColumns')==build_columns


def test_late_teaching_cannot_steal_results_control_focus_from_prior_draft_selection(active_m9_run,workspace_page):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click()
    held=[];pattern=f'**/analyses/{run.pk}/explanation/'
    page.route(pattern,lambda route:held.append((route,route.fetch())))
    with page.expect_request(pattern):select_public(page,run.pk)
    ready_plot(page);control=page.locator('[data-av01-layer=reactions]');control.focus()
    held[0][0].fulfill(response=held[0][1]);expect(page.locator('[data-result-conclusion]')).to_have_count(1)
    expect(control).to_be_focused()


@pytest.mark.parametrize('tab,dirty',[('结论',False),('预测对比',False),('为什么',False),('为什么',True)])
def test_teaching_member_links_select_visible_saved_evidence_without_draft_selection(active_m9_run,workspace_page,tab,dirty):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project)
    if dirty:
        page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click()
        page.locator('[data-property-label]').fill('仅当前草稿的描述');page.locator('[data-property-label]').press('Tab')
    select_public(page,run.pk);ready_plot(page)
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    before=page.locator('#workspace-canvas').inner_html();status=page.locator('#workspace-save-status').inner_text()
    page.get_by_role('tab',name=tab,exact=True).click()
    link=page.locator('[data-result-panel]:visible [data-teaching-member]').first
    expect(link).to_be_visible();link.click()
    expect(page.get_by_role('tab',name='结论',exact=True)).to_have_attribute('aria-selected','true')
    expect(page.locator('[data-av01-object-list] [aria-pressed=true]')).to_have_count(1)
    expect(page.locator('[data-av01-object-list] [aria-pressed=true]')).to_have_attribute('data-object-kind','ANALYSIS_SEGMENT')
    expect(page.locator('[data-av01-evidence]')).to_contain_text('N')
    expect(page.locator('[data-av01-canvas]')).to_be_focused()
    assert '仅当前草稿的描述' not in page.locator('[data-av01-evidence]').inner_text()
    assert page.locator('#workspace-canvas').inner_html()==before
    assert page.locator('#workspace-save-status').inner_text()==status


@pytest.mark.parametrize('focus',['tab','control'])
def test_late_http200_unavailable_teaching_preserves_results_tab_and_focus(active_m9_run,workspace_page,focus):
    owner,project,run=active_m9_run;page=workspace_page(user=owner,project=project);held=[]
    pattern=f'**/analyses/{run.pk}/explanation/'
    page.route(pattern,lambda route:held.append((route,route.fetch())))
    with page.expect_request(pattern):select_public(page,run.pk)
    ready_plot(page)
    target=page.get_by_role('tab',name='技术数据',exact=True) if focus=='tab' else page.locator('[data-av01-layer=reactions]')
    if focus=='tab':target.click()
    else:target.focus()
    route,response=held[0];body=response.json();body['explanation']['explanation_available']=False
    route.fulfill(response=response,json=body)
    expect(page.get_by_text('这次分析的证据暂不可用，请重新选择分析记录后重试。',exact=True)).to_be_visible()
    expect(target).to_be_focused()
    expect(page.get_by_role('tab',name='技术数据' if focus=='tab' else '结论',exact=True)).to_have_attribute('aria-selected','true')
    expect(page.locator('[data-av01-root]')).to_have_attribute('data-av01-availability','READY')
    expect(page.locator('[data-av01-layer=deformation]')).to_be_disabled()
