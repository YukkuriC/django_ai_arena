from django import template
register = template.Library()

import hashlib


@register.filter(name='g_icon')
def gravatar_icon(user, size=30):
    """ 使用学号邮箱生成gravatar对应图片路径 """
    return user.gravatar_icon(size)


@register.filter()
def if_plus(num):
    try:
        res = '+' if float(num) >= 0 else ''
        return res + num
    except:
        return num