'''
自动读取所有AI子模块
'''

import os

BASE_DIR = os.path.dirname(__file__)

for mod in os.listdir(BASE_DIR):
    mod_dir = os.path.join(BASE_DIR, mod)
    if os.path.isdir(mod_dir) and os.path.isfile(
            os.path.join(mod_dir, '__init__.py')):
        __import__(__name__ + '.' + mod)
