"""Bounded SSR regression against real backend and isolated test database."""
import pytest
from django.urls import reverse
from tests.application.test_physical_draft import context

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]
SIZES = ((1024, 768), (1280, 800), (1440, 900))


def assert_fits(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.url
    assert page.locator('main').is_visible()
    assert page.locator('.product-header').is_visible()
    for button in page.locator('main button[type=submit]').all():
        if button.is_visible():
            button.scroll_into_view_if_needed()
            box = button.bounding_box()
            assert box['x'] >= 0 and box['x'] + box['width'] <= page.viewport_size['width'] + 1


def test_resource_pages_fit_three_sizes_and_keyboard_skip(context, live_server, workspace_page):
    owner, project, material, section = context
    routes = [('materials:index', {}), ('materials:material_create', {}),
              ('materials:material_edit', {'material_id': material.pk}),
              ('materials:material_delete', {'material_id': material.pk}),
              ('materials:section_create', {}), ('materials:section_edit', {'section_id': section.pk}),
              ('materials:composite_section_create', {}), ('materials:section_delete', {'section_id': section.pk})]
    paths = ['/events/', '/accounts/password-change/'] + [reverse(name, kwargs={'project_id': project.pk, **kw}) for name, kw in routes]
    page = workspace_page(user=owner, project=project)
    for path in paths:
        response = page.goto(live_server.url + path)
        assert response.status == 200, path
        for width, height in SIZES:
            page.set_viewport_size({'width': width, 'height': height})
            assert_fits(page)
    page.goto(live_server.url + '/events/')
    page.keyboard.press('Tab')
    assert page.locator('.ui-skip').evaluate('e => e === document.activeElement')
    assert page.locator('.ui-skip').evaluate('e => getComputedStyle(e).outlineStyle') != 'none'
    page.keyboard.press('Enter')
    assert page.locator('#main-content').evaluate('e => e === document.activeElement')


def test_material_invalid_post_then_valid_save(context, live_server, workspace_page):
    from playwright.sync_api import expect
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse('materials:material_create', kwargs={'project_id': project.pk}))
    for name, value in [('name', '真实后端验证材料'), ('E_MPa', '0'), ('density_g_per_mm3', '.0007'), ('source_type', 'MEASURED'), ('note', '保留输入来源')]:
        page.locator(f'[name={name}]').fill(value)
    page.locator('main form').evaluate('f => f.noValidate = true')
    page.get_by_role('button', name='保存材料').click()
    expect(page.locator('[name=E_MPa]')).to_have_attribute('aria-invalid', 'true')
    assert page.locator('[name=E_MPa]').get_attribute('aria-describedby')
    assert page.get_by_role('alert').is_visible()
    assert page.locator('[name=note]').input_value() == '保留输入来源'
    page.locator('[name=E_MPa]').fill('2000')
    page.get_by_role('button', name='保存材料').click()
    expect(page.get_by_role('cell', name='真实后端验证材料', exact=True)).to_be_visible()


def test_rotated_section_centroid_comes_from_actual_preview(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse('materials:composite_section_create', kwargs={'project_id': project.pk}))
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    row = page.locator('[data-component-row]').first
    for suffix, value in [('width_mm', '2'), ('height_mm', '6'), ('center_x_mm', '10'), ('center_y_mm', '-3'), ('angle_deg', '30'), ('density_g_per_mm3', '.0007')]:
        row.locator(f'[name$="-{suffix}"]').fill(value)
    try:
        page.wait_for_function("document.querySelector('[data-section-preview-status]').dataset.state === 'ready'")
    except Exception as exc:
        raise AssertionError({'status': page.locator('[data-section-preview-status]').text_content(), 'pageerrors': errors}) from exc
    with page.expect_response('**/sections/preview/') as response:
        row.locator('[name$="-width_mm"]').fill('4')
    result = response.value.json()
    page.wait_for_function("document.querySelector('[data-section-preview-status]').dataset.state === 'ready'")
    component = page.locator('[data-section-component]').first
    assert '≈' in page.locator('[data-section-preview-svg]').text_content()
    assert component.get_attribute('data-input-angle-deg') == '30'
    assert component.get_attribute('transform').startswith('rotate(-30 ')
    centroid = page.locator('[data-section-centroid]')
    assert float(centroid.get_attribute('data-centroid-x-mm')) == result['properties']['centroid_x_mm']
    assert float(centroid.get_attribute('data-centroid-y-mm')) == result['properties']['centroid_y_mm']
    for width, height in SIZES:
        page.set_viewport_size({'width': width, 'height': height})
        assert_fits(page)
        assert page.locator('[data-section-preview-svg]').evaluate('e => [...e.querySelectorAll("[data-graphic-label]")].every(t => {const b=t.getBoundingClientRect(), s=e.getBoundingClientRect();return b.left >= s.left && b.right <= s.right && b.top >= s.top && b.bottom <= s.bottom;})')


def test_late_preview_response_does_not_restore_stale_properties(context, live_server, workspace_page):
    owner, project, _, _ = context
    page = workspace_page(user=owner, project=project)
    page.goto(live_server.url + reverse('materials:section_create', kwargs={'project_id': project.pk}))
    for name, value in [('width_mm', '2'), ('height_mm', '6'), ('density_g_per_mm3', '.0007')]:
        page.locator(f'[name={name}]').fill(value)
    page.wait_for_function("document.querySelector('[data-section-preview-status]').dataset.state === 'ready'")
    held = []
    def delay(route):
        held.append((route, route.fetch()))
    page.route('**/sections/preview/', delay)
    page.locator('[name=width_mm]').fill('4')
    page.wait_for_timeout(350)
    assert len(held) == 1
    page.locator('[name=width_mm]').fill('8')
    assert page.locator('[data-section-properties]').text_content().strip() == ''
    assert page.locator('[data-section-centroid]').count() == 0
    page.wait_for_timeout(350)
    assert len(held) == 2
    held[1][0].fulfill(response=held[1][1])
    page.wait_for_function("document.querySelector('[data-section-preview-status]').dataset.state === 'ready'")
    final = page.locator('[data-section-properties]').text_content()
    assert held[1][1].json()['properties']['A_mm2'] == 48
    held[0][0].fulfill(response=held[0][1])
    page.wait_for_timeout(150)
    assert page.locator('[data-section-properties]').text_content() == final
    assert page.locator('[data-section-component]').get_attribute('data-input-width-mm') == '8'
