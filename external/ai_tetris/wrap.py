# 设置路径
import os, sys
tetris_path = os.path.join(os.path.dirname(__file__), 'pkudsa.tetris',
                           'TetrisProgram')
sys.path.append(tetris_path)

import main

if 'custom import':
    _pool = {}

    def register_player(name, module):
        _pool[name] = module

    def import_custom(player_name, is_first):
        return _pool[player_name].Player(is_first)

    main.import_by_name = import_custom

if 'disable functions':
    null_func = lambda *a, **kw: None
    main.print = null_func
    main.RecordData.RecordData.save = null_func
