# 设置路径
import os, sys
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

import re, time, json
import constants as c
from plat import Platform
from .log_parser import parse_header, parse_logs, PLR_DICT
from ..helpers_core import stringfy_error


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
    plat.log.add(f'&e:{plat.error} run time error')
    plat.log.add(f'&e:{plat.winner} win')

    return plat


# 将比赛胜者转换为数据队列要求格式
def trans_winner(orig):
    if orig != None:
        orig = 1 - orig
    return orig


# 输出比赛记录至文件 - 已更新为JSON格式存储
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

    # 组装记录文件
    raw = {
        'id0': self.states[True]['index'][0],
        'name0': self.states[True]['path'],
        'id1': self.states[False]['index'][0],
        'name1': self.states[False]['path'],
        'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'logs': list(parse_logs('\n'.join(self.log))),  # 解析所有比赛记录
        'cause': '',  # 默认为得分结算
    }
    headers = ('timeout', 'violator', 'error', 'winner')
    tmp = (PLR_DICT[self.timeout], PLR_DICT[self.violator],
           PLR_DICT[self.error], PLR_DICT[self.winner])
    raw['winner'] = None if tmp[-1] == 'None' else int(tmp[-1][-1])

    for h, x in zip(headers[:-1], tmp[:-1]):
        if x != 'None':
            raw['cause'] = h
            break

    # 导出报错信息
    errors = []
    for k in (1, 0):
        if self.exception[k]:
            errors.append(stringfy_error(self.exception[k]))
    if len(errors) == 1:
        errors = errors[0]
    if errors:
        raw['error'] = errors

    with open(path, 'w', encoding='utf-8') as file:
        json.dump(raw, file, separators=',:')


# 读取比赛记录至json
def load_log(path):
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    if raw.startswith('{'):  # 直接读取JSON
        res = json.loads(raw)
    else:  # 解析文本存储格式
        res = parse_header(raw)
        res['logs'] = list(parse_logs(raw))
    return res