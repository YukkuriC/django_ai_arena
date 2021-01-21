from ._base import BasePairMatch
from .ai_pingpong import PingPongMatch
from .ai_paperio import PaperIOMatch
from .ai_osmo import OsmoMatch
from .ai_2048 import _2048Match
from .ai_ttt import TTTMatch

_mapper = {
    0: TTTMatch,
    1: PingPongMatch,
    2: PaperIOMatch,
    3: OsmoMatch,
    4: _2048Match,
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
