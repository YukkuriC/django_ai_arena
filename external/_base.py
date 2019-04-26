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

    def flush_queue(self):
        updated = False
        while not self.output.empty():
            self.result_raw.append(self.output.get())
            updated = True
        if updated:
            self.match.finished_rounds = len(self.result_raw)
            print(f'RESULT: {self.result_raw}')
            self.match.save()

    def check_active(self, now):
        '''
        获取当前比赛状态，并自动运行总结程序
        now: 传入当前时间
        '''
        # 判断超时
        res = True
        if self.process.is_alive():
            self.flush_queue()
            if now - self.t_start > self.timeout:  # 超时或外部中止自动杀进程
                self.process.terminate()
                self.flush_queue()
                res = self.summary(True)
        else:
            self.flush_queue()
            res = self.summary(False)

        # 返回结果
        return res

    @classmethod
    def process_run(cls, codes, match_dir, params, output):
        '''进程运行函数'''
        raise NotImplementedError

    def summary(self, timeout):
        '''
        输出总结结果
        timeout: 是否为超时杀进程
        '''
        pass


class BaseCodeLoader:
    '''
    比赛代码载入、检查功能
    '''

    @classmethod
    def verify_code(cls, code_raw):
        '''
        通过AST检查代码合法性
        params:
            code_raw: 代码整体字符串
        '''
        if isinstance(code_raw, bytes):
            code_raw = code_raw.decode('utf-8', 'ignore')

        # 将待导入代码转换为AST
        code_tree = ast.parse(code_raw, '<qwq>')

        # 检查非法import与函数
        for node in ast.walk(code_tree):
            if isinstance(node, ast.Import):
                for module in node.names:
                    assert module.name not in cls.Meta.module_blacklist, (
                        node.lineno, '非法import: ' + module.name)
            if isinstance(node, ast.ImportFrom):
                assert node.module not in cls.Meta.module_blacklist, (
                    node.lineno, '非法import: ' + node.module)
            if isinstance(node, ast.Call):
                func = node.func
                func_name = getattr(func, 'attr', getattr(func, 'id', None))
                assert func_name not in cls.Meta.func_blacklist, (
                    node.lineno, '非法函数调用: ' + func_name)

        # 检查是否已导入必要函数
        all_func = set()
        for node in code_tree.body:
            if isinstance(node, ast.FunctionDef):
                all_func.add(node.name)
        for func in cls.Meta.required_functions:
            assert func in all_func, '缺少必要函数: ' + func

        # 返回AST
        return code_tree

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

        # 检查代码合法性
        code_tree = cls.verify_code(code_raw)

        # 加载模块并输出
        try:
            pack = type(ast)('code')
            exec(compile(code_tree, '', 'exec'), pack.__dict__)
        except Exception as e:
            raise RuntimeError(cls.stringfy_error(e))

        return pack

    @staticmethod
    def stringfy_error(e):
        return '%s: %s' % (type(e).__name__, e)

    class Meta:
        module_blacklist = ['os', 'sys', 'builtins', 'subprocess']  # 禁止导入的模块
        func_blacklist = ['eval', 'exec', 'compile', '__import__',
                          'open']  # 禁止使用的函数
        required_functions = []  # 必要的函数接口


class BaseRecordLoader:
    '''
    在前端加载比赛记录
    '''

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
    init_params = None  # 用于容纳赛前准备参数
    template_dir = NotImplemented  # 前端渲染页地址
    __repr__ = __str__ = lambda self: '<%s: %s>' % (type(self).__name__, self.match_name)

    # 默认的获取比赛参数函数
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

    @classmethod
    def process_run(cls, codes, match_dir, params, output):
        '''
        默认的比赛运行框架
        结构:
            读取参数
            初始化环境 <pre_run>
            for i in range(params['rounds']):
                是否交换场地 <swap_fields>
                运行比赛 <run_once>
                发送结果至队列 <output_queue>
                保存记录至硬盘 <save_log>
        Params:
            codes: 列表，内容为双方代码路径
            match_dir: 比赛记录文件夹地址
            params: 比赛表单参数
            output: 用于输出比赛结果的multiprocessing.Queue对象
        '''
        # 读取参数
        players = [cls.load_code(code) for code in codes]  # 读取代码模块
        names = ('code1', 'code2')
        rounds = params['rounds']
        who_first = params['who_first']
        first_sequence = cls.get_first_sequence(rounds, who_first)

        # 初始化环境
        cls.init_params = cls.pre_run(locals(), globals())

        # 运行多局比赛
        last_invert = 0  # 上一局是否对方先手
        for rid in range(rounds):
            # 处理交换场地情况
            now_invert = first_sequence[rid]
            if now_invert != last_invert:
                players = players[::-1]
                names = names[::-1]
                cls.swap_fields(locals(), globals())
            last_invert = now_invert

            # 获取比赛记录
            log = cls.run_once(locals(), globals())

            # 统计结果
            result = cls.output_queue(log)
            if isinstance(result, tuple):
                output.put((now_invert, ) + result)  # 发送至输出队列

            # 生成比赛记录
            cls.save_log(rid, log, locals(), globals())

    def summary_raw(self):
        result_stat = {0: 0, 1: 0, None: 0}
        for result in self.result_raw:
            try:
                winner = result[1]
                if winner != None and result[0]:
                    winner = 1 - winner
                result_stat[winner] += 1
            except Exception as e:
                print(type(e).__name__, e)
        return result_stat

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

    @classmethod
    def pre_run(cls, d_local, d_global):
        '''
        抽象接口，进行多局比赛前准备
        返回值将附着至cls.init_params
        Params:
            d_local: 函数内locals()获取的本地变量
            d_global: 函数内globals()获取的全局变量
        '''
        pass

    @classmethod
    def swap_fields(cls, d_local, d_global):
        '''
        抽象接口，交换比赛双方场地时使用
        Params:
            d_local: 函数内locals()获取的本地变量
            d_global: 函数内globals()获取的全局变量
        '''
        pass

    @classmethod
    def run_once(cls, d_local, d_global):
        '''
        抽象接口，运行一局比赛
        并返回比赛记录对象
        Params:
            d_local: 函数内locals()获取的本地变量
            d_global: 函数内globals()获取的全局变量
        '''
        pass

    @classmethod
    def output_queue(cls, log):
        '''
        抽象接口，读取比赛记录
        返回比赛结果元组，其中首位代表比赛结果(0: 先手胜利; 1: 后手胜利; None: 平局)
        Params:
            log: 由run_once函数返回的比赛记录对象
        '''
        return (None, )

    @classmethod
    def save_log(cls, round_id, log, d_local, d_global):
        '''
        抽象接口，保存比赛记录至硬盘
        Params:
            log: 由run_once函数返回的比赛记录对象
            d_local: 函数内locals()获取的本地变量
            d_global: 函数内globals()获取的全局变量
        '''
        pass
