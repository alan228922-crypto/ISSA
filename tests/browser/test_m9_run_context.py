"""Focused presentation/race contracts; public end-to-end proof lives separately."""

from copy import deepcopy

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.endpoints.test_m9_run_contract import m9_run

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def sample_payload(*, state="ZERO_FORCE", comparison=True):
    """Hand-arranged immutable identities and server facts, not a numerical oracle."""
    segments = [
        {"analysis_member_id": "opaque:1", "axial_force_N": 0.00001, "teaching_state": state},
        {"analysis_member_id": "opaque:2", "axial_force_N": 0.00002, "teaching_state": state},
    ]
    member = {"type": "MEMBER_FORCE_STATE", "subject": {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "member-4"},
              "facts": {"actual_state": state, "segments": segments},
              "message_zh_CN": {"level_1": "该构件为近似零力构件。", "level_2": "近似零力不表示数学上严格等于 0。", "level_3": "对照各分析段真实轴力。"},
              "professional_values": {"segments": deepcopy(segments)}}
    maximum = {"type": "MAXIMUM_DISPLACEMENT", "subject": {"kind": "ANALYSIS_NODE_SET", "analysis_node_ids": ["node:node-2", "node:node-3"]},
               "facts": {"maximum_displacement_mm": 0.5, "tie_tolerance_mm": 1e-9, "candidate_analysis_node_ids": ["node:node-2", "node:node-3"]},
               "message_zh_CN": {"level_1": "最大位移出现在 node:node-2、node:node-3。", "level_2": "观察该位置和相邻构件的变形关系。", "level_3": "保留 ux、uy 与真实位移大小。"},
               "professional_values": {"maximum_displacement_mm": 0.5, "candidates": [
                   {"analysis_node_id": "node:node-2", "ux_mm": 0.3, "uy_mm": 0.4, "displacement_mm": 0.5},
                   {"analysis_node_id": "node:node-3", "ux_mm": -0.3, "uy_mm": 0.4, "displacement_mm": 0.5}]}}
    snapshot = {"nodes": [{"id": "node-2", "x_mm": 0, "y_mm": 0, "label": ""}, {"id": "node-3", "x_mm": 100, "y_mm": 0, "label": ""}],
                "physical_members": [{"id": "member-4", "start_node_id": "node-2", "end_node_id": "node-3", "label": "旧上弦杆"}],
                "member_joint_incidences": [], "analysis_member_mapping": {"opaque:1": "member-4", "opaque:2": "member-4"}}
    compared = {"schema_version": "comparison-v1", "project_id": 17, "analysis_run_id": 31, "comparison_available": comparison, "reason": None if comparison else "NO_PREDICTION"}
    if comparison:
        compared.update(prediction_id=5, source_draft_version=4, member_comparisons=[{
            "physical_member_client_key": "member-4", "predicted_state": "TENSION", "comparison_status": "MISMATCH",
            "actual": {"actual_state": state, "segments": deepcopy(segments)}}], maximum_displacement={
                **maximum["facts"], "predicted_point": {"kind": "NODE", "node_client_key": "node-2"}, "location_match": True}, load_path_evidence=[])
    return {"metadata": {"analysis_run_id": 31, "status": "SUCCESS", "model_revision_id": 7, "source_draft_version": 4, "is_stale": False}, "status": "SUCCESS",
            "data": {"ok": True, "analysis_run_id": 31, "model_revision_id": 7, "source_draft_version": 4, "status": "SUCCESS", "result_json": {
                "schema_version": "truss2d-result-v1", "member_results": [{"physical_member_id": "member-4", "analysis_member_id": "opaque:1", "state": "TENSION", "axial_force_N": 100}],
                "node_displacements": [{"analysis_node_id": "node:node-2", "ux_mm": 999, "uy_mm": 999}]}, "level_one": {"maximum_displacement": deepcopy(maximum["facts"])}},
            "comparison": compared,
            "explanation": {"schema_version": "explanation-v1", "explanation_available": True, "project_id": 17, "analysis_run_id": 31, "source_draft_version": 4,
                            "comparison_available": comparison, "comparison_reason": None if comparison else "NO_PREDICTION", "blocks": [member, maximum]},
            "report": {"ok": True, "report": {"metadata": {"project_id": 17, "analysis_run_id": 31, "model_revision_id": 7, "source_draft_version": 4},
                       "provenance": {"analysis_run_id": 31, "model_revision_id": 7, "source_draft_version": 4}, "geometry_connectivity": snapshot}},
            "reasoning": None, "reflection": None}


@pytest.fixture
def m9_page(context, workspace_page):
    return workspace_page(user=context[0], project=context[1])


def project_view(page, payload=None, *, dirty=False, version=4):
    return page.evaluate("""async ({payload,dirty,version}) => {
      const module = await import('/static/projects/workspace/teaching-view.js').catch(()=>null);
      if (!module) return {available:false, missingProjection:true};
      return module.buildTeachingView({payload,runNumber:1,workspace:{projectId:17,draftVersion:version,dirty}});
    }""", {"payload": payload or sample_payload(), "dirty": dirty, "version": version})


def test_selected_run_evidence_never_uses_current_draft(m9_page):
    """Break: old showLevelOne still requires current/raw result arguments."""
    result = m9_page.evaluate("""async () => {
      const {showLevelOne}=await import('/static/projects/workspace/results.js');
      return showLevelOne({runId:31,runLabel:'第 1 次分析',sourceDraftVersion:4,historical:false,canLinkCanvas:false,
        comparisonAvailable:true,members:[{key:'member-4',label:'旧上弦杆 · 构件 M4',actualState:'ZERO_FORCE',segments:[]}],
        displacement:{available:false}});
    }""")
    assert result["members"] == [{"physicalMemberClientKey": "member-4", "displayLabel": "旧上弦杆 · 构件 M4", "state": "ZERO_FORCE"}]
    assert result["overlay"] == {}


def test_product_selection_uses_real_run_package(m9_run, workspace_page):
    """Break: using a nonexistent bootstrap field rejects the actual served package."""
    owner, project, run = m9_run
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.pk))
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    expect(page.locator('[data-result-conclusion]')).to_contain_text('结论')
    expect(page.locator('[data-teaching-member]')).not_to_have_count(0)
    expect(page.locator('#workspace-canvas [data-result-state="TENSION"]')).not_to_have_count(0)


def test_dirty_product_keeps_evidence_but_disables_both_canvas_links(m9_run, workspace_page):
    """Break: a dirty same-version Draft is still described/linked as the analyzed model."""
    owner, project, run = m9_run
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.pk))
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    original = page.locator('[data-result-conclusion] button').first.inner_text()
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click()
    page.locator('[data-property-label]').fill('当前未保存的新描述')
    page.locator('[data-property-label]').press('Tab')
    page.locator('[data-ux-stage-target="understanding"]').click()
    expect(page.locator('[data-result-conclusion]')).to_contain_text('未保存')
    expect(page.locator('[data-result-conclusion] button').first).to_have_text(original)
    page.locator('[data-result-conclusion] button').first.click()
    expect(page.locator('[data-teaching-focused]')).to_have_count(0)
    expect(page.locator('#workspace-canvas [data-result-state]:not([data-result-state=""])')).to_have_count(0)


def test_dirty_provenance_remains_visible_in_explain_and_technical(m9_run, workspace_page):
    """R1: changing tabs must not claim old numerical evidence is current."""
    owner, project, run = m9_run
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(run.pk))
    page.locator('[data-ux-stage-target="understanding"]').click()
    page.get_by_role('tab', name='技术数据', exact=True).click()
    # Numeric-first Results can expose the tab before the M9 teaching chain finishes.
    # Compare the completed saved tables, never an intermediate empty placeholder.
    expect(page.locator('[data-engineering-content] table')).to_have_count(3)
    original_values = page.locator('[data-engineering-content] table').all_text_contents()
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click()
    page.locator('[data-property-label]').fill('Unsaved description, not historical identity')
    page.locator('[data-property-label]').press('Tab')
    page.locator('[data-ux-stage-target="understanding"]').click()
    page.get_by_role('tab', name='技术数据', exact=True).click()
    expect(page.locator('[data-engineering-content]')).not_to_contain_text('工程详情对应当前模型版本')
    expect(page.locator('[data-engineering-content]')).to_contain_text('不代表当前草稿')
    assert page.locator('[data-engineering-content] table').all_text_contents() == original_values
    page.get_by_role('tab', name='为什么', exact=True).click()
    page.get_by_text('查看具体数值与来源', exact=True).click()
    expect(page.locator('[data-teaching-level="3"]')).to_contain_text('历史证据，不代表当前草稿')
    expect(page.locator('[data-result-explanation]')).not_to_contain_text('Unsaved description')


@pytest.mark.parametrize('late_error', [False, True])
def test_workspace_ignores_obsolete_bootstrap_refresh(m9_run, workspace_page, late_error):
    """R2: the actual initial continuation must honor a null obsolete result."""
    owner, project, run = m9_run
    page = workspace_page(user=owner, project=project)
    # Finish the first document's discovery before intercepting a reload's
    # request; otherwise the held route can belong to the aborted document.
    expect(page.locator('#workspace-run-select option')).to_have_count(2)
    held = []
    page.route(f'**/projects/{project.pk}/analyses/', lambda route: held.append(route) if not held else route.continue_())
    page.reload()
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as response:
        page.locator('#workspace-analyze').click()
    assert response.value.status == 200
    new_run = response.value.json()['analysis_run_id']
    expect(page.locator('[data-result-conclusion]')).to_be_visible()
    if late_error:
        held[0].fulfill(status=500, json={'ok': False, 'error': {'code': 'INTERNAL_ERROR'}})
    else:
        with page.expect_response(lambda response: response.request.url.endswith(f'/projects/{project.pk}/analyses/')):
            held[0].continue_()
    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    expect(page.locator('#workspace-run-select')).to_have_value(str(new_run))
    expect(page.locator('#workspace-error')).not_to_be_visible()
    expect(page.locator('[data-result-conclusion]')).to_be_visible()


@pytest.mark.parametrize('operation', ['analyze', 'save'])
@pytest.mark.parametrize('late_error', [False, True])
def test_workspace_operation_completion_preserves_newer_run_selection(m9_run, workspace_page, operation, late_error):
    """R2: an explicitly selected B owns presentation after A's request starts."""
    from analysis.orchestration import analyze_project
    owner, project, first = m9_run
    second = analyze_project(project=project, actor=owner, expected_draft_version=1, prediction_id=first.prediction_id)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(first.pk))
    expect(page.locator('[data-result-conclusion] h2')).to_contain_text('第 1 次分析')
    path = 'analyze/' if operation == 'analyze' else 'model/save/'
    held = []
    page.route(f'**/projects/{project.pk}/{path}', lambda route: held.append(route))
    if operation == 'save':
        page.locator('[data-ux-stage-target="build"]').click()
        page.locator('[data-draft-object-kind="PHYSICAL_MEMBER"]').first.click()
        page.locator('[data-property-label]').fill('A save in progress')
        page.locator('[data-property-label]').press('Tab')
    else:
        page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_request(lambda request: request.method == 'POST' and request.url.endswith(f'/{path}')):
        page.locator('#workspace-analyze' if operation == 'analyze' else '#workspace-save').click()
    page.locator('[data-ux-stage-target="summary"]').click()
    page.locator('#workspace-run-select').select_option(str(second.pk))
    expect(page.locator('#workspace-run-select')).to_have_value(str(second.pk))
    expect(page.locator('[data-result-conclusion] h2')).to_contain_text('第 2 次分析')
    if late_error:
        held[0].fulfill(status=500, json={'ok': False, 'error': {'code': 'INTERNAL_ERROR'}})
    else:
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith(f'/{path}')) as response:
            held[0].continue_()
        assert response.value.status == 200
    if operation == 'save':
        # Completion and edit access are distinct: Results stays non-editable.
        page.wait_for_function("document.querySelector('#workspace-save').getAttribute('aria-busy') !== 'true'")
        expect(page.locator('#workspace-save')).to_be_disabled()
    else:
        page.wait_for_function("!document.querySelector('#workspace-analyze').disabled")
    expect(page.locator('#workspace-run-select')).to_have_value(str(second.pk))
    expect(page.locator('[data-ux-current-stage]')).to_have_text('当前：总结')
    expect(page.locator('#workspace-error')).not_to_be_visible()
    if operation == 'save':
        page.locator('[data-ux-stage-target="build"]').click()
        expect(page.locator('#workspace-save')).to_be_enabled()
        expect(page.locator('#workspace-run-select')).to_have_value(str(second.pk))


def test_historical_labels_use_selected_snapshot(m9_page):
    view = project_view(m9_page, version=9)
    assert view["members"][0]["label"] == "旧上弦杆 · 构件 M4"
    assert view["historical"] is True and view["canLinkCanvas"] is False


def test_server_classification_and_result_bytes_are_not_recomputed(m9_page):
    payload = sample_payload()
    before = deepcopy(payload)
    view = project_view(m9_page, payload)
    assert view["members"][0]["actualState"] == "ZERO_FORCE"  # raw result says TENSION
    assert payload == before
    payload["explanation"]["blocks"] = [payload["explanation"]["blocks"][1]]
    unavailable = project_view(m9_page, payload)
    assert unavailable["available"] is False  # no raw-state fallback


def test_unsaved_same_version_disables_result_linkage(m9_page):
    view = project_view(m9_page, dirty=True)
    assert view["canLinkCanvas"] is False
    assert view["members"][0]["actualState"] == "ZERO_FORCE"
    assert project_view(m9_page)["canLinkCanvas"] is True


@pytest.mark.parametrize("identity", ["__proto__", "constructor"])
def test_nonstandard_snapshot_identity_is_not_a_javascript_property(m9_page, identity):
    """Break: ordinary object prototypes are mistaken for immutable identity-map entries."""
    payload = sample_payload()
    snapshot = payload["report"]["report"]["geometry_connectivity"]
    snapshot["physical_members"][0]["id"] = identity
    snapshot["analysis_member_mapping"] = {"opaque:1": identity, "opaque:2": identity}
    payload["explanation"]["blocks"][0]["subject"]["physical_member_client_key"] = identity
    payload["data"]["result_json"]["member_results"][0]["physical_member_id"] = identity
    payload["comparison"]["member_comparisons"][0]["physical_member_client_key"] = identity
    view = project_view(m9_page, payload)
    assert view["available"] is True
    assert view["members"][0]["label"].startswith('旧上弦杆 · 构件 M·')
    assert identity not in view["members"][0]["label"]


@pytest.mark.parametrize("part", ["data", "comparison", "explanation", "report", "reflection"])
def test_inconsistent_run_provenance_is_unavailable(m9_page, part):
    payload = sample_payload()
    target = payload[part]
    if part == "report":
        target = target["report"]["metadata"]
    if part == "reflection":
        target = payload[part] = {"analysis_run_id": 99, "project_id": 17, "source_draft_version": 4, "status": "DRAFT"}
    target["analysis_run_id"] = 99
    view = project_view(m9_page, payload)
    assert view["available"] is False
    assert not view.get("members")


def test_run_switch_clears_all_derived_presentation(m9_page):
    observed = m9_page.evaluate("""async () => {
      const {createRunContext}=await import('/static/projects/workspace/run-context.js');
      const selection=document.createElement('select'); let resolve;
      const panels=['results','report','engineering','reflection','path'].map(()=>document.createElement('section'));
      const c=createRunContext({urls:{runs:'/runs'},select:selection,get:async()=>new Promise(r=>resolve=r),onSelect:()=>panels.forEach(p=>p.replaceChildren())});
      panels.forEach(p=>p.textContent='old evidence');
      const pending=c.refreshRuns(); await Promise.resolve();
      const cleared=panels.every(p=>p.textContent==='');
      resolve({response:{ok:true},body:{ok:true,runs:[]}}); await pending;
      return {cleared};
    }""")
    assert observed["cleared"] is True


def test_late_run_response_cannot_replace_new_selection(m9_page):
    observed = m9_page.evaluate("""async () => {
      const {createRunContext}=await import('/static/projects/workspace/run-context.js');
      const select=document.createElement('select'); let release; const selected=[];
      const urls={runs:'/runs',resultTemplate:'/data/{run_id}',comparisonTemplate:'/comparison/{run_id}',explanationTemplate:'/explanation/{run_id}',reportTemplate:'/report/{run_id}',reasoningTemplate:'/reasoning/{run_id}',reflectionTemplate:'/reflection/{run_id}'};
      const ok=body=>({response:{ok:true},body:{ok:true,...body}});
      const get=async url=>url==='/runs'?ok({runs:[{analysis_run_id:1,status:'SUCCESS'},{analysis_run_id:2,status:'SUCCESS'}]}):url==='/data/1'?new Promise(r=>release=r):ok({comparison:{},explanation:{}});
      const c=createRunContext({urls,select,get,onSelect:p=>{if(p)selected.push(p.metadata.analysis_run_id)}});
      await c.refreshRuns(); const a=c.selectRun(1); await Promise.resolve(); await c.selectRun(2);
      release(ok({})); await a;
      return {id:c.state().currentRunId,selected};
    }""")
    assert observed == {"id": 2, "selected": [2]}


@pytest.mark.parametrize("failure", [False, True])
def test_obsolete_refresh_and_error_leave_new_selection_intact(m9_page, failure):
    observed = m9_page.evaluate("""async failure => {
      const {createRunContext}=await import('/static/projects/workspace/run-context.js');
      const select=document.createElement('select'); let finish; let reject; let calls=0;
      const ok=body=>({response:{ok:true},body:{ok:true,...body}});
      const runs=[{analysis_run_id:1,status:'SOLVER_FAILED'},{analysis_run_id:2,status:'SOLVER_FAILED'}];
      const c=createRunContext({urls:{runs:'/runs'},select,get:async()=>++calls===1?ok({runs}):new Promise((r,j)=>{finish=r;reject=j})});
      await c.refreshRuns(); await c.selectRun(1); const pending=c.refreshRuns(); await Promise.resolve();
      await c.selectRun(2); if(failure)reject(new Error('old request'));else finish(ok({runs}));
      let error=false; try{await pending}catch{error=true}
      return {id:c.state().currentRunId,payload:c.state().payload?.metadata.analysis_run_id,error};
    }""", failure)
    assert observed == {"id": 2, "payload": 2, "error": False}
