import os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PY_OP = 'python' if sys.platform == 'win32' else 'python3'
OP_HEADER = f'{PY_OP} manage.py'
os.chdir(BASE_DIR)

for app in os.listdir('.'):
    if not (os.path.isdir(app)
            and os.path.isfile(os.path.join(app, 'models.py'))):
        continue
    os.system(f'{OP_HEADER} makemigrations {app}')

os.system(f'{OP_HEADER} migrate')