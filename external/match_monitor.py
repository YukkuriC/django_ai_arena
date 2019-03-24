from multiprocessing import Process, Queue
import os, sys


# 多进程支持
def setup_django():
    '''在多进程内挂载django数据库，返回django模块'''
    import django
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'main.settings'
    django.setup()


def run_process(logger_module=sys.modules[__name__]):
    '''
    启动主进程并挂载Queue对象至logger_module
    logger_module默认为自身模块(match_monitor)
    每次传参前来一句
    '''
    from django.db import connections
    connections.close_all()
    flag = hasattr(logger_module, 'process')  # 是否重启进程
    if flag and not logger_module.process.is_alive():
        logger_module.process.join()  # 防止linux僵尸
        flag = False
    if not flag:
        if not hasattr(logger_module, 'hook'):
            logger_module.hook = Queue()
        pc = Process(target=monitor, args=(logger_module.hook, ))
        pc.start()
        logger_module.process = pc
    return logger_module.hook


def monitor(dataq):
    '''
    主伴随进程，用于管理比赛进程数量、杀死超时进程等
    通过挂载于logger_module.hook的Queue传递参数，用于启动比赛
    '''
    # 初始化准备工作
    setup_django()
    from django.conf import settings
    from time import perf_counter as pf, sleep
    from .factory import Factory
    match_pool = []
    last_idle_then = pf()

    # 监控循环
    while 1:
        # 获取当前时间
        now = pf()

        # 在队列非空且存在空位时创建新进程
        while not dataq.empty() and len(match_pool) < settings.MATCH_POOL_SIZE:
            # 读取参数
            data = dataq.get()

            # 创建比赛
            if isinstance(data, tuple):
                AI_type, code1, code2, match_name, params = data
                print('Received: ' + match_name)
                match_dir = os.path.join(settings.PAIRMATCH_DIR,
                                         match_name)  # 将比赛文件夹转化为绝对路径
                os.makedirs(match_dir, exist_ok=1)

                # 装载进程
                new_match = Factory(AI_type, (code1, code2), match_name,
                                    params)
                new_match.start()
                match_pool.append(new_match)

            # 结束比赛
            if isinstance(data, str):
                print('TESTTESTTEST123')
                for match in match_pool:
                    if match.match_name == data:
                        match.timeout = -1
                        print('Killed: ' + data)
                        break

        # 移除所有超时或结束进程
        match_pool = [x for x in match_pool if x.check_active(now)]

        # 在仍有任务运行时更新闲置计时
        if match_pool:
            last_idle_then = now

        # 如果过长闲置则终止
        sleep(settings.MATCH_MONITOR_CYCLE)
        if now - last_idle_then > settings.MAX_MONITOR_IDLE_SEC:
            return


def start_match(AI_type, code1, code2, param_form):
    from match_sys import models
    from . import helpers

    # 获取match参数
    params = param_form.cleaned_data
    while 1:
        match_name = helpers.gen_random_string()
        if not models.PairMatch.objects.filter(name=match_name):
            break
    new_match = models.PairMatch()
    new_match.ai_type = AI_type
    new_match.name = match_name
    new_match.code1 = models.Code.objects.get(id=code1)
    new_match.code2 = models.Code.objects.get(id=code2)
    new_match.rounds = params['rounds']
    new_match.save()

    # 传送参数至进程 (AI_type,code1,code2,match_name,params)
    hook = run_process()  # 启动monitor进程
    code1 = str(new_match.code1.content)
    code2 = str(new_match.code2.content)
    hook.put((AI_type, code1, code2, match_name, params))
    print('Sent: ' + match_name)

    # 返回match对象
    return new_match


def kill_match(match_name):
    hook = run_process()
    hook.put(match_name)
    print('Killing: ' + match_name)