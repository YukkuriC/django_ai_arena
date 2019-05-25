from multiprocessing import Process
import os, sys, socket, json
from sqlite3 import connect


# 多进程支持
def setup_django():
    '''在多进程内挂载django数据库'''
    import django
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'main.settings'
    django.setup()


def init_db():
    '''
    创建或打开监控进程使用的数据库
    返回其连接
    '''
    from django.conf import settings
    conn=connect(settings.MONITOR_DB_PATH)

    # 检查版本是否对应
    query="select name from sqlite_master where name='%s' and type='table'"%settings.MONITOR_DB_VERSION

    if len(conn.execute(query).fetchall())==0:# 非当前版本
        print('NEW DATABASE <%s>'%settings.MONITOR_DB_VERSION)

        # 非当前版本爆破重建
        q_tables="select name from sqlite_master where type='table' and name<>'sqlite_sequence'"
        for table in conn.execute(q_tables).fetchall():
            conn.execute('drop table %s'%table)
        for query in settings.MONITOR_DB_TABLES:
            conn.execute(query)

    return conn

def _db_register(type,name):
    ''' 在数据库内注册指定比赛 '''

def _db_check(type,name):
    ''' 查看指定比赛是否存活 '''


def _db_unload(type,name):
    '''
    从数据库中移除指定比赛
    被移除的比赛将被对应监控进程停止
    '''

def worker():
    '''
    比赛维护进程
    循环从data_queue表内读取一行并执行
    直至data_queue为空时退出
    运行比赛时通过写入并监控running表控制超时、中止等操作
    '''
    setup_django()
    from django.conf import settings
    from time import perf_counter as pf, sleep
    from match_sys import models
    from . import helpers
    from .factory import Factory
    print('START MONITOR')
    conn=init_db()
    cursor=conn.cursor()

    # 循环读取队列内容
    # TODO: 线程安全
    while 1:
        line=cursor.execute('select * from data_queue limit 1').fetchall()
        if not line:
            break
        line=line[0]

        # 删除已读取行
        cursor.execute('delete from data_queue where match=?',line[3])
        conn.commit()

        # 创建新比赛对象
        AI_type, code1, code2, match_name, params, ranked = line
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

        # 在数据库中记录
        cursor.execute('insert into running values (?)',match_name)
        
        # 循环检测是否执行完毕
                # match_to_kill = data[1]
                # print([x.match_name for x in match_pool])
                # for match in match_pool:
                #     if match.match_name == match_to_kill:
                #         match.timeout = -1
                #         print('Killed: ' + match_to_kill)
                #         break


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
    match_queue = []  # 已创建的比赛进程队列
    match_pool = []  # 比赛进程容器
    last_idle_then = pf()  # 闲置时间戳

    # 监控socket读取内容
    sock_proc = Thread(target=inner_socket, args=(sock, dataq))
    sock_proc.start()

    # 监控循环
    while 1:
        # 获取当前时间
        now = pf()

        # 读取数据队列
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

                # 创建比赛对象
                new_match = Factory(AI_type, (code1, code2), match_name,
                                    params)
                match_queue.append(new_match)

            # 结束比赛
            if data[0] == 'kill_match':
                match_to_kill = data[1]
                print([x.match_name for x in match_pool])
                for match in match_pool:
                    if match.match_name == match_to_kill:
                        match.timeout = -1
                        print('Killed: ' + match_to_kill)
                        break

        # 在队列非空且存在空位时创建新进程
        while match_queue and len(match_pool) < settings.MATCH_POOL_SIZE:
            new_match = match_queue.pop(0)
            new_match.start()
            match_pool.append(new_match)
            print('Start:', match_pool)

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
            sock.shutdown(socket.SHUT_RD)
            sock.close()
            print('END MONITOR')
            os._exit(0)


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