from external._base import BasePairMatch
from external.factory import FactoryDeco
from functools import lru_cache
from os import path
import random, time

from . import osmo_api


@FactoryDeco(3)
class OsmoMatch(BasePairMatch):
    class Meta(BasePairMatch.Meta):
        game_whitelist = ['consts', 'world', 'cell']
        required_classes = [('Player', ['strategy'])]

    def get_timeout(self):
        '''获取超时限制'''
        return self.params['rounds'] * (
            osmo_api.consts.Consts["MAX_TIME"] * 2 + 10)

    @classmethod
    def pre_run(cls, d_local, d_global):
        '''
        局间继承参数
        '''
        # 覆盖默认参数
        osmo_api.apply_params(d_local['params'])

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
        if d_local['who_first'] != "4" or d_local['rid'] % 2 == 0:
            cls.last_seed = int(time.time() * 1000)
        wld = osmo_api.one_race(d_local['players'], cls.init_params,
                                d_local['names'], cls.last_seed)
        if wld.result['winner'] not in (0, 1):
            wld.result['winner'] = None
        return wld

    @classmethod
    def output_queue(cls, world):
        '''
        读取比赛记录
        返回比赛结果元组
        '''
        res = world.result
        return (res['winner'], )

    @classmethod
    def save_log(cls, round_id, world, d_local, d_global):
        '''
        保存比赛记录
        '''
        match_dir = d_local['match_dir']
        log_name = path.join(match_dir, 'logs/%02d.zlog' % round_id)
        osmo_api.save_log(world, log_name)

    @classmethod
    def runner_fail_log(cls, winner, descrip, d_local, d_global):
        ''' 内核错误 '''
        return osmo_api.FakeWorld(descrip, d_local['names'])

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        log_name = path.join(match_dir, 'logs/%02d.zlog' % rec_id)
        return cls.load_record_path(log_name)

    @classmethod
    @lru_cache()
    def load_record_path(cls, record_path):
        return osmo_api.load_log(record_path)

    @classmethod
    def stringfy_record_obj(cls, record):
        record = {**record}
        if record['cause'] == "RUNTIME_ERROR":  # 将Exception转换为str
            if isinstance(record["detail"], (list, tuple)):
                tmp = []
                for i in record["detail"]:
                    if isinstance(i, Exception):
                        i = cls.stringfy_error(i)
                    tmp.append(i)
                record['detail'] = tmp
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
            winner = rec['winner']
            if isinstance(winner, int) and rec["players"][0] == 'code2':
                winner = 1 - winner
            result_stat[winner] += 1
        return {
            'stat': result_stat,
        }
