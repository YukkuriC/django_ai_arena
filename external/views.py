from django.shortcuts import render, redirect
from django.http import JsonResponse
from main import settings
from main.helpers import sorry
from .factory import Factory
import os, pickle, zlib, json


def course_results(request, AI_type, folder):
    try:
        AI_type = int(AI_type)
        assert AI_type in settings.AI_TYPES
    except:
        return sorry(request, text='无效的游戏类型')
    title = settings.AI_TYPES[AI_type]
    request.session['curr_game'] = AI_type  # 设置当前页面游戏

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
        if os.path.isfile(f1):
            files.append(f)
        else:
            folders.append(f)
    debug = {
        'type': AI_type,
        'dir': file_folder,
        'pool': pool,
    }
    return render(request, 'results/filetree.html', locals())


def course_view(request, AI_type, file):
    try:
        AI_type = int(AI_type)
        assert AI_type in settings.AI_TYPES
    except:
        return sorry(request, text='无效的游戏类型')
    title = settings.AI_TYPES[AI_type]

    with open(file, 'rb') as f:
        record_content = pickle.loads(zlib.decompress(f.read()))
        record_content = json.dumps(record_content, separators=(',', ':'))
    return render(request, 'renderer/%s.html' % AI_type, locals())
