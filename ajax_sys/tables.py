from django.template import Template, Context
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from functools import lru_cache, partial
from main.helpers import sorry, show_date
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
    template_prefabs = {}
    max_page_size = 10

    @classmethod
    def grab_content(cls, request, prefab):
        '''从ORM获取列表与额外参数'''
        return [], {}

    @classmethod
    def send_error(cls, err):
        """ 输出报错json """
        return JsonResponse({'size': 0, 'status': 1, 'content': err})

    @classmethod
    def grab_cell(cls, cell_type, item, params):
        pass

    @classmethod
    def grab_row_link(cls, prefab, item, params):
        return '#'

    @classmethod
    def grab_rows(cls, prefab, item_list, params):
        res = []
        template = cls.template_prefabs[prefab]
        for item in item_list:
            row = []
            for cell_type in template:
                try:
                    cell = cls.grab_cell(cell_type, item, params)
                except Exception as e:
                    cell = '*ERROR* %s' % e
                row.append(cell)
            row_data = [cls.grab_row_link(prefab, item, params), row]
            res.append(row_data)
        return res

    def __new__(cls, request):
        '''页面访问接口'''

        # 获取模板
        prefab = request.GET.get('pre')
        if not prefab in cls.template_prefabs:
            return cls.send_error('参数错误')
        template = cls.template_prefabs[prefab]

        # 获取内容列表
        try:
            item_list, params = cls.grab_content(request, prefab)
        except Exception as e:
            return cls.send_error('内容读取错误(%s: %s)' % (type(e).__name__, e))

        # 翻页功能
        try:
            page_size = max(int(request.GET.get('page_size')), 1)
        except:
            page_size = cls.max_page_size
        max_page = (len(item_list) - 1) // page_size + 1
        page = request.GET.get('page')
        try:
            page = max(int(page), 0)
        except:
            page = 0
        item_list = item_list[page * page_size:(page + 1) * page_size]

        # 渲染内容
        content = {
            'size': max_page,
            'status': 0,
            'headers': template,
            'root': cls.root_link,
        }
        content['rows'] = cls.grab_rows(prefab, item_list, params)
        return JsonResponse(content)


class MatchTablePage(TablePageBase):
    root_link = '/match/'
    template_prefabs = {
        'send': 'code2 time rounds status'.split(),
        'recv': 'code1 time rounds status'.split(),
        'near': 'time type code1 code2 rounds status'.split(),
        'near_type': 'time code1 code2 rounds status'.split(),
    }

    @classmethod
    def grab_cell(cls, cell_type, item, params):
        if cell_type[:4] == 'code':  # name, id or null
            code = getattr(item, cell_type)
            res = [code.name]
            if params.get('code') == code:
                res.append(None)
            else:
                res.append(code.id)
                # gravatar
                res.append(code.author.gravatar_icon(settings.TABLE_ICON_SIZE))
            return res
        if cell_type == 'code1':
            return [
                item.code1.name, None
                if params.get('code') == item.code1 else item.code1.id
            ]
        elif cell_type == 'code2':
            return [
                item.code2.name, None
                if params.get('code') == item.code2 else item.code2.id
            ]
        elif cell_type == 'time':
            return show_date(item.run_datetime)
        elif cell_type == 'rounds':
            return '%s/%s' % (item.finished_rounds, item.rounds)
        elif cell_type == 'status':
            return item.get_status_display()
        elif cell_type == 'type':
            return [item.get_ai_type_display(), item.ai_type]
        return cell_type

    @classmethod
    def grab_row_link(cls, prefab, item, params):
        return item.name

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
        elif prefab[:4] == 'near':
            match_list = PairMatch.objects.filter(code1__author__is_team=0)
            if prefab == 'near_type':  # 特定类型
                aitype = request.GET.get('aitype')
                aitype = int(aitype)
                assert aitype in settings.AI_TYPES
                match_list = match_list.filter(ai_type=aitype)
            match_list = match_list[:settings.RECENT_MATCH_SHOWN]
        return match_list, params


class CodeTablePage(TablePageBase):
    root_link = '/code/'
    template_prefabs = {
        'ladder': 'name author records score tools'.split(),
        'ladder_t': 'index author records score'.split(),
        'home': 'name type records score'.split(),
    }

    @classmethod
    def grab_cell(cls, cell_type, item, params):
        if cell_type == 'name':
            return item.name
        elif cell_type == 'type':
            return [item.get_ai_type_display(), item.ai_type]
        elif cell_type == 'author':
            au = item.author
            return [au.name, au.id, au.gravatar_icon(settings.TABLE_ICON_SIZE)]
        elif cell_type == 'records':
            return '%.1f%% in %s' % (item.winning_rate * 100, item.num_records)
        elif cell_type == 'score':
            return item.score_show
        elif cell_type == 'tools':
            res = []
            res.append(('自由挑战', '/lobby/run_match/%s/?code2=%s' %
                        (item.ai_type, item.id)))
            return res
        elif cell_type == 'index':
            return f'#{item.index}'
        return cell_type

    @classmethod
    def grab_row_link(cls, prefab, item, params):
        return item.id

    @classmethod
    def grab_content(cls, request, prefab):
        if prefab.startswith('ladder'):
            AI_type = int(request.GET['type'])
            assert AI_type in settings.AI_TYPES
            code_list = Code.objects.filter(ai_type=AI_type)

            # 分组筛选
            if prefab == 'ladder':
                code_list = code_list.filter(author__is_team=False)
            if prefab == 'ladder_t':
                code_list = code_list.filter(
                    author__is_team=True,
                    author__stu_code__startswith=request.GET.get('group'),
                )

            code_list = code_list.order_by('-score')
            for i, code in enumerate(code_list):
                code.index = i + 1
        else:
            code_list = Code.objects.all()
        return code_list, {}
