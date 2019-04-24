from . import pingpong_api
from external._base import BasePairMatch
from os import path
from functools import lru_cache


class PingPongMatch(BasePairMatch):
    template_dir = 'renderer/pingpongio.html'

    class Meta(BasePairMatch.Meta):
        required_functions = ('serve', 'play', 'summarize')

    @classmethod
    def pre_run(cls, d_local, d_global):
        '''
        赛前准备，返回双方存储空间列表
        '''
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
        tmp = (d_local['players'], cls.init_params, d_local['names'],
               d_local['params'])
        print(tmp)
        return pingpong_api.one_race(*tmp)

    @classmethod
    def output_queue(cls, log):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        res = log['winner']
        res = 0 if res[0] == 'W' else 1
        return (res, )

    @classmethod
    def save_log(cls, round_id, log, d_local, d_global):
        '''
        保存比赛记录
        '''
        log_name = path.join(d_local['match_dir'], 'logs/%02d.zlog' % round_id)
        pingpong_api.save_log(log, log_name)

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        return pingpong_api.load_log(
            path.join(match_dir, 'logs', '%02d.zlog' % rec_id))

    @classmethod
    def stringfy_record(cls, record):
        return 'TODO'

    @staticmethod
    def summary_records(records):
        '''
        统计比赛记录
        '''
        result_stat = {0: 0, 1: 0, None: 0}
        for rec in records:
            if rec == None:
                continue
            winner = rec[rec['winner']] == 'code2'
            result_stat[winner] += 1
        return {
            'stat': result_stat,
        }
