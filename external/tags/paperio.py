from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(2)
class PaperIORecord(RecordBase):
    def i_holder(_, match, record):
        return record['players'][0] == 'code2'

    def i_winner(_, match, record):
        return record['result']

    def r_length(_, match, record):
        return len(record['timeleft'][0]) - 1

    desc_pool = [
        '回合数耗尽，结算得分', '运行超时', 'AI函数报错', '玩家撞墙', '玩家撞击纸带', '侧碰', '正碰，结算得分',
        '领地内互相碰撞'
    ]

    def r_win_desc(_, match, record):
        res = record['result']
        return _.desc_pool[res[1] + 3]

    def r_desc_plus(_, match, record):
        res = record['result']
        if abs(res[1]) == 3:
            return '%s : %s' % tuple(res[2])
        if res[1] == -1:
            return res[2]
        if res[1] == 1:
            if res[0] == res[2]:
                return '对手撞击'
            return '自己撞击'
        return '无'
