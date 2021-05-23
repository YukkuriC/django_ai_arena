from external._base import BasePairMatch
from external.factory import FactoryDeco
from . import api


# 比赛进程
@FactoryDeco(5)
class EufMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_classes = [['player_class', ['__init__', 'player_func']]]
        game_whitelist = ['GameMap', 'config']

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        运行一局比赛
        并返回比赛记录对象
        '''
        game = api.GameWithModule(d_local['players'], d_local['names'],
                                  d_local['params'])
        game.run()
        return game.map

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
        nullgame = api.NullGame(winner, descrip, d_local['names'],
                                d_local['params'])
        return nullgame.map

    @classmethod
    def get_winner(cls, record):
        ''' 判断胜者 '''
        winner = record['winner']
        names = record['player_name']
        first_player = names.get(0, names.get('0'))
        if winner != None and first_player == 'code2':
            winner = 1 - winner
        return winner
