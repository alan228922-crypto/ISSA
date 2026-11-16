"""Three student tasks and safe copy, exercised through the actual DOM presenter."""

from copy import deepcopy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.browser.test_m9_run_context import context, m9_page, sample_payload

pytestmark = [pytest.mark.browser, pytest.mark.django_db(transaction=True)]


def capture_focused_evidence(page, name):
    """Rare supplied-fact presentation, explicitly not a public Analyze proof."""
    root = page.locator('#m9-evidence-test')
    for summary in root.locator('details:not([open]) > summary').all():
        summary.click()
    root.scroll_into_view_if_needed()
    output = Path('.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots')
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output / f'focused-{name}.png'))


def render_teaching(page, payload, *, renderer="renderExplanation"):
    page.locator('[data-ux-stage-target="understanding"]').click()
    return page.evaluate("""async ({payload,renderer}) => {
      const {buildTeachingView}=await import('/static/projects/workspace/teaching-view.js');
      const results=await import('/static/projects/workspace/results.js');
      const view=buildTeachingView({payload,runNumber:1,workspace:{projectId:17,draftVersion:4,dirty:false}});
      document.querySelector('#m9-evidence-test')?.remove();
      const root=document.createElement('section'); root.id='m9-evidence-test'; document.querySelector('#workspace-results').append(root);
      results[renderer](root,view,{onFocusMember:()=>{},onReflect:()=>{}});
      return {text:root.textContent,levels:[...root.querySelectorAll('[data-teaching-level]')].map(el=>({level:el.dataset.teachingLevel,text:el.textContent})),available:view.available};
    }""", {"payload": payload, "renderer": renderer})


def evidence_payload():
    payload = sample_payload(state="TENSION")
    member = payload["explanation"]["blocks"][0]
    member["message_zh_CN"] = {"level_1": "该构件当前为受拉。", "level_2": "该物理构件的分析段均显示为受拉。", "level_3": "可结合各分析段的轴力数值进一步观察。"}
    for segment, force in zip(member["facts"]["segments"], [12.5, 4.25]):
        segment["axial_force_N"] = force
    member["professional_values"]["segments"] = deepcopy(member["facts"]["segments"])
    payload["comparison"]["member_comparisons"][0]["actual"]["segments"] = deepcopy(member["facts"]["segments"])
    return payload


def test_explain_levels_serve_conclusion_evidence_and_professional_tasks(m9_page):
    observed = render_teaching(m9_page, evidence_payload())
    levels = {entry["level"]: entry["text"] for entry in observed["levels"]}
    assert {"1", "2", "3"} <= levels.keys()
    assert "发生了什么" in levels["1"] and "受拉" in levels["1"]
    assert "依据是什么" in levels["2"] and "分析段 2" in levels["2"]
    assert "具体数值与来源" in levels["3"] and "12.5 N" in levels["3"]
    assert "4.25 N" in levels["3"] and "0.3 mm" in levels["3"]
    assert "第 1 次分析" in levels["3"]
    expect(m9_page.locator('#m9-evidence-test [data-teaching-level="3"]')).not_to_be_visible()
    m9_page.locator('#m9-evidence-test summary').click()
    expect(m9_page.locator('#m9-evidence-test [data-teaching-level="3"]')).to_be_visible()


def test_structured_explain_hides_internal_tokens_at_every_level(m9_page):
    payload = evidence_payload()
    sentinel_hash = "a" * 64
    payload["report"]["report"]["metadata"]["input_hash"] = sentinel_hash
    for block in payload["explanation"]["blocks"]:
        for level in ("level_1", "level_2", "level_3"):
            block["message_zh_CN"][level] += f" node:node-2 opaque:1 member-4 physical-snapshot-v2 INTERNAL_MAPPING_FAILURE {sentinel_hash}"
    observed = render_teaching(m9_page, payload)
    for sentinel in ("node:node-2", "opaque:1", "member-4", "physical-snapshot-v2", "INTERNAL_MAPPING_FAILURE", sentinel_hash):
        assert sentinel not in observed["text"]
    assert "节点 N2" in observed["text"] and "构件 M4" in observed["text"]
    assert "12.5 N" in observed["text"]
    accessible = m9_page.locator('#m9-evidence-test').aria_snapshot()
    assert "opaque:" not in accessible and sentinel_hash not in accessible


@pytest.mark.parametrize("width", [1024, 1280, 1440])
def test_four_result_tabs_and_disclosure_are_keyboard_accessible(m9_page, width):
    m9_page.set_viewport_size({"width": width, "height": 900})
    render_teaching(m9_page, evidence_payload())
    m9_page.evaluate("""async()=>{
      const {renderResultActions}=await import('/static/projects/workspace/results.js');
      renderResultActions(document.querySelector('#m9-evidence-test'),{onCompare:()=>{},onExplain:()=>{}});
    }""")
    root = m9_page.locator('#m9-evidence-test')
    expect(root.get_by_role('tab')).to_have_count(4)
    root.get_by_role('tab', name='结论', exact=True).focus()
    m9_page.keyboard.press('ArrowRight')
    expect(root.get_by_role('tab', name='预测对比', exact=True)).to_be_focused()
    root.locator('summary').focus()
    m9_page.keyboard.press('Enter')
    expect(root.locator('[data-teaching-level="3"]')).to_be_visible()
    assert m9_page.evaluate('document.documentElement.scrollWidth <= innerWidth')
