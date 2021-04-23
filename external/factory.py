from ._base import BasePairMatch


def FactoryDeco(match_type):
    def _deco(cls):
        _mapper[match_type] = cls
        return cls

    return _deco


_mapper = {}


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
