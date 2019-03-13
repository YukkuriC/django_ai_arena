from django.template import Template, Context
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from functools import lru_cache, partial
from main.helpers import sorry
from match_sys.models import PairMatch, Code


@lru_cache()
def get_template(TEMPLATE, FIELDS, fields):
    '''获取比赛记录表格模板字符串'''
    content = ''.join(globals().get(FIELDS).get(key, '') for key in fields)
    return Template(globals().get(TEMPLATE) % content)


MATCH_TEMPLATE_BASE = '''{{max_page}}|
{%%with root_link="/match/"%%}
{%%for match in match_list%%}
<tr {%% with sublink=match.name %%}{%% include "sub/trow_link.html" %%}{%% endwith %%}>
%s
</tr>
{%%endfor%%}
{%%endwith%%}
'''

MATCH_FIELDS = {
    'code1':
    '''<td>
{% if code == match.code1%} {{match.code1.name}}
{% else %} <a href="/code/{{match.code1.id}}/">{{match.code1.name}}</a>
{% endif %}
</td>''',
    'code2':
    '''<td>
{% if code == match.code2%} {{match.code2.name}}
{% else %} <a href="/code/{{match.code2.id}}/">{{match.code2.name}}</a>
{% endif %}
</td>''',
    'time':
    '''<td>{{match.run_datetime|date:"Y/m/d H:i:s"}}</td>''',
    'rounds':
    '''<td>{{match.finished_rounds}}/{{match.rounds}}</td>''',
    'status':
    '''<td>{{match.get_status_display}}</td>''',
    'type':
    '''<td>{{match.get_ai_type_display}}</td>'''
}


def match_template(fields):
    return get_template('MATCH_TEMPLATE_BASE', 'MATCH_FIELDS', fields)


MATCH_PREFABS = {
    'send':
    match_template((
        'code2',
        'time',
        'rounds',
        'status',
    )),
    'recv':
    match_template((
        'code1',
        'time',
        'rounds',
        'status',
    )),
    'near':
    match_template((
        'time',
        'type',
        'code1',
        'code2',
        'rounds',
        'status',
    )),
}


def match_table_content(request):
    '''从ajax获取match表格内容'''

    # 获取模板
    prefab = request.GET.get('pre')
    if not prefab in MATCH_PREFABS:
        return HttpResponse('0|参数错误')
    template = MATCH_PREFABS[prefab]

    # 获取内容列表
    if prefab in ('send', 'recv'):
        try:
            code = Code.objects.get(id=request.GET.get('codeid'))
        except:
            return HttpResponse('0|代码读取错误')
        if prefab == 'send':
            match_list = code.pmatch1.all()
        else:
            match_list = code.pmatch2.all()
    elif prefab == 'near':
        match_list = PairMatch.objects.all()[:100]

    # 翻页功能
    page_size = settings.MAX_PAIRMATCH_DISPLAY  # 先不考虑可变页长
    max_page = (len(match_list) - 1) // page_size + 1
    page = request.GET.get('page')
    try:
        page = max(int(page), 0)
    except:
        page = 0
    match_list = match_list[page * page_size:(page + 1) * page_size]

    # 渲染内容
    content = template.render(Context(locals()))
    return HttpResponse(content)


CODE_TEMPLATE_BASE = '''{{max_page}}|
{%%with root_link="/code/"%%}
{%%for code in code_list%%}
<tr {%% with sublink=code.id %%}{%% include "sub/trow_link.html" %%}{%% endwith %%}>
%s
</tr>
{%%endfor%%}
{%%endwith%%}
'''

CODE_FIELDS = {
    'name':
    '<td>{{code.name}}</td>'
    '',
    'author':
    '<td><a href="/user/{{code.author.id}}">{{code.author.username}}</a></td>'
    '',
    'records':
    '''<td>
{{code.num_matches}}赛{{code.num_records}}战- {{code.num_wins}}胜{{code.num_loses}}负{{code.num_draws}}平
</td>''',
    'score':
    '''<td>{{code.score_show}}</td>''',
    'tools':
    '''<td>
<a class='btn-sm btn-info' href='/lobby/run_match/{{code.ai_type}}/?code2={{code.id}}'>发起对战</a>
</td>''',
}


def code_template(fields):
    return get_template('CODE_TEMPLATE_BASE', 'CODE_FIELDS', fields)


CODE_PREFABS = {
    'ladder': code_template(('name', 'author', 'records', 'score', 'tools')),
    'home': code_template(('name', 'author', 'records', 'score'))
}


def code_table_content(request):
    '''从ajax获取code表格内容'''

    # 获取模板
    prefab = request.GET.get('pre')
    if not prefab in CODE_PREFABS:
        return HttpResponse('0|参数错误')
    template = CODE_PREFABS[prefab]

    # 获取内容列表
    if prefab == 'ladder':
        try:
            AI_type = int(request.GET['type'])
            assert AI_type in settings.AI_TYPES
        except:
            return HttpResponse('0|参数错误')
        code_list = Code.objects.filter(ai_type=AI_type).order_by('-score')
    else:
        code_list = Code.objects.all()

    # 翻页功能
    page_size = settings.MAX_CODE_DISPLAY  # 先不考虑可变页长
    max_page = (len(code_list) - 1) // page_size + 1
    page = request.GET.get('page')
    try:
        page = max(int(page), 0)
    except:
        page = 0
    code_list = code_list[page * page_size:(page + 1) * page_size]

    # 渲染内容
    content = template.render(Context(locals()))
    return HttpResponse(content)
