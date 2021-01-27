__doc__ = '''
井字棋基础设施
包含棋盘类与单局游戏运行内核
'''

from threading import Thread
from time import process_time

if 'enums':
    OK = 0  # 游戏继续
    ENDGAME = 1  # 形成三连
    DRAW = 2  # 棋盘已满平局
    INVALID = -1  # 非法返回值（类型错误/出界）
    CONFILCT = -2  # 冲突落子（下于已有棋子位置）
    ERROR = -3  # 代码报错
    TIMEOUT = -4  # 代码超时


class Board:
    """
    基础棋盘类，用于计算局面情形+发放双方玩家所用局面
    使用数字1、2分别代表不同方玩家落子
    """
    def __init__(self):
        self.pool = {}  # 仅填充1/2的字典
        self.history = []  # 落子历史

    def get_board(self, plr: int):
        """
        为指定玩家编号返回其局面字典
        字典键为2长度元组，每位数字（0，1，2）分别代表行号与列号
        返回对象中包含3*3棋盘位置，对应值均为字符串，含义如下：
            "S": 我方落子
            "F": 对方落子
            "E": 空
        """
        res = {}
        for x in range(3):
            for y in range(3):
                if (x, y) in self.pool:
                    res[x, y] = 'S' if self.pool[x, y] == plr else 'F'
                else:
                    res[x, y] = 'E'
        return res

    def drop(self, plr, pos):
        """
        指定玩家编号plr在指定位置pos落子
        返回落子结果
        """
        if self._drop_data_check(pos):  # 非法落子检查
            self.history.append('INVALID')
            return INVALID
        self.history.append(pos)
        if pos in self.pool:  # 冲突落子检查
            return CONFILCT
        self.pool[pos] = plr  # 落子，检查游戏结束状态
        return self._check_endgame()

    def _drop_data_check(self, pos):
        """
        检验落子位置对象是否符合要求
        要求：
            * 必须为列表或元组
            * 长度必须为2
            * 每位均为int，取值只可为0,1,2
        """
        if not isinstance(pos, (list, tuple)):
            return INVALID
        if len(pos) != 2:
            return INVALID
        for i in pos:
            if not (isinstance(i, int) and 0 <= i <= 2):
                return INVALID
        return OK

    def _check_endgame(self):
        """ 检查游戏状态是否结束 """
        for x in range(3):
            if self._3_equal(self.pool.get((x, i))
                             for i in range(3)):  # axis 0
                return ENDGAME
            if self._3_equal(self.pool.get((i, x))
                             for i in range(3)):  # axis 1
                return ENDGAME
        if self._3_equal(self.pool.get((i, i)) for i in range(3)):  # 正对角线
            return ENDGAME
        if self._3_equal(self.pool.get((i, 2 - i)) for i in range(3)):  # 反对角线
            return ENDGAME
        return OK  # 不执行平局判断

    def _3_equal(self, row):
        """ 辅助函数：检查一行3数（非空）相等状态 """
        row = iter(row)
        n1 = next(row)
        if not n1:
            return False
        for n in row:
            if n != n1:
                return False
        return True


class Game:
    """
    井字棋游戏对象
    接收运行双方代码并收集结果
    codes:
        双方代码模块，其中包含play函数，可接收Board.get_board结果作为参数并返回落子位置
    names:
        双方代码模块名称
    timeout:
        时间限制
    """
    def __init__(self, codes, names=['code1', 'code2'], timeout=10):
        self.codes = codes
        self.names = names
        self.timeout = timeout

    @staticmethod
    def _stringfy_error(e):
        return '%s: %s' % (
            type(e).__name__,
            e,
        )

    @staticmethod
    def _thread_wrap(code, board, thr_output: dict):
        """
        线程内运行代码，输出结果

        输入:
            code: 待运行模块
            board: 当前局面
            output: 容纳返回值的字典
                "result": 模块play函数运行结果
                "error": 捕捉的运行异常
                "dt": 运行用时 
        """
        res = {
            "result": None,
            "error": None,
        }

        try:
            t1 = process_time()
            output = code.play(board)
            t2 = process_time()
            res['result'] = output
        except Exception as e:
            t2 = process_time()
            res['error'] = Game._stringfy_error(e)

        res['dt'] = t2 - t1
        thr_output.update(res)

    def _get_result(self, winner, reason, extra=None):
        """
        构造比赛结果字典
        "orders": 该局落子顺序
        "winner": 胜者
            0 - 先手胜
            1 - 后手胜
            None - 平局
        "reason": 终局原因序号
        "extra": 额外描述
        "timeouts": 双方使用时间历史
        """
        return {
            'names': self.names,
            'orders': self.board.history,
            'winner': winner,
            'reason': reason,
            'extra': extra,
            'timeouts': self.timeout_history,
        }

    def match(self):
        """
        运行一场比赛
        返回值: 比赛结果字典
        """
        self.board = Board()
        timeouts = [self.timeout] * 2
        self.timeout_history = []

        for nround in range(9):
            # 构造当局进程
            plr_idx = nround % 2
            thread_output = {}
            frame = self.board.get_board(plr_idx + 1)
            thr = Thread(target=self._thread_wrap,
                         args=(self.codes[plr_idx], frame, thread_output))

            # 限时运行
            thr.start()
            thr.join(timeouts[plr_idx])

            # 判断线程死循环
            if thr.is_alive():
                return self._get_result(1 - plr_idx, TIMEOUT, '死循环')

            # 计时统计，判断超时
            timeouts[plr_idx] -= thread_output['dt']
            if timeouts[plr_idx] < 0:
                return self._get_result(1 - plr_idx, TIMEOUT)
            self.timeout_history.append(timeouts.copy())

            # 判断报错
            if thread_output['error']:
                return self._get_result(
                    1 - plr_idx,
                    ERROR,
                    thread_output['error'],
                )

            # 落子判断
            res = self.board.drop(plr_idx + 1, thread_output['result'])
            if res == OK:  # 继续循环
                continue
            return self._get_result(
                plr_idx if res == ENDGAME else 1 - plr_idx,
                res,
            )

        return self._get_result(None, DRAW)  # 平局


if __name__ == '__main__':
    import codes.dumb_ordered as plr1, codes.dumb_random as plr2

    game = Game([plr1, plr2])
    print(game.match())
