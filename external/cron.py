from django_cron import CronJobBase, Schedule
from django.conf import settings
from django.utils import timezone
from match_sys.models import Code
from .match_monitor import start_match
import random


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
        return []

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


def gen_times(targets):
    """
    将settings.TEAMLADDER_CONFIG转化为django_cron所需格式
    """
    mapper = expand_markers(targets)

    # 换算为时间表示
    res = []
    for h in range(24):
        for msep in range(mapper[h]):
            res.append('%02d:%02d' % (h, 60 * msep // mapper[h]))

    return res


class TeamLadder(CronJobBase):
    """
    小组天梯后台自动比赛
    """
    code = 'TeamLadder'
    schedule = Schedule(run_at_times=gen_times(settings.TEAMLADDER_CONFIG))
    print(schedule.run_at_times)

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
        return start_match(gameid, code.id, target.id, params, True, True)

    def do(self):
        """ 按游戏类型、组号随机发起比赛 """
        games_to_run = settings.TEAMLADDER_ENABLED

        # 按游戏类型遍历
        matches = []
        for gameid, params in games_to_run:
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
                matches.append(match_proc)

            # 阻塞至进程完成
            for proc in matches:
                proc.join()
