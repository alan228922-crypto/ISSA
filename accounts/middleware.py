from django.shortcuts import redirect


class ForcedPasswordChangeMiddleware:
    """服务端限制强制改密用户，避免直接输入业务 URL 绕过安全状态。"""
    allowed_prefixes=('/accounts/password-change/','/accounts/logout/','/accounts/login/','/static/')

    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        user=getattr(request,'user',None)
        if user and user.is_authenticated and user.must_change_password and not request.path.startswith(self.allowed_prefixes):
            return redirect('accounts:password_change')
        return self.get_response(request)
