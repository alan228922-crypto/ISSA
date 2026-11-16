"""Keyboard/toolbar parity through real public UI; no geometry injection."""
from pathlib import Path
import pytest
from playwright.sync_api import expect
from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_core_drawing import move_world
from tests.browser.test_cad_core_journey import member
from tests.browser.test_cad_transform_tools import select_members

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
OUT = Path('.superpowers/sdd/2026-11-09-cad-ux04-kb01/screenshots')
AIDS = [('grid-visible','F7','GRID','网格'),('snap','F9','GSNAP','网格吸附'),('object-snap','F3','OSNAP','物件捕捉'),('ortho','F8','ORTHO','正交'),('tracking','F11','TRACK','追踪'),('dynamic-input','F12','DYN','动态输入')]


def svg(p):
    return p.locator('#workspace-canvas')


def points(p):
    return p.locator('[data-object-kind="GeometryNode"] circle').evaluate_all('(els)=>els.map(e=>[+e.getAttribute("cx"),+e.getAttribute("cy")])')


def shot(p,name):
    OUT.mkdir(parents=True,exist_ok=True)
    p.screenshot(path=str(OUT/(name+'.png')))


def test_function_keys_use_same_toolbar_actions_and_status(public_page):
    p,_,_=public_page
    for suffix,key,_,label in AIDS:
        button=p.locator(f'[data-cad-{suffix}]')
        before=button.get_attribute('aria-pressed')
        svg(p).focus();p.keyboard.press(key)
        expect(button).to_have_attribute('aria-pressed','false' if before=='true' else 'true',timeout=1200)
        status_label={'snap':'SNAP','object-snap':'对象捕捉','ortho':'ORTHO'}.get(suffix,label)
        expect(p.locator('#workspace-snap-indicator')).to_contain_text(status_label+': '+('关' if before=='true' else '开'))
        button.click();expect(button).to_have_attribute('aria-pressed',before)


def test_idle_fallback_commands_do_not_require_input_click(public_page):
    p,_,_=public_page
    for suffix,_,command,_ in AIDS:
        button=p.locator(f'[data-cad-{suffix}]');before=button.get_attribute('aria-pressed')
        svg(p).focus();p.keyboard.type(command);p.keyboard.press('Enter')
        expect(button).to_have_attribute('aria-pressed','false' if before=='true' else 'true',timeout=1200)
        expect(p.locator('[data-cad-transform-command]')).to_have_value('')
        expect(svg(p)).to_be_focused()


def test_keyboard_history_keeps_native_text_undo(public_page):
    p,_,_=public_page;p.locator('[data-workspace-tool="NODE"]').click();p.keyboard.type('120,350');p.keyboard.press('Enter')
    assert points(p)==[[120,350]]
    p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus();p.keyboard.press('Control+z');assert points(p)==[]
    p.keyboard.press('Control+y');assert points(p)==[[120,350]]
    p.keyboard.press('Meta+z');assert points(p)==[]
    p.keyboard.press('Meta+Shift+z');assert points(p)==[[120,350]]
    p.keyboard.press('Meta+z');assert points(p)==[]
    p.keyboard.press('Meta+y');assert points(p)==[[120,350]]
    field=p.locator('[data-cad-transform-command]');field.fill('');field.focus();p.keyboard.type('native');p.keyboard.press('Meta+z' if p.evaluate("navigator.platform.includes('Mac')") else 'Control+z');expect(field).to_have_value('');assert points(p)==[[120,350]]


@pytest.mark.parametrize('suffix,key',[('tracking','F11'),('dynamic-input','F12')])
def test_added_function_key_toggles_existing_action(public_page,suffix,key):
    p,_,_=public_page;button=p.locator(f'[data-cad-{suffix}]');svg(p).focus();p.keyboard.press(key)
    expect(button).to_have_attribute('aria-pressed','false',timeout=1200)


@pytest.mark.parametrize('modifier',['Control','Meta'])
def test_save_shortcut_persists_committed_draft_from_text_field(public_page,modifier):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click()
    field=p.locator('[data-cad-transform-command]');field.fill('unsubmitted text');field.focus()
    with p.expect_response('**/model/save/',timeout=2500) as response:p.keyboard.press(modifier+'+s')
    assert response.value.ok
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    expect(p.locator('#workspace-save-status')).to_contain_text('无')
    expect(field).to_be_focused();expect(field).to_have_value('unsubmitted text')
    p.reload();assert points(p)==[[200,-100],[400,-100]]


def test_save_shortcut_does_not_apply_transform_preview(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    svg(p).focus();p.keyboard.type('M');p.keyboard.press('Enter');p.keyboard.type('100,-50')
    expect(p.locator('[data-transform-preview]')).to_have_count(1)
    pending=[];p.route('**/model/save/',lambda route:pending.append(route))
    p.keyboard.press('Control+s');expect(p.locator('[data-cad-shortcut-notice]')).to_contain_text('预览不会保存')
    p.wait_for_timeout(50)
    with p.expect_response('**/model/save/') as response:pending[0].continue_()
    assert response.value.ok
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    expect(p.locator('[data-cad-shortcut-notice]')).not_to_be_visible()
    p.reload();assert points(p)==[[200,-100],[400,-100]]


def test_save_shortcut_inflight_and_repeat_only_save_once(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus()
    pending=[];p.route('**/model/save/',lambda route:pending.append(route))
    p.keyboard.press('Control+s');expect(p.locator('[data-ux-save-indicator]')).to_have_text('保存中',timeout=1500)
    p.keyboard.press('Meta+s');svg(p).evaluate("el=>el.dispatchEvent(new KeyboardEvent('keydown',{key:'s',ctrlKey:true,repeat:true,bubbles:true,cancelable:true}))")
    p.wait_for_timeout(100);assert len(pending)==1
    with p.expect_response('**/model/save/') as response:pending[0].continue_()
    assert response.value.ok;expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    p.keyboard.press('Control+s');p.wait_for_timeout(100);assert len(pending)==1
    expect(p.locator('[data-cad-shortcut-notice]')).to_contain_text('没有未保存修改')


@pytest.mark.parametrize('status,code',[(403,'PROJECT_READ_ONLY'),(500,'REQUEST_FAILED')])
def test_save_shortcut_keeps_original_error_and_dirty_contract(public_page,status,code):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus()
    p.route('**/model/save/',lambda route:route.fulfill(status=status,json={'ok':False,'error':{'code':code,'message':'测试保存被拒绝','details':{}}}))
    with p.expect_response('**/model/save/',timeout=2500) as response:p.keyboard.press('Control+s')
    assert response.value.status==status
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('保存失败')
    expect(p.locator('#workspace-save-status')).to_contain_text('有')
    expect(p.locator('#workspace-error')).to_be_visible()
    expect(p.locator('#workspace-error')).to_contain_text('下一步')
    p.unroute('**/model/save/');svg(p).focus()
    with p.expect_response('**/model/save/') as response:p.keyboard.press('Control+s')
    assert response.value.ok;expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存')


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_tooltip_and_shortcut_help_visible_in_desktop_viewports(public_page,width,height):
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height})
    button=p.locator('[data-cad-grid-visible]');button.focus();button.hover()
    tooltip=p.locator('[data-cad-toolbar-tooltip]');expect(tooltip).to_be_visible(timeout=1500)
    expect(tooltip).to_contain_text('网格');expect(tooltip).to_contain_text('F7');expect(tooltip).to_contain_text('开启')
    assert tooltip.evaluate("el=>getComputedStyle(el).pointerEvents")=='none'
    p.keyboard.press('F7');expect(tooltip).to_contain_text('关闭');shot(p,f'tooltip-{width}')
    bounds=tooltip.bounding_box();assert bounds['x']>=0 and bounds['y']>=0 and bounds['x']+bounds['width']<=width and bounds['y']+bounds['height']<=height
    p.locator('[data-cad-shortcuts-open]').click();dialog=p.get_by_role('dialog',name='快捷键说明')
    expect(dialog).to_be_visible()
    for group in ['建模命令','几何编辑','绘图辅助','撤销／保存','取消／确认']:expect(dialog.get_by_role('heading',name=group,exact=True)).to_be_visible()
    expect(dialog).to_contain_text('GRID');expect(dialog).to_contain_text('Fn');expect(dialog).to_contain_text('Ctrl/Cmd+S');shot(p,f'help-{width}')
    b=dialog.bounding_box();assert b['x']>=0 and b['y']>=0 and b['x']+b['width']<=width and b['y']+b['height']<=height
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
    p.keyboard.press('Escape');expect(dialog).not_to_be_visible();expect(p.locator('[data-cad-shortcuts-open]')).to_be_focused()
    svg(p).focus();p.keyboard.press('?');expect(dialog).to_be_visible();p.keyboard.press('Escape');expect(svg(p)).to_be_focused()


def test_shortcuts_protect_native_fields_composition_and_node_question(public_page):
    p,_,_=public_page
    field=p.locator('[data-cad-transform-command]');field.fill('native');field.focus()
    for suffix,key,_,_ in AIDS:
        b=p.locator(f'[data-cad-{suffix}]');before=b.get_attribute('aria-pressed');p.keyboard.press(key);expect(b).to_have_attribute('aria-pressed',before)
    p.keyboard.press('?');expect(field).to_have_value('native?');expect(p.get_by_role('dialog',name='快捷键说明')).not_to_be_visible()
    field.dispatch_event('compositionstart');field.evaluate("el=>el.dispatchEvent(new KeyboardEvent('keydown',{key:'s',ctrlKey:true,isComposing:true,bubbles:true,cancelable:true}))")
    field.evaluate("el=>el.dispatchEvent(new KeyboardEvent('keydown',{key:'F11',isComposing:true,bubbles:true,cancelable:true}))")
    expect(p.locator('[data-cad-tracking]')).to_have_attribute('aria-pressed','true');expect(field).to_have_value('native?');field.dispatch_event('compositionend')
    p.locator('[data-workspace-tool="NODE"]').click();p.keyboard.press('?');expect(p.locator('[data-cad-command-input]')).to_have_value('?');expect(p.get_by_role('dialog',name='快捷键说明')).not_to_be_visible()
    p.keyboard.press('Escape');p.keyboard.type('120,350');p.keyboard.press('Enter');assert points(p)==[[120,350]]


def test_shortcuts_do_not_edit_results_or_readonly_workspace(public_page):
    from tests.browser.test_m9_reflection_handoff import db_read
    from competitions.models import CompetitionEvent
    p,_,project=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();p.locator('[data-ux-stage-target="understanding"]').click()
    svg(p).focus();before=p.locator('[data-cad-grid-visible]').get_attribute('aria-pressed')
    handled=svg(p).evaluate("el=>{const e=new KeyboardEvent('keydown',{key:'s',ctrlKey:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}");assert not handled
    p.keyboard.press('F7');expect(p.locator('[data-cad-grid-visible]')).to_have_attribute('aria-pressed',before)
    expect(p.locator('#workspace-save')).to_be_disabled()
    db_read(lambda:CompetitionEvent.objects.filter(pk=project.event_id).update(status='FINISHED_GRACE'));p.reload();expect(p.locator('#workspace-save')).to_be_disabled()
    svg(p).focus();handled=svg(p).evaluate("el=>{const e=new KeyboardEvent('keydown',{key:'s',metaKey:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}");assert not handled
    p.locator('[data-cad-shortcuts-open]').click();expect(p.get_by_role('dialog',name='快捷键说明')).to_be_visible()


def test_save_shortcut_uses_real_version_conflict_guard(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click()
    other=p.context.new_page();other.goto(p.url);other.locator('[data-workspace-tool="NODE"]').click();other.keyboard.type('120,350');other.keyboard.press('Enter')
    with other.expect_response('**/model/save/') as saved:other.locator('#workspace-save').click()
    assert saved.value.ok
    svg(p).focus()
    with p.expect_response('**/model/save/') as stale:p.keyboard.press('Control+s')
    assert stale.value.status==409 and stale.value.json()['error']['code']=='STALE_DRAFT'
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('保存失败');expect(p.locator('#workspace-save-status')).to_contain_text('有')
    expect(p.locator('#workspace-error')).to_contain_text('版本已发生变化');p.reload();assert points(p)==[[120,350]];other.close()


def test_save_completion_does_not_leave_a_false_saving_notice(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus()
    with p.expect_response('**/model/save/'):p.keyboard.press('Control+s')
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存')
    expect(p.locator('[data-cad-shortcut-notice]')).not_to_contain_text('正在保存')


def test_save_inflight_stage_roundtrip_cannot_enable_second_write(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus()
    pending=[];p.route('**/model/save/',lambda route:pending.append(route));p.keyboard.press('Control+s')
    expect(p.locator('#workspace-save')).to_have_attribute('aria-busy','true')
    p.locator('[data-ux-stage-target="understanding"]').click();p.locator('[data-ux-stage-target="build"]').click()
    expect(p.locator('#workspace-save')).to_be_disabled();svg(p).focus();p.keyboard.press('Control+s');p.wait_for_timeout(50);assert len(pending)==1
    with p.expect_response('**/model/save/'):pending[0].continue_()
    expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存');expect(p.locator('#workspace-save')).to_be_enabled()


def test_composition_guards_apply_on_canvas_and_repeats_do_not_toggle(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));p.locator('[data-workspace-tool="SELECT"]').click();svg(p).focus()
    canvas=svg(p);canvas.dispatch_event('compositionstart')
    for spec in [{'key':'F11'},{'key':'s','ctrlKey':True},{'key':'z','metaKey':True}]:
        assert canvas.evaluate("(el,spec)=>{const e=new KeyboardEvent('keydown',{...spec,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}",spec) is False
    assert len(points(p))==2;expect(p.locator('[data-cad-tracking]')).to_have_attribute('aria-pressed','true');canvas.dispatch_event('compositionend')
    for spec in [{'key':'F11','isComposing':True},{'key':'F11','keyCode':229}]:
        assert canvas.evaluate("(el,spec)=>{const e=new KeyboardEvent('keydown',{...spec,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}",spec) is False
    p.keyboard.press('F11');expect(p.locator('[data-cad-tracking]')).to_have_attribute('aria-pressed','false')
    assert canvas.evaluate("el=>{const e=new KeyboardEvent('keydown',{key:'F11',repeat:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}") is True
    expect(p.locator('[data-cad-tracking]')).to_have_attribute('aria-pressed','false')


def test_help_escape_keeps_unsubmitted_geometry_command(public_page):
    p,_,_=public_page;member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    svg(p).focus();p.keyboard.type('M');p.keyboard.press('Enter');p.keyboard.type('100,-50');expect(p.locator('[data-transform-preview]')).to_have_count(1)
    p.locator('[data-cad-shortcuts-open]').click();p.keyboard.press('Escape')
    expect(p.locator('[data-transform-panel]')).to_be_visible();expect(p.locator('[data-transform-preview]')).to_have_count(1);assert points(p)==[[200,-100],[400,-100]]
    p.locator('[data-cad-transform-command]').focus();p.keyboard.press('Enter');assert points(p)==[[300,-150],[500,-150]]


def test_non_workspace_does_not_consume_browser_save(public_page):
    p,_,_=public_page;p.goto(p.url.split('/projects/')[0]+'/events/')
    assert p.locator('#workspace-root').count()==0
    assert p.locator('body').evaluate("el=>{const e=new KeyboardEvent('keydown',{key:'s',ctrlKey:true,bubbles:true,cancelable:true});el.dispatchEvent(e);return e.defaultPrevented}") is False


def test_clean_save_advisory_clears_after_new_edit(public_page):
    p,_,_=public_page;svg(p).focus();p.keyboard.press('Control+s')
    expect(p.locator('[data-cad-shortcut-notice]')).to_contain_text('没有未保存修改')
    p.locator('[data-workspace-tool="NODE"]').click();p.keyboard.type('120,350');p.keyboard.press('Enter')
    expect(p.locator('#workspace-save-status')).to_contain_text('有');expect(p.locator('[data-cad-shortcut-notice]')).not_to_be_visible()


def test_pending_save_advisory_clears_after_cancel(public_page):
    p,_,_=public_page;p.locator('[data-workspace-tool="NODE"]').click();p.keyboard.press('Control+s')
    expect(p.locator('[data-cad-shortcut-notice]')).to_contain_text('预览不会保存')
    p.keyboard.press('Escape');expect(p.locator('[data-cad-shortcut-notice]')).not_to_be_visible()


@pytest.mark.parametrize('width,height',[(1024,768),(1280,800),(1440,900)])
def test_status_feedback_preserves_existing_canvas_edge_hit(public_page,width,height):
    from tests.browser.test_cad_core_drawing import client_point
    import json
    p,_,_=public_page;p.set_viewport_size({'width':width,'height':height});member(p,(200,-100),(400,-100));select_members(p,[(300,-100)])
    a=client_point(p,300,-100);p.mouse.click(a['x'],a['y'],button='right');p.keyboard.press('Escape')
    box=svg(p).bounding_box();x=min(width-2,box['x']+box['width']-2);y=min(height-3,box['y']+box['height']-100)
    info=p.evaluate("([x,y])=>({point:{x,y},hit:document.elementFromPoint(x,y)?.outerHTML.slice(0,250),canvas:document.querySelector('#workspace-canvas').getBoundingClientRect().toJSON(),footer:document.querySelector('#workspace-status-bar').getBoundingClientRect().toJSON(),isCanvas:document.querySelector('#workspace-canvas').contains(document.elementFromPoint(x,y))})",[x,y])
    OUT.mkdir(parents=True,exist_ok=True);(OUT/f'edge-hit-{width}.json').write_text(json.dumps(info,ensure_ascii=False,indent=2));shot(p,f'footer-edge-{width}')
    assert info['isCanvas'],info
    p.mouse.click(x,y,button='right');expect(p.locator('[data-cad-context-menu]').get_by_role('menuitem',name='适合视窗',exact=True)).to_be_visible()


@pytest.mark.parametrize('modifier',['Control','Meta'])
def test_save_shortcut_with_initial_and_unfocused_workspace_body(public_page,modifier):
    p,_,_=public_page;p.reload();assert p.evaluate('document.activeElement.tagName')=='BODY'
    p.evaluate("window.addEventListener('keydown',e=>{if(e.key==='s'&&(e.ctrlKey||e.metaKey))window.bodySaveEvent=e},true)")
    p.keyboard.press(modifier+'+s');assert p.evaluate('window.bodySaveEvent.defaultPrevented') is True
    expect(p.locator('[data-cad-shortcut-notice]')).to_contain_text('没有未保存修改')
    p.locator('[data-workspace-tool="NODE"]').click();p.keyboard.type('120,350');p.keyboard.press('Enter');svg(p).evaluate('el=>el.blur()')
    assert p.evaluate('document.activeElement.tagName')=='BODY'
    with p.expect_response('**/model/save/') as response:p.keyboard.press(modifier+'+s')
    assert response.value.ok;expect(p.locator('[data-ux-save-indicator]')).to_have_text('已保存');p.reload();assert points(p)==[[120,350]]
