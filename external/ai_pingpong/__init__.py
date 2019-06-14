from . import pingpong_api
from external._base import BasePairMatch
from os import path
from functools import lru_cache


class PingPongMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        game_whitelist = ['table']
        required_functions = ['serve', 'play', 'summarize']

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
        return pingpong_api.one_race(*tmp)

    @classmethod
    def output_queue(cls, log):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        res = log['winner']
        if res != None:
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
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误 '''
        descrip = [cls.stringfy_error(e) for e in descrip]
        if winner != None:
            descrip = descrip[1 - winner]
        from table import Table, DIM, TMAX
        main_table = Table()
        return {
            'DIM': DIM,
            'TMAX': TMAX,
            'tick_step': main_table.tick_step,
            'West': d_local['names'][0],
            'East': d_local['names'][1],
            'tick_total': main_table.tick,
            'winner': winner,
            'winner_life': -1,
            'reason': descrip,
            'log': []
        }

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        return pingpong_api.load_log(
            path.join(match_dir, 'logs', '%02d.zlog' % rec_id))

    @classmethod
    @lru_cache()
    def stringfy_record(cls, match_dir, rec_id):
        record = cls.load_record(match_dir, rec_id)
        record_trans = pingpong_api.jsonfy(record)
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
            if rec['winner'] == None:
                winner = None
            else:
                winner = rec[rec['winner']] == 'code2'
            result_stat[winner] += 1
        return {
            'stat': result_stat,
        }


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordMeta

    class PingPongRecord(metaclass=RecordMeta(1)):
        def r_holder(_, match, record):
            if record['West'] == 'code1':
                return match.code1.name
            return match.code2.name

        def r_length(_, match, record):
            nround = len(record['log']) - 1
            ntick = record['tick_total']
            return '%s回合 (%s Tick)' % (nround, ntick)

        def r_winner(_, match, record):
            if record['winner'] == None:
                return '平局'
            code2_hold = (record['West'] == 'code2')
            holder_win = (record['winner'] == 'West')
            code2_win = (code2_hold == holder_win)
            return '%s (%s, %s)' % (
                match.code2.name if code2_win else match.code1.name,
                ('发起方', '接收方')[code2_win],
                ('后手', '先手')[holder_win],
            )

        def r_win_desc(_, match, record):
            return record['reason']

        def r_desc_plus(_, match, record):
            return '剩余生命：%s' % record['winner_life']
