from external._base import BasePairMatch
from external.factory import FactoryDeco
from . import api
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


# 比赛进程
@FactoryDeco(5)
class EufMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_functions = ['player_func']
        game_whitelist = ['GameMap']

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
        return (cls.get_winner(match_log), )

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


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordBase, RecordDeco

    @RecordDeco(5)
    class EufRecord(RecordBase):
        def i_holder(_, match, record):
            return record['player_name']['0'] == 'code2'  # JSON化后数字key转为字符串

        def i_winner(_, match, record):
            return record['winner']

        def r_length(_, match, record):
            return len(record['history'])

        def r_win_desc(_, match, record):
            return record['result']

        def r_desc_plus(_, match, record):
            return '-'
