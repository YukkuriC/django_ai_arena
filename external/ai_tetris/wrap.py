from ..helpers_core import silenced

# 设置路径
import os, sys
tetris_outer = os.path.join(os.path.dirname(__file__), 'pkudsa.tetris')
tetris_path = os.path.join(tetris_outer, 'TetrisProgram')
sys.path.append(tetris_path)

# 静默import
with silenced():
    sys.path.insert(0, tetris_outer)
    from TetrisProgram import main
    from TetrisProgram.main import ReviewData, Game
    sys.path.pop(0)

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
    main.ReviewData.ReviewData.save = null_func
