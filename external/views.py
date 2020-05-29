from django.contrib import messages
from django.shortcuts import render, redirect
from main import settings
from main.helpers import sorry
from .helpers_core import stringfy_error
from .factory import Factory
import os, time


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
    folders, files = [], []
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
                messages.warning(request, f'读取{f}时出错: {stringfy_error(e)}')
        else:
            folders.append(f)

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
            break

    return render(request, 'results/filetree.html', locals())


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
