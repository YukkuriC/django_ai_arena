from os import path, makedirs
from functools import lru_cache
import json
from external._base import BasePairMatch
from external.factory import FactoryDeco
from .PyTicTacToe import ttt, ttt_extend


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
        return ttt_extend.GameSum15(d_local['players'], d_local['names'],
                                    1).match()

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
