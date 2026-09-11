from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView,LogoutView
from django.shortcuts import redirect,render
from .forms import ForcedPasswordChangeForm


class AccountLoginView(LoginView):
    template_name='accounts/login.html'


class AccountLogoutView(LogoutView):
    next_page='/accounts/login/'


@login_required
def password_change(request):
    if request.method=='POST':
        form=ForcedPasswordChangeForm(request.user,request.POST)
        if form.is_valid():
            user=form.save()
            user.must_change_password=False
            user.save(update_fields=['must_change_password'])
            update_session_auth_hash(request,user)
            return redirect('/events/')
    else:
        form=ForcedPasswordChangeForm(request.user)
    return render(request,'accounts/password_change.html',{'form':form})
