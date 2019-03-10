from time import perf_counter as pf
from random import randrange
from collections import namedtuple
import traceback

__doc__ = '''比赛逻辑

match函数输入双方名称与AI函数返回比赛结果
AI函数应接收游戏数据与自身存储空间，返回'left'，'right'或None
游戏数据格式：字典
    size : 场地大小
    log : 游戏记录
    now : 该回合游戏数据
        turnleft : 剩余回合数
        timeleft : 双方剩余思考时间
        fields : 纸片场地深拷贝
        bands : 纸带场地深拷贝
        players : 玩家信息
            id : 玩家标记（1或2）
            x : 横坐标（场地数组下标1）
            y : 纵坐标（场地数组下标2）
            direction : 当前方向
                0 : 向东
                1 : 向南
                2 : 向西
                3 : 向北
        me : 该玩家信息
        enemy : 对手玩家信息
'''
__all__ = ['match']

# 超时处理
if 'timeout':

    class TimeOut(Exception):
        pass

    def timer(timeleft, func, params):
        '''
        计时函数，统计一个函数运行时间并监控其是否超时

        params:
            timeleft - 剩余时间
            func - 待执行函数
            params - 函数参数

        returns:
            (函数返回值, 执行用时)
        '''
        # 运行并计时
        t1 = pf()
        res = func(*params)
        t2 = pf()

        # 若超时则报错，否则返回消耗时间
        if t2 - t1 >= timeleft:
            raise TimeOut()

        # 返回函数结果
        return res, t2 - t1


# 参数
if 'global params':
    # 待初始化时间参数
    MAX_TURNS = None  # 最大回合数（双方各操作一次为一回合）
    MAX_TIME = None  # 总思考时间（秒）
    TURNS = None  # 记录每个玩家剩余回合数
    TIMES = None  # 记录每个玩家剩余思考时间

    # 待初始化空间参数
    WIDTH, HEIGHT = None, None  # 游戏场地宽高
    BANDS = None  # 纸带判定区 = [[None] * HEIGHT for i in range(WIDTH)]
    FIELDS = None  # 已生成区域判定区 = [[None] * HEIGHT for i in range(WIDTH)]
    PLAYERS = [None] * 2

    # AI函数存储空间
    STAT = [None] * 2  # 比赛信息
    STORAGE = [{}, {}]  # 私有存储

    # 其它
    LOG_PUBLIC = None  # 全局比赛记录列表
    NULL = lambda storage: None  # 空函数
    FRAME_FUNC = NULL  # 逐帧处理函数接口
    # match.DEBUG_TRACEBACK - 作为报错输出存储变量


# 玩家对象执行游戏逻辑
class player:
    '''
    玩家逻辑

    params:
        id - 向players数组中添加位置
        x, y - 初始坐标
        expand - 初始纸片边长为(2 * expand + 1)
        init_direction - 初始方向，默认为随机方向
    '''
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # 方向数字对应前进方向

    def __init__(self, id, x, y, expand=1, init_direction=None):
        self.id, self.x, self.y = id, x, y
        self.band_direction = []  # 记录纸带轨迹，便于状态转换时回溯

        # 设置初始方向
        if init_direction is None:
            self.direction = randrange(4)
        else:
            self.direction = init_direction

        # 生成初始占有区域(l, r, u, d)
        self.field_border = [
            max(0, x - expand),
            min(WIDTH - 1, x + expand),
            max(0, y - expand),
            min(HEIGHT - 1, y + expand)
        ]
        for x in range(self.field_border[0], self.field_border[1] + 1):
            for y in range(self.field_border[2], self.field_border[3] + 1):
                FIELDS[x][y] = id

    def turn_left(self):
        '''左转'''
        self.direction = (self.direction + 3) % 4

    def turn_right(self):
        '''右转'''
        self.direction = (self.direction + 1) % 4

    def forward(self):
        '''
        向前移动一步，并相应更新场地

        returns:
            若未到达终盘条件 - None
            若到达终盘 - 
                胜利玩家ID（1或2，None代表同时死亡）
                终局原因编号（详见parse_match函数注释）
                额外内容
        '''
        # 移动
        next_step = self.directions[self.direction]
        self.x += next_step[0]
        self.y += next_step[1]

        # 边缘检测
        if self.x < 0 or self.x >= WIDTH or self.y < 0 or self.y >= HEIGHT:
            self.band_direction.append(self.direction)
            return 2 - self.id, 0  # 撞墙死

        # 更新占有区域边界
        self.field_border[0] = min(self.x, self.field_border[0])
        self.field_border[1] = max(self.x, self.field_border[1])
        self.field_border[2] = min(self.y, self.field_border[2])
        self.field_border[3] = max(self.y, self.field_border[3])

        # 更新玩家碰撞
        enemy = PLAYERS[2 - self.id]
        if enemy.x == self.x and enemy.y == self.y:
            # 自己领地内击杀对手
            if FIELDS[self.x][self.y] == self.id:  # 自己领地
                self.check_field_fill()
                return self.id - 1, 4, True

            # 以下情况先更新纸带
            self.extend_band()

            # 对手领地内送分
            if FIELDS[self.x][self.y] == enemy.id:
                return enemy.id - 1, 4, False

            # 侧碰击杀对手
            if enemy.direction % 2 != self.direction % 2:
                return self.id - 1, 2

            # 对撞统计数据
            return None, 3

        # 更新纸带碰撞
        if BANDS[self.x][self.y] is not None:
            # 缓存记录胜者为纸带主人的对手
            winner = 2 - BANDS[self.x][self.y]

            # 更新场地并返回比赛结果
            self.update_field()
            return winner, 1, self.id - 1

        # 更新场地
        self.update_field()

    def update_field(self):
        '''更新玩家在场地引起的效应'''
        # 场地内检查填充情况
        if FIELDS[self.x][self.y] == self.id:  # 在/回到自己场地
            if self.band_direction:  # 在回领地瞬间填充领地
                self.check_field_fill()

        # 场地外延伸纸带
        else:
            self.extend_band()

    def extend_band(self):
        '''（在自己领地外）延伸纸带'''
        self.band_direction.append(self.direction)
        BANDS[self.x][self.y] = self.id

    def check_field_fill(self):
        '''（返回自己领地时）检查填充'''
        # 1. 纸带转换为领地
        next_step = self.directions[self.direction]
        ptrx, ptry = self.x - next_step[0], self.y - next_step[1]  # 从上一步纸带位置回溯
        while self.band_direction:
            BANDS[ptrx][ptry] = None
            FIELDS[ptrx][ptry] = self.id
            next_step = self.directions[self.band_direction.pop()]
            ptrx -= next_step[0]
            ptry -= next_step[1]

        # 2. floodfill填充空腔
        targets = set(
            (x, y)
            for x in range(self.field_border[0], self.field_border[1] + 1)
            for y in range(self.field_border[2], self.field_border[3] + 1)
            if FIELDS[x][y] != self.id)
        while targets:
            iter = [targets.pop()]
            fill_pool = []
            in_bound = True  # 这次填充是否为界内填充
            while iter:
                curr = iter.pop()
                # floodfill
                for dx, dy in self.directions:
                    next_step = (curr[0] + dx, curr[1] + dy)
                    if next_step in targets:
                        targets.remove(next_step)
                        iter.append(next_step)

                # 判断当前点
                if in_bound:
                    if curr[0] == self.field_border[0] or curr[0] == self.field_border[1] or curr[1] == self.field_border[2] or curr[1] == self.field_border[3]:
                        in_bound = False
                    else:
                        fill_pool.append(curr)

            # 若未出界则填充内容
            if in_bound:
                for x, y in fill_pool:
                    FIELDS[x][y] = self.id

    def get_info(self):
        '''
        提取玩家信息，用于传递给AI函数

        returns:
            字典，包含id，位置，方向
        '''
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'direction': self.direction
        }


# 辅助函数
if 'helpers':

    def init_field(k, h, max_turn, max_time, plr_overrides=None):
        '''
        初始化比赛场地

        params:
            k - 场地半宽
            h - 场地高度
            max_turn - 总回合数（双方各行动一次为一回合）
            max_time - 总思考时间（秒）
            plr_overrides - 用于覆盖设置双方玩家参数
        '''
        # 初始化场地
        global WIDTH, HEIGHT, BANDS, FIELDS
        WIDTH = k * 2
        HEIGHT = h
        BANDS = [[None] * HEIGHT for i in range(WIDTH)]
        FIELDS = [[None] * HEIGHT for i in range(WIDTH)]

        # 初始化最大回合数、思考时间
        global MAX_TIME, MAX_TURNS, TURNS, TIMES
        MAX_TIME = max_time
        MAX_TURNS = max_turn
        TURNS = [MAX_TURNS] * 2
        TIMES = [MAX_TIME] * 2

        # 初始化玩家
        if not plr_overrides:
            plr_overrides = [{
                'x': k * i + k // 2 + randrange(-3, 4),
                'y': h // 2 + randrange(-3, 4),
            } for i in range(2)]
        for i in range(2):
            PLAYERS[i] = player(i + 1, **plr_overrides[i])

        # 创建初始场景拷贝
        f, b = field_copy()

        # 初始化比赛信息存储
        for i in range(2):
            first_frame = get_params(f, b, i)
            STAT[i] = {
                'size': (WIDTH, HEIGHT),
                'log': [first_frame],
                'now': first_frame
            }

        # 建立全局比赛记录
        global LOG_PUBLIC
        frame = get_params(f, b)
        FRAME_FUNC(frame)
        LOG_PUBLIC = [frame]

    def field_copy():
        '''
        创建比赛场地的拷贝（元组）

        returns:
            [0] - FIELDS拷贝
            [1] - BANDS拷贝
        '''
        f = tuple(tuple(i) for i in FIELDS)
        b = tuple(tuple(i) for i in BANDS)
        return f, b

    def get_params(fields, bands, curr_plr=None):
        '''
        生成传给AI函数的参数结构

        params:
            fields - 纸片信息元组
            bands - 纸带信息元组
            curr_plr - 当前玩家编号（0或1）

        return:
            字典
                turnleft : 剩余回合数
                timeleft : 双方剩余思考时间
                fields : 纸片场地深拷贝
                bands : 纸带场地深拷贝
                players : 玩家信息
                    id : 玩家标记（1或2）
                    x : 横坐标（场地数组下标1）
                    y : 纵坐标（场地数组下标2）
                    direction : 当前方向
                        0 : 向东
                        1 : 向南
                        2 : 向西
                        3 : 向北
                （在curr_plr有效时）
                me : 该玩家信息
                enemy : 对手玩家信息
                （在curr_plr无效时）
                band_route : 双方纸带行进方向
        '''
        res = {}
        res['turnleft'] = tuple(TURNS)
        res['timeleft'] = tuple(TIMES)
        res['fields'] = fields
        res['players'] = list(map(player.get_info, PLAYERS))
        res['bands'] = bands
        if curr_plr is None:
            res['band_route'] = list(
                map(lambda plr: tuple(plr.band_direction), PLAYERS))
        else:
            res['me'] = res['players'][curr_plr]
            res['enemy'] = res['players'][1 - curr_plr]
        return res

    def parse_match(funcs):
        '''
        读入双方AI函数，执行一次比赛

        params:
            funcs - 玩家模块列表
        
        returns:
            胜利玩家id, 终局原因编号 [, 额外描述]
            终局原因 : 
                0 - 撞墙
                1 - 纸带碰撞
                2 - 侧碰
                3 - 正碰，结算得分
                4 - 领地内互相碰撞
                -1 - AI函数报错
                -2 - 超时
                -3 - 回合数耗尽，结算得分
        '''
        # 双方初始化环境
        for plr_index in (0, 1):
            # 未声明load函数则跳过
            if 'load' not in dir(funcs[plr_index]):
                continue

            # 准备输入参数
            func = funcs[plr_index].load
            stat = STAT[plr_index]
            storage = STORAGE[plr_index]

            # 运行装载函数并计时
            try:
                timecost = timer(MAX_TIME, func, (stat, storage))[1]
            except TimeOut:
                return (1 - plr_index, -2)
            except Exception as e:
                match.DEBUG_TRACEBACK = traceback.format_exc()
                return (1 - plr_index, -1, e)

            TIMES[plr_index] -= timecost

        # 执行游戏逻辑
        for i in range(MAX_TURNS):
            for plr_index in (0, 1):
                # 获取当前玩家、AI、游戏信息、存储空间
                plr = PLAYERS[plr_index]
                func = funcs[plr_index].play
                stat = STAT[plr_index]
                storage = STORAGE[plr_index]

                # 执行AI并计时
                try:
                    action, timecost = timer(TIMES[plr_index], func,
                                             (stat, storage))
                except TimeOut:  # 超时
                    return (1 - plr_index, -2)
                except Exception as e:  # AI函数报错
                    match.DEBUG_TRACEBACK = traceback.format_exc()
                    return (1 - plr_index, -1, e)

                # 更新剩余回合数、用时
                TURNS[plr_index] -= 1
                TIMES[plr_index] -= timecost

                # 根据操作符转向
                if isinstance(action, str) and len(action) > 0:
                    op = action[0].upper()
                    if op == 'L':
                        plr.turn_left()
                    elif op == 'R':
                        plr.turn_right()

                # 前进并更新结果
                res = plr.forward()

                # 拷贝场景
                f, b = field_copy()

                # 双方玩家比赛记录
                for i in range(2):
                    new_frame = get_params(f, b, i)
                    STAT[i]['log'].append(new_frame)
                    STAT[i]['now'] = new_frame

                # 全局比赛记录
                frame = get_params(f, b)
                FRAME_FUNC(frame)  # 帧处理函数接口
                LOG_PUBLIC.append(frame)

                # 若终局则返回结果
                if res:
                    return res

        # 回合数耗尽
        return (None, -3)

    def count_score():
        '''
        统计场上面积数，用于评判胜负

        return:
            长度为2的元组，分别记录双方面积数
        '''
        res = [0, 0]
        for x in range(WIDTH):
            for y in range(HEIGHT):
                if FIELDS[x][y] is not None:
                    res[FIELDS[x][y] - 1] += 1
        return tuple(res)


# 主函数
def match(players,
          names=('plr1', 'plr2'),
          k=51,
          h=101,
          max_turn=2000,
          max_time=30,
          plr_overrides=None):
    '''
    一次比赛
    params:
        players - 先后手玩家代码文件列表
            详见AI_Template.pdf
        names - 先后手玩家名称
        plr2 - 玩家2代码文件
        k - 场地半宽（奇数）
        h - 场地高（奇数）
        max_turn - 总回合数（双方各行动一次为一回合）
        max_time - 总思考时间（秒）
        plr_overrides - 用于覆盖设置双方玩家参数

    returns:
        字典，包含比赛结果与记录信息:
            players : 参赛玩家名称
            size : 该局比赛场地大小
            log : 对局记录
            result : 对局结果，详见parse_match函数注释
    '''
    # 初始化比赛环境
    init_field(k, h, max_turn, max_time, plr_overrides)

    # 运行比赛，并记录终局场景
    match_result = parse_match(players)

    # 如果平手则统计得分
    if match_result[0] is None:
        scores = count_score()
        winner = 0 if scores[0] > scores[1] else 1 if scores[0] < scores[1] else None
        match_result = (winner, match_result[1], scores)

    # 双方总结比赛
    for i in range(2):
        try:
            players[i].summary(match_result[:2], STAT[i], STORAGE[i])
        except:
            pass

    # 生成对局记录对象
    return {
        'players': names,
        'size': (WIDTH, HEIGHT),
        'maxturn': MAX_TURNS,
        'maxtime': MAX_TIME,
        'result': match_result,
        'log': LOG_PUBLIC
    }


if __name__ == '__main__':

    class null_plr:
        def play(self, stat, storage):
            return 'l'

    t1 = pf()
    res = match((null_plr(), ) * 2)
    t2 = pf()
    print(t2 - t1)
