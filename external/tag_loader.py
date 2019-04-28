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
            return func(match, record)
        return 'NotImplemented'

    register.filter(name=name)(_func)


columns = ('r_holder', 'r_length', 'r_winner', 'r_win_desc', 'r_desc_plus')
for col in columns:
    register_record(col)
