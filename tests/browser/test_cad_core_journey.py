"""Public-control integration and test-only browser evidence for Package 1."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.application.test_physical_draft import context
from tests.browser.test_cad_core_drawing import open_core,client_point,move_world

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]
EVIDENCE=Path('.superpowers/sdd/2026-10-01-cad-core-drawing-v1/screenshots')


def save_reload(page):
    with page.expect_response('**/model/save/') as response:
        page.locator('#workspace-save').click()
    assert response.value.ok
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    return page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")


def member(page,start,end):
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page,*start,click=True);move_world(page,*end,click=True)


def test_core_student_blank_member_to_analysis_journey(context,workspace_page):
    from projects.models import Project
    from modeling.services import save_physical_draft
    owner,legacy,material,section=context
    complete=Project.objects.create(event=legacy.event,owner_user=owner,name='Complete core triangle')
    save_physical_draft(actor=owner,project=complete,payload={
        'schema_version':'physical-draft-v2','expected_draft_version':0,
        'nodes':[{'client_key':k,'x_mm':x,'y_mm':y,'label':''} for k,x,y in [('a',0,0),('b',1000,0),('c',500,500)]],
        'physical_members':[{'client_key':k,'start_node_client_key':a,'end_node_client_key':b,'material_id':material.pk,'section_id':section.pk,'label':'','is_active':True} for k,a,b in [('base','a','b'),('left','a','c'),('right','b','c')]],
        'member_joint_incidences':[],'supports':[],'node_loads':[],
    })
    page,project=open_core(context,workspace_page)
    page.on('dialog',lambda dialog:dialog.accept())
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    member(page,(200,-100),(500,-100))
    first_keys=page.locator('[data-object-kind="GeometryNode"]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.clientKey)')
    assert len(first_keys)==2
    assert page.locator('[data-workspace-tool="MEMBER"]').get_attribute('aria-pressed')=='true'
    member(page,(200,-100),(350,-250))
    member(page,(350,-50),(350,-150))
    assert page.locator('[data-object-kind="GeometryNode"]').count()==5
    page.locator('[data-workspace-tool="NODE"]').click();move_world(page,350,-100)
    assert page.locator('[data-cad-snap-marker]').get_attribute('data-snap-type')=='INT'
    assert page.locator('[data-object-kind="GeometryNode"]').count()==5
    move_world(page,350,-100,click=True)
    assert page.locator('[data-object-kind="GeometryNode"]').count()==6
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.locator('[data-cad-ortho]').click();move_world(page,200,-100,click=True)
    move_world(page,250,-10)
    page.locator('[data-cad-dynamic-length]').fill('40.5')
    page.locator('[data-cad-dynamic-angle]').fill('30.25')
    page.locator('[data-cad-dynamic-angle]').press('Enter')
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==4
    move_world(page,350,-250,click=True);move_world(page,260,-180)
    before=page.locator('[data-world-layer]').get_attribute('transform')
    page.mouse.wheel(0,-100)
    page.wait_for_function("before=>document.querySelector('[data-world-layer]').getAttribute('transform')!==before",arg=before)
    p=client_point(page,260,-180);page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle');page.mouse.move(p['x']+20,p['y']+10);page.mouse.up(button='middle')
    move_world(page,250,-250,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==5
    saved=save_reload(page)
    assert saved['schema_version']=='physical-draft-v2' and 'connections' not in saved
    assert saved['physical_members'][0]['start_node_client_key']==first_keys[0]
    assert saved['physical_members'][0]['end_node_client_key']==first_keys[1]
    assert len(saved['member_joint_incidences'])==2
    assert not errors,errors

    # An independently complete triangle exercises the real Analyze chain.
    page.goto(page.url.split('/projects/')[0]+f'/projects/{complete.pk}/workspace/')
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    assert page.locator('[data-cad-dynamic-overlay]').is_hidden()
    move_world(page,0,0,click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click();move_world(page,1000,0,click=True)
    page.locator('[data-workspace-tool="LOAD"]').click();move_world(page,500,500,click=True)
    assert page.locator('[data-cad-dynamic-overlay]').is_hidden()
    page.locator('[data-property-fy]').fill('-20');page.locator('[data-property-fy]').press('Tab')
    saved=save_reload(page)
    assert len(saved['supports'])==2 and saved['node_loads'][0]['fy_N']==-20
    page.locator('[data-ux-stage-target="check"]').click()
    with page.expect_response('**/model/check/') as check:
        page.locator('#workspace-model-check').click()
    assert check.value.json()['ok'] is True
    assert '模型检查通过' in page.locator('#workspace-check-issues').inner_text()
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as analyzed:
        page.locator('#workspace-analyze').click()
    assert analyzed.value.json()['ok'] is True
    page.wait_for_function("document.querySelector('#workspace-run-select').value !== ''")
    page.wait_for_function("document.querySelector('#workspace-root').dataset.uxStage === 'understanding'")
    with ThreadPoolExecutor() as pool:
        assert pool.submit(lambda:complete.analysis_runs.get().status).result()=='SUCCESS'
        before_counts=pool.submit(lambda:(complete.model_revisions.count(),complete.analysis_runs.count())).result()
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="SELECT"]').click();move_world(page,1000,0,click=True)
    page.locator('#workspace-canvas').focus();page.keyboard.press('Delete')
    page.get_by_role('dialog',name='删除会影响其他物件').get_by_role('button',name='保留并重新指定',exact=True).click()
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2
    incomplete=save_reload(page)
    assert any(m['end_node_client_key'] is None for m in incomplete['physical_members'])
    page.locator('[data-ux-stage-target="analyze"]').click()
    with page.expect_response('**/analyze/') as blocked:
        page.locator('#workspace-analyze').click()
    assert blocked.value.json()['ok'] is False
    with ThreadPoolExecutor() as pool:
        assert pool.submit(lambda:(complete.model_revisions.count(),complete.analysis_runs.count())).result()==before_counts
    assert not errors,errors


def test_core_selection_support_load_history_compatibility(context,workspace_page):
    page,_=open_core(context,workspace_page,[('a',0,0),('b',100,0)],[('m','a','b')])
    page.on('dialog',lambda dialog:dialog.accept())
    page.locator('[data-workspace-tool="SELECT"]').click()
    move_world(page,0,0,click=True)
    page.keyboard.down('Shift');move_world(page,100,0,click=True);page.keyboard.up('Shift')
    assert page.locator('[data-object-kind="GeometryNode"][data-selected="true"]').count()==2
    page.locator('#workspace-canvas').focus();page.keyboard.press('Backspace')
    page.get_by_role('dialog',name='删除会影响其他物件').get_by_role('button',name='保留并重新指定',exact=True).click()
    assert page.locator('[data-object-kind="GeometryNode"]').count()==0
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==0 # incomplete, not deleted
    page.locator('[data-cad-undo]').click()
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2
    assert page.locator('[data-object-kind="PhysicalMember"]').count()==1
    page.locator('[data-cad-redo]').click();page.locator('[data-cad-undo]').click()
    # Two-click WINDOW encloses endpoints; CROSSING includes a touched body.
    move_world(page,-20,30,click=True);move_world(page,120,-30,click=True)
    assert page.locator('[data-object-kind][data-selected="true"]').count()==3
    move_world(page,80,20,click=True);move_world(page,20,-20,click=True)
    assert page.locator('[data-object-kind="PhysicalMember"][data-selected="true"]').count()==1
    assert page.locator('[data-object-kind="GeometryNode"][data-selected="true"]').count()==0
    # Partial left-to-right drag must NOT contain/select the whole member.
    start=client_point(page,20,20);end=client_point(page,80,-20)
    page.mouse.move(start['x'],start['y']);page.mouse.down();page.mouse.move(end['x'],end['y']);page.mouse.up()
    assert page.locator('[data-object-kind][data-selected="true"]').count()==0
    move_world(page,0,0,click=True)
    grip=page.locator('[data-cad-node-grip="a"]').bounding_box()
    destination=client_point(page,0,20)
    page.mouse.move(grip['x']+grip['width']/2,grip['y']+grip['height']/2);page.mouse.down();page.mouse.move(destination['x'],destination['y']);page.mouse.up()
    assert float(page.locator('[data-client-key="m"] line').get_attribute('y1'))==20
    grip=page.locator('[data-cad-node-grip="a"]').bounding_box();destination=client_point(page,100,0)
    page.mouse.move(grip['x']+grip['width']/2,grip['y']+grip['height']/2);page.mouse.down();page.mouse.move(destination['x'],destination['y']);page.mouse.up()
    assert float(page.locator('[data-client-key="m"] line').get_attribute('y1'))==20
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2
    field=page.locator('[data-property-x]')
    field.focus();page.keyboard.press('Backspace')
    assert page.locator('[data-object-kind="GeometryNode"]').count()==2


def test_core_browser_visual_evidence(context,workspace_page):
    page,_=open_core(context,workspace_page,[('a',-100,0),('b',100,0),('c',0,-100),('d',0,100)],[('h','a','b'),('v','c','d')])
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    page.set_viewport_size({'width':1440,'height':900})
    page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="NODE"]').click();move_world(page,-100,0)
    page.screenshot(path=str(EVIDENCE/'node-marker.png'))
    move_world(page,0,0);page.screenshot(path=str(EVIDENCE/'int-marker.png'))
    page.locator('[data-workspace-tool="MEMBER"]').click();move_world(page,-50,-50,click=True);move_world(page,50,-50)
    page.screenshot(path=str(EVIDENCE/'blank-member-preview.png'))
    page.locator('[data-cad-ortho]').click();move_world(page,50,-10)
    page.screenshot(path=str(EVIDENCE/'ortho-snap-status.png'))
    p=client_point(page,50,-10);page.mouse.move(p['x'],p['y']);page.mouse.down(button='middle');page.mouse.move(p['x']+30,p['y']+20);page.mouse.up(button='middle')
    page.screenshot(path=str(EVIDENCE/'middle-pan-preview.png'))
    page.keyboard.press('Escape');page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    for _ in range(10):
        page.locator('[data-cad-zoom-in]').click()
    move_world(page,3,3);page.screenshot(path=str(EVIDENCE/'near-grid.png'))
    assert 'minor' in page.locator('[data-canvas-grid]').get_attribute('data-grid-visible-levels')
    for _ in range(8):
        page.locator('[data-cad-zoom-out]').click()
    move_world(page,20,20);page.screenshot(path=str(EVIDENCE/'mid-grid.png'))
    for _ in range(12):
        page.locator('[data-cad-zoom-out]').click()
    move_world(page,20,20);page.screenshot(path=str(EVIDENCE/'far-grid.png'))
    page.set_viewport_size({'width':1024,'height':768});page.locator('[data-cad-fit]').click();move_world(page,20,20)
    page.screenshot(path=str(EVIDENCE/'offset-responsive.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
