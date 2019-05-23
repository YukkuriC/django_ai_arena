from multiprocessing import Process, Queue
import os, sys, socket, json


# 多进程支持
def setup_django():
    '''在多进程内挂载django数据库，返回django模块'''
    import django
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'main.settings'
    django.setup()


def send_command(cmd: str):
    '''
    向监控进程传递命令
    若监控进程不存在则创建并挂载socket
    '''
    from django.db import connections
    from django.conf import settings
    connections.close_all()

    # 尝试创建监控进程
    new_socket = False
    try:
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(("localhost", settings.MONITOR_SOCKET_PORT))
        serversocket.listen(10)
        new_socket = True
    except OSError:
        pass

    # 从新socket创建监控进程
    if new_socket:
        pc = Process(target=monitor, args=(serversocket, ))
        pc.start()

    # 传递参数
    sock = socket.create_connection(('localhost',
                                     settings.MONITOR_SOCKET_PORT))
    sock.sendall(cmd.encode('utf-8', 'ignore'))
    sock.shutdown(socket.SHUT_WR)


def inner_socket(sock, que):
    """
    从socket中读取字节串
    输出至queue
    """
    while 1:
        conn, _ = sock.accept()
        data = b''
        while 1:
            new_data = conn.recv(1024)
            if new_data:
                data += new_data
            else:
                break
        que.put(data.decode('utf-8', 'ignore'))


def monitor(sock):
    '''
    主伴随进程，用于管理比赛进程数量、杀死超时进程等
    通过挂载于logger_module.hook的Queue传递参数，用于启动比赛
    '''
    # 初始化准备工作
    setup_django()
    from django.conf import settings
    from time import perf_counter as pf, sleep
    from match_sys import models
    from . import helpers
    from .factory import Factory
    print('START MONITOR')
    dataq = Queue()  # socket命令读取进程
    match_pool = []  # 比赛进程容器
    last_idle_then = pf()  # 闲置时间戳

    # 监控socket读取内容
    sock_proc = Process(target=inner_socket, args=(sock, dataq))
    sock_proc.start()

    # 监控循环
    while 1:
        # 获取当前时间
        now = pf()

        # 在队列非空且存在空位时创建新进程
        while not dataq.empty() and len(match_pool) < settings.MATCH_POOL_SIZE:
            # 读取参数
            data = dataq.get().split()

            # 创建比赛(Pairmatch)
            if data[0] == 'match':
                AI_type, code1, code2, match_name, params, ranked = json.loads(
                    data[1])

                # 创建新比赛对象
                new_match = models.PairMatch()
                new_match.ai_type = AI_type
                new_match.name = match_name
                new_match.code1 = models.Code.objects.get(id=code1)
                new_match.code2 = models.Code.objects.get(id=code2)
                new_match.old_score1 = new_match.code1.score
                new_match.old_score2 = new_match.code2.score
                new_match.rounds = params['rounds']
                new_match.is_ranked = ranked
                new_match.params = json.dumps(params)
                new_match.save()

                # 读取代码、比赛路径
                code1 = str(new_match.code1.content)
                code2 = str(new_match.code2.content)
                match_dir = os.path.join(settings.PAIRMATCH_DIR, match_name)
                os.makedirs(match_dir, exist_ok=1)

                # 装载进程
                new_match = Factory(AI_type, (code1, code2), match_name,
                                    params)
                new_match.start()
                match_pool.append(new_match)
                print('Received: ' + match_name, match_pool)

            # 结束比赛
            if data[0] == 'kill_match':
                match_to_kill = data[1]
                print([x.match_name for x in match_pool])
                for match in match_pool:
                    if match.match_name == match_to_kill:
                        match.timeout = -1
                        print('Killed: ' + match_to_kill)
                        break

        # 移除所有超时或结束进程
        tmp = [x for x in match_pool if x.check_active(now)]
        if tmp != match_pool:
            print(match_pool, '->', tmp)
            match_pool = tmp

        # 在仍有任务运行时更新闲置计时
        if match_pool or (not dataq.empty()):
            last_idle_then = now

        # 如果过长闲置则终止
        sleep(settings.MONITOR_CYCLE)
        if now - last_idle_then > settings.MONITOR_MAX_IDLE_SEC:
            sock_proc.terminate()
            sock_proc.join()
            print('END MONITOR')
            return


def start_match(AI_type, code1, code2, param_form, ranked=False):
    from match_sys import models
    from . import helpers

    # 生成随机match名称
    while 1:
        match_name = helpers.gen_random_string()
        if not models.PairMatch.objects.filter(name=match_name):
            break

    # 获取match参数
    params = param_form.cleaned_data
    create_params = json.dumps(
        [AI_type, code1, code2, match_name, params, ranked],
        separators=(',', ':'))

    # 传送参数至进程 (AI_type,code1,code2,match_name,params)
    send_command('match ' + create_params)
    print('Sent: ' + match_name)

    # 返回match对象名称
    return match_name


def kill_match(match_name):
    send_command('kill_match ' + match_name)
    print('Killing: ' + match_name)