"""通过公开控件验证命令流程，仅预置空白账号和资源库。"""
from pathlib import Path
import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_transform_tools import select_members
from tests.browser.test_cad_core_journey import member,save_reload
from tests.browser.test_cad_core_drawing import move_world,client_point

pytestmark=[pytest.mark.browser,pytest.mark.django_db(transaction=True)]
OUT=Path('.superpowers/sdd/2026-11-08-cad-ux04/screenshots')

def shot(p,name):
    OUT.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(OUT/(name+'.png')))

def command(p,text):
    p.locator('#workspace-canvas').focus();p.keyboard.type(text);p.keyboard.press('Enter')

def points(p):return p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[+e.getAttribute("cx"),+e.getAttribute("cy")])')

@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_command_direct_move_and_centroid_rotate(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    command(p,'m');expect(p.locator('[data-transform-panel]')).to_be_visible(timeout=1000)
    p.keyboard.type('100,-50');expect(p.locator('[data-cad-transform-command]')).to_be_focused(timeout=1000);shot(p,f'command-m-{width}-preview');p.keyboard.press('Enter')
    assert points(p)==[[300,-150],[500,-150]]
    command(p,'ro');p.keyboard.type('90');p.keyboard.press('Enter');assert points(p)==[[400,-250],[400,-50]]
    p.locator('[data-cad-undo]').click();assert points(p)==[[300,-150],[500,-150]];p.locator('[data-cad-redo]').click();saved=save_reload(p);assert len(saved['nodes'])==2;shot(p,f'command-ro-{width}-saved')

def test_command_focus_invalid_and_escape(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);before=points(p);command(p,'M');p.keyboard.type('12,abc');p.keyboard.press('Enter');assert points(p)==before;expect(p.locator('[data-cad-transform-command]')).to_be_focused(timeout=1000)
    p.keyboard.press('Control+a');p.keyboard.type('12,-5');p.keyboard.press('Escape');expect(p.locator('[data-transform-panel]')).to_be_hidden();assert points(p)==before


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_copy_base_repeat_and_pointer_move(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    command(p,'CO');expect(p.locator('[data-transform-status]')).to_contain_text('基点',timeout=1000);move_world(p,200,-100,click=True);move_world(p,220,-80);shot(p,f'copy-base-{width}-preview');move_world(p,220,-80,click=True);expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2)
    move_world(p,240,-60,click=True);expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(3);p.keyboard.press('Escape');p.locator('[data-cad-undo]').click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2);p.locator('[data-cad-redo]').click()
    # Undo 会清除已移除对象的选择，Redo 后显式重新选取。
    select_members(p,[(340,-60)]);command(p,'M');expect(p.locator('[data-transform-panel]')).to_be_visible();move_world(p,240,-60,click=True);move_world(p,260,-40,click=True);saved=save_reload(p);assert {(n['x_mm'],n['y_mm']) for n in saved['nodes']}=={(200,-100),(400,-100),(220,-80),(420,-80),(260,-40),(460,-40)};shot(p,f'copy-base-{width}-saved')


def test_rotate_pointer_center_and_preview(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'RO');move_world(p,200,-100,click=True);move_world(p,200,-50);shot(p,'rotate-explicit-center-preview');assert points(p)==[[200,-100],[400,-100]];p.keyboard.type('90');p.keyboard.press('Enter');assert points(p)==[[200,-100],[200,100]]


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_stretch_and_length_shared_joint_direct_entry(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250));original=save_reload(p);select_members(p,[(300,-100)])
    expect(p.locator('[data-cad-node-grip]')).to_have_count(2,timeout=1000)
    command(p,'ST');move_world(p,400,-100,click=True);p.keyboard.type('420,-80');shot(p,f'stretch-{width}-preview');p.keyboard.press('Enter');assert points(p)==[[200,-100],[420,-80],[400,-250]]
    p.locator('[data-cad-undo]').click();assert points(p)==[[200,-100],[400,-100],[400,-250]];select_members(p,[(300,-100)])
    command(p,'LEN');move_world(p,400,-100,click=True);p.keyboard.type('150');p.keyboard.press('Enter');assert points(p)==[[200,-100],[350,-100],[400,-250]]
    command(p,'LEN');move_world(p,350,-100,click=True);p.keyboard.type('+40');p.keyboard.press('Enter');assert points(p)==[[200,-100],[390,-100],[400,-250]]
    command(p,'LEN');move_world(p,390,-100,click=True);p.keyboard.type('-20');p.keyboard.press('Enter');assert points(p)==[[200,-100],[370,-100],[400,-250]]
    saved=save_reload(p);assert saved['physical_members']==original['physical_members'];assert [n['client_key'] for n in saved['nodes']]==[n['client_key'] for n in original['nodes']];shot(p,f'length-{width}-saved')


def test_selected_member_endpoint_grip_drag_and_illegal_stretch(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250));select_members(p,[(300,-100)]);expect(p.locator('[data-cad-node-grip]')).to_have_count(2,timeout=1000)
    a=client_point(p,400,-100);b=client_point(p,420,-80);p.mouse.move(a['x'],a['y']);p.mouse.down();p.mouse.move(b['x'],b['y']);shot(p,'member-endpoint-grip-preview');p.mouse.up();assert points(p)==[[200,-100],[420,-80],[400,-250]]
    before=points(p);command(p,'ST');move_world(p,420,-80,click=True);p.keyboard.type('200,-100');p.keyboard.press('Enter');assert points(p)==before;expect(p.locator('[data-transform-apply]')).to_be_disabled();p.keyboard.press('Escape')


def test_stretch_preview_includes_every_adjacent_member(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));member(p,(400,-100),(400,-250));select_members(p,[(300,-100)]);command(p,'ST');move_world(p,400,-100,click=True);p.keyboard.type('420,-80');expect(p.locator('[data-transform-preview] line')).to_have_count(2,timeout=1000);p.keyboard.press('Escape');assert points(p)==[[200,-100],[400,-100],[400,-250]]


def test_member_grip_escape_before_release_does_not_commit(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);before=points(p);a=client_point(p,400,-100);b=client_point(p,420,-80);p.mouse.move(a['x'],a['y']);p.mouse.down();p.mouse.move(b['x'],b['y']);p.keyboard.press('Escape');p.mouse.up();assert points(p)==before


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_context_menu_contexts_bounds_and_escape(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);a=client_point(p,300,-100);p.mouse.click(a['x'],a['y'],button='right');menu=p.locator('[data-cad-context-menu]');expect(menu).to_be_visible(timeout=1000)
    for name in ['复制','平移','旋转','拉伸','修改长度','取消选取']:expect(menu.get_by_role('menuitem',name=name,exact=True)).to_be_visible()
    shot(p,f'context-member-{width}');p.keyboard.press('Escape');expect(menu).to_have_count(0);expect(p.locator('[data-object-kind="PhysicalMember"][data-selected="true"]')).to_have_count(1)
    # 在画布边缘实际右击，菜单必须保持在可见视窗内。
    box=p.locator('#workspace-canvas').bounding_box();x=min(width-2,box['x']+box['width']-2);y=min(height-3,box['y']+box['height']-100);p.mouse.click(x,y,button='right');expect(menu.get_by_role('menuitem',name='适合视窗',exact=True)).to_be_visible();b=menu.bounding_box();assert b['x']>=0 and b['y']>=0 and b['x']+b['width']<=width and b['y']+b['height']<=height;shot(p,f'context-edge-{width}');p.keyboard.press('Escape')


def test_context_node_command_menu_and_native_input(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);a=client_point(p,400,-100);p.mouse.click(a['x'],a['y'],button='right');menu=p.locator('[data-cad-context-menu]');expect(menu.get_by_role('menuitem',name='输入坐标',exact=True)).to_be_visible(timeout=1000);menu.get_by_role('menuitem',name='输入坐标',exact=True).click();p.keyboard.type('450,-80');p.keyboard.press('Enter');assert points(p)==[[200,-100],[450,-80]]
    select_members(p,[(325,-90)]);command(p,'M');a=client_point(p,300,-90);p.mouse.click(a['x'],a['y'],button='right');expect(menu.get_by_role('menuitem',name='确认',exact=True)).to_be_disabled();expect(menu.get_by_role('menuitem',name='结束命令',exact=True)).to_be_enabled();p.keyboard.press('Escape');expect(p.locator('[data-transform-panel]')).to_be_visible();p.keyboard.press('Escape');expect(p.locator('[data-transform-panel]')).to_be_hidden()
    field=p.locator('[data-cad-transform-command]');field.fill('native');prevented=field.evaluate("el=>{const e=new MouseEvent('contextmenu',{bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}");assert not prevented;expect(menu).to_have_count(0)


@pytest.mark.parametrize('tool',['NODE','MEMBER'])
def test_context_can_end_existing_drawing_tool_without_geometry_change(public_page,tool):
    p,_,_=public_page;member(p,(200,-100),(400,-100));before=points(p);p.locator(f'[data-workspace-tool="{tool}"]').click()
    if tool=='MEMBER':move_world(p,200,-100,click=True)
    a=client_point(p,300,-180);p.mouse.click(a['x'],a['y'],button='right');menu=p.locator('[data-cad-context-menu]');expect(menu.get_by_role('menuitem',name='结束命令',exact=True)).to_be_visible(timeout=1000);expect(menu.get_by_role('menuitem',name='确认',exact=True)).to_be_disabled();menu.get_by_role('menuitem',name='结束命令',exact=True).click();expect(p.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed','true');assert points(p)==before;expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)


def test_context_paste_undo_redo_and_finish_repeat_copy(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'CO');move_world(p,200,-100,click=True);move_world(p,220,-80,click=True);a=client_point(p,300,-200);p.mouse.click(a['x'],a['y'],button='right');p.get_by_role('menuitem',name='结束命令',exact=True).click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2)
    p.mouse.click(a['x'],a['y'],button='right');p.get_by_role('menuitem',name='粘贴',exact=True).click();expect(p.locator('[data-transform-apply]')).to_be_disabled()  # 默认 +20 与已有副本冲突，安全拒绝。
    p.keyboard.press('Escape');p.mouse.click(a['x'],a['y'],button='right');p.get_by_role('menuitem',name='复原',exact=True).click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    p.mouse.click(a['x'],a['y'],button='right');p.get_by_role('menuitem',name='重做',exact=True).click();expect(p.locator('[data-object-kind="PhysicalMember"]')).to_have_count(2)


def test_keyboard_menu_confirm_and_command_focus_guards(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'M');p.keyboard.type('10,-20');a=client_point(p,300,-100);p.mouse.click(a['x'],a['y'],button='right');menu=p.locator('[data-cad-context-menu]');expect(menu.get_by_role('menuitem',name='确认',exact=True)).to_be_enabled();p.keyboard.press('Home');p.keyboard.press('Enter');assert points(p)==[[210,-120],[410,-120]]
    field=p.locator('[data-cad-transform-command]');field.fill('native');field.focus();native=field.evaluate("el=>['c','v'].map(key=>{const e=new KeyboardEvent('keydown',{key,ctrlKey:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented})");assert native==[False,False];expect(field).to_have_value('native');p.keyboard.press('Escape')
    p.locator('#workspace-canvas').focus();guard=p.locator('#workspace-canvas').evaluate("el=>[{isComposing:true},{repeat:true},{ctrlKey:true}].map(flags=>{const e=new KeyboardEvent('keydown',{key:'m',bubbles:true,cancelable:true,...flags});el.dispatchEvent(e);return e.defaultPrevented})");assert guard==[False,False,False];expect(p.locator('[data-transform-panel]')).to_be_hidden()


def test_stretch_pointer_keeps_attached_support_and_load(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SUPPORT"]').click();move_world(p,400,-100,click=True);p.locator('[data-workspace-tool="LOAD"]').click();move_world(p,400,-100,click=True);p.locator('[data-property-fy]').fill('-20');p.locator('[data-property-fy]').press('Tab');original=save_reload(p);select_members(p,[(300,-100)]);command(p,'ST');move_world(p,400,-100,click=True);expect(p.locator('[data-transform-attachments]')).to_contain_text('支座 1，荷载 1');target=client_point(p,380,-80);bounds=p.locator('#workspace-canvas').bounding_box();assert bounds['x']<=target['x']<=bounds['x']+bounds['width'];move_world(p,380,-80,click=True);shot(p,'stretch-attachment-pointer-before-save');assert points(p)==[[200,-100],[380,-80]], p.locator('[data-transform-status]').inner_text();saved=save_reload(p)
    for name in ['physical_members','supports','node_loads']:assert saved[name]==original[name]
    assert [(n['x_mm'],n['y_mm']) for n in saved['nodes']]==[(200,-100),(380,-80)]


def test_command_stretch_history_run_snapshot_isolation(public_page):
    from tests.browser.test_bridge_public_journey import check
    from tests.browser.test_m9_public_teaching_loop import analyze
    p,_,project=public_page
    member(p,(200,-100),(600,-100));member(p,(200,-100),(400,0));member(p,(400,0),(600,-100));p.locator('[data-workspace-tool="SUPPORT"]').click();move_world(p,200,-100,click=True);p.locator('[data-support-choice="ROLLER_Y"]').click();move_world(p,600,-100,click=True);p.locator('[data-workspace-tool="LOAD"]').click();move_world(p,400,0,click=True);p.locator('[data-property-fy]').fill('-20');p.locator('[data-property-fy]').press('Tab');original=save_reload(p);assert check(p)['ok'];a=analyze(p)
    base=p.url.split('/projects/')[0]+f'/projects/{project.pk}/analyses/{a}';facts=p.context.request.get(base+'/explanation/').json();p.locator('[data-ux-stage-target="build"]').click();select_members(p,[(300,-50)]);command(p,'ST');move_world(p,400,0,click=True);p.keyboard.type('420,20');p.keyboard.press('Enter');saved=save_reload(p)
    for name in ['physical_members','supports','node_loads']:assert saved[name]==original[name]
    assert check(p)['ok'];b=analyze(p);assert b!=a;assert p.context.request.get(base+'/explanation/').json()==facts
    p.locator('[data-ux-stage-target="summary"]').click();p.locator('#workspace-run-select').select_option(str(a));p.locator('[data-ux-stage-target="understanding"]').click();p.get_by_role('tab',name='为什么',exact=True).click();expect(p.locator('[data-cad-transform-toolbar]')).to_be_hidden();shot(p,'history-run-a-after-stretch')
    prevented=p.locator('#workspace-canvas').evaluate("el=>{const e=new MouseEvent('contextmenu',{bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}");assert not prevented;expect(p.locator('[data-cad-context-menu]')).to_have_count(0)


@pytest.mark.parametrize('verb,value',[('M','10,-20'),('RO','45'),('ST','420,-80'),('LEN','150')])
def test_invalid_command_value_cannot_restore_previous_preview(public_page,verb,value):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);before=points(p);command(p,verb)
    if verb in ['ST','LEN']:move_world(p,400,-100,click=True)
    p.keyboard.type(value);expect(p.locator('[data-transform-apply]')).to_be_enabled();field=p.locator('[data-cad-transform-command]');field.fill('bad');expect(p.locator('[data-transform-apply]')).to_be_disabled();p.locator('[data-transform-preview-button]').click();expect(p.locator('[data-transform-apply]')).to_be_disabled(timeout=1000);assert points(p)==before;p.keyboard.press('Escape')


def test_coordinate_resolver_failure_cannot_apply_last_valid_preview(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'ST');move_world(p,400,-100,click=True);move_world(p,420,-80);expect(p.locator('[data-transform-preview]')).to_have_count(1);before=points(p);target=client_point(p,440,-60)
    # 仅对坐标 API 做故障注入；不写入几何、Draft 或后端数据。
    p.locator('#workspace-canvas').evaluate("""(svg,point)=>{const original=svg.getScreenCTM;let calls=0;svg.getScreenCTM=function(){return ++calls===2?null:original.call(this)};try{svg.dispatchEvent(new MouseEvent('click',{clientX:point.x,clientY:point.y,bubbles:true,cancelable:true}))}finally{svg.getScreenCTM=original}}""",target)
    assert points(p)==before;expect(p.locator('[data-transform-apply]')).to_be_disabled()


def test_invalid_numeric_input_can_recover_with_fresh_drag(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'M');p.keyboard.type('bad');p.locator('[data-cad-transform-command]').fill('bad');a=client_point(p,300,-100);b=client_point(p,310,-120);p.mouse.move(a['x'],a['y']);p.mouse.down();p.mouse.move(b['x'],b['y'],steps=3);p.mouse.up()
    # 指针经浏览器 CTM 往返存在微米以下误差；数值命令仍使用精确断言。
    for actual,wanted in zip(points(p),[[210,-120],[410,-120]]):assert actual==pytest.approx(wanted,abs=1e-4)


def test_ime_escape_keeps_candidate_editing_then_normal_escape_cancels(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);before=points(p);command(p,'M');p.keyboard.type('100,-50');field=p.locator('[data-cad-transform-command]');before_text=field.input_value()
    prevented=field.evaluate("el=>{el.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));const e=new KeyboardEvent('keydown',{key:'Escape',isComposing:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}")
    assert not prevented;expect(field).to_have_value(before_text,timeout=1000);expect(field).to_be_focused();expect(p.locator('[data-transform-panel]')).to_be_visible();assert points(p)==before
    field.dispatch_event('compositionend');p.keyboard.press('Escape');expect(p.locator('[data-transform-panel]')).to_be_hidden();assert points(p)==before


def test_canvas_enter_confirms_mouse_preview_without_clearing_selection(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);command(p,'M');move_world(p,200,-100,click=True);move_world(p,220,-80);expect(p.locator('[data-transform-apply]')).to_be_enabled();p.keyboard.press('Enter');assert points(p)==[[220,-80],[420,-80]];expect(p.locator('[data-object-kind="PhysicalMember"][data-selected="true"]')).to_have_count(1)


def test_member_grips_are_only_interactive_in_build_stage(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)]);grips=p.locator('[data-cad-node-grip]');expect(grips).to_have_count(2);expect(grips.first).to_be_visible();p.locator('[data-ux-stage-target="check"]').click();expect(grips.first).to_be_hidden(timeout=1000);p.locator('[data-ux-stage-target="build"]').click();expect(grips.first).to_be_visible()
