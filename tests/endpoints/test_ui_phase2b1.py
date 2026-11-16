"""Workspace presentation boundaries and unmodified public event hooks."""
from html.parser import HTMLParser
import pytest
from django.urls import reverse
from tests.application.test_physical_draft import context

pytestmark = pytest.mark.django_db


class Controls(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[]
    def handle_starttag(self, tag, attrs):
        self.rows.append((tag,dict(attrs)))


def test_workspace_has_grouped_labeled_svg_controls_without_duplicate_hooks(client, context):
    owner, project, _, _ = context
    client.force_login(owner)
    response = client.get(reverse('projects:workspace',kwargs={'project_id':project.pk}))
    assert response.status_code == 200
    html=response.content.decode();parsed=Controls();parsed.feed(html)
    assert 'ui/controls.css' in html and 'workspace/workspace-ui.css' in html
    assert 'aria-label="绘图工具"' in html and 'aria-label="编辑工具"' in html
    for hook in ['data-cad-copy','data-cad-move','data-cad-rotate','data-cad-stretch','data-cad-length','data-cad-command-input','data-cad-transform-command','data-cad-grid-visible','data-cad-object-snap','data-cad-ortho','data-cad-shortcuts-open']:
        matches=[(tag,attrs) for tag,attrs in parsed.rows if hook in attrs]
        assert len(matches)==1,hook
    assert html.count('id="workspace-canvas"')==1
    for icon in ['select','node','member','support','load','copy','move','rotate','stretch','length','save','fit']:
        assert 'icons.svg#'+icon in html
    assert any(a.get('id') == 'workspace-bootstrap' for _,a in parsed.rows)
    assert not any('data-av01-canvas' in a for _,a in parsed.rows)


def test_preanalysis_tasks_have_labeled_sections_and_engineering_cautions(client, context):
    owner, project, _, _ = context;client.force_login(owner)
    html=client.get(reverse('projects:workspace',kwargs={'project_id':project.pk})).content.decode()
    assert '构件受力判断' in html and '最大位移位置' in html and '代表性传力路径' in html
    assert '预测是你的判断，不是计算结果' in html
    assert '交叉不自动连接' in html
    assert '箭头为显示尺度，请以数值为准' in html
    assert 'id="workspace-error"' in html and 'data-legacy-draft-export' not in html
    parsed=Controls();parsed.feed(html)
    for hook in ['data-prediction-start','data-prediction-complete','data-prediction-skip']:
        assert sum(hook in attrs for _,attrs in parsed.rows)==1
    for element_id in ['workspace-model-check','workspace-analyze']:
        assert sum(attrs.get('id')==element_id for _,attrs in parsed.rows)==1
