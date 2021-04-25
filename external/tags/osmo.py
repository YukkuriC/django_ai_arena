from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(3)
class OsmoRecord(RecordBase):
    def i_holder(_, match, record):
        return record['players'][0] == 'code2'

    def i_winner(_, match, record):
        return record['winner']

    def r_length(_, match, record):
        return len(record['data'])

    def r_win_desc(_, match, record):
        if record['cause'] == 'PLAYER_DEAD':
            return '吞噬玩家'
        elif record['cause'] == "RUNTIME_ERROR":
            return '代码错误'
        elif record['cause'] == "INVALID_RETURN_VALUE":
            return '输出格式错误'
        elif record['cause'] == "MAX_FRAME":
            return '最大帧数'
        elif record['cause'] == "TIMEOUT":
            return '玩家超时'
        return record['cause']

    def r_desc_plus(_, match, record):
        if record['cause'] == 'PLAYER_DEAD':
            dead = record['detail']
            if all(dead):
                dead = '双方同时'
            else:
                dead = '先手玩家' if dead[0] else '后手玩家'
            return dead + '被吞噬'
        elif record['cause'] == "RUNTIME_ERROR":
            res = list(record['detail'])
            if record['winner'] != None:
                res = res[0] or res[1]
            return res
        elif record['cause'] == "MAX_FRAME":
            last_frame = record['data'][-1]
            return "%s : %s" % (round(last_frame[0][4], 2),
                                round(last_frame[1][4], 2))
        return '-'
