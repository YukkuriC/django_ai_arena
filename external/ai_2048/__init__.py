from external._base import BasePairMatch
from external.factory import FactoryDeco
from functools import lru_cache
import time
from collections import Counter
from os import path
from . import api_2048


@FactoryDeco(4)
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
            cls.last_seed = int(time.time())
        plat = api_2048.one_match(d_local['players'], d_local['params'],
                                  d_local['names'], cls.last_seed)
        return plat

    @classmethod
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误时返回空对象 '''
        return api_2048.fake_runner(winner, descrip, d_local['params'],
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
        return cls.load_record_path(log_name)

    @classmethod
    @lru_cache()
    def load_record_path(cls, record_path):
        return api_2048.load_log(record_path)

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

    @classmethod
    def analyze_tags(cls, record):
        res = []

        # 统计盘面
        last_board = None
        for frame in reversed(record['logs']):
            if 'P' in frame:
                last_board = frame['P']
                break
        if last_board:
            board_flatten = [
                last_board[r][c] for r in range(4) for c in range(8)
            ]
            # 统计最大值
            max_val = max(map(abs, board_flatten))
            if max_val >= 10:
                res.append(["4096!", "red"])
            elif max_val == 9:
                res.append(["2048!", "orange"])

            # 统计双方回合差
            counter = Counter()
            for frame in record['logs']:
                if 'D' in frame:
                    counter[frame['D']['p']] += 1
            n_count = abs(counter[0] - counter[1])
            if n_count > 20:
                res.append([f"{n_count}回合塞爆!", "purple"])

            # 统计局面倾向
            n_p1, n_p2 = max(board_flatten), -min(board_flatten)
            n_diff = abs(n_p1 - n_p2)
            if n_diff >= 3:
                res.append([f"{n_diff}级压胜!", "green"])

        else:  # 空盘面
            res.append(["空盘", "gray"])

        # 统计回合数
        try:
            res.append([f"{record['logs'][-1]['D']['r']+1}回合"])
        except:
            pass

        return res
