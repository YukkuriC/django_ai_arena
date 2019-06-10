from external._base import BasePairMatch
from functools import lru_cache
from os import path
import random, time
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings

from . import osmo_api


class OsmoMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_classes = [('Player', ['strategy'])]

    def get_timeout(self):
        '''获取超时限制'''
        return self.params['rounds'] * (
            osmo_api.consts.Consts["MAX_TIME"] * 2 + 10)

    @classmethod
    def pre_run(cls, d_local, d_global):
        '''
        局间继承参数
        '''
        # 覆盖默认参数
        osmo_api.apply_params(d_local['params'])

        return [{}, {}]

    @classmethod
    def swap_fields(cls, d_local, d_global):
        '''
        交换场地
        '''
        cls.init_params = cls.init_params[::-1]

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        运行一局比赛
        并返回比赛记录对象
        '''
        if d_local['who_first'] != "4" or d_local['rid'] % 2 == 0:
            cls.last_seed = int(time.time())
        wld = osmo_api.one_race(d_local['players'], cls.init_params,
                                d_local['names'], cls.last_seed)
        if wld.result['winner'] not in (0, 1):
            wld.result['winner'] = None
        return wld

    @classmethod
    def output_queue(cls, world):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        res = world.result
        return (res['winner'], )

    @classmethod
    def save_log(cls, round_id, world, d_local, d_global):
        '''
        保存比赛记录
        '''
        match_dir = d_local['match_dir']
        log_name = path.join(match_dir, 'logs/%02d.zlog' % round_id)
        osmo_api.save_log(world, log_name)

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        log_name = path.join(match_dir, 'logs/%02d.zlog' % rec_id)
        return osmo_api.load_log(log_name)

    @classmethod
    @lru_cache()
    def stringfy_record(cls, match_dir, rec_id):
        record = {**cls.load_record(match_dir, rec_id)}
        if record['cause'] == "RUNTIME_ERROR":  # 将Exception转换为str
            if isinstance(record["detail"], (list, tuple)):
                tmp = []
                for i in record["detail"]:
                    if isinstance(i, Exception):
                        i = cls.stringfy_error(i)
                    tmp.append(i)
                record['detail'] = tmp
        return super().stringfy_record_obj(record)

    @staticmethod
    def summary_records(records):
        '''
        统计比赛记录
        '''
        result_stat = {0: 0, 1: 0, None: 0}
        for rec in records:
            if rec == None:
                continue
            winner = rec['winner']
            if isinstance(winner, int) and rec["players"][0] == 'code2':
                winner = 1 - winner
            result_stat[winner] += 1
        return {
            'stat': result_stat,
        }


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordMeta

    class OsmoRecord(metaclass=RecordMeta(3)):
        def r_holder(_, match, record):
            if record['players'][0] == 'code1':
                return match.code1.name
            return match.code2.name

        def r_length(_, match, record):
            return len(record['data'])

        def r_winner(_, match, record):
            if record['winner'] == None:
                return '平手'
            holder_win = not record['winner']

            code2_hold = (record['players'][0] == 'code2')
            code2_win = (code2_hold == holder_win)
            return '%s (%s, %s)' % (
                match.code2.name if code2_win else match.code1.name,
                ('发起方', '接收方')[code2_win],
                ('后手', '先手')[holder_win],
            )

        def r_win_desc(_, match, record):
            if record['cause'] == 'PLAYER_DEAD':
                return '吞噬玩家'
            elif record['cause'] == "RUNTIME_ERROR":
                return '代码错误'
            elif record['cause'] == "INVALID_RETURN_VALUE":
                return '输出格式错误'
            elif record['cause'] == "MAX_FRAME":
                return '最大帧数'
            elif record['cause'] == "TIMEOUT":
                return '玩家超时'
            return record['cause']

        def r_desc_plus(_, match, record):
            if record['cause'] == 'PLAYER_DEAD':
                dead = record['detail']
                if all(dead):
                    dead = '双方同时'
                else:
                    dead = '先手玩家' if dead[0] else '后手玩家'
                return dead + '被吞噬'
            elif record['cause'] == "RUNTIME_ERROR":
                res = list(record['detail'])
                if record['winner'] != None:
                    res = res[0] or res[1]
                return res
            elif record['cause'] == "MAX_FRAME":
                last_frame = record['data'][-1]
                return "%s : %s" % (round(last_frame[0][4], 2),
                                    round(last_frame[1][4], 2))
            return '-'
