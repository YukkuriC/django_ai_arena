from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(4)
class _2048Record(RecordBase):
    def i_holder(_, match, record):
        return record['name0'] == 'code2'

    def i_winner(_, match, record):
        return record['winner']

    def r_length(_, match, record):
        return len(record['logs'])

    def r_win_desc(_, match, record):
        if record['cause'] == '':
            return '得分统计'
        elif record['cause'] == "violator":
            return '操作违规'
        elif record['cause'] == "timeout":
            return '超时'
        elif record['cause'] == "error":
            return '报错'
        return record['cause']

    def r_desc_plus(_, match, record):
        # 获取报错信息
        if record['cause'] == "error" and 'error' in record:
            return record['error']
        # 默认获取结束事件倒数第2行
        raw = record['logs'][-1]['E']
        return raw[-2]
