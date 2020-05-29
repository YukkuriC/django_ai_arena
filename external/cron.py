from django_cron import CronJobBase, Schedule
from django.conf import settings
from django.db import connections
from django.db.models import Q
from django.utils import timezone
from match_sys.models import Code, PairMatch
from .match_monitor import start_match, unit_monitor
from datetime import datetime
from multiprocessing import Process, Queue
import random, json


def expand_markers(targets):
    """
    将区间起点表示展开为按小时的列表
    """
    # 输入合法性检查
    targets = {
        k: v
        for (k, v) in targets if isinstance(k, int) and 0 <= k < 24
        and isinstance(v, int) and 0 <= v <= 60
    }
    if not targets:
        return [0] * 24

    # 展开为列表
    first_time = None
    last_time = last_freq = None
    mapper = [0] * 24

    def helper(t1, t2, f):
        if t2 <= t1:
            t2 += 24
        for t in range(t1, t2):
            mapper[t % 24] = f

    for time, freq in sorted(targets.items()):
        if first_time is None:
            first_time = time
        if last_time != None:
            helper(last_time, time, last_freq)
        last_time, last_freq = time, freq
    helper(last_time, first_time, last_freq)

    return mapper


class CronLogger(CronJobBase):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.matches = []  # 比赛进程列表
        self.logs = []  # 输出记录
        self.error_logger = Queue()  # 错误日志队列

    def post_process(self):
        """ 完成全部比赛，并组装记录字串 """

        # 阻塞至全部比赛完成
        for proc in self.matches:
            proc.join()

        # 读取报错队列内容
        while not self.error_logger.empty():
            self.logs.append(self.error_logger.get())

        # 返回记录
        return '\n'.join(self.logs)


class TeamLadder(CronLogger):
    """
    小组天梯后台自动比赛
    """
    code = 'TeamLadder'

    # 确定当前任务时间间隔
    density = expand_markers(settings.TEAMLADDER_CONFIG)
    cur_density = density[timezone.now().hour]
    cur_gap = 60 / cur_density if cur_density > 0 else 3600
    schedule = Schedule(run_every_mins=cur_gap)

    NMATCH = expand_markers(settings.TEAMLADDER_NMATCH)

    def run_once(self, code, codes, gameid, params):
        """
        单个代码发起匹配赛
        code: 随机选取的代码
        codes: 代码所在组
        gameid: 游戏类型
        params: 比赛参数
        """

        # 选取目标代码
        codes = sorted(
            filter(lambda x: x != code, codes),
            key=lambda x: abs(x.score - code.score)
        )[:settings.RANKING_RANDOM_RANGE]
        target = random.choice(codes)

        # 发起比赛
        self.logs.append(f'{code.author.stu_code} - {target.author.stu_code}')
        return start_match(gameid, code.id, target.id, params, True)

    def do(self):
        """ 按游戏类型、组号随机发起比赛 """
        games_to_run = settings.TEAMLADDER_ENABLED

        # 按游戏类型遍历
        for gameid, params in games_to_run:
            self.logs.append(settings.AI_TYPES[gameid])
            all_codes = Code.objects.filter(
                ai_type=gameid,
                author__is_team=True,
            )

            # 分别获取FN组代码，并按代码数权重抽样
            codes, code_freq = [], []
            nmatch = self.NMATCH[timezone.now().hour]
            for grp in 'FN':
                code_grp = list(
                    all_codes.filter(author__stu_code__istartswith=grp))
                grp_size = len(code_grp)
                if grp_size > 1:
                    codes.append(code_grp)
                    code_freq.append(grp_size * (grp_size - 1))  # C(N,2)
            grp_seq = random.choices(
                codes,
                code_freq,
                k=nmatch,
            ) if codes else []

            # 各组抽选代码发起比赛
            for grp in grp_seq:
                match_proc = self.run_once(
                    random.choice(grp),
                    grp,
                    gameid,
                    params,
                )
                self.logs.append(match_proc)

        # 返回记录
        return self.post_process()


class BaseMatch(CronLogger):
    code = 'BaseMatch'
    schedule = Schedule(run_every_mins=0)

    def do(self):
        """
        运行比赛
        从数据库抓取未执行的比赛并执行
        """
        # 自动清除滞留比赛
        running_match = PairMatch.objects.filter(Q(status=1) | Q(status=-1))
        invalid_match = running_match.filter(
            timeout_datetime__lt=datetime.now())  # 比赛内部进程统一使用datetime
        if invalid_match:
            l = len(invalid_match)
            invalid_match.update(status=3)
            self.logs.append(f'{l} INVALID REMOVED')

        # 获取当前剩余的任务数
        num_running = len(running_match)
        num_left = settings.MATCH_POOL_SIZE - num_running
        self.logs.append(f'{num_running} RUNNING, {num_left} LEFT')
        if num_left <= 0:
            return

        # 获取最早的未发起比赛
        new_matches = PairMatch.objects.filter(
            status=0).order_by('run_datetime')[:num_left]

        # 分别发起
        for match in new_matches:
            self.logs.append('START: ' + match.name)
            match_proc = Process(
                target=unit_monitor,
                args=('match', match.name, [
                    match.ai_type,
                    json.loads(match.params),
                ], self.error_logger))
            connections.close_all()  # 用于主进程MySQL保存所有更改
            match_proc.start()
            self.matches.append(match_proc)

        # 返回记录
        return self.post_process()
