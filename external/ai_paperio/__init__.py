from os import path
from sys import modules
from external._base import BasePairMatch
from external.factory import FactoryDeco
from functools import lru_cache

# 设置路径
import os, sys
paperio_path = os.path.join(os.path.dirname(__file__), 'paper.io.sessdsa')
sys.path.append(paperio_path)
import match_core, match_interface


# 比赛进程
@FactoryDeco(2)
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
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误 '''
        if winner != None:
            descrip = descrip[1 - winner]
        match_core.init_field(
            cls.init_params.get('k', 51), cls.init_params.get('h', 101),
            cls.init_params.get('max_turn', 2000),
            cls.init_params.get('max_time', 30))
        match_result = (winner, -1, descrip)
        return {
            'players': d_local['names'],
            'size': (match_core.WIDTH, match_core.HEIGHT),
            'maxturn': match_core.MAX_TURNS,
            'maxtime': match_core.MAX_TIME,
            'result': match_result,
            'log': match_core.LOG_PUBLIC
        }

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        return cls.load_record_path(
            path.join(match_dir, 'logs', '%02d.clog' % rec_id))

    @classmethod
    @lru_cache()
    def load_record_path(cls, record_path):
        return match_interface.load_match_log(record_path)

    @classmethod
    def stringfy_record_obj(cls, record):
        record = {**record}  # 复制一份
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
