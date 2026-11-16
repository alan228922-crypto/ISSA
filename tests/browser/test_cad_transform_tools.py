"""Public UI geometry transforms: no geometry/controller/model injection."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_core_drawing import move_world
from tests.browser.test_cad_core_journey import member,save_reload

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]
OUT=Path('.superpowers/sdd/2026-11-07-cad-ux03/browser')


def shot(p,name):
    OUT.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(OUT/(name+'.png')))
    s=p.evaluate('''()=>({viewport:{width:innerWidth,height:innerHeight},scroll:{x:scrollX,y:scrollY},focus:document.activeElement?.outerHTML?.slice(0,250),transform:document.querySelector('[data-world-layer]').getAttribute('transform')})''');s.update(nodes=p.locator('[data-object-kind="GeometryNode"]').count(),members=p.locator('[data-object-kind="PhysicalMember"]').count());(OUT/(name+'.json')).write_text(json.dumps(s,ensure_ascii=False,indent=2))


def select_members(p,points):
    p.locator('[data-workspace-tool="SELECT"]').click()
    for i,(x,y) in enumerate(points):
        if i:p.keyboard.down('Shift')
        move_world(p,x,y,click=True)
        if i:p.keyboard.up('Shift')


def apply_preview(p):
    p.locator('[data-transform-apply]').click()


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_copy_group_paste_repeat_undo_save(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height})
    member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250))
    select_members(p,[(300,-100),(400,-175)])
    p.locator('[data-cad-copy]').click();expect(p.locator('[data-transform-status]')).to_contain_text('不包含支座和荷载')
    p.locator('[data-cad-paste]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2)
    shot(p,f'paste-{width}-preview');apply_preview(p);expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(4)
    expect(p.locator('[data-object-kind="PhysicalMember"][data-selected="true"]')).to_have_count(2)
    p.locator('[data-cad-paste]').click();apply_preview(p);expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(6)
    p.locator('[data-cad-undo]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(4)
    p.locator('[data-cad-redo]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(6)
    saved=save_reload(p);assert len(saved['nodes'])==9 and len(saved['physical_members'])==6
    assert len({n['client_key'] for n in saved['nodes']})==9
    assert {(n['x_mm'],n['y_mm']) for n in saved['nodes']}=={(200,-100),(400,-100),(400,-250),(220,-80),(420,-80),(420,-230),(240,-60),(440,-60),(440,-210)}
    shot(p,f'paste-{width}-saved')


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_numeric_move_preview_cancel_and_identity(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));original=save_reload(p);before_points=p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])');select_members(p,[(300,-100)])
    expect(p.locator('[data-cad-move]')).to_be_enabled(timeout=1000);p.locator('[data-cad-move]').click();p.locator('[data-transform-dx]').fill('100.25');p.locator('[data-transform-dy]').fill('-50.5');p.locator('[data-transform-preview-button]').click();shot(p,f'move-{width}-preview')
    p.keyboard.press('Escape');expect(p.locator('[data-transform-panel]')).to_be_hidden();assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before_points;p.reload();assert p.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft.nodes")==original['nodes']
    select_members(p,[(300,-100)]);p.locator('[data-cad-move]').click();p.locator('[data-transform-dx]').fill('100.25');p.locator('[data-transform-dy]').fill('-50.5');p.locator('[data-transform-preview-button]').click();apply_preview(p)
    p.locator('[data-cad-undo]').click();assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before_points;p.locator('[data-cad-redo]').click();saved=save_reload(p)
    assert [(n['x_mm'],n['y_mm']) for n in saved['nodes']]==[(300.25,-150.5),(500.25,-150.5)];assert saved['physical_members']==original['physical_members'];assert [n['client_key'] for n in saved['nodes']]==[n['client_key'] for n in original['nodes']];shot(p,f'move-{width}-saved')


def test_move_shared_node_is_blocked(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250));select_members(p,[(300,-100)]);expect(p.locator('[data-cad-move]')).to_be_enabled(timeout=1000);p.locator('[data-cad-move]').click();expect(p.locator('[data-transform-status]')).to_contain_text('相邻');expect(p.locator('[data-transform-panel]')).to_be_hidden();shot(p,'move-shared-blocked')


def test_move_drag_attachment_notice_and_pan(public_page):
    from tests.browser.test_cad_core_drawing import client_point
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SUPPORT"]').click();move_world(p,200,-100,click=True);p.locator('[data-workspace-tool="LOAD"]').click();move_world(p,400,-100,click=True);p.locator('[data-property-fy]').fill('-20');p.locator('[data-property-fy]').press('Tab');original=save_reload(p)
    select_members(p,[(300,-100)]);expect(p.locator('[data-cad-move]')).to_be_enabled(timeout=1000);p.locator('[data-cad-move]').click();expect(p.locator('[data-transform-attachments]')).to_contain_text('支座 1，荷载 1');p.locator('[data-transform-ack]').check()
    a=client_point(p,300,-100);b=client_point(p,310.5,-120.25);p.mouse.move(a['x'],a['y']);p.mouse.down();p.mouse.move(b['x'],b['y'],steps=4);shot(p,'move-drag-preview');p.mouse.up();shot(p,'move-drag-committed');expect(p.locator('[data-transform-panel]')).to_be_hidden()
    saved=save_reload(p)
    for n,old in zip(saved['nodes'],original['nodes']):assert (n['x_mm'],n['y_mm'])==pytest.approx((old['x_mm']+10.5,old['y_mm']-20.25),abs=1e-5)  # Browser pointer/CTM round-trip, numeric command is tested at exact precision.
    assert saved['supports']==original['supports'] and saved['node_loads']==original['node_loads'];assert saved['physical_members']==original['physical_members']
    before=p.locator('[data-world-layer]').get_attribute('transform');p.mouse.move(500,500);p.mouse.down(button='middle');p.mouse.move(520,510);p.mouse.up(button='middle');assert p.locator('[data-world-layer]').get_attribute('transform')!=before


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_rotate_group_unique_centroid_cancel_and_save(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250));original=save_reload(p);select_members(p,[(300,-100),(400,-175)]);before=p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')
    expect(p.locator('[data-cad-rotate]')).to_be_enabled(timeout=1000);p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill('90');p.locator('[data-transform-preview-button]').click();shot(p,f'rotate-{width}-preview');assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before
    p.locator('[data-transform-cancel]').click();expect(p.locator('[data-transform-preview]')).to_have_count(0);p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill('90');p.locator('[data-transform-preview-button]').click();apply_preview(p);p.locator('[data-cad-undo]').click();assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before;p.locator('[data-cad-redo]').click();saved=save_reload(p)
    expected=[(850/3,-850/3),(850/3,-250/3),(1300/3,-250/3)]
    for n,point in zip(saved['nodes'],expected):assert (n['x_mm'],n['y_mm'])==pytest.approx(point,abs=1e-9)
    assert saved['physical_members']==original['physical_members'];assert [n['client_key'] for n in saved['nodes']]==[n['client_key'] for n in original['nodes']];shot(p,f'rotate-{width}-saved')


@pytest.mark.parametrize('angle,expected',[('-45',[(229.28932188134524,-29.28932188134526),(370.71067811865476,-170.71067811865476)]),('22.5',[(207.61204674887132,-138.26834323650897),(392.3879532511287,-61.73165676349102)])])
def test_rotate_negative_and_fractional(public_page,angle,expected):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);expect(p.locator('[data-cad-rotate]')).to_be_enabled(timeout=1000);p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill(angle);p.locator('[data-transform-preview-button]').click();apply_preview(p);saved=save_reload(p)
    for n,point in zip(saved['nodes'],expected):assert (n['x_mm'],n['y_mm'])==pytest.approx(point,abs=1e-9)


def test_keyboard_clipboard_scope_cancel_and_transform_pipeline(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    p.keyboard.press('Control+c');p.keyboard.press('Control+v');expect(p.locator('[data-transform-preview]')).to_have_count(1)
    p.keyboard.press('Escape');p.keyboard.press('Control+v');expect(p.locator('[data-transform-title]')).to_contain_text('20 mm');apply_preview(p)
    expect(p.locator('[data-object-kind="PhysicalMember"][data-selected="true"]')).to_have_count(1)
    p.locator('[data-cad-move]').click();p.locator('[data-transform-dx]').fill('100');p.locator('[data-transform-dy]').fill('-50');apply_preview(p)
    p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill('90')
    # Observe shortcut default without reading or replacing the OS clipboard.
    p.evaluate("""()=>{window.copyPrevented=[];document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&['c','v'].includes(e.key))window.copyPrevented.push(e.defaultPrevented)})}""")
    p.locator('[data-transform-angle]').focus();p.keyboard.press('Control+c');assert p.evaluate('window.copyPrevented')==[False]
    apply_preview(p);shot(p,'pipeline-rotate-applied');p.locator('[data-cad-copy]').click();p.locator('[data-cad-paste]').click();apply_preview(p)
    expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(3)
    for expected in [2,2,2,1]:p.locator('[data-cad-undo]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(expected)
    for expected in [2,2,2,3]:p.locator('[data-cad-redo]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(expected)
    saved=save_reload(p);assert len(saved['nodes'])==6;assert saved['supports']==saved['node_loads']==[]
    shot(p,'pipeline-saved')


def test_transform_invalid_values_acknowledgement_and_pointer_cancel(public_page):
    from tests.browser.test_cad_core_drawing import client_point
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SUPPORT"]').click();move_world(p,200,-100,click=True);select_members(p,[(300,-100)]);before=p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')
    p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill('90');apply_preview(p);expect(p.locator('[data-transform-status]')).to_contain_text('请先确认');assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before
    p.locator('[data-transform-angle]').fill('');expect(p.locator('[data-transform-apply]')).to_be_disabled();p.keyboard.press('Escape')
    p.locator('[data-cad-move]').click();p.locator('[data-transform-ack]').check();a=client_point(p,300,-100);b=client_point(p,310,-110);p.mouse.move(a['x'],a['y']);p.mouse.down();p.mouse.move(b['x'],b['y']);p.locator('#workspace-canvas').dispatch_event('pointercancel');p.mouse.up();expect(p.locator('[data-transform-panel]')).to_be_hidden();assert p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[e.getAttribute("cx"),e.getAttribute("cy")])')==before
    p.locator('[data-cad-copy]').click();p.locator('[data-cad-paste]').click();apply_preview(p);saved=save_reload(p);assert len(saved['supports'])==1 and len(saved['nodes'])==4


def test_transform_historical_run_isolation_and_public_analyze(public_page):
    from tests.browser.test_bridge_public_journey import check
    from tests.browser.test_m9_public_teaching_loop import analyze
    p,_,project=public_page
    # Keep Dynamic Input ON: all geometry comes from normal public drawing controls.
    member(p,(200,-100),(600,-100));member(p,(200,-100),(400,0));member(p,(400,0),(600,-100))
    p.locator('[data-workspace-tool="SUPPORT"]').click();move_world(p,200,-100,click=True);p.locator('[data-support-choice="ROLLER_Y"]').click();move_world(p,600,-100,click=True)
    p.locator('[data-workspace-tool="LOAD"]').click();move_world(p,400,0,click=True);p.locator('[data-property-fy]').fill('-20');p.locator('[data-property-fy]').press('Tab');save_reload(p);assert check(p)['ok'];a=analyze(p)
    base=p.url.split('/projects/')[0]+f'/projects/{project.pk}/analyses/{a}'
    historical=p.context.request.get(base+'/explanation/').json()
    p.locator('[data-ux-stage-target="build"]').click();select_members(p,[(300,-50),(500,-50),(400,-100)])
    p.locator('[data-cad-move]').click();p.locator('[data-transform-ack]').check();p.locator('[data-transform-dx]').fill('10');p.locator('[data-transform-dy]').fill('-20');apply_preview(p);save_reload(p);assert check(p)['ok'];b=analyze(p);assert b!=a
    assert p.context.request.get(base+'/explanation/').json()==historical
    p.locator('[data-ux-stage-target="summary"]').click();p.locator('#workspace-run-select').select_option(str(a));p.locator('[data-ux-stage-target="understanding"]').click();p.get_by_role('tab',name='为什么',exact=True).click();expect(p.locator('[data-teaching-level="1"]')).to_be_visible();expect(p.locator('[data-cad-transform-toolbar]')).to_be_hidden();shot(p,'historical-results-after-move')


@pytest.mark.parametrize('operation',['paste','move','rotate'])
def test_transform_updates_visible_dirty_indicator(public_page,operation):
    p,_,_=public_page;member(p,(200,-100),(400,-100));save_reload(p);select_members(p,[(300,-100)]);expect(p.locator('#workspace-save-status')).to_have_text('未保存修改：无')
    if operation=='paste':p.locator('[data-cad-copy]').click();p.locator('[data-cad-paste]').click()
    elif operation=='move':p.locator('[data-cad-move]').click();p.locator('[data-transform-dx]').fill('10');p.locator('[data-transform-dy]').fill('0')
    else:p.locator('[data-cad-rotate]').click();p.locator('[data-transform-angle]').fill('90')
    apply_preview(p);shot(p,f'dirty-{operation}-applied');expect(p.locator('#workspace-save-status')).to_have_text('未保存修改：有',timeout=1000)
    p.locator('[data-cad-undo]').click();expect(p.locator('#workspace-save-status')).to_have_text('未保存修改：无');p.locator('[data-cad-redo]').click();expect(p.locator('#workspace-save-status')).to_have_text('未保存修改：有')


def test_transform_meta_shortcuts_and_input_ime_guards(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    p.keyboard.press('Meta+c');p.keyboard.press('Meta+v');expect(p.locator('[data-transform-preview]')).to_have_count(1);p.keyboard.press('Escape')
    p.locator('[data-cad-rotate]').click();field=p.locator('[data-transform-angle]');field.fill('22.5');field.focus()
    # Event-level guard characterization: never read/write OS clipboard contents.
    native=field.evaluate("""el=>['c','v'].flatMap(key=>['ctrlKey','metaKey'].map(mod=>{const e=new KeyboardEvent('keydown',{key,[mod]:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}))""")
    assert native==[False]*4;expect(field).to_be_focused();expect(field).to_have_value('22.5');p.keyboard.press('Escape')
    guarded=p.locator('#workspace-canvas').evaluate("""el=>{el.focus();const result=[];for(const flags of [{isComposing:true},{repeat:true},{keyCode:229}]){const e=new KeyboardEvent('keydown',{key:'v',ctrlKey:true,bubbles:true,cancelable:true,...flags});el.dispatchEvent(e);result.push(e.defaultPrevented)};el.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));const e=new KeyboardEvent('keydown',{key:'v',ctrlKey:true,bubbles:true,cancelable:true});el.dispatchEvent(e);result.push(e.defaultPrevented);el.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}));return result}""")
    assert guarded==[False]*4;expect(p.locator('[data-transform-panel]')).to_be_hidden();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    p.keyboard.press('Control+v');expect(p.locator('[data-transform-panel]')).to_be_visible();p.locator('[data-workspace-tool="NODE"]').click();expect(p.locator('[data-transform-panel]')).to_be_hidden();expect(p.locator('[data-transform-preview]')).to_have_count(0)
