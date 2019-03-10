from django.db import models
from django.conf import settings
from usr_sys import models as usr_models
from main.helpers import set_autodelete
from external.factory import Factory
import os, shutil


def get_path(self, filename):
    '''按绝对路径记录代码存储路径'''
    return '%s/code/%03d/%s_%s' % (settings.STORAGE_DIR, self.ai_type,
                                   self.author.stu_code, filename)


class Code(models.Model):
    name = models.CharField('名称', max_length=128)
    author = models.ForeignKey(
        usr_models.User, models.CASCADE, verbose_name='发布者')
    ai_type = models.IntegerField('AI类型', choices=settings.AI_TYPES.items())
    content = models.FileField('上传代码', upload_to=get_path)
    public = models.BooleanField('是否公开', default=True)
    edit_datetime = models.DateTimeField('最后修改时间')

    if 'records':
        num_matches = models.IntegerField('参与比赛场数', default=0)
        num_wins = models.IntegerField('获胜对战数', default=0)
        num_loses = models.IntegerField('失败对战数', default=0)
        num_draws = models.IntegerField('平局对战数', default=0)
        score = models.FloatField('等级分', default=1000)

        @property
        def num_records(self):
            return self.num_wins + self.num_loses + self.num_draws

    def __str__(self):
        return '%s (%s)' % (self.name, self.author.username)

    def available(self, user):
        return self.author == user or self.public

    class Meta:
        verbose_name = "AI脚本"
        verbose_name_plural = "AI脚本"


set_autodelete(locals(), Code, 'content')


class PairMatch(models.Model):
    ai_type = models.IntegerField(
        verbose_name='AI类型', choices=settings.AI_TYPES.items())
    name = models.CharField('名称', max_length=128)
    code1 = models.ForeignKey(
        Code,
        models.CASCADE,
        verbose_name='我方代码',
        related_name='pmatch1',
    )
    code2 = models.ForeignKey(
        Code,
        models.CASCADE,
        verbose_name='对方代码',
        related_name='pmatch2',
    )
    rounds = models.IntegerField('总局数')
    finished_rounds = models.IntegerField('已完成局数', default=0)
    run_datetime = models.DateTimeField('发布时间', null=True)
    finish_datetime = models.DateTimeField('完成时间', null=True)
    status = models.IntegerField(
        '状态', default=0, choices=settings.PAIRMATCH_STATUS.items())

    def __str__(self):
        return '%s - %s vs. %s' % (self.run_datetime, self.code1, self.code2)

    def available(self, user):
        return self.code1.author == user or self.code2.author == user or (
            self.code1.public and self.code2.public)

    class Meta:
        ordering = ["-id"]
        verbose_name = "一对一比赛"
        verbose_name_plural = "一对一比赛"

    @staticmethod
    def del_folder(sender, instance, **kwargs):
        match_name = getattr(instance, 'name', None)
        if not match_name:
            return

        path_to_remove = os.path.join(settings.PAIRMATCH_DIR, instance.name)
        try:
            shutil.rmtree(path_to_remove)
        except:
            pass


# 绑定删除文件夹事件
models.signals.post_delete.connect(PairMatch.del_folder, PairMatch)
