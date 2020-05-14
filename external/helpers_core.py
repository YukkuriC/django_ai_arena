""" 放置无需加载django内核的辅助函数 """

MAX_ERR_LENGTH = 50


def stringfy_error(e):
    """ 显示异常类型、内容与行号（如果可行） """
    if not isinstance(e, Exception):
        return e

    # 显示错误信息
    err_str = str(e).replace('\r', '').replace('\n', r'\n')  # 移除换行符

    # 显示类型+行号
    res = '%s: %s' % (type(e).__name__, err_str)
    if e.__traceback__:
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        res = 'Line %s %s' % (tb.tb_lineno, res)

    # 过长时省略显示
    if len(res) > MAX_ERR_LENGTH:
        res = res[:MAX_ERR_LENGTH - 3] + '...'
    return res