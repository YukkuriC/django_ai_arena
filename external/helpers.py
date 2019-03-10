from random import choices
from django.conf import settings

def gen_random_string(k=settings.MATCH_CODE_LENGTH):
    return ''.join(choices(settings.RAND_CHARPOOL, k=k))
