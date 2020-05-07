# 设置路径
import os, sys
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

import re, time
import constants as c
from plat import Platform
from .log_parser import parse_header, parse_logs


# 根据给定参数生成Platform所需数据
def gen_states(players, names):
    """
    Params:
        players: 参赛双方代码模块
        names: 参赛双方名称 (记录于path中)
    """
    states = {}
    for i in (0, 1):
        states[1 - i] = {
            'player': players[i],
            'index': (i, 1 - i),
            'path': names[i],
            'time': 0,
            'time0': 0,
            'error': False,
            'exception': None,
        }
    return states


# 单场比赛函数
def one_match(players, params, names):
    """
    Params:
        players: 参赛双方代码模块
        params: 比赛参数
        names: 参赛双方名称 (记录于path中)
    """
    players = [object.__new__(p.Player) for p in players]

    # 初始参数
    states = gen_states(players, names)

    # 运行比赛
    plat = Platform(states, '', None, 0, params['max_time'],
                    params['max_turn'])
    plat.results = plat.play()
    return plat


# 在运行报错时生成备选对象
def fake_runner(winner, params, names):
    """
    Params:
        winner: 胜者
        params: 比赛参数
        names: 参赛双方名称 (记录于path中)
    """
    states = gen_states('xx', names)
    plat = Platform(states, '', None, 0, params['max_time'],
                    params['max_turn'])

    # 手动写入比赛结果
    plat.winner = trans_winner(winner)
    plat.error = 'both' if winner == None else 'player %d' % (1 - winner)

    return plat


# 将比赛胜者转换为数据队列要求格式
def trans_winner(orig):
    if orig != None:
        orig = 1 - orig
    return orig


# 输出比赛记录至文件
def dump_log(self, path):
    """
    Params:
        self: 已完成比赛的平台对象 (命名为self用于复用代码)
        path: 待输出文件路径
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    # 获取所有棋子并计数
    results = {
        True: self.board.getScore(True),
        False: self.board.getScore(False)
    }
    scores = {True: {}, False: {}}
    for level in range(1, c.MAXLEVEL):
        scores[True][level] = results[True].count(level)
        scores[False][level] = results[False].count(level)

    with open(path, 'w', encoding='utf-8') as file:
        myDict = {
            True: 'player 0',
            False: 'player 1',
            None: 'None',
            'both': 'both'
        }  # 协助转换为字符串
        title = 'player0: %d from path %s\n' % (self.states[True]['index'][0], self.states[True]['path']) + \
                'player1: %d from path %s\n' % (self.states[False]['index'][0], self.states[False]['path']) + \
                'time: %s\n' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + \
                '{:*^45s}\n'.format('basic record')
        file.write(title)
        file.write('=' * 45 + '\n|{:^10s}|{:^10s}|{:^10s}|{:^10s}|\n'.format('timeout', 'violator', 'error', 'winner') + \
                   '-' * 45 + '\n|{:^10s}|{:^10s}|{:^10s}|{:^10s}|\n'.format(myDict[self.timeout], myDict[self.violator], myDict[self.error], myDict[self.winner]) + \
                   '=' * 45 + '\n')
        file.write('=' * 60 + '\n|%6s|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|\n' % ('player', *range(1, c.MAXLEVEL)) + \
                   '-' * 60 + '\n|%6d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|\n' % (0, *[scores[True][_] for _ in range(1, c.MAXLEVEL)]) + \
                   '-' * 60 + '\n|%6d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|%3d|\n' % (1, *[scores[False][_] for _ in range(1, c.MAXLEVEL)]) + \
                   '=' * 60 + '\n')
        file.write('{:*^45s}\n'.format('complete record'))
        for log in self.log:
            file.write(log + '\n')  # '&'表示一条log的开始


# 读取比赛记录至json
def load_log(path):
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    res = parse_header(raw)
    res['logs'] = list(parse_logs(raw))
    return res