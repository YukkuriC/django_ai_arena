from external._base import BasePairMatch
from external.factory import FactoryDeco
from external.helpers_core import stringfy_error
from .wrap import Game, register_player


# 比赛进程
@FactoryDeco(6)
class TetrisMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_classes = [('Player', ['output'])]

    @classmethod
    def pre_run(cls, d_local, d_global):
        for module, name in zip(d_local['players'], d_local['names']):
            register_player(name, module)

    @classmethod
    def run_once(cls, d_local, d_global):
        play = Game(*d_local['names'], 100)
        while play.state == "gaming":
            play.turn()
        play.end()

        return play.reviewData.gameData

    @classmethod
    def _trans_winner(cls, record):
        ''' winner转换至平台设定 '''
        return record["winner"] - 1 if record["winner"] > 0 else None

    @classmethod
    def output_queue(cls, record):
        return (cls._trans_winner(record), )

    @classmethod
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        winner = winner + 1 if isinstance(winner, int) else -1
        names = d_local['names']
        log = {
            "player1": names[0],
            "player2": names[1],
            "winner": winner,
            "reason": stringfy_error(e),
            "tag": None,
            "matchData": {}
        }

    @classmethod
    def get_winner(cls, record):
        ''' 判断胜者 '''
        winner = cls._trans_winner(record)
        if winner != None and record['player1'] == 'code2':
            winner = 1 - winner
        return winner

    @classmethod
    def analyze_tags(cls, record):
        return record["tag"]