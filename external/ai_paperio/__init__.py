from os import path
from sys import modules
from external._base import BasePairMatch
from functools import lru_cache
from . import match_core, match_interface
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


class PaperIOMatch(BasePairMatch):
    template_dir = 'renderer/paperio.html'

    def get_timeout(self):
        '''局数*总思考时间*2方'''
        return self.params['rounds'] * (self.params['max_time'] * 2 + 5
                                        )  # 超时限制

    @staticmethod
    def process_run(codes, match_dir, params, output):
        # 读取参数
        players = [PaperIOMatch.load_code(code) for code in codes]  # 读取代码模块
        names = ('code1', 'code2')
        rounds = params['rounds']
        who_first = params['who_first']
        first_sequence = PaperIOMatch.get_first_sequence(rounds, who_first)
        params = {
            k: params[k]
            for k in (  # 'k', 'h',
                'max_turn', 'max_time')
        }

        # 初始化环境
        match_interface.clear_storage()
        for i in range(2):
            try:
                players[i].init(match_core.STORAGE[i])
            except:
                pass

        # 运行多局比赛
        last_invert = 0  # 上一局是否对方先手
        for rid in range(rounds):
            # 处理交换场地情况
            now_invert = first_sequence[rid]
            if now_invert != last_invert:
                match_interface.swap_storage()
                players = players[::-1]
                names = names[::-1]
            last_invert = now_invert

            # 获取比赛记录
            match_log = match_core.match(players, names, **params)

            # 统计结果
            result = match_log['result']
            output.put((now_invert, ) + result)  # 发送至输出队列

            # 生成比赛记录
            log_name = path.join(match_dir, 'logs/%02d.clog' % rid)
            match_interface.save_compact_log(match_log, log_name)

    def summary_raw(self):
        result_stat = {0: 0, 1: 0, None: 0}
        for result in self.result_raw:
            winner = result[1]
            if winner != None and result[0]:
                winner = 1 - winner
            result_stat[winner] += 1
        return result_stat

    # class Meta(BasePairMatch.Meta):
    #     required_functions = ['play']

    @classmethod
    @lru_cache()
    def load_record(cls, match_dir, rec_id):
        return match_interface.load_match_log(
            path.join(match_dir, 'logs', '%02d.clog' % rec_id))

    @classmethod
    def stringfy_record(cls, record):
        record['traces'] = list(map(list, record['traces']))
        record['timeleft'] = list(map(list, record['timeleft']))
        if record['result'][1] == -1:  # 将Exception转换为str
            record['result'] = list(record['result'])
            e = record['result'][2]
            record['result'][2] = cls.stringfy_error(e)
        return super().stringfy_record(record)

    @staticmethod
    def summary_records(records):
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