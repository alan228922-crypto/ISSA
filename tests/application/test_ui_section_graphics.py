"""显示投影与旋转的边界；不计算或验证截面性质。"""
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_section_view_preserves_real_dimensions_rotation_and_global_y():
    module = (ROOT / 'materials/static/materials/section-graphics.js').as_uri()
    script = f'''import {{sectionView}} from {json.dumps(module)};
const v=sectionView([{{width_mm:2,height_mm:6,center_x_mm:10,center_y_mm:-3,angle_deg:30}}],400,300);
console.log(JSON.stringify({{scale:v.scale,bounds:v.bounds,origin:v.project(10,-3),right:v.project(12,-3),above:v.project(10,-1),rect:v.rectangles[0]}}));'''
    result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value['right']['x'] - value['origin']['x'] == pytest.approx(2 * value['scale'])
    assert value['above']['y'] - value['origin']['y'] == pytest.approx(-2 * value['scale'])
    assert value['rect']['width'] / value['rect']['height'] == pytest.approx(1 / 3)
    assert value['rect']['angle'] == -30
    assert value['bounds']['right'] - value['bounds']['left'] == pytest.approx(2 * 3**.5 / 2 + 3)
    assert not any(key in value for key in ['A_mm2', 'Ix_mm4', 'Iy_mm4', 'centroid_x_mm'])
