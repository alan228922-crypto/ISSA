"""真实低采样放点与同一输入区域的显式鼠标编辑契约。"""

import json
import subprocess

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page
from tests.browser.test_cad_core_drawing import client_point
from tests.browser.test_cad_core_journey import save_reload

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
VIEWPORTS = [(1024, 768), (1280, 800), (1440, 900)]
POINTS = [(200, -100), (270, -100), (340, -100), (410, -100),
          (480, -100), (550, -100), (620, -100), (235, 0),
          (305, 0), (375, 0), (445, 0), (515, 0), (585, 0)]


def click_world_once(page, point):
    screen = client_point(page, *point)
    page.mouse.move(screen['x'], screen['y'], steps=1)
    page.mouse.down()
    page.mouse.up()
    return screen


def first_eight(page, width, height):
    page.set_viewport_size({'width': width, 'height': height})
    expect(page.locator('[data-cad-dynamic-input]')).to_have_attribute('aria-pressed', 'true')
    page.locator('[data-workspace-tool="NODE"]').click()
    for index, point in enumerate(POINTS[:8], 1):
        click_world_once(page, point)
        expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(index)
    # Only observe the real native event path; no controller or state injection.
    page.evaluate("""() => {
      window.pointerTrace = [];
      for (const type of ['pointermove','pointerdown','pointerup','click','focusin'])
        document.addEventListener(type, e => window.pointerTrace.push({
          type, x:e.clientX, y:e.clientY, target:e.target.tagName,
          attributes:e.target.getAttributeNames().filter(n=>n.startsWith('data-cad')),
          buttons:e.buttons, button:e.button
        }), {capture:true});
    }""")


def evidence(page, tmp_path, name, screen, intended):
    page.screenshot(path=str(tmp_path / (name + '.png')))
    observed = page.evaluate("""p => {
      const hit=document.elementFromPoint(p.x,p.y), active=document.activeElement;
      return {trace:window.pointerTrace,point:p,hit:hit?.tagName,
        hitAttributes:hit?.getAttributeNames().filter(n=>n.startsWith('data-cad')),
        inputFocused:!!active?.closest('input'),
        focusedAttributes:active?.getAttributeNames().filter(n=>n.startsWith('data-cad')),
        nodes:document.querySelectorAll('[data-object-kind="GeometryNode"]').length,
        members:document.querySelectorAll('[data-object-kind="PhysicalMember"]').length,
        dynamicOn:document.querySelector('[data-cad-dynamic-input]').getAttribute('aria-pressed')};
    }""", screen)
    observed.update(viewport=page.viewport_size, intended=intended,
                    branch=subprocess.check_output(['git','branch','--show-current']).decode().strip(),
                    head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip())
    (tmp_path / (name + '.json')).write_text(json.dumps(observed, ensure_ascii=False, indent=2))
    return observed


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_rapid_blank_node_sequence_preserves_exact_unique_nodes(public_page, tmp_path, width, height):
    """捕获旧面板把快速放点吃成输入聚焦，且不能靠加 pointermove 通过。"""
    page, _, _ = public_page
    first_eight(page, width, height)
    screen = client_point(page, *POINTS[8])
    evidence(page, tmp_path, 'before-ninth', screen, 'NODE drawing')
    click_world_once(page, POINTS[8])
    observed = evidence(page, tmp_path, 'after-ninth', screen, 'NODE drawing')
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(9)
    assert not observed['inputFocused'], observed
    assert observed['hit'] != 'INPUT', observed
    for index, point in enumerate(POINTS[9:], 10):
        click_world_once(page, point)
        expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(index)
    evidence(page, tmp_path, 'thirteen-nodes', screen, 'NODE drawing')
    saved = save_reload(page)
    assert {n['client_key']: (n['x_mm'], n['y_mm']) for n in saved['nodes']} == {
        f'node-{index}': point for index, point in enumerate(POINTS, 1)
    }
    assert len({n['client_key'] for n in saved['nodes']}) == 13


@pytest.mark.parametrize('width,height', VIEWPORTS)
@pytest.mark.parametrize('focused', ['x', 'y'])
def test_mouse_click_on_dynamic_input_preserves_edit_intent(public_page, tmp_path, width, height, focused):
    """点选字段实际位置编辑，不能把字段点击强制转交 Canvas。"""
    page, _, _ = public_page
    first_eight(page, width, height)
    x, y = page.locator('[data-cad-x]'), page.locator('[data-cad-y]')
    x.click()
    expect(x).to_be_focused()
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(8)
    x.fill('237.25')
    y.click()
    y.fill('-123.75')
    field = page.locator(f'[data-cad-{focused}]')
    field.click()
    point = client_point(page, 400, 0)
    page.mouse.move(point['x'], point['y'], steps=1)
    expect(x).to_have_value('237.25')
    expect(y).to_have_value('-123.75')
    evidence(page, tmp_path, 'explicit-input-click', point, 'Mouse field editing')
    field.press('Enter')
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(9)
    saved = save_reload(page)
    assert {n['client_key']: (n['x_mm'], n['y_mm']) for n in saved['nodes']} == {
        **{f'node-{index}': point for index, point in enumerate(POINTS[:8], 1)},
        'node-9': (237.25, -123.75),
    }
    assert len({n['client_key'] for n in saved['nodes']}) == 9


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_dynamic_input_reserves_visible_space_outside_canvas(public_page, tmp_path, width, height):
    """保留区不占 SVG 命中位置，模式切换和输入开关不移动 Canvas。"""
    page, _, _ = public_page
    first_eight(page, width, height)
    canvas = page.locator('#workspace-canvas')
    before = canvas.bounding_box()
    editor = page.locator('[data-cad-dynamic-overlay]')
    box = editor.bounding_box()
    assert 0 <= box['x'] and box['x'] + box['width'] <= width
    assert 0 <= box['y'] and box['y'] + box['height'] <= before['y']
    point = client_point(page, *POINTS[8])
    for steps in (1, 12):
        page.mouse.move(point['x'], point['y'], steps=steps)
        assert editor.bounding_box() == box
    page.locator('[data-cad-dynamic-input]').click()
    expect(editor).to_be_hidden()
    assert canvas.bounding_box() == before
    page.locator('[data-cad-dynamic-input]').click()
    expect(editor).to_be_visible()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    click_world_once(page, POINTS[0])
    expect(page.locator('[data-cad-dynamic-length]')).to_be_visible()
    assert canvas.bounding_box() == before
    evidence(page, tmp_path, 'reserved-editor', point, 'Fixed editor outside Canvas')


@pytest.mark.parametrize('steps', [1, 12])
def test_dense_nodes_and_members_keep_pointer_targets(public_page, tmp_path, steps):
    """13 节点/23 构件公开绘图，不依赖高采样绕过遮挡。"""
    page, _, _ = public_page
    first_eight(page, 1280, 800)
    for index, point in enumerate(POINTS[8:], 9):
        screen = client_point(page, *point)
        page.mouse.move(screen['x'], screen['y'], steps=steps)
        page.mouse.down(); page.mouse.up()
        expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(index)
    bottom, top = POINTS[:7], POINTS[7:]
    edges = list(zip(bottom, bottom[1:])) + list(zip(top, top[1:]))
    edges += [(b, t) for index, t in enumerate(top) for b in (bottom[index], bottom[index + 1])]
    for index, (start, end) in enumerate(edges, 1):
        page.locator('[data-workspace-tool="MEMBER"]').click()
        for point in (start, end):
            screen = client_point(page, *point)
            page.mouse.move(screen['x'], screen['y'], steps=steps)
            page.mouse.down(); page.mouse.up()
        expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(index)
    evidence(page, tmp_path, 'dense-members', screen, '13 nodes / 23 members')
    saved = save_reload(page)
    assert len(saved['nodes']) == 13 and len(saved['physical_members']) == 23
    assert len({n['client_key'] for n in saved['nodes']}) == 13


@pytest.mark.parametrize('mode', ['POLAR', 'RELATIVE'])
def test_reserved_numeric_modes_keep_mouse_editability(public_page, tmp_path, mode):
    """保留原有相对/极坐标输入与一次提交，不重新解析几何。"""
    page, _, _ = public_page
    first_eight(page, 1280, 800)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    click_world_once(page, POINTS[0])
    length = page.locator('[data-cad-dynamic-length]')
    length.click()
    if mode == 'RELATIVE':
        length.press('Tab')
        page.locator('[data-cad-dynamic-angle]').press('Tab')
        first, second = page.locator('[data-cad-dynamic-dx]'), page.locator('[data-cad-dynamic-dy]')
        values, expected = ('-30.25', '20.5'), (169.75, -79.5)
    else:
        first, second = length, page.locator('[data-cad-dynamic-angle]')
        values, expected = ('30.5', '-90'), (200, -130.5)
    first.click(); first.fill(values[0])
    second.click(); second.fill(values[1])
    screen = client_point(page, 400, 0)
    page.mouse.move(screen['x'], screen['y'], steps=1)
    expect(first).to_have_value(values[0])
    expect(second).to_have_value(values[1])
    evidence(page, tmp_path, 'numeric-mouse-edit', screen, mode)
    second.press('Enter')
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    saved = save_reload(page)
    node = next(n for n in saved['nodes'] if n['client_key'] == 'node-9')
    assert (node['x_mm'], node['y_mm']) == expected
    assert len(saved['nodes']) == 9 and len(saved['physical_members']) == 1
    assert saved['physical_members'][0]['start_node_client_key'] == 'node-1'
