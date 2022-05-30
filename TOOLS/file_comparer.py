from hashlib import md5
import os, shutil, json

CUR_PATH = os.path.dirname(__file__)
SITE_PATH = os.path.abspath(os.path.join(CUR_PATH, '../'))
DATA = {
    "app": ["match_sys", "usr_sys", "ajax_sys"],
    "folder": ["main"],
    "folder_r": ["assets", "templates", "external"]
}
IGNORE_PATH = ['__pycache__', 'migrations']
CMP_FILE = os.path.join(CUR_PATH, 'compare.json')


def is_valid(path):
    return not any(p in path for p in IGNORE_PATH)


def get_md5(filepath):
    filepath = os.path.join(SITE_PATH, filepath)
    with open(filepath, 'rb') as f:
        data = f.read()
    return md5(data).hexdigest()


def iter_folder(dir):  # 单层目录
    base_dir = os.path.join(SITE_PATH, dir)
    if not os.path.isdir(base_dir):
        return
    for f in os.listdir(base_dir):
        f = os.path.join(dir, f)
        if os.path.isfile(os.path.join(SITE_PATH, f)) and is_valid(f):
            yield f


def iter_folder_r(dir):  # 多层目录
    base_dir = os.path.join(SITE_PATH, dir)
    if not os.path.isdir(base_dir):
        return
    for root, d, fs in os.walk(base_dir):
        for f in fs:
            f = os.path.relpath(os.path.join(root, f), SITE_PATH)
            if is_valid(f):
                yield f


def iter_app(appname):
    yield from iter_folder(appname)
    yield from iter_folder_r(os.path.join(appname, 'templates'))


def FILES():
    for k in 'folder folder_r app'.split():
        fs = DATA.get(k, [])
        for f in fs:
            yield from globals()['iter_' + k](f)


# 读入命令
try:
    cmd = os.sys.argv[1]
    assert cmd.strip() in '12'
except:
    cmd = ''
    while not (cmd and cmd.strip() in '12'):
        cmd = input('1 抓取目标md5\n2 对比源md5抓取文件\n指令: ')

FILES = list(FILES())

# 获取目标md5
if cmd == '1':
    res = {}
    for f in FILES:
        f = f.replace('\\', '/')
        res[f] = get_md5(f)
    with open(CMP_FILE, 'w', encoding='utf-8') as f:
        json.dump(res, f, separators=(',', ':'))

# 对比抓取文件
elif cmd == '2':
    with open(CMP_FILE, encoding='utf-8') as f:
        compare = json.load(f)
    for f in FILES:
        f = f.replace('\\', '/')
        old_md5 = compare.get(f)
        new_md5 = get_md5(f)
        if old_md5 != new_md5:
            orig = os.path.join(SITE_PATH, f)
            tmp_path = os.path.join(CUR_PATH, f)
            os.makedirs(os.path.dirname(tmp_path), exist_ok=1)
            os.link(orig, tmp_path)
