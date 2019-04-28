import os, sys
pingpong_path = os.path.dirname(__file__)
sys.path.append(pingpong_path)

from table import Table, LogEntry, RacketData, BallData, CardData, DIM, TMAX, PL, RS
from table import ROUND_NUMBER, print_none, my_print
from table import Card, Vector, RacketAction
import pickle, zlib
import shelve, pickle, json


def do_race(num_rounds, codes, plr_names=['code1', 'code2'], params=None):
    """
    执行num_rounds轮游戏
    输出每局游戏的结果记录
    """

    # 初始化
    storages = [{}, {}]  # 双方记录空间
    total_logs = []

    # 运行多局比赛
    for round_count in range(num_rounds):
        res = one_race(codes, storages, plr_names, params)
        total_logs.append(res)

    # 输出比赛记录
    return total_logs


def one_race(codes, storages, plr_names, params=None):
    sides = ('West', 'East')
    kw = ('serve', 'play', 'summarize')

    # 生成球桌
    main_table = Table()
    for i, side in enumerate(sides):
        main_table.players[side].bind_play(plr_names[i],
                                           *(getattr(codes[i], x) for x in kw))

    # 比赛记录
    log = []

    # 读取历史数据
    for i, side in enumerate(sides):
        main_table.players[side].set_datastore(storages[i])

    # 发球
    main_table.serve()

    # 开始打球
    while not main_table.finished:
        # 记录日志项
        log.append(
            LogEntry(main_table.tick,
                     RacketData(main_table.players[main_table.side]),
                     RacketData(main_table.players[main_table.op_side]),
                     BallData(main_table.ball),
                     CardData(main_table.card_tick, main_table.cards,
                              main_table.active_card)))
        # 运行一趟
        main_table.time_run()

    # 记录最后的回合
    log.append(
        LogEntry(main_table.tick,
                 RacketData(main_table.players[main_table.side]),
                 RacketData(main_table.players[main_table.op_side]),
                 BallData(main_table.ball),
                 CardData(main_table.card_tick, main_table.cards,
                          main_table.active_card)))

    # 终局，让双方进行本局总结
    main_table.postcare()

    # 终局，保存复盘资料
    return {
        'DIM': DIM,
        'TMAX': TMAX,
        'tick_step': main_table.tick_step,
        'West': plr_names[0],
        'East': plr_names[1],
        'tick_total': main_table.tick,
        'winner': main_table.winner,
        'winner_life': main_table.players[main_table.winner].life,
        'reason': main_table.reason,
        'log': log
    }


def save_log(log, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, 'wb') as f:
        f.write(zlib.compress(pickle.dumps(log), -1))


def load_log(path):
    with open(path, 'rb') as f:
        obj = pickle.loads(zlib.decompress(f.read()))
    return obj


def jsonfy(obj):
    '''将比赛记录转换为可json序列化的结构'''

    def _j(obj):
        # LogEntry保留
        if isinstance(obj, LogEntry):  # tick,side,op,ball,card
            return {
                k: _j(v)
                for k, v in obj.__dict__.items() if not k.startswith('__')
            }

        # Card重用映射
        if isinstance(obj, Card):  # code,params,pos
            obj = (obj.code, obj.param, _j(obj.pos))  # 转换为元组
            if obj not in card_mapper:  # 插入新的卡片映射
                card_mapper[obj] = len(card_pool)
                card_pool.append(obj)
            return card_mapper[obj]  # 返回映射表下标

        # 其余类型
        if isinstance(obj, Vector):  # x,y
            obj = (obj.x, obj.y)
        if isinstance(obj, CardData):  # tick,cards,active_card
            obj = (obj.card_tick, obj.cards, obj.active_card)
        if isinstance(obj, BallData):  # pos,vel
            obj = (obj.pos, obj.velocity)
        if isinstance(obj, RacketAction):  # bat,acc,run,card
            obj = (obj.bat, obj.acc, obj.run, obj.card)
        if isinstance(obj, RacketData):
            # life,pos,action,*life_costs*4,cardbox
            obj = (obj.life, obj.pos, obj.action, obj.bat_lf, obj.acc_lf,
                   obj.run_lf, obj.card_lf, obj.card_box)

        # 统一递归处理列表与字典
        if hasattr(obj, '__iter__'):
            if isinstance(obj, dict):
                return {k: _j(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return tuple(map(_j, obj))

        return obj  # 其余对象

    card_mapper = {}
    card_pool = []
    res = _j(obj)
    res['card_map'] = card_pool
    return res


def recover_log(obj):
    '''将可json序列化结构复原为比赛记录对象'''
    card_pool = obj['card_map']
    del obj['card_map']
    # TODO
    return obj
