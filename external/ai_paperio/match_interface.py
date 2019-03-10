import os, pickle, zlib, array

try:
    import match_core
except ImportError:
    from . import match_core

if 'storage operations':

    def clear_storage():
        '''
        清除双方私有存储字典
        '''
        match_core.STORAGE = [{}, {}]

    def swap_storage():
        '''
        交换双方私有存储字典
        玩家先后手交换时使用
        '''
        match_core.STORAGE = match_core.STORAGE[::-1]


# 直接调用序列化与压缩进行存储
if 'simple log':

    def save_match_log(obj, path):
        '''
        保存比赛记录为文件
        params:
            obj - 待保存对象
            path - 保存路径
        '''
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(path, 'wb') as f:
            f.write(zlib.compress(pickle.dumps(obj), -1))

    def load_match_log(path):
        '''
        读取比赛记录文件为对象
        params:
            path - 保存路径
        '''
        with open(path, 'rb') as f:
            obj = pickle.loads(zlib.decompress(f.read()))
        return obj


# 用于压缩/复原比赛记录
if 'replay helper':

    def grab_plr_directions(frames):
        '''从比赛记录读取双方玩家方向'''
        players_info = [frame['players'] for frame in frames]
        p1d, p2d = array.array('b'), array.array('b')
        for i, ps in enumerate(players_info):
            p1, p2 = ps
            if i == 0:
                p2d.append(p2['direction'])
                p1d.append(p1['direction'])
            elif i % 2:
                p1d.append(p1['direction'])
            else:
                p2d.append(p2['direction'])
        return p1d, p2d

    def gen_player_module(directions):
        '''创建通过方向序列重构输出的玩家模块'''

        class bot_plr:
            opl = directions
            cp = 0

            @classmethod
            def play(cls, *a, **kw):
                d = (cls.opl[cls.cp + 1] - cls.opl[cls.cp]) % 4
                cls.cp += 1
                return ' r l' [d]

        return bot_plr


# 通过轨迹信息进行存储与复原
if 'compact log':

    def save_compact_log(match_log, path):
        '''
        保存比赛记录为仅记录路径的原始文件
        params:
            match_log - 待保存比赛记录
            path - 保存路径
        '''
        # 生成记录对象
        compact_log = {k: v
                       for k, v in match_log.items()
                       if k != 'log'}  # 排除帧序列，仅保存轨迹
        compact_log['traces'] = grab_plr_directions(match_log['log'])
        compact_log['init'] = [{
            'x': plr['x'],
            'y': plr['y'],
            'init_direction': plr['direction'],
        } for plr in match_log['log'][0]['players']]

        # 提取耗时信息
        t1, t2 = array.array('f'), array.array('f')
        for frame in match_log['log']:
            t_left = frame['timeleft']
            t1.append(t_left[0])
            t2.append(t_left[1])
        compact_log['timeleft'] = (t1, t2)

        # 保存
        save_match_log(compact_log, path)

    def load_compact_log(path):
        '''
        读取紧密比赛记录
        params:
            path - 保存路径
        '''
        compact_log = load_match_log(path)

        # 读取参数
        bot_plrs = list(map(gen_player_module, compact_log['traces']))
        names = compact_log['players']
        k, h = compact_log['size']
        k //= 2
        mturn = compact_log['maxturn']
        mtime = compact_log['maxtime']
        overrides = compact_log['init']

        # 复原比赛
        expand_log= match_core.match(bot_plrs, names, k, h, mturn, mtime, overrides)
        expand_log['result']=compact_log['result']
        for frame,tleft in zip(expand_log['log'],zip(*compact_log['timeleft'])):
            frame['timeleft']=tleft


if 'samples':

    def repeated_match(players,
                       names,
                       rounds,
                       log_record=False,
                       *args,
                       **kwargs):
        '''
        双方进行多次比赛

        params:
            players - 先后手玩家模块列表
            names - 双方玩家名称
            rounds - 比赛局数
            log_record - 是否生成比赛记录文件，默认为否
            *args, **kwargs - 比赛运行参数
        
        return:
            元组，包含比赛结果及统计
                [0] - 比赛结果统计字典
                    0 - 先手玩家胜
                    1 - 后手玩家胜
                    None - 平局
                [1] - 原始比赛结果列表
        '''
        # 初始化存储空间
        clear_storage()

        # 总初始化函数
        for i in range(2):
            try:
                players[i].init(match_core.STORAGE[i])
            except:
                pass

        # 初始化统计变量
        result_raw = []
        result_stat = {0: 0, 1: 0, None: 0}

        # 运行多局比赛
        for i in range(rounds):
            # 获取比赛记录
            match_log = match(players, names, *args, **kwargs)

            # 统计结果
            result = match_log['result']
            result_raw.append(result)
            result_stat[result[0]] += 1

            # 生成比赛记录
            if log_record:
                log_name = 'log/%s-VS-%s_%s.zlog' % (*names, i)
                save_match_log(match_log, log_name)

        # 总总结函数
        for i in range(2):
            try:
                players[i].summaryall(match_core.STORAGE[i])
            except:
                pass

        # 返回结果
        return result_stat, result_raw


if __name__ == '__main__':
    from random import choice

    class null_plr:
        def play(stat, storage):
            return choice('lrxxxx')

    res = repeated_match((null_plr, null_plr), ('test1', 'test2'), 10, True)
    print(res)