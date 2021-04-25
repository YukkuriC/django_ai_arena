from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(5)
class EufRecord(RecordBase):
    def i_holder(_, match, record):
        return record['player_name']['0'] == 'code2'  # JSON化后数字key转为字符串

    def i_winner(_, match, record):
        return record['winner']

    def r_length(_, match, record):
        return len(record['history'])

    def r_win_desc(_, match, record):
        return record['result']

    def r_desc_plus(_, match, record):
        return '-'
