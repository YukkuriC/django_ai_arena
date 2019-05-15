from ._base import BasePairMatch
from .ai_pingpong import PingPongMatch
from .ai_paperio import PaperIOMatch
from .ai_osmo import OsmoMatch

_mapper = {
    1: PingPongMatch,
    2: PaperIOMatch,
    3: OsmoMatch,
}


def Factory(match_id, *args, **kw):
    '''
    工厂函数，获取PairMatch类
    仅输入比赛id时返回类
    输入参数时返回实例
    '''
    obj = _mapper.get(match_id, BasePairMatch)
    if args or kw:
        obj = obj(*args, **kw)
    return obj
