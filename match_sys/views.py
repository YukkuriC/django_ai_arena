from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from external import match_monitor
from external.factory import Factory
from main.helpers import login_required, get_user, sorry
from usr_sys.models import User
from . import forms
from .models import Code, PairMatch
import os, json


def game_info(request):
    # TODO: 列出所有可用的比赛，显示其规则，引用至站内对战入口与github项目
    return redirect('/home/')


def lobby(request):
    # TODO: 对战大厅，列出所有比赛类型，最近的比赛记录等
    return redirect('/home/')


@login_required(1)
def invite_match(request):
    # TODO: 支持向其他用户发起指定参数的比赛
    return redirect('/home/')


# 表单页
if 'forms':

    @login_required(1)
    def upload(request):
        if request.method == 'POST':
            print(request.POST)
            form = forms.CodeUploadForm(request.POST, request.FILES)
            if form.is_valid():
                code = form.instance
                code.author = User.objects.get(id=request.session['userid'])
                code.edit_datetime = timezone.now()
                form.save()
                messages.info(request, '上传文件"%s"成功' % code.name)
                return redirect('/home/')
            else:
                messages.warning(request, '请检查非法输入')
                return render(request, 'upload.html', locals())
        return render(request, 'upload.html', {'form': forms.CodeUploadForm()})

    @login_required(1)
    def pairmatch(request):
        '''启动一对一比赛'''

        # 读取参数
        try:
            AI_type = int(request.GET.get('id'))
        except:
            AI_type = settings.DEFAULT_AI
        finally:
            title = settings.AI_TYPES[AI_type]

        # 获取可选AI列表
        codes = Code.objects.filter(ai_type=AI_type)
        my_codes = codes.filter(author=request.session['userid'])  # 我方所有
        target_codes = my_codes.union(codes.filter(public=True))  # 我方所有+所有公开

        if request.method == 'POST':
            form = forms.PairMatchFormFactory.get(AI_type, request.POST)
            my_code = request.POST.get('code1')
            target_code = request.POST.get('code2')
            if not (my_code and my_codes.filter(id=my_code)):
                form.errors['code1'] = '非法输入: %s' % target_code
            if not (target_code and
                    (my_codes.filter(id=target_code)
                     or codes.filter(public=True, id=target_code))):
                form.errors['code2'] = '非法输入: %s' % target_code
            if form.is_valid():  # run match
                match_monitor.start_match(AI_type, my_code, target_code, form)
                messages.info(request, '创建比赛成功')
                return redirect('/code/%s/' % my_code)
            else:  # invalid input
                messages.warning(request, '请检查非法输入')
                return render(request, 'pairmatch.html', locals())
        form = forms.PairMatchFormFactory.get(AI_type)
        return render(request, 'pairmatch.html', locals())


# 查看比赛结果
if 'view':

    @login_required(1)
    def view_code(request, code_id):
        # 获取代码对象
        try:
            code = Code.objects.get(id=int(code_id))
        except:
            return sorry(request, text='无效的代码编号')

        # 检测权限
        user = get_user(request)
        if not code.available(user):
            return sorry(request, 403, text='没有权限查看')

        # 处理操作请求
        if code.author==user:
            pass

        # 读取可查看比赛列表
        match_pool1 = [m for m in code.pmatch1.all() if m.available(user)]
        match_pool2 = [m for m in code.pmatch2.all() if m.available(user)]

        return render(request, 'view_code.html', locals())

    @login_required(1)
    def view_pairmatch(request, match_name):
        # 读取比赛对象
        try:
            match = PairMatch.objects.get(name=match_name)
        except:
            return sorry(request, text='无效的比赛地址')
        match_dir = os.path.join(settings.PAIRMATCH_DIR, match_name)

        # 检测权限
        user = get_user(request)
        if not match.available(user):
            return sorry(request, 403, text='没有权限查看')

        # 处理操作请求
        if match.code1.author==user:
            op=request.GET.get('op')
            if match.status==1 and op=='stop':
                match_monitor.kill_match(match.name)
                messages.info(request,'比赛已中止')
            elif match.status!=1 and op=='del':
                upper=match.code1.id
                match.delete()
                messages.info(request,'比赛记录已删除')
                return redirect('/code/%d'%upper)

        # 读取比赛记录
        loader = Factory(match.ai_type)
        records = loader.load_records(match)
        result_summary = loader.summary_records(records)
        result_stat = result_summary['stat']

        return render(request, 'view_match.html', locals())

    @login_required(1)
    def view_record(request, match_name, record_id):
        try:
            match = PairMatch.objects.get(name=match_name)
        except:
            return sorry(request, text='无效的比赛地址')
        match_dir = os.path.join(settings.PAIRMATCH_DIR, match_name)
        loader = Factory(match.ai_type)
        try:
            record_id = int(record_id)
            record = loader.load_record(match_dir, record_id)
            record_content = loader.stringfy_record(record)
        except:
            return sorry(request, text='无效的记录编号')

        not_last_record = (record_id + 1 != match.finished_rounds)

        return render(request, loader.template_dir, locals())
