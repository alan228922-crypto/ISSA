from django import forms
from django.forms import formset_factory

from .models import Material


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = (
            "name",
            "E_MPa",
            "density_g_per_mm3",
            "tensile_strength_MPa",
            "compressive_strength_MPa",
            "source_type",
            "note",
        )
        labels = {
            "name": "材料名称",
            "E_MPa": "弹性模量 E（MPa）",
            "density_g_per_mm3": "密度（g/mm³）",
            "tensile_strength_MPa": "抗拉强度（MPa，可选）",
            "compressive_strength_MPa": "抗压强度（MPa，可选）",
            "source_type": "数据来源",
            "note": "说明",
        }


class RectangleSectionForm(forms.Form):
    name = forms.CharField(label="截面名称", max_length=200)
    width_mm = forms.DecimalField(label="宽度（mm）", min_value=0.000001)
    height_mm = forms.DecimalField(label="高度（mm）", min_value=0.000001)
    density_g_per_mm3 = forms.DecimalField(label="密度（g/mm³）", min_value=0)

    def definition(self):
        return {
            "schema_version": "section-definition-v1",
            "type": "rectangle",
            "width_mm": float(self.cleaned_data["width_mm"]),
            "height_mm": float(self.cleaned_data["height_mm"]),
            "density_g_per_mm3": float(self.cleaned_data["density_g_per_mm3"]),
        }


class CompositeSectionForm(forms.Form):
    name = forms.CharField(label="截面名称", max_length=200)


class CompositeComponentForm(forms.Form):
    width_mm = forms.DecimalField(label="宽度（mm）", min_value=0.000001)
    height_mm = forms.DecimalField(label="高度（mm）", min_value=0.000001)
    center_x_mm = forms.DecimalField(label="中心 X（mm）")
    center_y_mm = forms.DecimalField(label="中心 Y（mm）")
    angle_deg = forms.DecimalField(label="旋转角度（°）")
    density_g_per_mm3 = forms.DecimalField(label="密度（g/mm³）", min_value=0)

    def definition(self):
        return {key: float(self.cleaned_data[key]) for key in (
            "width_mm", "height_mm", "center_x_mm", "center_y_mm", "angle_deg", "density_g_per_mm3",
        )}


CompositeComponentFormSet = formset_factory(
    CompositeComponentForm, extra=0, can_delete=True, min_num=1, validate_min=True,
)
