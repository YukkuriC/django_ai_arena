from external._base import BasePairMatch
from functools import lru_cache
import time, random
from os import path
from . import api_2048


class _2048Match(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_classes = [('Player', ['output'])]

    def get_timeout(self):
        '''获取超时限制'''
        return self.params['rounds'] * (self.params['max_time'] * 2 + 10)

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        运行一局比赛
        并返回比赛记录对象
        '''
        # 定期重设随机种子
        if d_local['who_first'] != "4" or d_local['rid'] % 2 == 0:
            random.seed(int(time.time()))
        plat = api_2048.one_match(d_local['players'], d_local['params'],
                                  d_local['names'])
        return plat

    @classmethod
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误时返回空对象 '''
        return api_2048.fake_runner(winner, d_local['params'],
                                    d_local['names'])

    @classmethod
    def output_queue(cls, plat):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        return (api_2048.trans_winner(plat.winner), )

    @classmethod
    def save_log(cls, round_id, plat, d_local, d_global):
        '''
        保存比赛记录
        '''
        match_dir = d_local['match_dir']
        log_name = path.join(match_dir, 'logs/%02d.txt' % round_id)
        api_2048.dump_log(plat, log_name)

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        log_name = path.join(match_dir, 'logs/%02d.txt' % rec_id)
        return api_2048.load_log(log_name)

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
            if isinstance(winner, int) and rec["name0"] == 'code2':
                winner = 1 - winner
            result_stat[winner] += 1
        return {
            'stat': result_stat,
        }
