from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Max
from external import match_monitor
from external.factory import Factory
from main.helpers import login_required, get_user, sorry
from usr_sys.models import User
from . import forms
from .models import Code, PairMatch
import os, json


def game_info(request):
    # TODO: 列出所有可用的比赛，显示其规则，引用至站内对战入口与github项目
    return sorry(request, text='WORK IN PROGRESS')


if 'multi-view':

    def lobby(request):
        '''
        对战大厅
        列出所有比赛类型，最近的比赛记录等
        '''
        request.session['curr_game'] = ''  # 清除当前界面游戏
        games = {i: {'name': j} for i, j in settings.AI_TYPES.items()}

        # 统计每类AI数目
        pool = []
        for i in games:
            codes = Code.objects.filter(ai_type=i)
            games[i]['size'] = len(codes)
            games[i]['users'] = len(set(c.author for c in codes))

        # 抓取最近的比赛记录
        matches = PairMatch.objects.all()[:settings.MAX_PAIRMATCH_DISPLAY]

        return render(request, 'lobby.html', locals())

    def ladder(request, AI_type):
        '''天梯'''

        # 读取参数
        try:
            AI_type = int(AI_type)
            assert AI_type in settings.AI_TYPES
        except:
            return sorry(request, text='无效的比赛编号')
        title = settings.AI_TYPES[AI_type]
        request.session['curr_game'] = AI_type  # 设置当前页面游戏

        # 代码排序
        all_codes = Code.objects.filter(ai_type=AI_type)
        sorted_codes = all_codes.order_by('-score')

        # 翻页筛选 TODO
        codes = sorted_codes

        # 用户均分统计
        users = all_codes.values('author').annotate(
            score=Max('score'), count=Count('id')).values(
                'author_id', 'author__username', 'score',
                'count').order_by('-score')

        return render(request, 'ladder.html', locals())


# 表单页
if 'forms':

    @login_required(1)
    def upload(request):
        ai_type = request.GET.get('id', '')

        if request.method == 'POST':
            form = forms.CodeUploadForm(request.POST, request.FILES)
            if form.is_valid():
                # 验证用户代码数未超标
                if Code.objects.filter(
                        author=request.session['userid'],
                        ai_type=form.cleaned_data['ai_type']).count(
                        ) >= settings.MAX_CODE_PER_GAME:
                    return sorry(
                        request,
                        403,
                        text=[
                            '已超过最大可上传代码数',
                            '请删除不必要的代码',
                            '或在已有代码上进行修改',
                        ])

                code = form.instance
                code.author = User.objects.get(id=request.session['userid'])
                code.edit_datetime = timezone.now()
                form.save()
                messages.info(request, '上传文件"%s"成功' % code.name)
                return redirect('/home/')
            else:
                print(form.errors)
                messages.warning(request, '请检查非法输入')
                return render(request, 'upload.html', locals())
        form = forms.CodeUploadForm()
        return render(request, 'upload.html', locals())

    @login_required(1)
    def edit_code(request, code_id):
        return sorry(request, text='WORK IN PROGRESS')

    @login_required(1)
    def pairmatch(request, AI_type):
        '''启动一对一比赛'''

        # 读取参数
        try:
            AI_type = int(AI_type)
            assert AI_type in settings.AI_TYPES
        except:
            return sorry(request, text='无效的比赛编号')
        title = settings.AI_TYPES[AI_type]
        request.session['curr_game'] = AI_type  # 设置当前页面游戏

        # 获取可选AI列表
        codes = Code.objects.filter(ai_type=AI_type)
        my_codes = codes.filter(author=request.session['userid'])  # 我方所有
        # 筛选对方代码
        code2_empty = True
        try:
            target_user = request.GET.get('user2')
            if target_user:
                target_codes = codes.filter(author=target_user)
                if target_codes:
                    code2_empty = False
                else:
                    messages.warning(request, '用户没有上传代码')
        except:
            messages.warning(request, '输入用户非法')
        if code2_empty:
            target_codes = codes.all()  # 所有代码

        # 读取筛选条件
        my_code = request.GET.get('code1', '')
        target_code = request.GET.get('code2', '')

        if request.method == 'POST':
            form = forms.PairMatchFormFactory.get(AI_type, request.POST)
            my_code = request.POST.get('code1')
            target_code = request.POST.get('code2')
            if not (my_code and my_codes.filter(id=my_code)):
                form.errors['code1'] = '非法输入: %s' % target_code
            if not (target_code and target_codes.filter(id=target_code)):
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

    @login_required(1)
    def invite_match(request, AI_type):
        # TODO: 支持向其他用户发起指定参数的比赛
        request.session['curr_game'] = AI_type  # 设置当前页面游戏
        return sorry(request, text='WORK IN PROGRESS')


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
        my_code = code.author == user

        # 读取可查看比赛列表
        match_pool1 = code.pmatch1.all()
        match_pool2 = code.pmatch2.all()

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
        my_match = match.code1.author == user

        # 处理操作请求
        if my_match:
            op = request.GET.get('op')
            if match.status == 1 and op == 'stop':
                match_monitor.kill_match(match.name)
                messages.info(request, '比赛已中止')
            elif match.status != 1 and op == 'del':
                upper = match.code1.id
                match.delete()
                messages.info(request, '比赛记录已删除')
                return redirect('/code/%d' % upper)

        # 获取等级分变动
        if match.delta_score != None:
            delta_show = '+' if match.delta_score >= 0 else ''
            delta_show += '%.2f' % match.delta_score

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
