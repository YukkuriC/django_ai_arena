from os import path, makedirs
from functools import lru_cache
import json
from external._base import BasePairMatch
from external.factory import FactoryDeco
from .PyTicTacToe import ttt
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


# 比赛进程
@FactoryDeco(0)
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
    def get_winner(cls, record):
        ''' 判断胜者 '''
        winner = record['winner']
        if winner != None and record['names'][0] == 'code2':
            winner = 1 - winner
        return winner


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordBase, RecordDeco

    @RecordDeco(0)
    class TTTRecord(RecordBase):
        def i_holder(_, match, record):
            return record['names'][0] == 'code2'

        def i_winner(_, match, record):
            return record['winner']

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
