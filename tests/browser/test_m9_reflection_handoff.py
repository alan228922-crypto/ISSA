"""Reflection navigation is read-only; asynchronous operations own their selection."""

import pytest
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import expect

from tests.browser.test_m9_run_context import context, m9_page, m9_run

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def db_read(callback):
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(callback).result()


@pytest.fixture
def active_m9_run(m9_run):
    from competitions.models import CompetitionEvent

    owner, project, run = m9_run
    CompetitionEvent.objects.filter(pk=project.event_id).update(status=CompetitionEvent.Status.ACTIVE)
    return owner, project, run


@pytest.fixture
def two_active_runs(active_m9_run):
    from analysis.orchestration import analyze_project

    owner, project, first = active_m9_run
    second = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=first.prediction_id)
    assert second.status == 'SUCCESS'
    return owner, project, first, second


def open_evidence(workspace_page, owner, project, run):
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.pk))
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    page.get_by_role('tab', name='为什么', exact=True).click()
    return page


def test_evidence_handoff_targets_same_run(m9_run, workspace_page):
    owner, project, run = m9_run
    page = open_evidence(workspace_page, owner, project, run)
    expect(page.locator('[data-evidence-reflect]')).to_have_count(1)
    page.locator('[data-evidence-reflect]').click()
    expect(page.locator('[data-ux-summary-target="reflection"]')).to_have_attribute('aria-selected', 'true')
    expect(page.locator('#workspace-reflection')).to_be_visible()
    expect(page.locator('#workspace-run-select')).to_have_value(str(run.pk))


def test_reflection_navigation_never_writes_or_fills_answers(m9_run, workspace_page):
    from learning.models import Reflection

    owner, project, run = m9_run
    page = open_evidence(workspace_page, owner, project, run)
    posts = []
    page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
    before = db_read(lambda: Reflection.objects.count())
    expect(page.locator('[data-evidence-reflect]')).to_have_count(1)
    page.locator('[data-evidence-reflect]').click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    assert page.locator('#workspace-reflection textarea').evaluate_all('(fields)=>fields.map(f=>f.value)') == ['', '', '']
    assert posts == []
    assert db_read(lambda: Reflection.objects.count()) == before


@pytest.mark.parametrize('role', ['MANAGER', 'DEVELOPER'])
def test_readonly_viewer_cannot_author_reflection(active_m9_run, workspace_page, role):
    from accounts.models import User
    from competitions.models import EventMembership
    from django.test import Client

    owner, project, run = active_m9_run
    client = Client()
    client.force_login(owner)
    assert client.get(f'/projects/{project.pk}/analyses/{run.pk}/data/').status_code == 200
    assert client.post(f'/projects/{project.pk}/analyses/{run.pk}/reflection/',
                       {'original_reasoning': '仅学生本人可见的草稿内容'}, content_type='application/json').status_code == 201
    viewer = User.objects.create_user('m9-' + role.lower(), role=role)
    if role == 'MANAGER':
        EventMembership.objects.create(user=viewer, event=project.event, membership_type=EventMembership.Type.MANAGER)
    page = open_evidence(workspace_page, viewer, project, run)
    expect(page.locator('[data-evidence-reflect]')).to_have_count(1)
    page.locator('[data-evidence-reflect]').click()
    expect(page.locator('#workspace-reflection button')).to_have_count(0)
    expect(page.locator('#workspace-reflection textarea:not(:disabled)')).to_have_count(0)
    expect(page.locator('#workspace-reflection')).not_to_contain_text('仅学生本人可见的草稿内容')


@pytest.mark.parametrize('operation', ['save', 'complete', 'load'])
@pytest.mark.parametrize('late_error', [False, True])
@pytest.mark.parametrize('aba', [False, True])
def test_reflection_aba_and_late_failure_are_selection_scoped(m9_page, operation, late_error, aba):
    observed = m9_page.evaluate("""async ({operation,late_error,aba})=>{
      const {createReflectionWorkspace}=await import('/static/projects/workspace/reflection.js');
      let release,reject; const calls=[],changes=[];
      const pending=(url)=>{calls.push(url);return new Promise((r,j)=>{release=r;reject=j})};
      const c=createReflectionWorkspace({urls:{reflectionTemplate:'/reflection/{run_id}/',reflectionCompleteTemplate:'/reflection/{run_id}/complete/'},
        request:pending,get:pending,onChange:body=>changes.push(body?.original_reasoning||null)});
      const ref=(id,text)=>({ok:true,analysis_run_id:id,status:'DRAFT',original_reasoning:text});
      c.useReflection(1,ref(1,'old A'),1);
      const work=operation==='save'?c.saveReflection({original_reasoning:'submitted A'}):operation==='complete'?c.completeReflection():c.loadReflection(1);
      for(let i=0;i<10&&!release;i++)await Promise.resolve();
      c.useReflection(2,ref(2,'B'),2);if(aba)c.useReflection(1,ref(1,'new A selection'),3);
      const before=changes.length;
      if(late_error)reject(new Error('old A error'));else release({response:{ok:true},body:ref(1,'late A')});
      let returned,error=false;try{returned=await work}catch{error=true}
      return {returned:returned??null,error,current:c.state().original_reasoning,newChanges:changes.length-before,calls};
    }""", {'operation': operation, 'late_error': late_error, 'aba': aba})
    assert observed['returned'] is None and observed['error'] is False
    assert observed['current'] == ('new A selection' if aba else 'B')
    assert observed['newChanges'] == 0
    assert observed['calls'] == ['/reflection/1/complete/' if operation == 'complete' else '/reflection/1/']


def test_same_run_save_and_complete_are_serialized(m9_page):
    observed = m9_page.evaluate("""async()=>{
      const {createReflectionWorkspace}=await import('/static/projects/workspace/reflection.js');
      let release;const calls=[];
      const response=status=>({response:{ok:true},body:{ok:true,analysis_run_id:1,status}});
      const c=createReflectionWorkspace({urls:{reflectionTemplate:'/reflection/{run_id}/',reflectionCompleteTemplate:'/reflection/{run_id}/complete/'},
        request:async url=>{calls.push(url);return url.endsWith('/complete/')?response('COMPLETED'):new Promise(r=>release=r)}});
      c.useReflection(1,null,1);const saving=c.saveReflection({original_reasoning:'my own thought'});const completing=c.completeReflection();
      for(let i=0;i<10&&!release;i++)await Promise.resolve();const before=[...calls];release(response('DRAFT'));
      await saving;await completing;return {before,after:calls,status:c.state().status};
    }""")
    assert observed['before'] == ['/reflection/1/']
    assert observed['after'] == ['/reflection/1/', '/reflection/1/complete/']
    assert observed['status'] == 'COMPLETED'


def test_partial_save_and_explicit_completion_keep_existing_contract(active_m9_run, workspace_page):
    from learning.models import Reflection

    owner, project, run = active_m9_run
    page = open_evidence(workspace_page, owner, project, run)
    expect(page.locator('[data-evidence-reflect]')).to_have_count(1)
    page.locator('[data-evidence-reflect]').click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    root = page.locator('#workspace-reflection')
    root.locator('[name="original_reasoning"]').fill('我先观察荷载和支座。')
    with page.expect_response('**/reflection/') as saved:
        root.get_by_role('button', name='保存草稿', exact=True).click()
    assert saved.value.status == 201, saved.value.text()[:1200]
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=run.pk).status) == 'DRAFT'
    root.locator('[name="unexpected_results"]').fill('两段轴力给了我新的观察依据。')
    root.locator('[name="next_iteration_intent"]').fill('下一次我想自己观察节点位移。')
    with page.expect_response('**/reflection/'):
        root.get_by_role('button', name='保存草稿', exact=True).click()
    with page.expect_response('**/reflection/complete/') as completed:
        root.get_by_role('button', name='完成反思', exact=True).click()
    assert completed.value.status == 200
    expect(root.locator('textarea:not(:disabled)')).to_have_count(0)
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=run.pk).next_iteration_intent) == '下一次我想自己观察节点位移。'


def test_unsaved_reflection_text_does_not_cross_public_run_selection(two_active_runs, workspace_page):
    from learning.models import Reflection

    owner, project, first, second = two_active_runs
    page = open_evidence(workspace_page, owner, project, first)
    page.locator('[data-evidence-reflect]').click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    page.locator('#workspace-reflection [name="original_reasoning"]').fill('unsaved A only')
    page.locator('#workspace-run-select').select_option(str(second.pk))
    expect(page.locator('#workspace-reflection')).to_contain_text('不会带入')
    page.get_by_role('button', name='开始反思', exact=True).click()
    assert page.locator('#workspace-reflection textarea').evaluate_all('(fields)=>fields.map(f=>f.value)') == ['', '', '']
    assert db_read(lambda: Reflection.objects.filter(analysis_run__project=project).count()) == 0


def test_real_pending_save_finishes_on_a_without_replacing_b(two_active_runs, workspace_page):
    from learning.models import Reflection

    owner, project, first, second = two_active_runs
    page = open_evidence(workspace_page, owner, project, first)
    page.locator('[data-evidence-reflect]').click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    page.locator('#workspace-reflection [name="original_reasoning"]').fill('explicit saved A only')
    held = []
    target = f'**/analyses/{first.pk}/reflection/'
    page.route(target, lambda route: held.append(route) if route.request.method == 'POST' else route.continue_())
    with page.expect_request(lambda request: request.method == 'POST' and request.url.endswith(f'/analyses/{first.pk}/reflection/')):
        page.get_by_role('button', name='保存草稿', exact=True).click()
    page.locator('#workspace-run-select').select_option(str(second.pk))
    expect(page.get_by_role('button', name='开始反思', exact=True)).to_be_visible()
    page.get_by_role('button', name='开始反思', exact=True).click()
    page.locator('#workspace-reflection [name="original_reasoning"]').fill('B local text')
    with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/analyses/{first.pk}/reflection/')) as response:
        held[0].continue_()
    assert response.value.status == 201
    expect(page.locator('#workspace-reflection [name="original_reasoning"]')).to_have_value('B local text')
    assert db_read(lambda: Reflection.objects.get(analysis_run_id=first.pk).original_reasoning) == 'explicit saved A only'
    assert db_read(lambda: Reflection.objects.filter(analysis_run_id=second.pk).count()) == 0
