import re

PLR_DICT = {True: 'player 0', False: 'player 1', None: 'None', 'both': 'both'}

if 'REGEXP':
    HEADER = re.compile(r"""
        (?#文件头)
        player0:
            \s+ (?P<id0>\d+) (?#先手玩家ID)
            [\w\s]*? path \s* (?P<name0>.+?) (?#先手玩家文件名)
        \n
        player1:
            \s+ (?P<id1>\d+) (?#后手玩家ID)
            [\w\s]*? path \s* (?P<name1>.+?) (?#后手玩家文件名)
        \n
        time:
            \s+ (?P<time>[\w\s\-\:]+?) (?#比赛时间)
        \n
        (?#比赛结果)
        [\d\w\s\*=]*
        (?P<headers>(?: \| [\w\s]*? ){4}) \| [\w\s\-]+?
        (?P<results>(?: \| [\w\s]* ){4})
    """, re.VERBOSE | re.DOTALL)
    LOGS = re.compile(r"""
        &(?:
            (?: (?#group: 0-4)
                (?P<D>d) (\d+): \s* (?#玩家操作+回合数)
                player\s* (\d+) [\w\s]*? (?#玩家编号)
                (position|direction) (?#位置/方向)
                \s+ (.+?) \n (?#操作内容)
            )|(?: (?#group: 5-7)
                (?P<P>p) (\d+): \s* (?#当前局面+回合数)
                ((?: (?#整盘内容)
                    [+-] \d+
                    \s+
                ){32})
            )|(?: (?#group: 8-9)
                (?P<E>e): \s* (?#结果)
                (.+?) [\n$] (?#结果语句)
            )
        )
    """, re.VERBOSE | re.DOTALL)

if 'PARSERS':

    def parse_D(grps):
        """
        读取操作
        范围：0-4
        """
        return {'r': int(grps[1]), 'p': int(grps[2]), 'd': grps[3:5]}

    def parse_P(grps):
        """
        读取盘面
        范围：5-7
        """
        return [[int(x) for x in line.split()[:8]]
                for line in grps[7].split('\n')[:4]]

    def parse_E(grps):
        """
        读取结果
        范围：8-9
        """
        return grps[9]

    LOG_PARSERS = {x: globals()['parse_' + x] for x in 'DPE'}


def parse_header(raw):
    raw = HEADER.search(raw).groupdict()

    # 提取结果
    headers = [x.strip() for x in raw['headers'].split('|')]
    tmp = [x.strip() for x in raw['results'].split('|')]
    del raw['results'], raw['headers']
    raw['winner'] = None if tmp[-1] == 'None' else int(tmp[-1][-1])
    for h, x in reversed(list(zip(headers[:-1], tmp[:-1]))):
        if x != 'None':
            raw['cause'] = h
            break
    for k in 'id0', 'id1':
        raw[k] = int(raw[k])

    return raw


def parse_logs(raw):
    """
    {D+P}: 正常回合
    {D+E}: 违规
    {D+P+E}: 结算得分
    start -> D
    D -> P+E (yield)
    P -> D
    E -> E+end
    """
    cached = {}
    for match in LOGS.finditer(raw):
        dct, grps = match.groupdict(), match.groups()
        if dct['D']:
            if cached:
                yield cached
            cached = {'D': parse_D(grps)}
        elif dct['P']:
            cached['P'] = parse_P(grps)
        else:  # E
            if not 'E' in cached:
                cached['E'] = []
            cached['E'].append(parse_E(grps))
    if cached:
        yield cached


if __name__ == '__main__':
    with open('sample.txt') as f:
        raw = f.read()
    print(parse_header(raw))
    for log in parse_logs(raw):
        print(log)