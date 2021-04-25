from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(1)
class PingPongRecord(RecordBase):
    def i_holder(_, match, record):
        return record['West'] == 'code2'

    def i_winner(_, match, record):
        if record['winner'] == None:
            return None
        return record['winner'] != 'West'

    def r_length(_, match, record):
        nround = len(record['log']) - 1
        ntick = record['tick_total']
        return '%s回合 (%s Tick)' % (nround, ntick)

    def r_win_desc(_, match, record):
        return record['reason']

    def r_desc_plus(_, match, record):
        return '剩余生命：%s' % record['winner_life']
