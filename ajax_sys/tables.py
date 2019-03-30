from django.template import Template, Context
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from functools import lru_cache, partial
from main.helpers import sorry
from match_sys.models import PairMatch, Code

# 设置页
template_base = '''{{{{max_page}}}}|
{{%with root_link="{root}"%}}
{{%for item in item_list%}}
<tr {{% with sublink={sub} %}}{{% include "sub/trow_link.html" %}}{{% endwith %}}>
{content}
</tr>
{{%endfor%}}
{{%endwith%}}
'''


class TablePageBase:
    root_link = NotImplemented
    sub_link = NotImplemented
    prefab_setter = []
    row_items = {}
    max_page_size = 10

    @classmethod
    def set_templates(cls):
        cls.template_prefabs = {}  # 模板缓存

        # 提前组装模板
        for name, fields in cls.prefab_setter:
            content = ''.join(
                cls.row_items.get(key, '') for key in fields.split())
            template_str = template_base.format(
                root=cls.root_link, sub=cls.sub_link, content=content)
            cls.template_prefabs[name] = Template(template_str)

    @classmethod
    def grab_content(cls, request, prefab):
        '''从ORM获取列表与额外参数'''
        return [], {}

    def __new__(cls, request):
        '''页面访问接口'''

        # 获取模板
        prefab = request.GET.get('pre')
        if not prefab in cls.template_prefabs:
            return HttpResponse('0|参数错误')
        template = cls.template_prefabs[prefab]

        # 获取内容列表
        try:
            item_list, params = cls.grab_content(request, prefab)
        except Exception as e:
            return HttpResponse('0|内容读取错误(%s: %s)' % (type(e).__name__, e))

        # 翻页功能
        page_size = cls.max_page_size  # 先不考虑可变页长
        max_page = (len(item_list) - 1) // page_size + 1
        page = request.GET.get('page')
        try:
            page = max(int(page), 0)
        except:
            page = 0
        item_list = item_list[page * page_size:(page + 1) * page_size]

        # 渲染内容
        content = template.render(Context(locals()))
        return HttpResponse(content)


class MatchTablePage(TablePageBase):
    root_link = '/match/'
    sub_link = 'item.name'
    prefab_setter = (
        ('send', 'code2 time rounds status'),
        ('recv', 'code1 time rounds status'),
        ('near', 'time type code1 code2 rounds status'),
    )
    row_items = {
        'code1':
        '''<td>
{% if params.code == item.code1%} {{item.code1.name}}
{% else %} <a href="/code/{{item.code1.id}}/">{{item.code1.name}}</a>
{% endif %}
</td>''',
        'code2':
        '''<td>
{% if params.code == item.code2%} {{item.code2.name}}
{% else %} <a href="/code/{{item.code2.id}}/">{{item.code2.name}}</a>
{% endif %}
</td>''',
        'time':
        '''<td>{{item.run_datetime|date:"Y/m/d H:i:s"}}</td>''',
        'rounds':
        '''<td>{{item.finished_rounds}}/{{item.rounds}}</td>''',
        'status':
        '''<td>{{item.get_status_display}}</td>''',
        'type':
        '''<td>{{item.get_ai_type_display}}</td>'''
    }

    @classmethod
    def grab_content(cls, request, prefab):
        params = {}
        if prefab in ('send', 'recv'):
            code = Code.objects.get(id=request.GET.get('codeid'))
            params['code'] = code
            if prefab == 'send':
                match_list = code.pmatch1.all()
            else:
                match_list = code.pmatch2.all()
        elif prefab == 'near':
            match_list = PairMatch.objects.all()[:100]

        return match_list, params


class CodeTablePage(TablePageBase):
    root_link = '/code/'
    sub_link = 'item.id'
    prefab_setter = (
        ('ladder', 'name author records score tools'),
        ('home', 'name author records score'),
    )
    row_items = {
        'name':
        '<td>{{item.name}}</td>',
        'author':
        '<td><a href="/user/{{item.author.id}}">{{item.author.name}}</a></td>',
        'records':
        '''<td>
{{item.num_matches}}赛{{item.num_records}}战- {{item.num_wins}}胜{{item.num_loses}}负{{item.num_draws}}平
</td>''',
        'score':
        '<td>{{item.score_show}}</td>',
        'tools':
        '''<td>
<a class='btn-sm btn-info' href='/lobby/run_match/{{item.ai_type}}/?code2={{item.id}}'>发起对战</a>
</td>''',
    }

    @classmethod
    def grab_content(cls, request, prefab):
        if prefab == 'ladder':
            AI_type = int(request.GET['type'])
            assert AI_type in settings.AI_TYPES
            code_list = Code.objects.filter(ai_type=AI_type).order_by('-score')
        else:
            code_list = Code.objects.all()
        return code_list, {}


MatchTablePage.set_templates()
CodeTablePage.set_templates()
