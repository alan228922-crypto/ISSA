"""Direct keyboard intent enters the existing precise placement public workflow."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_core_drawing import move_world
from tests.browser.test_cad_core_journey import save_reload

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
VIEWPORTS = [(1024, 768), (1280, 800), (1440, 900)]
EVIDENCE = Path('.superpowers/sdd/2026-11-06-cad-ux02-p1/browser')


def nodes(page):
    return page.locator('[data-object-kind="GeometryNode"]')


def members(page):
    return page.locator('[data-object-kind="PhysicalMember"]')


def observe_input_events(page):
    page.evaluate("""() => {
      window.cadInputTrace=[];
      for(const type of ['keydown','input','focusin'])
        document.querySelector('#workspace-root').addEventListener(type,e=>cadInputTrace.push({
          type,key:e.key,repeat:e.repeat,isComposing:e.isComposing,
          target:e.target.tagName,attributes:e.target.getAttributeNames().filter(n=>n.startsWith('data-cad')),
          value:e.target.value
        }),true);
    }""")


def capture(page, name):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCE / (name + '.png')))
    (EVIDENCE / (name + '.json')).write_text(json.dumps(page.evaluate("""() => ({
      viewport:{width:innerWidth,height:innerHeight},
      nodes:document.querySelectorAll('[data-object-kind="GeometryNode"]').length,
      members:document.querySelectorAll('[data-object-kind="PhysicalMember"]').length,
      focused:document.activeElement?.getAttributeNames().filter(n=>n.startsWith('data-cad')),
      dynamicOn:document.querySelector('[data-cad-dynamic-input]').getAttribute('aria-pressed'),
      eventTrace:window.cadInputTrace||[]
    })"""), ensure_ascii=False, indent=2))


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_node_direct_keyboard_pair_continuous_and_persisted(public_page, width, height):
    """Missing tool-to-keyboard wiring must fail without a numeric-field click."""
    page, _, _ = public_page
    page.set_viewport_size({'width': width, 'height': height})
    observe_input_events(page)
    page.locator('[data-workspace-tool="NODE"]').click()
    for index, text in enumerate(('120,350', '237.25,-123.75', '-50,80.5'), 1):
        page.keyboard.type(text)
        command = page.locator('[data-cad-command-input]')
        expect(command).to_have_value(text)
        expect(command).to_be_visible()
        # Input feedback must stay above SVG, not be a hidden side-panel command.
        box, svg = command.bounding_box(), page.locator('#workspace-canvas').bounding_box()
        assert box['y'] >= 0 and box['y'] + box['height'] <= svg['y']
        move_world(page, 400, 0)
        expect(command).to_have_value(text)
        capture(page, f'node-{width}-{index}-entry')
        page.keyboard.press('Enter')
        expect(nodes(page)).to_have_count(index)
        expect(page.locator('[data-workspace-tool="NODE"]')).to_have_attribute('aria-pressed', 'true')
    saved = save_reload(page)
    assert {n['client_key']: (n['x_mm'], n['y_mm']) for n in saved['nodes']} == {
        'node-1': (120, 350), 'node-2': (237.25, -123.75), 'node-3': (-50, 80.5)}
    assert saved['member_joint_incidences'] == []
    page.locator('[data-cad-fit]').click()
    capture(page, f'node-{width}-saved')


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_member_direct_length_tab_angle_reuses_start_and_history(public_page, width, height):
    """Automatic numeric focus must not be required before length/angle typing."""
    page, _, _ = public_page
    page.set_viewport_size({'width': width, 'height': height})
    observe_input_events(page)
    page.locator('[data-workspace-tool="NODE"]').click()
    move_world(page, 200, -100, click=True)
    start = nodes(page).first.get_attribute('data-client-key')
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type('30.5')
    length, angle = page.locator('[data-cad-dynamic-length]'), page.locator('[data-cad-dynamic-angle]')
    expect(length).to_have_value('30.5')
    page.keyboard.press('Tab')
    expect(angle).to_be_focused()
    page.keyboard.type('-90')
    move_world(page, 400, 0)
    expect(length).to_have_value('30.5')
    expect(angle).to_have_value('-90')
    capture(page, f'member-{width}-entry')
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
    expect(nodes(page)).to_have_count(2)
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
    expect(page.locator('[data-workspace-tool="MEMBER"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('[data-cad-undo]').click()
    expect(members(page)).to_have_count(0)
    expect(nodes(page)).to_have_count(1)
    page.locator('[data-cad-redo]').click()
    saved = save_reload(page)
    assert saved['physical_members'][0]['start_node_client_key'] == start
    assert len(saved['nodes']) == 2 and len(saved['physical_members']) == 1
    end = next(n for n in saved['nodes'] if n['client_key'] != start)
    assert (end['x_mm'], end['y_mm']) == (200, -130.5)
    page.locator('[data-cad-fit]').click()
    capture(page, f'member-{width}-saved')


@pytest.mark.parametrize('text', ['120,', '-', 'abc', '1,NaN', '1,2,3'])
def test_node_incomplete_invalid_input_never_authors_geometry(public_page, text):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type(text)
    expect(page.locator('[data-cad-command-input]')).to_be_focused()
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(0)
    expect(page.locator('[data-cad-node-input-error]')).to_contain_text('绝对坐标 X,Y')
    page.keyboard.press('ControlOrMeta+A')
    page.keyboard.type('120,350')
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1)


@pytest.mark.parametrize('length,angle', [('0', '90'), ('-5', '90'), ('30.5', ''), ('30.5', 'abc')])
def test_member_invalid_pair_keeps_start_for_correction(public_page, length, angle):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type(length)
    page.keyboard.press('Tab')
    page.keyboard.type(angle)
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(0)  # provisional start is not a Draft node
    expect(members(page)).to_have_count(0)
    expect(page.locator('#workspace-error')).to_contain_text('长度')
    page.locator('[data-cad-dynamic-length]').fill('30.5')
    page.locator('[data-cad-dynamic-angle]').fill('-90')
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
    expect(nodes(page)).to_have_count(2)


@pytest.mark.parametrize('cancel', ['Escape', 'tool', 'blur', 'stage', 'window'])
def test_direct_node_entry_does_not_survive_cancel_or_focus_loss(public_page, cancel):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type('120,350')
    expect(page.locator('[data-cad-command-input]')).to_be_focused()
    if cancel == 'Escape':
        page.keyboard.press('Escape')
        expect(page.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed', 'true')
    elif cancel == 'tool':
        page.locator('[data-workspace-tool="MEMBER"]').click()
    elif cancel == 'blur':
        page.locator('[data-member-material]').focus()
    elif cancel == 'stage':
        page.locator('[data-ux-stage-target="summary"]').click()
    else:
        page.evaluate('window.dispatchEvent(new Event("blur"))')
    expect(page.locator('[data-cad-command-input]')).to_have_value('')
    page.locator('#workspace-canvas').focus()
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(0)


@pytest.mark.parametrize('kind', ['composition', 'repeat', 'modified'])
def test_direct_entry_ignores_unsafe_enter(public_page, kind):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type('120,350')
    command = page.locator('[data-cad-command-input]')
    expect(command).to_be_focused()
    props = {'composition': {'isComposing': True}, 'repeat': {'repeat': True}, 'modified': {'ctrlKey': True}}[kind]
    command.dispatch_event('keydown', {'key': 'Enter', **props})
    expect(nodes(page)).to_have_count(0)
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1)


def test_direct_entry_off_and_other_forms_keep_keyboard_ownership(public_page):
    page, _, _ = public_page
    page.locator('[data-cad-dynamic-input]').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    page.keyboard.type('120,350')
    expect(page.locator('[data-cad-command-input]')).to_be_visible()
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1)
    expect(page.locator('[data-cad-dynamic-input]')).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('[data-cad-dynamic-overlay]')).to_be_hidden()
    page.locator('[data-member-material]').focus()
    page.keyboard.type('237.25,-123.75')
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1)
    page.locator('[data-ux-stage-target="summary"]').click()
    page.keyboard.type('1,2')
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1)


def test_member_before_first_point_does_not_capture_numbers(public_page):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click()
    page.keyboard.type('30.5')
    page.keyboard.press('Tab')
    page.keyboard.type('-90')
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(0)
    expect(members(page)).to_have_count(0)


def test_member_decimal_prefix_and_dynamic_off(public_page):
    """A leading decimal must reach native input, and OFF must stay OFF after commit."""
    page, _, _ = public_page
    page.locator('[data-cad-dynamic-input]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type('.5')
    expect(page.locator('[data-cad-dynamic-length]')).to_have_value('.5')
    page.keyboard.press('Tab')
    page.keyboard.type('0')
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
    expect(page.locator('[data-cad-dynamic-overlay]')).to_be_hidden()
    saved = save_reload(page)
    assert {(n['x_mm'], n['y_mm']) for n in saved['nodes']} == {(200, -100), (200.5, -100)}


@pytest.mark.parametrize('tool', ['NODE', 'MEMBER'])
def test_composition_lifecycle_and_shortcuts_do_not_submit(public_page, tool):
    page, _, _ = public_page
    page.locator(f'[data-workspace-tool="{tool}"]').click()
    canvas = page.locator('#workspace-canvas')
    canvas.dispatch_event('keydown', {'key': '1', 'ctrlKey': True})
    canvas.dispatch_event('keydown', {'key': '1', 'isComposing': True})
    expect(canvas).to_be_focused()
    if tool == 'MEMBER':
        move_world(page, 200, -100, click=True)
        page.keyboard.type('30.5')
        page.keyboard.press('Tab')
        page.keyboard.type('-90.5')
        field = page.locator('[data-cad-dynamic-angle]')
    else:
        page.keyboard.type('120,350')
        field = page.locator('[data-cad-command-input]')
    field.dispatch_event('compositionstart', {'data': ''})
    field.dispatch_event('keydown', {'key': 'Enter'})
    expect(nodes(page)).to_have_count(0)
    field.dispatch_event('compositionend', {'data': ''})
    field.dispatch_event('keydown', {'key': 'Enter', 'repeat': True})
    expect(nodes(page)).to_have_count(0)
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1 if tool == 'NODE' else 2)
    if tool == 'MEMBER':
        saved = save_reload(page)
        end = next(n for n in saved['nodes'] if n['client_key'] == 'node-2')
        assert end['x_mm'] == pytest.approx(199.7338406672996, abs=1e-9)
        assert end['y_mm'] == pytest.approx(-130.49883865345723, abs=1e-9)


def test_member_blur_discards_values_but_preserves_original_start(public_page):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type('30.5')
    page.keyboard.press('Tab')
    page.keyboard.type('-90')
    page.locator('[data-member-material]').focus()
    expect(page.locator('[data-cad-dynamic-length]')).to_have_value('')
    expect(page.locator('[data-cad-dynamic-angle]')).to_have_value('')
    page.locator('#workspace-canvas').focus()
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(0)
    page.keyboard.type('30.5')
    page.keyboard.press('Tab')
    page.keyboard.type('-90')
    page.keyboard.press('Enter')
    saved = save_reload(page)
    assert {(n['x_mm'], n['y_mm']) for n in saved['nodes']} == {(200, -100), (200, -130.5)}


def test_reflection_and_material_forms_keep_text_input(public_page):
    from tests.browser.test_m9_public_teaching_loop import draw_triangle, analyze

    page, _, _ = public_page
    draw_triangle(page)
    analyze(page)
    page.get_by_role('tab', name='为什么', exact=True).click()
    page.get_by_role('button', name='进入反思', exact=True).click()
    page.get_by_role('button', name='开始反思', exact=True).click()
    field = page.locator('#workspace-reflection [name="original_reasoning"]')
    field.click()
    page.keyboard.type('120,350')
    page.keyboard.press('Enter')
    page.keyboard.type('30.5')
    expect(field).to_have_value('120,350\n30.5')
    expect(nodes(page)).to_have_count(3)
    expect(members(page)).to_have_count(3)
    page.locator('[data-ux-stage-target="build"]').click()
    page.get_by_role('link', name='管理材料与截面', exact=True).click()
    page.get_by_role('link', name='新建材料', exact=True).click()
    # A real form outside Workspace has no CAD handler at all.
    field = page.locator('input[type="text"]').first
    field.click()
    page.keyboard.type('120,350')
    expect(field).to_have_value('120,350')


@pytest.mark.parametrize('tool', ['NODE', 'MEMBER'])
def test_composition_focus_loss_does_not_lock_next_direct_entry(public_page, tool):
    page, _, _ = public_page
    page.locator(f'[data-workspace-tool="{tool}"]').click()
    if tool == 'MEMBER':
        move_world(page, 200, -100, click=True)
    page.keyboard.type('1')
    page.locator('[data-cad-command-input]' if tool == 'NODE' else '[data-cad-dynamic-length]').dispatch_event('compositionstart', {'data': ''})
    page.locator('[data-member-material]').focus()
    page.locator(f'[data-workspace-tool="{tool}"]').click()
    if tool == 'NODE':
        page.keyboard.type('120,350')
    else:
        move_world(page, 200, -100, click=True)
        page.keyboard.type('30.5')
        page.keyboard.press('Tab')
        page.keyboard.type('-90')
    page.keyboard.press('Enter')
    expect(nodes(page)).to_have_count(1 if tool == 'NODE' else 2)


def test_member_composition_cancelled_to_in_root_field_can_resume(public_page):
    """Focus may stay inside Workspace without delivering compositionend."""
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type('1')
    page.locator('[data-cad-dynamic-length]').dispatch_event('compositionstart', {'data': '', 'bubbles': True})
    page.locator('[data-member-material]').focus()
    page.locator('#workspace-canvas').focus()
    page.keyboard.type('30.5')
    page.keyboard.press('Tab')
    page.keyboard.type('-90')
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
    saved = save_reload(page)
    assert {(n['x_mm'], n['y_mm']) for n in saved['nodes']} == {(200, -100), (200, -130.5)}


@pytest.mark.parametrize('flag', ['isComposing', 'ctrlKey', 'metaKey', 'altKey'])
def test_direct_tab_does_not_steal_composition_or_browser_shortcut(public_page, flag):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, 200, -100, click=True)
    page.keyboard.type('30.5')
    page.keyboard.press('Tab')
    page.keyboard.type('-90')
    page.evaluate("window.addEventListener('keydown',e=>window.tabPrevented=e.defaultPrevented)")
    angle = page.locator('[data-cad-dynamic-angle]')
    angle.dispatch_event('keydown', {'key': 'Tab', flag: True})
    expect(angle).to_be_focused()
    assert page.evaluate('window.tabPrevented') is False
    expect(members(page)).to_have_count(0)
    page.keyboard.press('Enter')
    expect(members(page)).to_have_count(1)
