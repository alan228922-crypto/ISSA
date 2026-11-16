from django import forms


class CreateParticipantForm(forms.Form):
    team_number = forms.RegexField(label='队伍编号', regex=r'^[0-9]{1,2}$', max_length=2)
    captain_student_id = forms.CharField(label='队长学号（初始凭证）', max_length=128,
                                         widget=forms.PasswordInput(render_value=False))


class JoinParticipantForm(forms.Form):
    username = forms.CharField(label='既有账号', max_length=150)
    same_team_verified = forms.BooleanField(label='已核实这是同一支队伍')


class ReactivateParticipantForm(forms.Form):
    same_team_verified = forms.BooleanField(label='已核实这是同一支队伍')


class DeactivateParticipantForm(forms.Form):
    confirmed = forms.BooleanField(label='确认仅停用此赛事的参赛资格，保留项目和历史')
