from os import path
from sys import modules
from external._base import BasePairMatch
from functools import lru_cache
from . import match_core, match_interface
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


# 比赛进程
class PaperIOMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        required_functions = ['play']

    def get_timeout(self):
        '''局数*总思考时间*2方'''
        return self.params['rounds'] * (self.params['max_time'] * 2 + 5
                                        )  # 超时限制

    @classmethod
    def pre_run(cls, d_local, d_global):
        '''
        赛前准备
        '''

        # 初始化环境
        match_interface.clear_storage()
        for i in range(2):
            try:
                players[i].init(match_core.STORAGE[i])
            except:
                pass

        # 筛选保留params内参数
        tmp = d_local['params']
        return {
            k: tmp[k]
            for k in (  # 'k', 'h',
                'max_turn', 'max_time')
        }

    @classmethod
    def swap_fields(cls, d_local, d_global):
        '''
        交换场地
        '''
        match_interface.swap_storage()

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        运行一局比赛
        并返回比赛记录对象
        '''
        return match_core.match(d_local['players'], d_local['names'],
                                **cls.init_params)

    @classmethod
    def output_queue(cls, match_log):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        return match_log['result']

    @classmethod
    def save_log(cls, round_id, log, d_local, d_global):
        '''
        保存比赛记录为.clog文件
        '''
        log_name = path.join(d_local['match_dir'], 'logs/%02d.clog' % round_id)
        match_interface.save_compact_log(log, log_name)

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        return match_interface.load_match_log(
            path.join(match_dir, 'logs', '%02d.clog' % rec_id))

    @classmethod
    @lru_cache()
    def stringfy_record(cls, match_dir, rec_id):
        record = {**cls.load_record(match_dir, rec_id)}  # 复制一份
        record['traces'] = list(map(list, record['traces']))
        record['timeleft'] = [[round(x, 3) for x in lst]
                              for lst in record['timeleft']]
        if record['result'][1] == -1:  # 将Exception转换为str
            record['result'] = list(record['result'])
            e = record['result'][2]
            record['result'][2] = cls.stringfy_error(e)
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
            winner = rec['result'][0]
            if winner != None and rec['players'][0] == 'code2':
                winner = 1 - winner
            result_stat[winner] += 1
        result_stat['draw'] = result_stat[None]
        return {
            'stat': result_stat,
        }


# 比赛记录显示模板
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from external.tag_loader import RecordMeta

    class PaperIORecord(metaclass=RecordMeta(2)):
        def r_holder(_, match, record):
            if record['players'][0] == 'code1':
                return match.code1.name
            return match.code2.name

        def r_length(_, match, record):
            return len(record['timeleft'][0]) - 1

        def r_winner(_, match, record):
            res = record['result']
            if res[0] == None:
                return '平手'

            code2_hold = (record['players'][0] == 'code2')
            holder_win = not res[0]
            code2_win = (code2_hold == holder_win)
            return '%s (%s, %s)' % (
                match.code2.name if code2_win else match.code1.name,
                ('发起方', '接收方')[code2_win],
                ('后手', '先手')[holder_win],
            )

        desc_pool = [
            '回合数耗尽，结算得分', '运行超时', 'AI函数报错', '玩家撞墙', '玩家撞击纸带', '侧碰', '正碰，结算得分',
            '领地内互相碰撞'
        ]

        def r_win_desc(_, match, record):
            res = record['result']
            return _.desc_pool[res[1] + 3]

        def r_desc_plus(_, match, record):
            res = record['result']
            if abs(res[1]) == 3:
                return '%s : %s' % tuple(res[2])
            if res[1] == -1:
                return res[2]
            if res[1] == 1:
                if res[0] == res[2]:
                    return '对手撞击'
                return '自己撞击'
            return '无'
