from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q, Count, Max
from django.http import JsonResponse
from external import match_monitor
from external.factory import Factory
from main.helpers import login_required, get_user, sorry
from usr_sys.models import User
from . import forms
from .models import Code, PairMatch
import os, json, shutil, random


def game_info(request, AI_type):
    """列出所有可用的比赛，显示其规则，引用至站内对战入口与github项目"""
    # 验证游戏ID存在
    try:
        AI_type = int(AI_type)
        assert AI_type in settings.AI_TYPES
    except:
        return sorry(request, text='无效的游戏类型')
    title = settings.AI_TYPES[AI_type]
    request.session['curr_game'] = AI_type  # 设置当前页面游戏

    try:
        return render(request, 'game_info/%s.html' % AI_type, locals())
    except:
        return sorry(request, text='WORK IN PROGRESS')


if 'multi-view':

    def lobby(request):
        '''
        对战大厅
        列出所有比赛类型，最近的比赛记录等
        '''
        request.session['curr_game'] = ''  # 清除当前界面游戏
        games = {
            i: {
                'name': j,
                'size': 0,
                'users': 0
            }
            for i, j in settings.AI_TYPES.items()
        }

        # 统计每类AI数目
        grps = Code.objects.values('ai_type',
                                   'author').annotate(ncode=Count('id'))
        for grp in grps:
            target = games[grp['ai_type']]
            target['size'] += grp['ncode']
            target['users'] += 1

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

        # 用户均分统计
        users = all_codes.values('author').annotate(
            score=Max('score'), count=Count('id')).values(
                'author_id', 'author__username', 'author__nickname', 'score',
                'count').order_by('-score')

        return render(request, 'ladder.html', locals())


# 表单页
if 'forms':

    @login_required(1)
    def upload(request):
        ai_type = request.GET.get('id', '')
        user = get_user(request)

        if request.method == 'POST':
            form = forms.CodeUploadForm(request.POST, request.FILES)
            if form.is_valid():
                # 验证用户代码数未超标
                if user.code_set.filter(
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
                code.author = user
                code.edit_datetime = timezone.now()
                form.save()
                messages.info(request, '上传文件"%s"成功' % code.name)
                return redirect('/home/')
            else:
                messages.warning(request, '请检查非法输入')
                return render(request, 'upload.html', locals())
        form = forms.CodeUploadForm()
        return render(request, 'upload.html', locals())

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

        # 获取自由模式得分参数，转换为百分比
        score_ratio = settings.SCORE_FACTOR_NORANK * 100

        # 读取筛选条件
        my_code = request.GET.get('code1', '')
        target_code = request.GET.get('code2', '')

        if request.method == 'POST':
            form = forms.PairMatchFormFactory.get(AI_type, request.POST)
            my_code = request.POST.get('code1')
            target_code = request.POST.get('code2')
            if not (my_code and my_codes.filter(id=my_code)):
                form.errors['code1'] = '非法输入: %s' % my_code
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
    def ranked_match(request, AI_type):
        '''积分匹配赛'''

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

        # 读取筛选条件
        my_code = request.GET.get('code1', '')

        if request.method == 'POST':
            form = forms.PairMatchFormFactory.get(AI_type, request.POST)
            my_code = request.POST.get('code1')
            if not (my_code and my_codes.filter(id=my_code)):
                form.errors['code1'] = '非法输入: %s' % my_code

            # 选取目标代码
            if form.is_valid():
                my_code_obj = my_codes.filter(id=my_code)[0]
                target_codes = codes.exclude(author=request.session['userid'])
                target_codes = sorted(
                    target_codes,
                    key=lambda code: abs(code.score - my_code_obj.score)
                )[:settings.RANKING_RANDOM_RANGE]
                if not target_codes:
                    form.errors['code1'] = '暂无可用的匹配代码'

            if form.is_valid():  # run match
                target = random.choice(target_codes).id
                match_monitor.start_match(AI_type, my_code, target, form, True)
                messages.info(request, '创建比赛成功')
                return redirect('/code/%s/' % my_code)
            else:  # invalid input
                messages.warning(request, '请检查非法输入')
                return render(request, 'ranked_match.html', locals())
        form = forms.PairMatchFormFactory.get(AI_type)
        return render(request, 'ranked_match.html', locals())

    @login_required(1)
    def invite_match(request, AI_type):
        # TODO: 支持向其他用户发起指定参数的比赛
        request.session['curr_game'] = AI_type  # 设置当前页面游戏
        return sorry(request, text='WORK IN PROGRESS')


# 查看、编辑代码等
if 'view code':

    @login_required(1)
    def view_code(request, code_id, code_op=None):
        '''查看代码对象、分发下级命令'''

        # 获取代码对象
        try:
            code = Code.objects.get(id=int(code_id))
        except:
            return sorry(request, text='无效的代码编号')

        # 检测权限
        user = get_user(request)
        my_code = code.author == user

        # 代码主页
        if code_op == None:
            return render(request, 'view_code.html', locals())

        # 代码编辑页
        elif code_op == 'edit':
            return _code_editor(request, code, user, True)

        # 代码删除页
        elif code_op == 'del':
            return _code_del(request, code, user)

        # 查看公开代码
        elif code_op == 'view':
            return _code_editor(request, code, user, False)

        # 复制公开代码
        elif code_op == 'fork':
            return _code_fork(request, code, user)

        return sorry(request, text=['亲亲', '"%s"这样的命令' % code_op, '是不存在的呢'])

    def _code_editor(request, code, user, is_edit):
        '''
        CodeMirror代码编辑器页
        提供编辑自己代码+查看公开代码功能
        '''

        # 检测权限及重定向
        my_code = code.author == user

        if is_edit:
            if not my_code:  # 非本人进入编辑模式
                return redirect('/code/%s/view/' % code.id)
        else:
            if my_code:  # 本人进入查看模式
                return redirect('/code/%s/edit/' % code.id)
            elif not code.public:  # 查看非公开代码
                return sorry(request, 403, text='没有编辑权限')

        # GET请求输出代码至编辑器
        if request.method == 'GET':
            code_content = code.content.read().decode('utf-8', 'ignore')
            return render(request, 'edit_code.html', locals())

        # 非编辑模式拒绝POST
        elif not is_edit:
            return JsonResponse({})

        # POST请求ajax
        res = {}
        to_update = False

        # 更新名称
        new_name = request.POST.get('name')
        if new_name:
            new_name = new_name[:20]
            to_update = True
            code.name = new_name
            res['name'] = new_name

        # 更新代码是否公开
        new_public = request.POST.get('public')
        try:
            new_public = int(new_public)
        except:
            pass
        if isinstance(new_public, int):
            to_update = True
            code.public = bool(new_public)

        # 验证更新代码
        new_code = request.POST.get('code')
        if new_code:
            loader = Factory(code.ai_type)
            validated = False

            # 尝试读取代码
            try:
                loader.load_code(new_code, True)
                validated = True
                res['code_status'] = 0
                messages.info(request, '更新代码"%s"成功' % code.name)
            except Exception as e:
                messages.warning(request, '代码有误: ' + str(e))
                res['code_status'] = 1

            # 保存代码
            if validated:
                code_path = str(code.content)
                shutil.copyfile(code_path, code_path + '.bak')
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                to_update = True
                code.edit_datetime = timezone.now()
                try:
                    os.remove(code_path + '.bak')
                except:
                    pass

        if to_update:
            code.save()
        return JsonResponse(res)

    def _code_del(request, code, user):
        '''验证密码删除代码'''

        # 权限检测
        if not code.author == user:
            return sorry(request, 403, text='没有删除权限')

        # 检测密码验证
        if request.method == 'POST':
            pw = request.POST.get('check_pw', '')

            # 删除代码
            if user.match_passwd(pw):
                code.delete()
                messages.info(request, '代码已删除')
                return redirect('/home/')

            # 密码错误
            else:
                messages.warning(request, '密码错误')

        return render(request, 'delete_code.html', locals())

    def _code_fork(request, code, user):
        '''复制已有公开代码'''

        # 权限检测
        if not (code.author == user or code.public):
            return sorry(request, 403, text='没有复制权限')

        # 验证用户代码数未超标
        if user.code_set.filter(
                ai_type=code.ai_type).count() >= settings.MAX_CODE_PER_GAME:
            return sorry(request, 403, text='已超过最大可保留代码数')

        # 生成新代码
        new_code = Code(ai_type=code.ai_type, author=user)
        new_code.edit_datetime = timezone.now()
        new_code.public = code.public
        new_code.name = ('副本-' + code.name)[:20]

        # 保存副本代码
        new_content = ContentFile(code.content.read())
        new_code.content.save('test', new_content)

        new_code.save()
        messages.info(request, '创建副本"%s"成功' % new_code.name)
        return redirect('/home/')


# 查看比赛结果
if 'view':

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
            record_content = loader.stringfy_record(match_dir, record_id)
        except:
            return sorry(request, text='无效的记录编号')

        not_last_record = (record_id + 1 != match.finished_rounds)

        return render(request, loader.template_dir, locals())
