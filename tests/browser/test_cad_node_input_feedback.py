"""Direct NODE validation owns inline copy; geometry and legacy errors keep their authority."""
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_core_drawing import move_world
from tests.browser.test_cad_core_journey import member, save_reload
from tests.browser.test_bridge_public_journey import check

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
COPY = '请输入完整的绝对坐标 X,Y，例如 120,350；支持负数和小数。'
EVIDENCE = Path('.superpowers/sdd/2026-11-07-cad-ux02-p1-copy01') / os.environ.get('COPY01_EVIDENCE_PHASE', 'observed')
VIEWPORTS = [(1024, 768), (1280, 800), (1440, 900)]


def feedback(page):
    return page.locator('[data-cad-node-input-error]')


def count_nodes(page):
    return page.locator('[data-object-kind="GeometryNode"]').count()


def input_state(page):
    return page.evaluate("""() => {
      const rect = el => {if (!el) return null; const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
      const error=document.querySelector('[data-cad-node-input-error]'), global=document.querySelector('#workspace-error');
      return {viewport:{width:innerWidth,height:innerHeight},scroll:{x:scrollX,y:scrollY},
        canvas:rect(document.querySelector('#workspace-canvas')),reserve:rect(document.querySelector('[data-cad-input-reserve]')),
        error:rect(error),errorText:error?.textContent,global:rect(global),globalText:global?.textContent,
        worldTransform:document.querySelector('[data-world-layer]').getAttribute('transform'),
        focus:document.activeElement?.getAttributeNames().filter(n=>n.startsWith('data-cad')),
        documentWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth};
    }""")


def capture(page, name, scenario):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCE / (name + '.png')))
    row = input_state(page)
    row.update(scenario=scenario,actual_nodes=count_nodes(page),source='real Chromium/public UI/test-owned temporary DB')
    (EVIDENCE / (name + '.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2))
    return row


def invalid_direct(page, text='120,abc'):
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type(text)
    page.keyboard.press('Enter')


@pytest.mark.parametrize('width,height', VIEWPORTS)
@pytest.mark.parametrize('text', ['120,abc', '120,'])
def test_direct_node_invalid_copy_visible_without_scroll(public_page, width, height, text):
    page, _, _ = public_page
    page.set_viewport_size({'width': width, 'height': height})
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type(text)
    before = input_state(page)
    page.keyboard.press('Enter')
    state = capture(page, f'invalid-{width}-'+('incomplete' if text=='120,' else 'format'), 'Direct NODE invalid Enter in normal viewport, no explicit scroll')
    assert count_nodes(page) == 0
    expect(feedback(page)).to_have_text(COPY)
    expect(feedback(page)).to_be_visible()
    command = page.locator('[data-cad-command-input]')
    expect(command).to_be_focused()
    expect(command).to_have_attribute('aria-invalid', 'true')
    assert feedback(page).get_attribute('id') in command.get_attribute('aria-describedby').split()
    expect(page.locator('[data-cad-command-label]')).to_have_text('节点坐标 X,Y（mm）')
    assert '@' not in command.get_attribute('placeholder') and '<' not in command.get_attribute('placeholder')
    assert state['scroll'] == before['scroll'] and state['canvas'] == before['canvas'] and state['worldTransform'] == before['worldTransform']
    assert state['reserve']['height'] == before['reserve']['height'] == 64
    error = state['error']
    assert error['x'] >= 0 and error['y'] >= 0 and error['x']+error['width'] <= width
    assert error['y']+error['height'] <= min(height,state['canvas']['y'])
    assert state['documentWidth'] <= state['clientWidth']
    hit = page.evaluate("""r=>Boolean(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('[data-cad-node-input-error]'))""",error)
    assert hit
    expect(page.locator('#workspace-error')).to_be_hidden()


@pytest.mark.parametrize('exit_kind', ['Escape', 'NODE', 'MEMBER', 'SELECT', 'form', 'stage', 'window'])
def test_direct_error_clears_on_entry_exit(public_page, exit_kind):
    page, _, _ = public_page
    invalid_direct(page)
    expect(feedback(page)).to_have_text(COPY)
    if exit_kind == 'Escape':page.keyboard.press('Escape')
    elif exit_kind in ['NODE','MEMBER','SELECT']:page.locator(f'[data-workspace-tool="{exit_kind}"]').click()
    elif exit_kind == 'form':page.locator('[data-member-material]').focus()
    elif exit_kind == 'stage':page.locator('[data-ux-stage-target="summary"]').click()
    else:page.evaluate("window.dispatchEvent(new Event('blur'))")
    expect(feedback(page)).to_be_hidden()
    expect(page.locator('[data-cad-command-input]')).not_to_have_attribute('aria-invalid','true')
    assert count_nodes(page) == 0
    if exit_kind == 'stage':page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type('-50,80.5');page.keyboard.press('Enter')
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(1)
    capture(page,'exit-'+exit_kind,'Cancelled error does not survive tool/focus/stage lifecycle; new direct entry commits once')


def test_direct_error_recovers_without_duplicate_commit(public_page):
    page, _, _ = public_page
    invalid_direct(page,'120,')
    expect(feedback(page)).to_have_text(COPY)
    command=page.locator('[data-cad-command-input]')
    command.fill('237.25,-123.75')
    expect(feedback(page)).to_be_hidden()
    page.keyboard.press('Enter');page.keyboard.press('Enter')
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(1)
    expect(feedback(page)).to_be_hidden()
    expect(page.locator('[data-workspace-tool="NODE"]')).to_have_attribute('aria-pressed','true')
    saved=save_reload(page)
    assert [(n['x_mm'],n['y_mm']) for n in saved['nodes']]==[(237.25,-123.75)]
    page.locator('[data-cad-fit]').click()
    capture(page,'corrected-and-saved','Invalid pair corrected to valid signed decimals, one Node after Save/Reload')


def test_direct_error_does_not_repeat_live_text_for_unchanged_enter(public_page):
    page, _, _ = public_page
    invalid_direct(page)
    expect(feedback(page)).to_have_text(COPY)
    page.evaluate("""()=>{window.errorTextMutations=[];new MutationObserver(rows=>errorTextMutations.push(...rows.map(r=>r.type))).observe(document.querySelector('[data-cad-node-input-error]'),{childList:true,characterData:true,subtree:true})}""")
    page.keyboard.press('Enter');page.keyboard.press('Enter')
    assert page.evaluate('errorTextMutations') == []
    assert count_nodes(page) == 0


@pytest.mark.parametrize('text,expected', [('@30.25,-20.5',(230.25,-120.5)),('30.5<-90',(200,-130.5))])
def test_advanced_relative_polar_copy_and_geometry_preserved(public_page,text,expected):
    page, _, _ = public_page
    invalid_direct(page)
    page.keyboard.press('ControlOrMeta+A');page.keyboard.type('200,-100');page.keyboard.press('Enter')
    page.locator('[data-workspace-tool="MEMBER"]').click();move_world(page,200,-100,click=True)
    page.get_by_text('精确绘制',exact=True).click()
    command=page.locator('[data-cad-command-input]')
    expect(page.locator('[data-cad-command-label]')).to_have_text('坐标命令')
    assert '@' in command.get_attribute('placeholder') and '<' in command.get_attribute('placeholder')
    command.click();command.fill(text);command.press('Enter')
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    expect(feedback(page)).to_be_hidden()
    capture(page,'advanced-'+('relative' if text.startswith('@') else 'polar'),'Legacy command syntax and restored guidance, not direct NODE restrictions')
    saved=save_reload(page)
    assert saved['physical_members'][0]['start_node_client_key']=='node-1'
    end=next(n for n in saved['nodes'] if n['client_key']!='node-1')
    assert (end['x_mm'],end['y_mm']) == expected


def test_legacy_invalid_and_member_validation_keep_global_copy(public_page):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click();move_world(page,200,-100,click=True)
    page.get_by_text('精确绘制',exact=True).click()
    command=page.locator('[data-cad-command-input]');command.fill('@abc,0');command.press('Enter')
    expect(page.locator('#workspace-error')).to_contain_text('@dx,dy')
    assert COPY not in page.locator('#workspace-error').inner_text()
    expect(feedback(page)).to_be_hidden()
    length,angle=page.locator('[data-cad-dynamic-length]'),page.locator('[data-cad-dynamic-angle]')
    length.click();length.fill('0');angle.click();angle.fill('-90');angle.press('Enter')
    expect(page.locator('#workspace-error')).to_contain_text('长度')
    assert count_nodes(page)==0
    length.fill('30.5');angle.press('Enter')
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    capture(page,'member-validation-recovered','Legacy/global validation preserved, MEMBER Length/Tab/Angle path unchanged')


def test_model_check_support_and_incomplete_errors_preserved(public_page):
    page, _, _ = public_page
    member(page,(200,-100),(600,-100));save_reload(page)
    result=check(page);assert result['ok'] is False
    expect(page.locator('#workspace-check-issues')).to_contain_text('支座')
    expect(feedback(page)).to_be_hidden()
    page.locator('[data-ux-stage-target="build"]').click()
    page.locator('[data-draft-object-key="member-1"]').click()
    page.locator('[data-property-end-node]').select_option('')
    save_reload(page);result=check(page);assert result['ok'] is False
    expect(page.locator('#workspace-check-issues')).to_contain_text('终点')
    assert COPY not in page.locator('#workspace-check-issues').inner_text()


def test_unrelated_save_failure_survives_direct_error(public_page):
    page, _, _ = public_page
    other=page.context.new_page();other.goto(page.url)
    page.locator('[data-workspace-tool="NODE"]').click();page.keyboard.type('120,350');page.keyboard.press('Enter');save_reload(page)
    other.locator('[data-workspace-tool="NODE"]').click();other.keyboard.type('237.25,-123.75');other.keyboard.press('Enter')
    with other.expect_response('**/model/save/') as response:other.locator('#workspace-save').click()
    assert response.value.status==409
    expect(other.locator('#workspace-error')).to_contain_text('版本')
    original=other.locator('#workspace-error').inner_text()
    invalid_direct(other)
    expect(feedback(other)).to_have_text(COPY)
    assert other.locator('#workspace-error').inner_text()==original
    other.keyboard.press('Escape');expect(feedback(other)).to_be_hidden()
    assert other.locator('#workspace-error').inner_text()==original
    capture(other,'stale-save-preserved','Real second-tab STALE_DRAFT remains global; direct error and cancellation do not erase it')
    other.close()
