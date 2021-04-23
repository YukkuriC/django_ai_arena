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
        super().__init__(*names, config.MAX_TIME, config.MAX_TURN, maps)

        # 强制初始化
        self.player_func1 = modules[0].player_func
        self.player_func2 = modules[1].player_func
        self.__dict__['_Game__game_end'] = False

    def run(self):
        ''' 按平台规范写入胜者 '''
        winner = super().run()
        if winner not in (0, 1):
            winner = None
        self.map['winner'] = winner


class NullPlayer:
    player_func = None


class NullGame(GameWithModule):
    null_plr = [NullPlayer, NullPlayer]

    def __init__(self, winner, descrip, names, params):
        super().__init__(self.null_plr, names, params)
        record = self.map
        record['winner'] = winner
        record['result'] = stringfy_error(descrip) if isinstance(
            descrip, Exception) else [*map(stringfy_error, descrip)]
