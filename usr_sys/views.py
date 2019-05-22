from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.template import loader
from django.conf import settings
from django.contrib import messages
from . import forms
from main.helpers import login_required, get_user, set_user, send_valid_email, sorry
from .models import User, UserMailCheck, UserResetPwMail


def index(request):
    return redirect('/home/')
    return render(request, 'index.html')


@login_required(0)
def register(request):
    '''
    注册
    '''
    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)

        # check if user exists
        if User.objects.filter(username=request.POST.get('username')):
            form.add_error('username', '用户名已被注册')
        if User.objects.filter(stu_code=request.POST.get('stu_code')):
            form.add_error('stu_code', '学号已被注册')
        if request.POST.get('passwd') != request.POST.get('pw2'):
            form.add_error('pw2', '两次密码输入不同')

        # input validation
        if form.is_valid():
            # register new user
            new_user = User()
            new_user.username = form.cleaned_data['username']
            new_user.stu_code = form.cleaned_data['stu_code']
            new_user.real_name = form.cleaned_data['name']
            new_user.register_datetime = timezone.now()
            new_user.set_passwd(form.cleaned_data['passwd'])
            set_user(request, new_user)
            messages.info(request, '注册成功')
            return redirect('/validate/')
        else:  # invalid input
            messages.warning(request, '请检查非法输入')
            return render(request, 'register.html', locals())
    return render(request, 'register.html', {'form': forms.RegisterForm()})


@login_required(0)
def login(request):
    '''
    登录
    '''
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        # check username
        key = request.POST.get('username')
        pw = request.POST.get('passwd')
        if key and pw:
            user = None
            try:
                user = User.objects.get(username=key)
            except:
                try:
                    user = User.objects.get(stu_code=key)
                except:
                    pass
            if user and user.match_passwd(pw):
                set_user(request, user)
                messages.info(request, '登录成功')
                return redirect('/home/')
        messages.warning(request, '用户名或密码错误')
        return render(request, 'login.html', locals())
    return render(request, 'login.html', {'form': forms.LoginForm()})


def logout(request):
    '''
    登出
    '''
    request.session.clear()
    return redirect('/login/')


@login_required(1, 0)
def validate(request):
    '''
    新用户电子邮件发送页面
    '''
    user = get_user(request)
    if user.email_validated:
        return redirect('/home/')

    # update validate link if (re)post
    if request.method == 'POST':
        send_valid_email(user, request)

    if hasattr(user, 'usermailcheck'):
        checker = user.usermailcheck
        send_time = checker.send_time
        expire_time = send_time + timezone.timedelta(
            days=settings.EMAIL_VALID_LAST_DAYS)
        resend_time = send_time + timezone.timedelta(
            minutes=settings.EMAIL_VALID_RESEND_MINUTES)
        server_time = timezone.now()
        resend_delta = max(int((resend_time - server_time).total_seconds()), 0)
        expire_delta = max(int((expire_time - server_time).total_seconds()), 0)
    return render(request, 'validate.html', locals())


def activate(request, code):
    '''
    激活电子邮件指向
    '''
    try:
        checker = UserMailCheck.objects.get(check_hash=code)
        if timezone.now() > checker.send_time + timezone.timedelta(
                settings.EMAIL_VALID_LAST_DAYS):
            raise ValueError
        checker.user.email_validated = True
        checker.user.save()
        set_user(request, checker.user)
        messages.info(request, '用户已激活')
        checker.delete()
    except Exception as e:
        messages.warning(request, '无效的激活链接')
    return redirect('/home/')


@login_required(1)
def home(request, user_override=None):
    '''
    个人主页
    user_override参数用于显示其他用户主页
    '''
    if user_override == None:
        user = get_user(request)
    else:
        user = user_override

    return render(request, 'home.html', locals())


@login_required(1, 0)
def changepasswd(request):
    if request.method == 'POST':
        form = forms.ChangePasswdForm(request.POST)

        # check old passwd
        user = get_user(request)
        if not user.match_passwd(request.POST.get('old_passwd')):
            form.add_error('old_passwd', '密码错误')
        if request.POST.get('new_passwd') != request.POST.get('new_pw2'):
            form.add_error('new_pw2', '两次密码输入不同')

        if form.is_valid():
            user.set_passwd(form.cleaned_data['new_passwd'])
            messages.info(request, '修改密码成功')
            return redirect('/home/')
        else:
            messages.warning(request, '请检查非法输入')
            return render(request, 'changepasswd.html', locals())
    return render(request, 'changepasswd.html',
                  {'form': forms.ChangePasswdForm()})


@login_required(1)
def user_settings(request):
    '''
    个人设置
    '''
    user = get_user(request)

    # GET请求
    if request.method == 'GET':
        return render(request, 'settings.html',
                      {'form': forms.SettingsForm(user.__dict__)})

    form = forms.SettingsForm(request.POST)
    if form.is_valid():
        user.nickname = form.cleaned_data['nickname']
        user.real_name = form.cleaned_data['real_name']
        user.save()
        return redirect('/home/')
    else:
        messages.warning(request, '请检查非法输入')
        return render(request, 'changepasswd.html', locals())


@login_required(1)
def view_user(request, userid):
    '''其它用户主页，快速访问对战页面'''

    # 验证用户
    try:
        user = User.objects.get(id=userid)
    except:
        try:
            user = User.objects.get(username=userid)
        except:
            return sorry('该用户不存在')

    # 本用户主页
    if user.id == request.session.get('userid'):
        return redirect('/home/')

    return home(request, user)


@login_required(0)
def forgotpasswd(request, code=None):
    if code == None:  # 验证页面
        form = forms.ForgotPasswdForm()

        # 判断发送邮件逻辑
        if request.method == 'POST':
            form = forms.ForgotPasswdForm(request.POST)

            # 检查用户名与学号匹配情况
            if form.is_valid():
                name = request.POST.get('username')
                code = request.POST.get('stu_code')
                try:
                    user = User.objects.get(username=name, stu_code=code)
                except:
                    form.add_error('username', '用户名与学号不匹配')
                    form.add_error('stu_code', '用户名与学号不匹配')

            # 发送邮件
            if form.is_valid():
                send_valid_email(user, request, 'forgotpw')
                return redirect('/login/')
            else:
                messages.warning(request, '请检查非法输入')
        return render(request, 'forgotpasswd.html', locals())
    else:
        try:
            checker = UserResetPwMail.objects.get(check_hash=code)
            if timezone.now() > checker.send_time + timezone.timedelta(
                    settings.EMAIL_VALID_LAST_DAYS):
                raise ValueError

            form = forms.ResetPasswdForm()
            if request.method == 'POST':
                form = forms.ResetPasswdForm(request.POST)
                if request.POST.get('new_passwd') != request.POST.get(
                        'new_pw2'):
                    form.add_error('new_pw2', '两次密码输入不同')
                if form.is_valid():
                    checker.user.set_passwd(form.cleaned_data['new_pw2'])
                    set_user(request, checker.user)
                    messages.info(request, '密码已重设')
                    checker.delete()
                    return redirect('/home/')
                messages.warning(request, '请检查非法输入')
            return render(request, 'changepasswd.html', locals())
        except:
            return sorry(request, text='无效的链接')
