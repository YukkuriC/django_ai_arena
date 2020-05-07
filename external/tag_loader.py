from django import template
from collections import defaultdict

register = template.Library()


# 模板注册元类
def RecordMeta(match_type):
    def _meta(name, root, attrs):
        res = type.__new__(type, name, root, attrs)
        RecordMeta.storage[match_type] = res()
        return res

    return _meta


RecordMeta.storage = defaultdict(object)


# 自动注册模板
def register_record(name):
    def _func(match, record):
        target = RecordMeta.storage[match.ai_type]
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
        返回先手胜利信息 (holder_win)
            0: 先手方胜利
            1: 后手方胜利
            None: 平局
            [0]: 是否为接收方胜利
            [1]: 是否为先手胜利
        """

    def r_holder(_, match, record):
        if _.i_holder(match, record):
            return match.code2.name
        return match.code1.name

    def r_winner(_, match, record):
        holder_win = _.i_winner(match, record)
        if holder_win is None:
            return '平手'
        code2_hold=_.i_holder(match, record)
        code2_win = (code2_hold==holder_win)
        return '%s (%s, %s)' % (
            match.code2.name if code2_win else match.code1.name,
            ('发起方', '接收方')[code2_win],
            ('后手', '先手')[holder_win],
        )


columns = ('r_holder', 'r_length', 'r_winner', 'r_win_desc', 'r_desc_plus')
for col in columns:
    register_record(col)
