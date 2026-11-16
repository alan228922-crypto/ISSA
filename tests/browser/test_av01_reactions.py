"""Task3: isolated production Renderer, supplied facts vs genuine Runs labeled."""
from copy import deepcopy
import math

import pytest
from django.urls import reverse
from tests.application.test_physical_draft import context
from tests.endpoints.test_analysis_visualization import saved_context
from tests.browser.av01_harness import av01_page,projection_fixture,expected_context,mount,load_modules,screenshot

pytestmark=pytest.mark.browser


@pytest.mark.parametrize('rx,ry',[(84,0),(-84,0),(0,326),(0,-326),(84,-326)])
def test_reaction_components_match_saved_sign_and_value(av01_page,rx,ry):
    p=projection_fixture();p['reactions'][0].update(rx_N=rx,ry_N=ry);mount(av01_page,p)
    for component,value in [('Rx',rx),('Ry',ry)]:
        arrow=av01_page.locator(f'[data-av01-reaction][data-component="{component}"]')
        if value==0:assert arrow.count()==0;continue
        assert arrow.count()==1
        assert float(arrow.get_attribute('data-value'))==value
        line=arrow.locator('line');dx=float(line.get_attribute('x2'))-float(line.get_attribute('x1'));dy=float(line.get_attribute('y2'))-float(line.get_attribute('y1'))
        assert (dx>0)==(value>0) if component=='Rx' else (dy<0)==(value>0)
        assert 20<=math.hypot(dx,dy)<=64.0000001
        assert f'{component} = {value:+d} N' in av01_page.locator('[data-mount]').inner_text()


@pytest.mark.parametrize('value,expected',[(0,'0'),(-0.0,'0'),(1e-12,'1e-12'),(-1e-12,'-1e-12'),(1e9,'1e+9'),(None,'暂不可用'),(float('nan'),'暂不可用'),(float('inf'),'暂不可用')])
def test_zero_tiny_and_numeric_formatting(av01_page,value,expected):
    load_modules(av01_page)
    actual=av01_page.evaluate('(v)=>av01.formatVisualizationNumber(v)',value)
    assert actual==expected
    assert av01_page.evaluate('()=>av01.formatVisualizationNumber(0.12345678901234568,{exact:true})')=='0.12345678901234568'


@pytest.mark.parametrize('value',[0,-0.0,1e-12,-1e-12])
def test_zero_has_no_arrow_tiny_has_a_nonzero_arrow(av01_page,value):
    p=projection_fixture();p['reactions'][0].update(rx_N=value,ry_N=0);p['reactions'][1].update(rx_N=84 if value else 0,ry_N=0);mount(av01_page,p)
    node=av01_page.locator('[data-av01-reaction][data-analysis-node="node:n1"]')
    assert node.count()==(1 if value else 0)
    if value:
        assert abs(float(node.get_attribute('data-value')))==1e-12
        line=node.locator('line');assert math.hypot(float(line.get_attribute('x2'))-float(line.get_attribute('x1')),float(line.get_attribute('y2'))-float(line.get_attribute('y1')))==pytest.approx(20)
        assert 'e-12' in av01_page.locator('[data-mount]').inner_text()
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


def test_extreme_finite_reaction_ranges_remain_finite_and_bounded(av01_page):
    p=projection_fixture();p['reactions'][0].update(rx_N=1e308,ry_N=-1e-308);mount(av01_page,p)
    arrows=av01_page.locator('[data-av01-reaction]')
    assert arrows.count()==2
    for line in arrows.locator('line').all():
        coords=[float(line.get_attribute(k)) for k in ['x1','x2','y1','y2']]
        assert all(math.isfinite(c) for c in coords)
        assert 20<=math.hypot(coords[1]-coords[0],coords[3]-coords[2])<=64.000001
    assert 'Infinity' not in av01_page.locator('[data-av01-canvas]').inner_html()


def test_same_node_supports_share_one_reaction_display(av01_page):
    p=projection_fixture();p['supports'][1]['analysis_node_id']='node:n1';p['reactions']=p['reactions'][:1];p['reactions'][0]['support_ids']=['s1','s2'];p['nodes'][0]['support_ids']=['s1','s2'];p['nodes'][1]['support_ids']=[];mount(av01_page,p)
    assert av01_page.locator('[data-av01-reaction]').count()==2
    assert av01_page.locator('[data-av01-reaction-row]').count()==1
    av01_page.locator('[data-av01-values] summary').click()
    assert av01_page.locator('[data-av01-reaction-row]').inner_text().count('支座')>=2
    assert av01_page.evaluate('()=>JSON.stringify(inputFacts)===beforeFacts')


@pytest.mark.parametrize('value',[None,float('nan'),float('inf')])
def test_missing_or_invalid_reaction_is_not_a_zero(av01_page,value):
    p=projection_fixture();p['reactions'][0]['rx_N']=value;mount(av01_page,p)
    assert av01_page.locator('[data-av01-reaction]').count()==0
    assert '暂不可用' in av01_page.locator('[data-mount]').inner_text()


@pytest.mark.parametrize('field',['runId','revisionId','modelHash','inputHash'])
def test_wrong_snapshot_context_cannot_render(av01_page,field):
    p=projection_fixture();context=expected_context(p);context[field]='wrong';mount(av01_page,p,context=context)
    assert av01_page.locator('[data-av01-original-segment]').count()==0
    assert '暂不可用' in av01_page.locator('[data-mount]').inner_text()


def test_internal_ids_never_become_visible_labels(av01_page):
    p=mount(av01_page);text=av01_page.locator('[data-mount]').inner_text()
    for raw in ['node:n1','m1:1',p['provenance']['model_hash'],p['provenance']['input_hash']]:assert raw not in text
    assert not av01_page.locator('[data-mount] input[type=text],[data-cad-node-grip],[contenteditable]').count()
    assert '箭头长度经过显示缩放' in text
    screenshot(av01_page,'task3-reactions-1280')


@pytest.mark.django_db(transaction=True)
def test_support_direct_load_uses_saved_reaction(saved_context,client,av01_page):
    from analysis.orchestration import analyze_project
    from modeling.services import save_physical_draft
    from projects.workspace import _draft
    from concurrent.futures import ThreadPoolExecutor
    from django.db import connections
    from analysis.models import AnalysisRun
    def prepare():
        try:
            owner,project,_,_,_=saved_context
            payload=deepcopy(_draft(project));payload['expected_draft_version']=project.draft_version
            target={'target_node_client_key':'n1'} if payload['schema_version'].endswith('v2') else {'target_connection_client_key':'c1'}
            payload['node_loads'].append({'client_key':'direct',**target,'fx_N':30,'fy_N':0,'label':'支座直接外力'})
            save_physical_draft(actor=owner,project=project,payload=payload);project.refresh_from_db()
            run=analyze_project(project=project,actor=owner,expected_draft_version=project.draft_version);assert run.status=='SUCCESS'
            client.force_login(owner)
            assert client.get(reverse('projects:analysis_data',kwargs={'project_id':project.pk,'run_id':run.pk})).status_code==200
            response=client.get(reverse('projects:analysis_visualization',kwargs={'project_id':project.pk,'run_id':run.pk}));assert response.status_code==200
            return response.json()['visualization'],run.pk,deepcopy(run.result_json),run.model_revision.physical_snapshot_schema_version
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:
        projection,run_id,before,schema=executor.submit(prepare).result()
    mount(av01_page,projection)
    av01_page.locator('[data-case-origin]').evaluate("el=>el.textContent='真实保存 Run · 独立 Renderer（授权 API，非正式 Results 挂载）'")
    assert abs(projection['reactions'][0]['rx_N'])==pytest.approx(130)
    arrow=av01_page.locator('[data-av01-reaction][data-component=Rx]');assert arrow.count()==1
    assert float(arrow.get_attribute('data-value'))==projection['reactions'][0]['rx_N']
    def persisted():
        try:return AnalysisRun.objects.get(pk=run_id).result_json
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:assert executor.submit(persisted).result()==before
    screenshot(av01_page,'task3-genuine-direct-load-'+schema)


def test_exact_zero_reactions_are_explicit_without_directional_glyphs(av01_page):
    p=projection_fixture()
    for row in p['reactions']:row.update(rx_N=0,ry_N=0)
    mount(av01_page,p)
    assert av01_page.locator('[data-av01-reaction]').count()==0
    assert '反力均为 0 N' in av01_page.locator('[data-av01-status]').inner_text()


def test_label_overflow_has_a_real_readonly_numeric_fallback(av01_page):
    p=projection_fixture();p['label_source']['nodes'][0]['label']='左支座的历史工程说明'*30
    mount(av01_page,p)
    assert av01_page.locator('[data-av01-overflow]').is_visible()
    av01_page.locator('[data-av01-values] summary').click()
    assert av01_page.locator('[data-av01-reaction-row]').count()==2
    assert '84' in av01_page.locator('[data-av01-values]').inner_text()
    assert '-326' in av01_page.locator('[data-av01-values]').inner_text()
