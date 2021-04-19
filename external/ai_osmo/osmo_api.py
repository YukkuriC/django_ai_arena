# 设置路径
import os, sys
osmo_path = os.path.join(os.path.dirname(__file__), 'osmo.sessdsa', 'src')
sys.path.append(osmo_path)

import world, consts
import pickle, zlib
from .. import helpers_core

world.print = lambda *a, **kw: None


class FakeWorld:
    """ 用于覆盖初始化报错的对局 """

    def __init__(self, plrs, names):
        detail = [(isinstance(e, Exception) and e) for e in plrs]
        if all(detail):
            winner = None
        else:
            winner = not detail[1]
        self.result = {
            "players": names,
            "winner": winner,
            "cause": "RUNTIME_ERROR",
            "detail": detail,
            "data": [],
        }


def apply_params(params):
    """ 覆盖默认参数 """
    if not hasattr(consts, 'def_consts'):
        consts.def_consts = {**consts.Consts}
    consts.Consts.clear()
    for k, v in consts.def_consts.items():
        consts.Consts[k] = v
    for k, v in params.items():
        consts.Consts[k] = v


def one_race(modules, storages, plr_names, seed=None):
    '''运行一局比赛并输出结果对象'''
    # 创建World记录对象
    recorders = [world.WorldStat(consts.Consts["MAX_FRAME"]) for i in 'xx']
    for s, r in zip(storages, recorders):
        s['world'] = r

    # 初始化双方玩家对象
    plrs = [None, None]
    for i in (0, 1):
        try:
            plrs[i] = modules[i].Player(i, storages[i])
        except Exception as e:
            plrs[i] = e
    if any(isinstance(e, Exception) for e in plrs):  # 初始化报错
        return FakeWorld(plrs, plr_names)

    extra_mode = consts.Consts.get('extra_mode', '')

    wld = world.World(*plrs, plr_names, recorders, seed)
    while not wld.result:
        wld.update(consts.Consts["FRAME_DELTA"])
        extra_mode_wrap(wld, extra_mode)
    return wld


def save_log(wld, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    # 转为列表格式储存，除去所有死细胞
    tmp = {**wld.result}
    tmp['data'] = [[[
        cell.pos[0], cell.pos[1], cell.veloc[0], cell.veloc[1], cell.radius
    ] for cell in frame if not cell.dead] for frame in tmp['data']]

    # 将异常转换为带行号的信息
    tmp["detail"] = [(helpers_core.stringfy_error(e)
                      if isinstance(e, Exception) else e)
                     for e in tmp["detail"]]

    with open(path, 'wb') as f:
        f.write(zlib.compress(pickle.dumps(tmp), -1))


def load_log(path):
    with open(path, 'rb') as f:
        obj = pickle.loads(zlib.decompress(f.read()))
    return obj


import math, random
import cell


def extra_mode_wrap(world, mode):
    if not mode:
        return
    Consts = consts.Consts
    if mode == 'a':
        r = world.frame_count * 0.1
        world.cells.append(
            cell.Cell(
                len(world.cells),
                [Consts["WORLD_X"] / 2, Consts["WORLD_Y"] / 2],
                [6 * math.cos(r), 3 * math.sin(r)], 2))
