import copy
import random
import math
import time

# 每次组合打多少局
ROUND_NUMBER = 5
# 每局的物理时限（单方）
ROUND_CLOCK = 30.0
# 桌面的坐标系，单位"pace"
DIM = (-900000, 900000, 0, 1000000)
# 最大时间，单位"tick"，每个回合3600tick，200回合
TMAX = 800000
# 球的初始坐标(x,y)，在west中间
BALL_POS = (DIM[0], (DIM[3] - DIM[2]) // 2)
# 球的初速度，(vx,vy)，单位"p/t"，向东北飞行
BALL_V = (1000, 1000)
# 球拍的生命值，100个回合以上
RACKET_LIFE = 100000
# 迎球和跑位扣减距离除以系数的平方（LIFE=0-2500)
FACTOR_DISTANCE = 20000
# 加速则扣减速度除以系数结果的平方（LIFE=0-2500)
FACTOR_SPEED = 20
# 游戏方代码
PL = {'West': 'W', 'East': 'E'}
# 游戏结束原因代码
RS = {'invalid_bounce': 'B', 'miss_ball': 'M', 'life_out': 'L', 'time_out': 'T',
      'clock_out': 'K', 'run_error': 'E'}
# 道具出现频率每多少ticks出现一个道具
CARD_FREQ = int(3600 * 2.5)
# 道具出现的空间范围
CARD_EXTENT = (-800000, 800000, 100000, 900000)
# 道具箱的最大容量
MAX_CARDS = 3
# 球桌上最多道具
MAX_TABLE_CARDS = 10
# 卡牌代码
CARD_SPIN = 'SP'  # 旋转球：用于抵消被用道具方施加在球拍上的加速，使之正常反弹回来；param=0.5，增加的速度乘以parm
CARD_SPIN_PARAM = 0.5
CARD_DSPR = 'DS'  # 隐身术：隐藏被用道具方的位置和跑位方向1次；param=0，位置乘以parm，方向乘以parm
CARD_DSPR_PARAM = 0
CARD_INCL = 'IL'  # 补血包：给被用道具方补血（增加体力值）；param=2000，life加上param
CARD_INCL_PARAM = 2000
CARD_DECL = 'DL'  # 掉血包：给被用道具方减血（减少体力值）；param=2000，life减去param
CARD_DECL_PARAM = 2000
CARD_TLPT = 'TP'  # 瞬移术：被用道具方可以移动一段距离而不消耗体力值；param=250000，只作用在跑位阶段
CARD_TLPT_PARAM = 250000
CARD_AMPL = 'AM'  # 变压器：放大被用道具方的体力值损失；param=2；体力值损失增加1倍。
CARD_AMPL_PARAM = 2
ALL_CARDS = [(CARD_SPIN, CARD_SPIN_PARAM), (CARD_DSPR, CARD_DSPR_PARAM), (CARD_INCL, CARD_INCL_PARAM),
             (CARD_DECL, CARD_DECL_PARAM), (CARD_TLPT, CARD_TLPT_PARAM), (CARD_AMPL, CARD_AMPL_PARAM)]


def print_none(*args, **kwargs):
    pass
    return


my_print = print


# print = print_none


def sign(n):  # 返回n的符号，小于0为-1，否则为1
    return -1 if n < 0 else 1


def copy_card(card):  # 安全拷贝道具
    if isinstance(card, str):
        return card
    return Card(card.code, card.param, copy.copy(card.pos)) if card is not None else None


class Card:  # 道具
    def __init__(self, code, param, pos):
        self.code = code
        self.param = param
        self.pos = pos  # 道具所在的位置

    def __eq__(self, other):  # 判断相等，可以是道具代码，也可以是Card对象
        if isinstance(other, str):
            return self.code == other
        elif isinstance(other, Card):
            return self.code == other.code
        else:
            return False


class CardBox(list):  # 道具箱，list类型的子类
    def collect(self, card):  # 添加道具到道具箱，如果道具箱满的话，就移除最旧的道具腾出空间
        while self.isfull():
            self.pop(0)
        else:
            self.append(card)

    def discard(self, card):  # 移除道具，card参数可以是代码字符串或者Card对象
        if card in self:
            return self.pop(self.index(card))
        else:
            return None

    def isfull(self):  # 返回道具箱是否已满
        return len(self) >= MAX_CARDS

    def __str__(self):  # 输出道具名
        ret_str = '['
        for card in self:
            ret_str += card.code + ' '
        ret_str += ']'
        return ret_str


class Vector:  # 矢量
    def __init__(self, x, y=None):
        if y is None and isinstance(x, tuple):
            self.x, self.y = x
        else:
            self.x, self.y = x, y

    def __add__(self, other):
        return self.__class__(self.x + other.x, self.y + other.y)

    def __eq__(self, other):  # 判定相等，考虑误差+／-2000
        return abs(self.x - other.x) <= 2000 and abs(self.y - other.y) <= 2000

    def __str__(self):
        return "<%s,%s>" % (self.x, self.y)

    __repr__ = __str__


class Position(Vector):  # 位置
    pass


class Ball:  # 球
    def __init__(self, extent, pos, velocity):
        # 球所在的坐标系参数extent，球的位置坐标pos，球的运动速度矢量velocity
        self.extent, self.pos, self.velocity = extent, pos, velocity

    def __str__(self):
        return 'BALL(ext=%s,pos=%s,vel=%s)' % (self.extent, self.pos, self.velocity)

    __repr__ = __str__

    def bounce_wall(self):  # 球在墙壁上反弹
        self.velocity.y = -self.velocity.y

    def bounce_racket(self):  # 球在球拍反弹
        self.velocity.x = -self.velocity.x

    def update_velocity(self, acc_vector, active_card):  # 给球加速，球桌坐标系
        param = 1
        if active_card[1] == CARD_SPIN:
            param = CARD_SPIN_PARAM

        # 球改变速度，仅垂直方向
        self.velocity.y += int(acc_vector * param)

    # 以下是李逸飞同学的超强算法
    # 用于检测是否得到道具。有错误的话，锅由李逸飞来背。邮箱：1500012435@pku.edu.cn
    def get_card(self, card, eps=2000):
        # 多写点注释。self.pos:(x0,y0),card.pos:(x1,y1),self.velocity:(u,v),self.extent[3]=L
        # 直线方程为 l:-v*x+u*y+v*x0-u*y0=0
        # card经过多次对称后，位置为(x1,±y1+2*k*l)
        # 点到直线距离公式dist=|-v*x1+u*(±y1+2*k*l)+v*x0-u*y0|/|self.velocity|
        # 记-v*x1+u*(±y1)+v*x0-u*y0=A1,A2,u*2*l为delta。则求最短距离，即是求A1%delta,A2%delta,-A1%delta,-A2%delta中最小值，再除以self.velocity的模长。
        A1 = (self.velocity.y * (-card.pos.x + self.pos.x) + self.velocity.x * (card.pos.y - self.pos.y))
        A2 = (self.velocity.y * (-card.pos.x + self.pos.x) + self.velocity.x * (-card.pos.y - self.pos.y))
        delta = (2 * abs(self.velocity.x) * self.extent[3])
        return min(A1 % delta, -A1 % delta, A2 % delta, -A2 % delta) / math.sqrt(
            self.velocity.x ** 2 + self.velocity.y ** 2) < eps

    def fly(self, ticks, list_cards):  # 球运动，更新位置，并返回触壁次数和路径经过的道具（元组）
        # 判断card.pos，如果球经过的话，就返回count的同时返回所有经过的道具列表，并从list_cards中移除。
        hit_cards = [card for card in list_cards if self.get_card(card)]
        # 对获得的道具按照获取时间先后进行排序
        if self.velocity.x > 0:
            hit_cards.sort(key=lambda card: card.pos.x)
        else:
            hit_cards.sort(key=lambda card: -card.pos.x)
        # 从球桌上删除被获取的道具
        for card in hit_cards:
            list_cards.remove(card)

        # x方向的位置
        self.pos.x += self.velocity.x * ticks

        if self.velocity.y == 0:
            return 0, hit_cards

        # 以下是李逸飞同学的简短新算法
        # ===========NEW!=============
        Y = self.velocity.y * ticks + self.pos.y  # Y是没有墙壁时到达的位置
        if Y % self.extent[3] != 0:  # case1：未在边界
            count = Y // self.extent[3]  # 穿过了多少次墙（可以是负的，最后取绝对值）

            # 两种情形：a） 穿过偶数次墙，这时没有对称变换，速度保持不变。到达的位置就是Y0=Y-self.extent[3]*count
            #         b） 穿过奇数次墙，是一次对称和一次平移的复合，速度反向。先做平移，到达Y0=Y-self.extent[3]*count，再反射，到self.extent[3]-Y0
            # 综合两种情形，奇数时Y0是负的，多一个self.extent[3];偶数时Y0是正的，没有self.extent[3]。综上，ynew=Y0*(-1)^count+(1-(-1)^count)/2*self.extent[3]
            # 因不清楚负数能不能做任意整指数幂，所以用取余来表示奇偶性。

            self.pos.y = (Y - count * self.extent[3]) * (1 - 2 * (count % 2)) + self.extent[3] * (count % 2)
            self.velocity.y = self.velocity.y * ((count + 1) % 2 * 2 - 1)
            return abs(count), hit_cards
        else:  # case2： 恰好在边界

            # 两种情形：a） 向上穿墙，穿了1 - Y // self.extent[3] 次（代入Y = 0验证）
            #           b） 向下穿墙，穿了 Y // self.extent[3] 次（代入Y = self.extent[3] 验证）
            # 无论怎样，实际位置要么在0，要么在self.extent[3]。直接模( 2 * self.extent[3] )即可。
            # 速度只和count奇偶有关，同上。

            count = (Y // self.extent[3]) if (Y > 0) else (1 - Y // self.extent[3])
            self.pos.y = Y % (2 * self.extent[3])
            self.velocity.y = self.velocity.y * ((count + 1) % 2 * 2 - 1)
            return count, hit_cards
            # ===========END==============


'''
        # y方向速度为0
        if self.velocity.y == 0:
            return 0  # y坐标不改变，触壁次数为0
        elif self.velocity.y > 0:  # 向上y+飞
            # y方向的位置，考虑触壁反弹
            bounce_ticks = (self.extent[3] - self.pos.y) / self.velocity.y
            if bounce_ticks >= ticks:  # 没有触壁
                self.pos.y += self.velocity.y * ticks
                return 0
            else:  # 至少1次触壁
                # 计算后续触壁
                ticks -= bounce_ticks
                count, remain = divmod(ticks, ((self.extent[3] - self.extent[2]) / self.velocity.y))
                if count % 2 == 0:  # 偶数，则是速度改变方向
                    self.pos.y = self.extent[3] - remain * self.velocity.y
                    self.velocity.y = -self.velocity.y
                else:  # 奇数，速度方向不变
                    self.pos.y = self.extent[2] + remain * self.velocity.y
                return count + 1
        else:  # 向下y-飞
            # y方向的位置，考虑触壁反弹
            bounce_ticks = (self.extent[2] - self.pos.y) / self.velocity.y
            if bounce_ticks >= ticks:  # 没有触壁
                self.pos.y += self.velocity.y * ticks
                return 0
            else:  # 至少1次触壁
                # 计算后续触壁
                ticks -= bounce_ticks
                count, remain = divmod(ticks, ((self.extent[2] - self.extent[3]) / self.velocity.y))
                if count % 2 == 0:  # 偶数，则是速度改变方向
                    self.pos.y = self.extent[2] - remain * self.velocity.y
                    self.velocity.y = -self.velocity.y
                else:  # 奇数，速度方向不变
                    self.pos.y = self.extent[3] + remain * self.velocity.y
                return count + 1
'''


class RacketAction:  # 球拍动作
    def __init__(self, tick, bat_vector, acc_vector, run_vector, side: str, card: Card):
        # self.t0 = tick  # tick时刻的动作，都是一维矢量，仅在y轴方向
        self.bat = bat_vector  # t0~t1迎球的动作矢量（移动方向及距离）
        self.acc = acc_vector  # t1触球加速矢量（加速的方向及速度）
        self.run = run_vector  # t1~t2跑位的动作矢量（移动方向及距离）
        self.card = (side, card)  # 对'SELF'/'OPNT'使用道具

    def normalize(self):
        # 全都规范为整数
        self.bat = int(self.bat)
        self.acc = int(self.acc)
        self.run = int(self.run)


class Racket:  # 球拍
    def __init__(self, side, pos):  # 选边'West'／'East'和位置
        self.side, self.pos = side, pos
        self.life = RACKET_LIFE
        self.bat_lf = self.run_lf = self.acc_lf = self.card_lf = 0  # 各种操作对生命值的损耗
        self.name = self.serve = self.play = self.summarize = None
        self.action = self.datastore = None
        self.clock_time = 0.0
        self.card_box = CardBox()  # 道具箱，本方拥有的道具，不超过MAX_CARDS个，超过的话按照队列形式删除旧的道具。

    def bind_play(self, name, serve, play, summarize):  # 绑定玩家名称和serve, play, summarize函数
        self.name = name
        self.serve = serve  # 发球函数
        self.play = play  # 接球函数
        self.summarize = summarize  # 总结函数

    def set_action(self, action):  # 设置球拍动作，包括使用道具
        self.action = action
        card = self.card_box.discard(action.card[1])  # 先从道具箱中移除道具
        if card is None:  # 如果道具不存在，那就删除card引用
            self.action.card = (None, None)

    def set_datastore(self, ds):  # 设置数据存储，一个字典
        self.datastore = ds

    def get_velocity(self):
        # 球拍的全速是球X方向速度，按照体力值比例下降，当体力值下降到55%，将出现死角
        return int((self.life / RACKET_LIFE) * BALL_V[0])

    def update_pos_bat(self, tick_step, active_card):
        # 如果指定迎球的距离大于最大速度的距离，则采用最大速度距离
        bat_distance = sign(self.action.bat) * min(abs(self.action.bat), self.get_velocity() * tick_step)
        self.pos.y += bat_distance
        # 减少生命值
        self.bat_lf = -(abs(bat_distance) ** 2 // FACTOR_DISTANCE ** 2) * \
                      (CARD_AMPL_PARAM if active_card[1] == CARD_AMPL else 1)
        self.life += self.bat_lf

    def update_pos_run(self, tick_step, active_card):
        # 如果指定跑位的距离大于最大速度的距离，则采用最大速度距离
        run_distance = sign(self.action.run) * min(abs(self.action.run), self.get_velocity() * tick_step)
        self.pos.y += run_distance
        # 减少生命值
        param = 0
        self.run_lf = 0
        if active_card[1] == CARD_TLPT:  # 如果碰到瞬移卡，则从距离减去CARD_TLPT_PARAM再计算体力值减少
            param = CARD_TLPT_PARAM
        if abs(run_distance) - param > 0:
            self.run_lf = -(abs(run_distance) - param) ** 2 // FACTOR_DISTANCE ** 2
            self.life += self.run_lf

    def update_acc(self, active_card):
        # 按照给球加速度的指标减少生命值
        self.acc_lf = -(abs(self.action.acc) ** 2 // FACTOR_SPEED ** 2) * \
                      (CARD_AMPL_PARAM if active_card[1] == CARD_AMPL else 1)
        self.life += self.acc_lf


class TableData:  # 球桌信息，player计算用
    def __init__(self, tick, tick_step, side, op_side, ball, card):
        self.tick = tick
        self.step = tick_step
        self.side = side  # 字典，迎球方信息
        self.op_side = op_side  # 字典，跑位方信息
        self.ball = ball  # 字典，球的信息
        self.cards = card  # 字典，道具信息


class RacketData:  # 球拍信息，记录日志用
    def __init__(self, racket):
        self.side, self.name, self.life = racket.side, racket.name, racket.life
        self.bat_lf, self.acc_lf, self.run_lf, self.card_lf = racket.bat_lf, racket.acc_lf, racket.run_lf, racket.card_lf
        self.pos, self.action = copy.copy(racket.pos), copy.copy(racket.action)
        self.card_box = copy.copy(racket.card_box)


class BallData:  # 球的信息，记录日志用
    def __init__(self, ball_or_pos, velocity=None):
        if velocity is None:
            self.pos, self.velocity = copy.copy(ball_or_pos.pos), \
                                      copy.copy(ball_or_pos.velocity)
        else:
            self.pos, self.velocity = ball_or_pos, velocity


class CardData:  # 道具信息，记录日志用
    def __init__(self, card_tick, cards, active_card):
        self.card_tick = card_tick  # 道具出现时间的计时，0-CARD_FREQ
        self.cards = copy.copy(cards)  # 道具对象的列表，数量上限为MAX_TABLE_CARDS
        self.active_card = active_card  # (<被用道具方SELF/OPNT>, <Card>)


class Table:  # 球桌
    def __init__(self):
        # 桌面坐标系的范围，单位"pace"
        self.xmin, self.xmax, self.ymin, self.ymax = DIM
        self.tick = 0
        self.ball = Ball(DIM, Vector(*BALL_POS), Vector(*BALL_V))  # 球的初始化
        self.clock_start = time.time()  # 第一次调用
        self.clock_end = time.time()  # 第二次调用

        # tick增加的步长
        self.tick_step = (self.xmax - self.xmin) // BALL_V[0]  # 这是水平方向速度
        # 道具的计时器，以及球桌上散布的道具，当前被激活使用的道具
        self.card_tick = self.tick
        self.cards = list()
        self.active_card = (None, None)

        # 球拍，位置是球拍坐标系
        self.players = {'West': Racket('West', Position(self.xmin, self.ymax // 2)),
                        'East': Racket('East', Position(self.xmax, self.ymax // 2))}
        self.side = 'West'  # 球的初始位置在西侧的中央，发球的首先是West
        self.op_side = 'East'
        self.players['West'].set_action(RacketAction(self.tick, 0, 0, 0, None, None))
        self.players['East'].set_action(RacketAction(self.tick, 0, 0, 0, None, None))

        # 是否结束
        self.finished = False
        self.winner = None
        self.reason = None

    def deploy_card(self):  # 放置道具到球桌上
        if self.card_tick >= CARD_FREQ:  # 判断道具计时器是不是到了，到了就放置随机道具到球桌上
            self.card_tick -= CARD_FREQ  # 重置计时器
            card_info = random.choice(ALL_CARDS)
            self.cards.append(Card(card_info[0], card_info[1],
                                   Position(random.randint(CARD_EXTENT[0], CARD_EXTENT[1]),
                                            random.randint(CARD_EXTENT[2], CARD_EXTENT[3]))))
            # 桌上不超过MAX_TABLE_CARDS个道具
            while len(self.cards) > MAX_TABLE_CARDS:
                self.cards.pop(0)

    def change_side(self):  # 换边
        self.side, self.op_side = self.op_side, self.side

    def serve(self):  # 发球，始终是West发球
        self.tick = 0  # 当前的时刻tick
        player = self.players[self.side]  # 现在side是West
        try:
            self.clock_start = time.time()
            pos_y, velocity_y = player.serve(self.players[self.op_side].name,
                                             player.datastore)  # 只提供y方向的位置和速度
            self.clock_end = time.time()
            player.clock_time += self.clock_end - self.clock_start
        except:  # 调用发球出错
            self.finished = True
            self.winner = self.op_side
            self.reason = "run_error"
            return
        if player.clock_time > ROUND_CLOCK:
            self.finished = True
            self.winner = self.op_side
            self.reason = "clock_out"
            return
        pos_y, velocity_y = int(pos_y), int(velocity_y)
        self.ball = Ball(DIM, Position(BALL_POS[0], pos_y),
                         Vector(BALL_V[0], velocity_y))  # 球的初始化
        self.change_side()  # 换边迎球
        return

    def time_run(self):  # 球跑一趟
        # 首先取得迎球方和跑位方的对象
        player = self.players[self.side]
        op_player = self.players[self.op_side]

        # t0时刻调用在t1时刻击球的一方
        # 1，首先让球从t0飞到t1时刻（确定轨迹）
        count_bounce, hit_cards = self.ball.fly(self.tick_step, self.cards)
        if count_bounce not in (1, 2):  # 反弹没有在1、2次，对方输了
            self.finished = True
            self.winner = self.side
            self.reason = "invalid_bounce"
            print(count_bounce, player.pos, op_player.pos, self.ball)
            return
        # 将击中的道具加入道具箱
        for card in hit_cards:
            op_player.card_box.collect(card)

        # 2，产生新的道具放到球桌上
        self.deploy_card()

        # 让跑位方的道具生效
        # active_card=(<被用道具方West/East>, <道具代码>)
        self.active_card = op_player.action.card
        player.card_lf = 0
        op_player.card_lf = 0
        if self.active_card[1] == CARD_DECL:
            # 让迎球方掉血
            player.card_lf = - CARD_DECL_PARAM
            player.life += player.card_lf
        if self.active_card[1] == CARD_INCL:
            # 让跑位方加血
            op_player.card_lf = CARD_INCL_PARAM
            op_player.life += op_player.card_lf
        # 3，调用迎球方的算法
        #    参数：t0时刻双方位置和体力值，以及跑位方的跑位方向；
        #    参数：球在t1时刻的位置和速度

        dict_side = {
            'name': player.name,
            'position': copy.copy(player.pos),
            'life': player.life,
            'clock': player.clock_time,  # 花费的物理时间（秒）
            'cards': [copy_card(c) for c in player.card_box]}
        dict_op_side = {
            'name': op_player.name,
            'position': copy.copy(op_player.pos),
            'life': op_player.life,
            'clock': op_player.clock_time,  # 花费的物理时间（秒）
            'cards': [copy_card(c) for c in op_player.card_box],
            'active_card': (self.active_card[0], copy_card(self.active_card[1])),
            'accelerate': None if self.active_card[1] == CARD_DSPR else
            (-1 if op_player.action.acc < 0 else 1),
            'run_vector': None if self.active_card[1] == CARD_DSPR else
            (-1 if op_player.action.run < 0 else 1)}
        dict_ball = {
            'position': copy.copy(self.ball.pos),
            'velocity': copy.copy(self.ball.velocity)}
        dict_card = {
            'card_tick': self.card_tick,
            'cards': [copy_card(c) for c in self.cards]}
        # 调用，返回迎球方的动作
        try:
            self.clock_start = time.time()
            player_action = player.play(TableData(self.tick, self.tick_step,
                                                  dict_side, dict_op_side, dict_ball, dict_card),
                                        player.datastore)
            player_action.normalize()
            self.clock_end = time.time()
            player.clock_time += self.clock_end - self.clock_start
        except:  # 调用迎球出错
            self.finished = True
            self.winner = self.op_side
            self.reason = "run_error"
            return
        if player.clock_time > ROUND_CLOCK:
            self.finished = True
            self.winner = self.op_side
            self.reason = "clock_out"
            return

        # 设置迎球方的动作，迎球方使用的道具生效要到下一趟
        # 将迎球方动作中的距离速度等值规整化为整数
        player.set_action(player_action)

        # 执行迎球方的两个动作：迎球和加速
        player.update_pos_bat(self.tick_step, self.active_card)
        if not (player.pos == self.ball.pos):
            # 没接上球
            print("player_pos:" + str(player.pos), "ball_pos:" + str(self.ball.pos))
            self.finished = True
            self.winner = self.op_side
            self.reason = "miss_ball"
            return
        player.update_acc(self.active_card)
        if player.life <= 0:
            # 生命值用尽，失败
            self.finished = True
            self.winner = self.op_side
            self.reason = "life_out"
            return
        self.ball.update_velocity(player.action.acc, self.active_card)
        self.ball.bounce_racket()  # 球在球拍反弹

        # 执行跑位方的一个动作：跑位
        op_player.update_pos_run(self.tick_step, self.active_card)
        if op_player.life <= 0:
            # 生命值用尽，失败
            self.finished = True
            self.winner = self.side
            self.reason = "life_out"
            return

        self.card_tick += self.tick_step  # 道具计时增加
        self.tick += self.tick_step  # 时间从t0到t1
        if self.tick >= TMAX:
            # 时间到，生命值高的胜出
            self.finished = True
            self.winner = self.side if (player.life > op_player.life) else self.op_side
            self.reason = "time_out"
            return

        self.change_side()  # 换边迎球
        return

    def postcare(self):  # 善后处理
        west_player = self.players['West']
        east_player = self.players['East']
        west_player.summarize(self.tick, self.winner, self.reason,
                              RacketData(west_player), RacketData(east_player),
                              BallData(self.ball), west_player.datastore)
        east_player.summarize(self.tick, self.winner, self.reason,
                              RacketData(west_player), RacketData(east_player),
                              BallData(self.ball), east_player.datastore)
        return


class LogEntry:
    def __init__(self, tick, side, op_side, ball, card):
        self.tick = tick  # 当前的时间
        self.side = side  # RacketData类对象
        self.op_side = op_side  # RacketData类对象
        self.ball = ball  # BallData类对象
        self.card = card  # CardData类对象
