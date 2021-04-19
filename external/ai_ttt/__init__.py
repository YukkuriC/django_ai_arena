from os import path, makedirs
from functools import lru_cache
import json
from external._base import BasePairMatch
from .PyTicTacToe import ttt
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


# 比赛进程
class TTTMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_functions = ['play']

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        运行一局比赛
        并返回比赛记录对象
        '''
        return ttt.Game(d_local['players'], d_local['names'], 1).match()

    @classmethod
    def output_queue(cls, match_log):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        return (match_log['winner'], )

    @classmethod
    def get_log_path(cls, match_dir, round_id):
        """ 获取log路径 """
        return path.join(match_dir, '%02d.json' % round_id)

    @classmethod
    def save_log(cls, round_id, log, d_local, d_global):
        '''
        保存比赛记录为.clog文件
        '''
        log_name = cls.get_log_path(d_local['match_dir'], round_id)
        with open(log_name, 'w', encoding='utf-8') as f:
            json.dump(log, f, separators=',:')

    @classmethod
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误 '''
        if winner != None:
            descrip = descrip[1 - winner]
        return {
            'orders': [],
            'names': ['code1', 'code2'],
            'winner': winner,
            'reason': ttt.ERROR,
            'extra': None,
            'timeouts': [],
        }

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        log_name = cls.get_log_path(match_dir, rec_id)
        return cls.load_record_path(log_name)

    @classmethod
    @lru_cache()
    def load_record_path(cls, record_path):
        with open(record_path, encoding='utf-8') as f:
            res = json.load(f)
        return res

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
            if winner != None and rec['names'][0] == 'code2':
                winner = 1 - winner
            result_stat[winner] += 1
        result_stat['draw'] = result_stat[None]
        return {
            'stat': result_stat,
        }


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordBase, RecordMeta

    class TTTRecord(RecordBase, metaclass=RecordMeta(0)):
        def i_holder(_, match, record):
            return record['names'][0] == 'code2'

        def i_winner(_, match, record):
            res = record['winner']
            if res == None:
                return None
            return not res

        def r_length(_, match, record):
            return len(record['orders'])

        desc_pool = [
            '代码超时',
            '代码报错',
            '冲突落子',
            '非法返回值',
            '游戏继续',  # 0
            '形成三连',
            '棋盘已满平局',
        ]

        def r_win_desc(_, match, record):
            return _.desc_pool[record['reason'] + 4]

        def r_desc_plus(_, match, record):
            return record['extra'] or '无'
