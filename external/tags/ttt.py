from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(0)
class TTTRecord(RecordBase):
    def i_holder(_, match, record):
        return record['names'][0] == 'code2'

    def i_winner(_, match, record):
        return record['winner']

    def r_length(_, match, record):
        return len(record['orders'])

    desc_pool = [
        '代码超时',
        '代码报错',
        '冲突选数',
        '非法返回值',
        '游戏继续',  # 0
        '获得组合',
        '棋盘已满平局',
    ]

    def r_win_desc(_, match, record):
        return _.desc_pool[record['reason'] + 4]

    def r_desc_plus(_, match, record):
        return record['extra'] or '无'