"""动态输入保持可编辑，同时不能盖住正在绘图的几何命中目标。"""

import json

import pytest
from playwright.sync_api import expect

from tests.application.test_physical_draft import context
from tests.browser.test_m9_public_teaching_loop import public_page, analyze
from tests.browser.test_cad_core_drawing import client_point, move_world
from tests.browser.test_cad_core_journey import member, save_reload
from tests.browser.test_bridge_public_journey import check

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
VIEWPORTS = [(1024, 768), (1280, 800), (1440, 900)]
POINTS = [(200, -100), (600, -100), (400, 0)]


def place_triangle_nodes(page):
    expect(page.locator('[data-cad-dynamic-input]')).to_have_attribute('aria-pressed', 'true')
    page.locator('[data-workspace-tool="NODE"]').click()
    for index, point in enumerate(POINTS, start=1):
        move_world(page, *point, click=True)
        expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(index)


def overlay_observation(page):
    return page.evaluate("""() => {
      const svg=document.querySelector('#workspace-canvas'), overlay=document.querySelector('[data-cad-dynamic-overlay]');
      const rect=el=>{const r=el.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom}};
      return {viewport:{width:innerWidth,height:innerHeight},overlay:rect(overlay),
        fields:[...overlay.querySelectorAll('input')].filter(el=>el.getClientRects().length).map(rect),
        active:document.activeElement?.getAttributeNames().filter(n=>n.startsWith('data-cad')).join(','),
        nodes:[...svg.querySelectorAll('[data-node-body]')].map(el=>{
          const r=el.getBoundingClientRect(),x=(r.left+r.right)/2,y=(r.top+r.bottom)/2;
          const hit=document.elementFromPoint(x,y);
          return {x,y,canvasHit:!!hit?.closest('#workspace-canvas'),hit:hit?.tagName};
        })};
    }""")


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_dynamic_on_public_triangle_completes_analysis(public_page, tmp_path, width, height):
    page, _, _ = public_page
    page.set_viewport_size({'width': width, 'height': height})
    place_triangle_nodes(page)
    try:
        for index, (start, end) in enumerate([(POINTS[0], POINTS[1]), (POINTS[0], POINTS[2]), (POINTS[2], POINTS[1])], start=1):
            member(page, start, end)
            expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(index)
    finally:
        page.screenshot(path=str(tmp_path / f'triangle-drawing-{width}x{height}.png'))
        (tmp_path / 'drawing-observation.json').write_text(json.dumps(overlay_observation(page), indent=2))
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    move_world(page, *POINTS[0], click=True)
    page.locator('[data-support-choice="ROLLER_Y"]').click()
    move_world(page, *POINTS[1], click=True)
    page.locator('[data-workspace-tool="LOAD"]').click()
    move_world(page, *POINTS[2], click=True)
    page.locator('[data-property-fy]').fill('-20')
    page.locator('[data-property-fy]').press('Tab')
    saved = save_reload(page)
    assert len(saved['nodes']) == 3 and len(saved['physical_members']) == 3
    assert {row['client_key'] for row in saved['nodes']} == {'node-1', 'node-2', 'node-3'}
    assert check(page)['ok'] is True
    analyze(page)
    page.screenshot(path=str(tmp_path / f'triangle-analyzed-{width}x{height}.png'))


@pytest.mark.parametrize('focused', ['x', 'y'])
def test_dynamic_xy_mouse_edit_preserves_pair_and_single_submit(public_page, tmp_path, focused):
    page, _, _ = public_page
    page.locator('[data-workspace-tool="NODE"]').click()
    move_world(page, 200, -100)
    x, y = page.locator('[data-cad-x]'), page.locator('[data-cad-y]')
    x.click()
    x.fill('237.25')
    y.click()
    y.fill('-123.75')
    field = page.locator(f'[data-cad-{focused}]')
    field.click()
    before = page.locator('[data-cad-dynamic-overlay]').bounding_box()
    move_world(page, 400, 0)
    expect(x).to_have_value('237.25')
    expect(y).to_have_value('-123.75')
    assert page.locator('[data-cad-dynamic-overlay]').bounding_box() == before
    page.screenshot(path=str(tmp_path / f'xy-edit-focus-{focused}.png'))
    field.press('Enter')
    expect(page.locator('[data-object-kind="GeometryNode"]')).to_have_count(1)
    saved = save_reload(page)
    assert [(n['x_mm'], n['y_mm']) for n in saved['nodes']] == [(237.25, -123.75)]


@pytest.mark.parametrize('width,height', VIEWPORTS)
def test_dynamic_overlay_keeps_nodes_and_canvas_edges_hittable(public_page, tmp_path, width, height):
    page, _, _ = public_page
    page.set_viewport_size({'width': width, 'height': height})
    place_triangle_nodes(page)
    page.locator('[data-workspace-tool="MEMBER"]').click()
    move_world(page, *POINTS[2], click=True)
    bounds = page.evaluate("""() => {
      const r=document.querySelector('#workspace-canvas').getBoundingClientRect(),
        c=document.querySelector('.workspace-center').getBoundingClientRect(),
        bar=document.querySelector('#workspace-status-bar').getBoundingClientRect();
      return {left:Math.max(0,r.left,c.left),top:Math.max(0,r.top,c.top),
        right:Math.min(innerWidth,r.right,c.right),bottom:Math.min(innerHeight,r.bottom,c.bottom,bar.top)};
    }""")
    points = [client_point(page, *POINTS[2])]
    points += [{'x': x, 'y': y} for x in (bounds['left'] + 12, bounds['right'] - 12)
               for y in (bounds['top'] + 12, bounds['bottom'] - 12)]
    for index, point in enumerate(points):
        page.mouse.move(point['x'], point['y'])
        # Pointer coordinates can wrap the fixed status bar onto another row.
        # Sample the current visible bottom edge, not its pre-move position.
        canvas_now = page.locator('#workspace-canvas').bounding_box()
        bottom = min(page.locator('#workspace-status-bar').bounding_box()['y'], canvas_now['y']+canvas_now['height'])
        if point['y'] >= bottom:
            point = {**point, 'y': bottom - 12}
            page.mouse.move(point['x'], point['y'])
        observed = overlay_observation(page)
        page.screenshot(path=str(tmp_path / f'overlay-{width}x{height}-position-{index}.png'))
        assert all(row['canvasHit'] for row in observed['nodes']), observed
        for rect in [observed['overlay'], *observed['fields']]:
            # Owner approved a reserved editor above, outside the SVG canvas.
            assert 0 <= rect['left'] < rect['right'] <= width, observed
            assert 0 <= rect['top'] < rect['bottom'] <= bounds['top'], observed
        assert page.evaluate('p=>!!document.elementFromPoint(p.x,p.y)?.closest("#workspace-canvas")', point), observed
    # 字段仍可真正用鼠标点选；Enter 使用既有精确端点流程。
    length, angle = page.locator('[data-cad-dynamic-length]'), page.locator('[data-cad-dynamic-angle]')
    length.click()
    length.fill('30.5')
    angle.click()
    angle.fill('-20.25')
    move_world(page, 350, -50)
    expect(length).to_have_value('30.5')
    expect(angle).to_have_value('-20.25')
    angle.press('Enter')
    expect(page.locator('[data-object-kind="PhysicalMember"]')).to_have_count(1)
    page.keyboard.press('Escape')
    expect(page.locator('[data-workspace-tool="SELECT"]')).to_have_attribute('aria-pressed', 'true')
