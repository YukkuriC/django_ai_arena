import os, sys
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    'dsa2021',
    'src',
))
from GameCore import Game
from HexagonForce import Generate_Hexagon
import config
if 'disable print':
    import HexagonForce
    HexagonForce.print = lambda *a, **kw: None

import random
from external.helpers_core import stringfy_error


def output_error(descrip):
    return stringfy_error(descrip) if isinstance(
        descrip, Exception) else [*map(stringfy_error, descrip)]


class GameWithModule(Game):
    @property
    def map(self):
        return self.get_history()

    def __init__(self, modules, names, params):
        """
        重写初始化
        params:
            modules: 双方玩家模块
            names: 双方姓名（code1/code2，用于标识先后手）
            params: 可重载比赛参数
        """
        # TODO 重写参数

        # 创建地图
        # TODO 可选多种地图
        maps = Generate_Hexagon(4, 0.20, 0.20)

        # 父类初始化
        super().__init__(*names, maps)

        # 尝试实例化玩家类
        players = [None] * 2
        errors = [None] * 2
        for i, mod in enumerate(modules):
            try:
                players[i] = mod.player_class(i)
            except Exception as e:
                errors[i] = e
        endgame, winner = False, None
        if any(errors):
            endgame = True
            if all(errors):
                self.map['result'] = output_error(errors)
            else:
                winner = int(bool(errors[0]))
                self.map['result'] = output_error(errors[1 - winner])
            self.map['result'] = '初始化错误: %s' % self.map['result']

        # 强制初始化
        self.__dict__.update(
            _Game__game_end=endgame,
            _Game__player=players,
            _Game__winner=winner,
        )

    def run(self):
        ''' 按平台规范写入胜者 '''
        if not self._Game__game_end:
            super().run()
        if self._Game__winner not in (0, 1):
            self._Game__winner = None
        self.map['winner'] = self._Game__winner


class NullPlayer:
    class player_class:
        player_func = None


class NullGame(GameWithModule):
    null_plr = [NullPlayer, NullPlayer]

    def __init__(self, winner, descrip, names, params):
        super().__init__(self.null_plr, names, params)
        record = self.map
        record['winner'] = winner
        record['result'] = output_error(descrip)
