# 设置路径
import os, sys
osmo_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(osmo_path)

import world, consts
import pickle, zlib

world.print = lambda *a, **kw: None


def apply_params(params):
    """ 覆盖默认参数 """
    if not hasattr(consts, 'def_consts'):
        consts.def_consts = {**consts.Consts}
    consts.Consts.clear()
    for k, v in consts.def_consts:
        consts.Consts[k] = v
    for k, v in params.items():
        consts.Consts[k] = v


def one_race(modules, storages, plr_names):
    '''运行一局比赛并输出结果对象'''
    plrs = [m.Player(i, s) for i, m, s in zip((0, 1), modules, storages)]
    wld = world.World(*plrs, plr_names)
    while not wld.result:
        wld.update(consts.Consts["FRAME_DELTA"])
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

    with open(path, 'wb') as f:
        f.write(zlib.compress(pickle.dumps(tmp), -1))


def load_log(path):
    with open(path, 'rb') as f:
        obj = pickle.loads(zlib.decompress(f.read()))
    return obj
