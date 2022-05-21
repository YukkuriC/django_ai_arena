from external.tag_loader import RecordBase, RecordDeco


@RecordDeco(6)
class TetrisRecord(RecordBase):
    def i_holder(_, match, record):
        return record['player1'] == 'code2'

    def i_winner(_, match, record):
        w = record['winner']
        return w - 1 if w > 0 else None

    def r_length(_, match, record):
        return len(record['matchData'])

    def r_win_desc(_, match, record):
        return record['reason']

    def r_desc_plus(_, match, record):  # 报错信息
        errors = record.get('errors')
        if errors:
            return ';\n'.join(e for e in errors if e)
        return '无'