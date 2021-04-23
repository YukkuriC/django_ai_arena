import os

from django.db import models
from django.dispatch import receiver
from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.http import JsonResponse, HttpRequest
from django.utils import timezone
from django.core import mail
from django.conf import settings
from django.template import loader
from django.shortcuts import render
from usr_sys import models as usr_models
import json


def attach_settings(request):
    return {'settings': settings}


def auto_admin(model_pool):
    '''一行注册admin'''
    for md_name in dir(model_pool):
        md = getattr(model_pool, md_name)

        if isinstance(md, models.base.ModelBase):
            tmp = []
            for name, field in md.__dict__.items():
                if isinstance(field, models.query_utils.DeferredAttribute):
                    tmp.append(name)

            class AutoAdmin(admin.ModelAdmin):
                list_display = tmp

            try:
                admin.site.register(md, AutoAdmin)
            except admin.sites.AlreadyRegistered:
                pass


def set_autodelete(local_dict, model, field):
    '''
    使FileField自动清理文件
    '''
    def auto_delete_file_on_delete(sender, instance, **kwargs):
        file_field = getattr(instance, field, None)
        if file_field:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)

    def auto_delete_file_on_change(sender, instance, **kwargs):
        if not instance.pk:
            return

        try:
            old_file = getattr(model.objects.get(pk=instance.pk), field)
        except model.DoesNotExist:
            return

        new_file = getattr(instance, field)
        if not old_file == new_file:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)

    del1 = '%s_%s_del1' % (model.__name__, field)
    del2 = '%s_%s_del2' % (model.__name__, field)

    local_dict[del1] = auto_delete_file_on_delete
    local_dict[del2] = auto_delete_file_on_change

    models.signals.post_delete.connect(local_dict[del1], model)
    models.signals.pre_save.connect(local_dict[del2], model)


def show_date(date):
    """ 显示日期 """
    try:
        d_show = date.timetuple()
    except:
        return '-'
    d_now = timezone.now().timetuple()
    if d_show[:3] == d_now[:3]:  # 同一天显示时间
        pattern = "%H:%M"
        if d_show[3:5] == d_now[3:5]:  # 时分相同
            pattern += ':%S'
    elif d_show[0] == d_now[0]:  # 同年显示月日
        pattern = "%m{M}%d{D}"
    else:  # 不同年显示年月
        pattern = "%Y{Y}%m{M}"
    return date.strftime(pattern).format(Y='年', M='月', D='日')


if 'user system':

    def login_required(req_yes, req_email=True, target=None):
        if target == None:
            target = '/login/' if req_yes else '/home/'

        def decorator(func):
            def wrap(req, *a, **kw):
                if bool(req.session.get('userid')) == req_yes:
                    if req_yes and req_email and not get_user(
                            req).email_validated:
                        return redirect('/validate/')
                    return func(req, *a, **kw)
                return redirect(target)

            return wrap

        return decorator

    def get_user(request, update_login=False):
        try:
            user = usr_models.User.objects.get(id=request.session['userid'])
        except:
            return None
        user.login_datetime = timezone.now()
        user.save()
        return user

    def set_user(request, user):
        request.session['userid'] = user.id
        request.session['username'] = user.name
        if user.is_admin:
            request.session['username'] += ' (管理员)'

    def send_valid_email(user, request, type='valid'):
        if type == 'forgotpw':  # 忘记密码
            mail_class = usr_models.UserResetPwMail
            mail_name = 'userresetpwmail'
        else:  # 新用户激活
            mail_class = usr_models.UserMailCheck
            mail_name = 'usermailcheck'

        # create email checker
        if hasattr(user, mail_name):
            checker = getattr(user, mail_name)
            if timezone.now() < checker.send_time + timezone.timedelta(
                    minutes=settings.EMAIL_VALID_RESEND_MINUTES):
                messages.warning(request, '邮件发送过于频繁')
                return False
        else:
            checker = mail_class()
            checker.user = user
        checker.send_time = timezone.now()
        checker.activate()

        # send email
        expire_time = checker.send_time + timezone.timedelta(
            days=settings.EMAIL_VALID_LAST_DAYS)

        http = 'https' if request.is_secure() else 'http'
        host = settings.ROOT_HOST or request.META['HTTP_HOST']
        if type == 'forgotpw':
            link = '%s://%s/forgotpasswd/%s' % (http, host, checker.check_hash)
            title = '代码竞技场重设密码'
            template_name = 'email/resetpasswd.html'
        else:
            link = '%s://%s/validate/%s' % (http, host, checker.check_hash)
            title = '代码竞技场激活邮件'
            template_name = 'email/activation.html'

        html_content = loader.render_to_string(template_name, locals())
        mail.send_mail(title,
                       html_content,
                       settings.EMAIL_HOST_USER, [user.email],
                       html_message=html_content)

        messages.info(request, '邮件发送成功')
        return True


if 'pages':

    def sorry(request,
              code=404,
              title='Oops...',
              text=['你来到了', '一片没有知识的', '荒原']):
        if isinstance(text, str):
            text = [text]
        return render(request, 'sorry.html', locals(), status=code)
