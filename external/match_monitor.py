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


def init_db(check=False):
    '''
    创建或打开监控进程使用的数据库
    返回其连接
    '''
    from django.conf import settings
    conn = connect(settings.MONITOR_DB_PATH)

    # 检查版本是否对应
    query = "select name from sqlite_master where name='%s' and type='table'" % settings.MONITOR_DB_VERSION

    if len(conn.execute(query).fetchall()) == 0:  # 非当前版本
        print('NEW DATABASE <%s>' % settings.MONITOR_DB_VERSION)

        # 非当前版本爆破重建
        q_tables = "select name from sqlite_master where type='table' and name<>'sqlite_sequence'"
        for table in conn.execute(q_tables).fetchall():
            conn.execute('drop table %s' % table)
        for query in settings.MONITOR_DB_TABLES:
            conn.execute(query)

    return conn


def _db_timestamp():
    ''' 获取时间戳 '''
    from django.utils import timezone
    return timezone.now().timestamp()


def _db_running(cursor):
    ''' 当前运行任务数 '''
    return len(cursor.execute('select type from tasks').fetchall())


def _db_validate(conn):
    '''
    移除库内不合法记录
    仅在数据库记录已满时运行
    '''
    try:
        conn.execute('delete from tasks where endtime<?', (_db_timestamp(), ))
        conn.commit()
    except Exception as e:
        print('DB VALIDATE ERROR:', e)


def _db_register(conn, type, name, endtime):
    ''' 在数据库内注册指定比赛 '''
    try:
        res = conn.execute('insert into tasks values (?,?,?)',
                           (type, name, int(endtime)))
        conn.commit()
    except Exception as e:
        print('DB REGISTER ERROR:', e)
        return False
    return True


def _db_check(cursor, type, name):
    ''' 查看指定比赛是否存活 '''
    try:
        res = cursor.execute('select * from tasks where type=? and name=?',
                             (type, name))
    except Exception as e:
        print('DB CHECK ERROR:', e)
        return False
    return bool(res.fetchall())


def _db_unload(conn, type, name):
    '''
    从数据库中移除指定比赛
    被移除的比赛将被对应监控进程停止
    '''
    try:
        conn.execute('delete from tasks where type=? and name=?', (type, name))
        conn.commit()
    except Exception as e:
        print('DB UNLOAD ERROR:', e)


def unit_monitor(type, name, data):
    '''
    比赛维护进程
    每个监控进程维护一个比赛进程
    监控数据库获取其维护比赛的状态，并进行中止等操作
    '''
    # 初始化
    setup_django()
    from django.conf import settings
    from time import perf_counter as pf, sleep
    from match_sys import models
    from . import helpers
    from .factory import Factory
    # print('START:', type, name)
    conn = init_db()
    cursor = conn.cursor()

    # 任务超限时待机
    num_tasks = _db_running(cursor)
    if num_tasks >= settings.MATCH_POOL_SIZE:
        _db_validate(conn)
        while 1:
            sleep(settings.MONITOR_CYCLE)
            if _db_running(cursor) < settings.MATCH_POOL_SIZE:
                break

    # 运行比赛进程
    match_dir = os.path.join(settings.PAIRMATCH_DIR, name)
    os.makedirs(match_dir, exist_ok=1)
    if type == None:  # 扩展区域
        pass
    else:  # 默认type=='match'一对一比赛
        AI_type, params = data
        match_process = Factory(AI_type, name, params)
    match_process.start()

    # 注册比赛进程
    endtime = _db_timestamp() + match_process.timeout
    _db_register(conn, type, name, endtime)

    # 循环监测运行状态与数据库
    cycle = 0
    while 1:
        # 检查运行状况
        now = pf()
        if not match_process.check_active(now):
            break

        # 检查数据库注册条目
        cycle += 1
        if cycle >= settings.MONITOR_DB_CHECK_CYCLE:
            cycle -= settings.MONITOR_DB_CHECK_CYCLE
            if not _db_check(cursor, type, name):  # 外部中止
                match_process.timeout = -1

        sleep(settings.MONITOR_CYCLE)  # 待机

    # 移除注册
    _db_unload(conn, type, name)
    # print('END:', type, name)


def start_match(AI_type, code1, code2, param_form, ranked=False):
    from match_sys import models
    from . import helpers
    from django.utils import timezone
    from django.db import connections

    # 生成随机match名称
    while 1:
        match_name = helpers.gen_random_string()
        if not models.PairMatch.objects.filter(name=match_name):
            break

    # 获取match参数
    params = param_form.cleaned_data

    # 创建未启动比赛对象
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

    # 传送参数至进程 (AI_type,code1,code2,match_name,params)
    match_proc = Process(
        target=unit_monitor, args=('match', match_name, [AI_type, params]))
    connections.close_all()  # 用于主进程MySQL保存所有更改
    match_proc.start()

    # 返回match对象名称
    return match_name


def kill_match(type, match_name):
    conn = init_db()
    _db_unload(conn, type, match_name)