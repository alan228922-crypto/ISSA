from django import forms


class ProjectCreateForm(forms.Form):
    name = forms.CharField(label='项目名称', max_length=200, strip=True, initial='我的结构方案')
