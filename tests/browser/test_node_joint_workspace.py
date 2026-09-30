import pytest
from pathlib import Path

from tests.application.test_physical_draft import context


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_v2_workspace_renders_node_targets_without_connection_tool(context, workspace_page):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project

    owner, project, material, section = context
    v2_project(project)
    save_physical_draft(actor=owner, project=project, payload=v2_payload(material, section))
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-object-kind="Connection"]').count() == 0
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
    assert page.locator('[data-object-kind="Support"]').count() == 1
    assert page.locator('[data-object-kind="NodeLoad"]').count() == 1
    page.locator('[data-draft-object-kind="SUPPORT"][data-draft-object-key="s1"]').click()
    assert page.locator('[data-property-support-target]').input_value() == 'n1'
    page.locator('[data-draft-object-kind="NODE_LOAD"][data-draft-object-key="l1"]').click()
    assert page.locator('[data-property-load-target]').input_value() == 'n2'
    evidence = Path(__file__).resolve().parents[2] / '.superpowers/sdd/2026-09-29-node-as-joint-architecture/screenshots'
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(evidence / 'v2-node-support-load.png'))


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_node_joint_editor_authors_crossing_incidence_and_keeps_independent_delete(context, workspace_page):
    owner, project, _, _ = context
    project.draft_schema_version = "physical-draft-v2"
    project.save(update_fields=["draft_schema_version"])
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {applyEditorAction}=await import('/static/projects/workspace/editor.js');
      const node=(key,x,y)=>({client_key:key,x_mm:x,y_mm:y,label:''});
      const member=(key,a,b)=>({client_key:key,start_node_client_key:a,end_node_client_key:b,material_id:null,section_id:null,label:'',is_active:true});
      let draft={schema_version:'physical-draft-v2',version:0,nodes:[node('a',0,0),node('b',100,0),node('c',50,-50),node('d',50,50)],physical_members:[member('horizontal','a','b'),member('vertical','c','d')],member_joint_incidences:[],supports:[],node_loads:[]};
      const crossing=applyEditorAction(draft,{type:'PLACE_JOINT_NODE',node:node('joint',50,0)});
      const before=JSON.stringify(crossing.member_joint_incidences);
      const supported=applyEditorAction(crossing,{type:'CREATE_SUPPORT_AT_NODE',nodeClientKey:'joint',support:{client_key:'s1',support_type:'PINNED',restrained_axis:null}});
      const loaded=applyEditorAction(supported,{type:'CREATE_NODE_LOAD_AT_NODE',nodeClientKey:'joint',nodeLoad:{client_key:'l1',fx_N:0,fy_N:-10,label:''}});
      const deleted=applyEditorAction(loaded,{type:'DELETE_OBJECTS',targets:[{kind:'GEOMETRY_NODE',clientKey:'joint'}]});
      return {before, support:loaded.supports[0], load:loaded.node_loads[0], deleted:{nodes:deleted.nodes.length,members:deleted.physical_members.length,incidences:deleted.member_joint_incidences.length,support:deleted.supports[0].target_node_client_key,load:deleted.node_loads[0].target_node_client_key}, connectionMarkup:document.querySelector('[data-object-kind="Connection"]')?.outerHTML || null};
    }""")
    assert result["before"] == '[{"member_client_key":"horizontal","node_client_key":"joint"},{"member_client_key":"vertical","node_client_key":"joint"}]'
    assert result["support"]["target_node_client_key"] == "joint"
    assert result["load"]["target_node_client_key"] == "joint"
    assert result["deleted"] == {"nodes": 4, "members": 2, "incidences": 0, "support": None, "load": None}
    assert result["connectionMarkup"] is None


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_v2_endpoint_edit_preserves_valid_incidences_and_rejects_invalid_rebind(context, workspace_page):
    owner, project, _, _ = context
    project.draft_schema_version = "physical-draft-v2"
    project.save(update_fields=["draft_schema_version"])
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {applyEditorAction}=await import('/static/projects/workspace/editor.js');
      const node=(key,x,y)=>({client_key:key,x_mm:x,y_mm:y,label:''});
      const draft={schema_version:'physical-draft-v2',version:0,nodes:[node('a',0,0),node('mid',50,0),node('b',100,0),node('c',80,0),node('off',150,50)],physical_members:[{client_key:'m',start_node_client_key:'a',end_node_client_key:'b',material_id:null,section_id:null,label:'',is_active:true}],member_joint_incidences:[{member_client_key:'m',node_client_key:'mid'}],supports:[],node_loads:[]};
      const action=(key)=>({type:'UPDATE_OBJECT',target:{kind:'PHYSICAL_MEMBER',clientKey:'m'},changes:{end_node_client_key:key}});
      let invalidCode=null;try{applyEditorAction(draft,action('off'));}catch(error){invalidCode=error.code;}
      const valid=applyEditorAction(draft,action('c'));
      return {invalidCode,incidences:valid.member_joint_incidences};
    }""")
    assert result["invalidCode"] == "EDITOR_INVALID_TOPOLOGY"
    assert result["incidences"] == [{"member_client_key": "m", "node_client_key": "mid"}]


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_numeric_node_placement_previews_affected_member_before_second_enter(context, workspace_page):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project

    owner, project, material, section = context
    v2_project(project)
    save_physical_draft(actor=owner, project=project, payload=v2_payload(material, section))
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="NODE"]').click()
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('500,0')
    command.press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2
    assert 'm1' in page.locator('[data-modeling-instruction]').text_content()
    command.press('Enter')
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 3


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("numeric", [False, True])
def test_member_endpoint_on_existing_member_previews_new_joint_before_commit(context, workspace_page, numeric):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].append({"client_key": "start", "x_mm": 500.0, "y_mm": 100.0, "label": ""})
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-object-kind="GeometryNode"][data-client-key="start"]').click(force=True)
    if numeric:
        page.locator('.ux-precision summary').click()
        command = page.locator('[data-cad-command-input]')
        command.fill('500,0')
        command.press('Enter')
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
        assert 'm1' in page.locator('[data-modeling-instruction]').text_content()
        command.press('Enter')
    else:
        point = page.evaluate("""() => { const matrix=document.querySelector('[data-world-layer]').getScreenCTM(); const point=new DOMPoint(500,0).matrixTransform(matrix); return {x:point.x,y:point.y}; }""")
        page.mouse.move(point['x'], point['y'])
        assert 'm1' in page.locator('[data-modeling-instruction]').text_content()
        assert page.locator('[data-object-kind="PhysicalMember"]').count() == 1
        page.mouse.click(point['x'], point['y'])
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 2
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    draft = page.evaluate("""() => JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft""")
    candidates = [node for node in draft['nodes'] if abs(node['x_mm'] - 500) < 1e-6 and abs(node['y_mm']) < 1e-6]
    assert candidates, draft['nodes']
    new_joint = candidates[0]
    assert {'member_client_key': 'm1', 'node_client_key': new_joint['client_key']} in draft['member_joint_incidences']


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_numeric_near_existing_endpoint_reuses_identity_without_false_new_joint_preview(context, workspace_page):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project

    owner, project, material, section = context
    v2_project(project)
    payload = v2_payload(material, section)
    payload["nodes"].extend([
        {"client_key": "mid", "x_mm": 500.0, "y_mm": 0.0, "label": ""},
        {"client_key": "start", "x_mm": 500.0, "y_mm": 100.0, "label": ""},
    ])
    payload["member_joint_incidences"] = [{"member_client_key": "m1", "node_client_key": "mid"}]
    save_physical_draft(actor=owner, project=project, payload=payload)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-object-kind="GeometryNode"][data-client-key="start"]').click(force=True)
    page.locator('.ux-precision summary').click()
    command = page.locator('[data-cad-command-input]')
    command.fill('500.0000000005,0')
    command.press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 2
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 4


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("member_count", [2, 3])
def test_real_pointer_crossing_click_persists_explicit_incidences(context, workspace_page, member_count):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_project

    owner, project, material, section = context
    v2_project(project)
    draft = {
        "schema_version": "physical-draft-v2", "expected_draft_version": 0,
        "nodes": [{"client_key": key, "x_mm": x, "y_mm": y, "label": ""} for key, x, y in [("a", -100, 0), ("b", 100, 0), ("c", 0, -100), ("d", 0, 100)] + ([("e", -100, -100), ("f", 100, 100)] if member_count == 3 else [])],
        "physical_members": [{"client_key": key, "start_node_client_key": first, "end_node_client_key": last, "material_id": material.pk, "section_id": section.pk, "label": "", "is_active": True} for key, first, last in [("horizontal", "a", "b"), ("vertical", "c", "d")] + ([("diagonal", "e", "f")] if member_count == 3 else [])],
        "member_joint_incidences": [], "supports": [], "node_loads": [],
    }
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    assert page.locator('[data-object-kind="Connection"]').count() == 0
    page.locator('[data-workspace-tool="NODE"]').click()
    point = page.evaluate("""() => { const matrix=document.querySelector('[data-world-layer]').getScreenCTM(); const point=new DOMPoint(0,0).matrixTransform(matrix); return {x:point.x,y:point.y}; }""")
    page.mouse.move(point["x"], point["y"])
    instruction = page.locator('[data-modeling-instruction]').text_content()
    assert f"{member_count} 条构件" in instruction
    assert "horizontal" in instruction and "vertical" in instruction
    if member_count == 3:
        assert "diagonal" in instruction
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2 * member_count
    page.mouse.click(point["x"], point["y"])
    assert page.locator('[data-object-kind="GeometryNode"]').count() == 2 * member_count + 1
    evidence = Path(__file__).resolve().parents[2] / '.superpowers/sdd/2026-09-29-node-as-joint-architecture/screenshots'
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(evidence / f'v2-{member_count}-member-joint.png'))
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    incidences = page.evaluate("""() => JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.member_joint_incidences""")
    assert {(row["member_client_key"], row["node_client_key"]) for row in incidences} == {(key, "node-1") for key in (["horizontal", "vertical", "diagonal"][:member_count])}


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_v2_prediction_browser_authoring_uses_nodes_not_connections(context, workspace_page):
    from modeling.services import save_physical_draft
    from tests.application.test_node_joint_draft import v2_payload, v2_project

    owner, project, material, section = context
    v2_project(project)
    save_physical_draft(actor=owner, project=project, payload=v2_payload(material, section))
    page = workspace_page(user=owner, project=project)
    result = page.evaluate("""async () => {
      const {createPredictionWorkspace}=await import('/static/projects/workspace/prediction.js');
      const {predictionCanvasSelection}=await import('/static/projects/workspace/state.js');
      const draft=JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft;
      const workspace=createPredictionWorkspace({urls:{current:'',create:'',completeTemplate:'/predictions/{prediction_id}/'},draft,
        get:async()=>({response:{ok:true},body:{state:'NONE'}}),
        post:async()=>({response:{ok:true},body:{ok:true,status:'DRAFT',prediction:{prediction_id:1}}})});
      await workspace.loadPrediction(); await workspace.startPrediction();
      workspace.selectMaximumDisplacement(predictionCanvasSelection({draft,selectedObject:{kind:'GEOMETRY_NODE',clientKey:'n2'}}));
      for (const selection of [{kind:'GEOMETRY_NODE',clientKey:'n1'},{kind:'PHYSICAL_MEMBER',clientKey:'m1'},{kind:'GEOMETRY_NODE',clientKey:'n2'}]) workspace.appendRepresentativePath(predictionCanvasSelection({draft,selectedObject:selection}));
      return workspace.predictionPayload();
    }""")
    assert result["schema_version"] == "prediction-v2"
    assert result["max_displacement_location"] == {"kind": "NODE", "node_client_key": "n2"}
    assert [item["kind"] for item in result["representative_load_path"]] == ["NODE", "PHYSICAL_MEMBER", "NODE"]
