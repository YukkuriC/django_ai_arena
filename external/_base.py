from time import perf_counter as pf
from multiprocessing import Process, Queue
from os import path
from sys import modules
from datetime import datetime
import ast, random, json
if __name__ != '__mp_main__':  # 由参赛子进程中隔离django库
    from django.conf import settings


class BaseProcess:
    '''
    比赛子进程维护器
    params:
        codes: 参赛双方代码文件路径
        match_name: 比赛名称
        params: 比赛设置参数字典
    '''

    def __init__(self, codes, match_name, params):
        from match_sys import models

        # 接收队列
        self.result_raw = []
        self.output = Queue()

        # 初始化进程
        self.params = params
        self.match_name = match_name
        match_dir = path.join(settings.PAIRMATCH_DIR, match_name)
        self.process = Process(
            target=self.process_run,
            args=(codes, match_dir, params, self.output),
            daemon=1)

        # 获取match对象
        self.match = models.PairMatch.objects.get(name=match_name)

    def start(self):
        '''启动进程'''
        self.t_start = pf()
        self.timeout = self.get_timeout()
        self.process.start()
        try:
            self.match.status = 1
            self.match.run_datetime = datetime.now()
            self.match.save()
        except:
            pass

    def check_active(self, now):
        '''
        获取当前比赛状态，并自动运行总结程序
        now: 传入当前时间
        '''
        # 读取进程队列输出内容
        updated = False
        while not self.output.empty():
            self.result_raw.append(self.output.get())
            updated = True
        if updated:
            self.match.finished_rounds = len(self.result_raw)
            self.match.save()

        # 判断超时
        if self.process.is_alive():
            if now - self.t_start > self.timeout:  # 超时或外部中止自动杀进程
                self.process.terminate()
                return self.summary(True)
            return True
        return self.summary(False)

    @staticmethod
    def process_run(codes, match_dir, params, output):
        '''进程运行函数'''
        raise NotImplementedError

    def summary(self, timeout):
        '''
        输出总结结果
        timeout: 是否为超时杀进程
        '''
        pass

    if 'grabbing parameters':

        def get_timeout(self):
            '''默认获取超时限制'''
            return settings.DEFAULT_MAX_RUNNING_SEC * self.params.get(
                'rounds', 1)

        @staticmethod
        def get_first_sequence(rounds, who_first):
            '''
            获取双方先手序列
            0为己方(code1)先手，1为对方(code2)先手
            '''
            # 使用序列重载
            if isinstance(who_first, (list, tuple)):
                seq = []
                while len(seq) < rounds:
                    seq.extend(who_first)
                return seq[:rounds]

            # 输入预设类型编号
            else:
                who_first = int(who_first)
                if who_first < 2:  # 0己方/1对方
                    return [who_first] * rounds
                elif who_first == 2:  # 2各半
                    return [i < (rounds + 1) // 2 for i in range(rounds)]
                else:  # 3随机
                    return [random.randrange(2) for i in range(rounds)]


class BaseCodeLoader:
    '''
    比赛代码载入、检查功能
    '''

    @classmethod
    def load_code(cls, code_raw, raw=False):
        '''
        加载代码文件，返回其模块
        params:
            code_raw: 代码文件路径或代码整体字符串
            raw: 是否为直接的代码字串
        '''
        # 直接读取字符串
        if raw:
            if isinstance(code_raw, bytes):
                code_raw = code_raw.decode('utf-8', 'ignore')

        # 读取代码文件内容
        else:
            try:
                with open(code_raw, encoding='utf-8', errors='ignore') as f:
                    code_raw = f.read()
            except Exception as e:
                raise SyntaxError('文件读取失败: ' + str(e))

        # 将待导入代码转换为AST
        try:
            code_tree = ast.parse(code_raw, '<qwq>')
        except Exception as e:
            raise SyntaxError('解析失败: ' + cls.stringfy_error(e))

        # 在最底层禁止非函数定义与__doc__的节点
        for node in code_tree.body:
            if isinstance(node, ast.FunctionDef):
                continue
            if isinstance(node, (ast.Expr, ast.Assign)):
                if isinstance(node.value, ast.Str):
                    continue
            raise SyntaxError('第%d行: 非法语句' % node.lineno)

        # 替换非法import与函数
        for node in ast.walk(code_tree):
            if isinstance(node, ast.Import):
                for module in node.names:
                    if module.name in cls.Meta.module_blacklist:
                        module.name = 'math'
                        module.asname = None
            if isinstance(node, ast.ImportFrom):
                if node.module in cls.Meta.module_blacklist:
                    node.module = 'math'
                    for sub in node.names:
                        sub.name = 'sin'
                        sub.asname = None
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute
                              ) and func.attr in cls.Meta.func_blacklist:
                    func.attr = 'print'
                elif isinstance(
                        func, ast.Name) and func.id in cls.Meta.func_blacklist:
                    func.id = 'print'

        # 加载模块并输出
        try:

            class pack:
                exec(compile(code_tree, '', 'exec'))
        except Exception as e:
            raise RuntimeError(cls.stringfy_error(e))

        return pack

    @staticmethod
    def stringfy_error(e):
        return '%s: %s' % (type(e).__name__, e)

    class Meta:
        module_blacklist = ['os', 'sys', 'builtins']  # 禁止导入的模块
        func_blacklist = ['eval', 'exec', 'compile', '__import__']  # 禁止使用的函数


class BaseRecordLoader:
    @classmethod
    def load_record(cls, match_dir, rec_id):
        '''
        读取比赛记录文件，实现时可lru_cache
        params:
            match_dir: 比赛对应存储文件夹
            rec_id: 比赛记录编号
        '''
        pass

    @classmethod
    def load_records(cls, match):
        '''
        批量读取比赛存储文件夹内所有文件

        '''
        match_dir = path.join(settings.PAIRMATCH_DIR, match.name)
        res = [None] * match.finished_rounds
        for i in range(match.finished_rounds):
            try:
                res[i] = cls.load_record(match_dir, i)
            except:
                pass
        return res

    @classmethod
    def stringfy_record(cls, record):
        '''将比赛记录输出为字符串，以传输至前端'''
        return json.dumps(record, separators=(',', ':'))

    @staticmethod
    def summary_records(records):
        '''将比赛记录汇总统计'''
        pass


class BasePairMatch(BaseProcess, BaseCodeLoader, BaseRecordLoader):
    '''
    组装功能组件
    增加比赛记录统计与天梯分计算部分
    '''

    def summary_raw(self):
        '''
        抽象接口
        将队列输出结果result_raw内容汇总为统计字典
        {0: code1获胜, 1: code2获胜, None: 平局}
        '''
        return {0: 0, 1: 0, None: 0}

    def calculate_dscore(self, code1, code2, results):
        '''
        计算双方代码天梯分变动
        默认为ELO算法
        '''
        real_score = results[0] + 0.5 * results[None]
        e_score = sum(results.values()) / (1 + 10**
                                           ((code2.score - code1.score) / 400))
        return (real_score - e_score) * settings.SCORE_FACTOR_PAIRMATCH

    def summary(self, timeout):
        '''
        输出总结结果
        timeout: 是否为超时杀进程
        '''
        result_stat = self.summary_raw()

        # 计算等级分变化
        code1 = self.match.code1
        code2 = self.match.code2
        dscore = self.calculate_dscore(code1, code2, result_stat)

        # 写入双方代码统计
        if code1 != code2:
            code1.score += dscore
            code1.num_matches += 1
            code1.num_wins += result_stat[0]
            code1.num_loses += result_stat[1]
            code1.num_draws += result_stat[None]
            code1.save()
            code2.score -= dscore
            code2.num_matches += 1
            code2.num_wins += result_stat[1]
            code2.num_loses += result_stat[0]
            code2.num_draws += result_stat[None]
            code2.save()

        # 写入match信息
        self.match.finish_datetime = datetime.now()
        self.match.status = 2 + bool(timeout)
        self.match.delta_score = dscore
        self.match.save()