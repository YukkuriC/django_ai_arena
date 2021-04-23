from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from collections import defaultdict

register = template.Library()


# 模板注册元类
def RecordDeco(match_type):
    def _deco(cls):
        RecordDeco.storage[match_type] = cls()
        return cls

    return _deco


RecordDeco.storage = defaultdict(object)


# 自动注册模板
def register_record(name):
    def _func(match, record):
        target = RecordDeco.storage[match.ai_type]
        func = getattr(target, name, None)
        if func:
            try:
                return func(match, record)
            except Exception as e:
                return '*ERROR* %s' % e
        return 'NotImplemented'

    register.filter(name=name)(_func)


# 模板基类
class RecordBase:
    def i_holder(_, match, record):
        """返回该记录是否为玩家2先手 (code2_hold)"""

    def i_winner(_, match, record):
        """
        返回先手胜利信息 (holder_lost)
            0: 先手方胜利
            1: 后手方胜利
            None: 平局
        """

    def r_holder(_, match, record):
        if _.i_holder(match, record):
            return match.code2.name
        return match.code1.name

    def r_winner(_, match, record):
        holder_lose = _.i_winner(match, record)
        if holder_lose is None:
            return '平手'
        code2_hold = _.i_holder(match, record)
        code2_win = (code2_hold != holder_lose)
        return '%s (%s, %s)' % (
            match.code2.name if code2_win else match.code1.name,
            ('发起方', '接收方')[code2_win],
            ('先手', '后手')[holder_lose],
        )


columns = ('r_holder', 'r_length', 'r_winner', 'r_win_desc', 'r_desc_plus')
for col in columns:
    register_record(col)


# 显示记录标签
@register.simple_tag
def record_tags(tags, default_color='inherit'):
    res = ['<span>']

    for tag in tags:
        res.append(
            f'<b style="color:{tag[1] if len(tag)>1 else default_color}">{conditional_escape(tag[0])}</b>'
        )

    res.append('</span>')

    return mark_safe(' '.join(res))
