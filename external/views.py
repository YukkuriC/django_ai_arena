from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as esc
from main import settings
from main.helpers import sorry, login_required
from .helpers_core import stringfy_error
from .factory import Factory
import os, time
from collections import Counter


@login_required(1)
def course_results(request, AI_type, folder):
    try:
        AI_type = int(AI_type)
        assert AI_type in settings.AI_TYPES
    except:
        return sorry(request, text='无效的游戏类型')
    title = settings.AI_TYPES[AI_type]
    request.session['curr_game'] = AI_type  # 设置当前页面游戏
    loader = Factory(AI_type)

    file_folder = '%s/results/%03d' % (settings.MEDIA_ROOT, AI_type)
    if not os.path.isdir(file_folder):
        return sorry(request, text='比赛记录未开放')
    if folder:
        folder = folder.replace('\\', '/').rstrip('/')
        file_folder = os.path.join(file_folder, folder)
    print(file_folder)
    if not (os.path.isdir(file_folder)):
        if os.path.isfile(file_folder):
            return course_view(request, AI_type, file_folder)
        return sorry(request, text='目录不存在')
    pool = os.listdir(file_folder)
    folders, files, errors = [], [], []
    for f in pool:
        f1 = os.path.join(file_folder, f)
        if os.path.isfile(f1):  # 读取记录
            try:
                rec_unit = {
                    'name': f,  # 记录名称
                    'record': loader.load_record_path(f1),  # 记录对象
                    'time': time.ctime(os.path.getmtime(f1)),  # 修改时间
                }
                files.append(rec_unit)
            except Exception as e:
                errors.append(f)
        else:
            try:
                folder_unit = {
                    'name': f,  # 记录名称
                    'time': time.ctime(os.path.getctime(f1)),  # 修改时间
                }
                folders.append(folder_unit)
            except Exception as e:
                errors.append(f)

    # 加载tags
    for record in files:
        record['tags'] = loader.analyze_tags(record['record'])

    # 加载额外信息
    extra = extra_info(AI_type, files)

    # 根据GET参数决定排序方式
    sort_method = request.GET.get(
        'sort',
        request.session.get('course_results_sort', 'name'),
    )
    request.session['course_results_sort'] = sort_method  # 缓存参数于session中
    sort_keys = {'name': '名称', 'time': '时间'}
    for key in sort_keys:
        if sort_method == key:
            files.sort(key=lambda x: x[key])
            folders.sort(key=lambda x: x[key])
            break

    return render(request, 'results/filetree.html', locals())


@login_required(1)
def course_view(request, AI_type, file):
    try:
        AI_type = int(AI_type)
        assert AI_type in settings.AI_TYPES
    except:
        return sorry(request, text='无效的游戏类型')
    title = settings.AI_TYPES[AI_type]

    loader = Factory(AI_type)
    record = loader.load_record_path(file)
    record_content = loader.stringfy_record_obj(record)
    return render(request, 'renderer/%s.html' % AI_type, locals())


def extra_info(AI_type, records):
    """
    解析额外信息
    返回待显示信息
    """
    logs = []

    # 提取胜者信息
    extra_info_scores(AI_type, records, logs)  # 整个文件夹统计比分

    return logs


def extra_info_scores(AI_type, records, logs):
    """ 统计比分信息并输出至记录 """
    # 计分字典
    # c[n1,n2] = c[n2,n1] = {n1:0, n2:0}
    score_counter = {}

    for record_pack in records:
        record = record_pack['record']

        # 获取信息接口
        names = pick_names(AI_type, record)
        winner = pick_winner(AI_type, record)

        # 获取计分字典
        if names in score_counter:
            curr_counter = score_counter[names]
        else:
            curr_counter = {n: 0 for n in names}
            score_counter[names] = score_counter[names[::-1]] = curr_counter

        # 输出单记录与比分信息
        record_extra = f'发起方: {names[0]}; '
        if record['winner'] == None:
            record_extra += '平局'
            for n in names:
                curr_counter[n] += 0.5
        else:
            winner_name = names[winner]
            curr_counter[winner_name] += 1
            record_extra += f'胜者: {winner_name}'
        record_pack['extra'] = record_extra  # 写入额外信息

    # 组装比分字符串
    name_used = set()
    for names, score_pair in score_counter.items():
        if names in name_used:
            continue
        name_used.add(names[::-1])  # 移除反向键值
        data = list(score_pair.items())
        base = f'''<div class='row'>
        <div class='col-sm-4 text-left'>{esc(data[0][0])}</div>
        <div class='col-sm-4 text-center'>{data[0][1]} : {data[1][1]}</div>
        <div class='col-sm-4 text-right'>{esc(data[1][0])}</div>
        </div>'''
        logs.append(mark_safe(f'<h2 style="text-align:center">{base}</h2>'))


def pick_names(AI_type, record):
    """ 按类型提取双方代码名称 """
    if AI_type == 3:  # osmo
        return tuple(record['players'])
    if AI_type == 4:  # 2048
        return tuple(
            os.path.basename(os.path.splitext(record[f'name{i}'])[0])
            for i in range(2))
    if AI_type == 5:  # stellar
        names = record['player_name']
        return tuple(names[str(i)] for i in (0, 1))

    return ('foo', 'bar')


def pick_winner(AI_type, record):
    """ 按类型提取胜者 """
    return record['winner']