import os, sys, django, time, random

if '常数':
    groups = '1234567890QWERTYUIOPASDFGHJKLZXCVBNM'
    chars = groups + groups[10:].lower()
    codes = {
        "A": "ALPHA",
        "B": "BRAVO",
        "C": "CHARLIE",
        "D": "DELTA",
        "E": "ECHO",
        "F": "FOXTROT",
        "G": "GOLF",
        "H": "HOTEL",
        "I": "INDIA",
        "J": "JULIET",
        "K": "KILO",
        "L": "LIMA",
        "M": "MIKE",
        "N": "NOVEMBER",
        "O": "OSCAR",
        "P": "PAPA",
        "Q": "QUEBEC",
        "R": "ROMEO",
        "S": "SIERRA",
        "T": "TANGO",
        "U": "UNIFORM",
        "V": "VICTOR",
        "W": "WHISKEY",
        "X": "X-RAY",
        "Y": "YANKEE",
        "Z": "ZULU",
        "0": "007",
        "1": "114",
        "2": "251",
        "3": "3721",
        "4": "404",
        "5": "514",
        "6": "666",
        "7": "777",
        "8": "8848",
        "9": "996",
    }
    for k in codes:
        codes[k] = codes[k].capitalize()

if 'Django':
    base_dir = os.path.abspath(os.path.join(__file__, '../..'))
    sys.path.append(base_dir)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'main.settings'
    django.setup()

    from usr_sys.models import User


def get_username(prefix, grp):
    code = codes[grp.upper()]
    return f'{prefix}_{code}'


def get_pw(username, seed):
    random.seed('%s%s' % (username, seed))
    return ''.join(random.choice(chars) for i in range(8))


def create_user(username, pw):
    print('USERNAME:', username, 'PW:', pw)
    user, _ = User.objects.get_or_create(username=username)
    user.username = user.nickname = user.real_name = username
    user.email_field = user.stu_code = username[:5]  #F11_4
    user.set_passwd(pw)
    user.email_validated = True
    user.is_team = True
    user.save()


if '输入参数':
    header = year = seed = ''
    check_header = lambda tmp: tmp in list('FN')
    check_year = lambda tmp: tmp.isnumeric() and len(tmp) == 2
    try:
        header = sys.argv[1]
        assert check_header(header)
        year = sys.argv[2]
        assert check_year(year)
        seed = sys.argv[3]
    except:
        pass

    while not check_header(header):
        header = input('前缀 (F/N):')
    while not check_year(year):
        year = input('年份 (两位数字):')
    if not seed:
        seed = str(round(time.time() * 1000))[-5:]
        print('种子设置为:', seed)

if '创建用户':
    prefix = header + year
    file = os.path.join(__file__, '..', f'{prefix}_{seed}.csv')
    file = os.path.abspath(file)

    with open(file, 'w', encoding='utf-8') as f:
        print('username,password', file=f)
        for grp in groups:
            username = get_username(prefix, grp)
            pw = get_pw(username, seed)
            create_user(username, pw)
            print(username, pw, sep=',', file=f)
