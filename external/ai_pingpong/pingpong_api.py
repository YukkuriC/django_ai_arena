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


def transform_obj(obj):
    if hasattr(obj, '__iter__'):
        if isinstance(obj, dict):
            return {k: transform_obj(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return list(map(transform_obj, obj))
    if isinstance(obj, (LogEntry, RacketData, BallData, CardData, Card, Vector,
                        RacketAction)):
        return {
            k: transform_obj(v)
            for k, v in obj.__dict__.items() if not k.startswith('__')
        }
    return obj


if __name__ == '__main__':
    import teams.T_idiot as bot
    import traceback
    import json, pickle, zlib, base64

    tmp = one_race([bot, bot], [{}, {}])
    tmp1 = transform_obj(tmp)
    t1 = json.dumps(tmp1, separators=(',', ':'))
    print(len(t1))
    t2 = pickle.dumps(tmp)
    print(len(t2))
    t3 = zlib.compress(t2, -1)
    print(len(t3))
    # while 1:
    #     try:
    #         print(repr(eval(input('>>> '))))
    #     except (EOFError,SystemExit):
    #         break
    #     except:
    #         traceback.print_exc()
    # # 终局打印信息输出
    # my_print(
    #     "%03d) %s win! for %s, West:%s(%d）, East:%s(%d),总时间: %d ticks %.3fs:%.3fs"
    #     % (round_count, main_table.winner, main_table.reason, west_name,
    #     main_table.players['West'].life, east_name,
    #     main_table.players['East'].life, main_table.tick,
    #     main_table.players['West'].clock_time,
    #     main_table.players['East'].clock_time))
