from django.db import models
from django.contrib.auth.hashers import make_password, check_password, hashlib
from django.conf import settings
from main.helpers import set_autodelete
import os, hashlib
from posixpath import join as sjoin


### models
class User(models.Model):
    username = models.CharField('用户名', max_length=20, unique=True)
    nickname = models.CharField('昵称', max_length=20, null=True)
    pw_hash = models.CharField('密码hash', max_length=128)
    stu_code = models.CharField('学号', max_length=10)
    email_field = models.CharField(
        '电子邮箱', unique=True, max_length=256, null=True)
    real_name = models.CharField('真实姓名', max_length=32)
    register_datetime = models.DateTimeField('注册时间', auto_now_add=True)
    login_datetime = models.DateTimeField('上次登录时间', null=True)
    email_validated = models.BooleanField('已验证电子邮箱', default=False)
    is_admin = models.BooleanField('管理员马甲', default=False)
    is_team = models.BooleanField('小组账户', default=False)

    def __str__(self):
        return '%s (%s, %s)' % (self.username, self.name, self.stu_code)

    def match_passwd(self, pw):
        return check_password(pw, self.pw_hash)

    def set_passwd(self, pw):
        self.pw_hash = make_password(pw)
        self.save()

    @property
    def email(self):
        if not self.email_field:
            self.email_field = self.stu_code + '@pku.edu.cn'
            self.save()
        return self.email_field

    @property
    def name(self):
        return self.nickname or self.username

    def gravatar_icon(self, size=30):
        # 小组用户搜索头像覆盖
        if self.is_team:
            icon_dir = sjoin(
                settings.TEAM_ICON_DIR,  # team_icon
                self.stu_code[:3],  # N19
            )
            icon_folder = os.path.join(settings.MEDIA_ROOT, icon_dir)
            if os.path.isdir(icon_folder):
                for img in os.listdir(icon_folder):
                    if img.startswith(self.stu_code[3]):
                        return sjoin(
                            settings.MEDIA_URL,
                            icon_dir,
                            img,
                        )

        email = self.email.lower()
        hasher = hashlib.md5()
        hasher.update(email.encode('utf-8'))
        email_hash = hasher.hexdigest()
        return "//www.gravatar.com/avatar/%s?s=%s&d=retro" % (email_hash, size)

    class Meta:
        ordering = ["stu_code"]
        verbose_name = "用户"
        verbose_name_plural = "用户"


class UserMailCheck(models.Model):
    user = models.OneToOneField(User, models.CASCADE, verbose_name='用户')
    send_time = models.DateTimeField('请求时间')
    check_hash = models.CharField('校验hash', max_length=256)

    def activate(self):
        hasher = hashlib.sha256()
        hash_str = self.user.stu_code
        hash_str += self.user.register_datetime.strftime("%Y%m%d%H%I%S")
        hash_str += self.send_time.strftime("%Y%m%d%H%I%S")
        hasher.update(hash_str.encode())
        self.check_hash = hasher.hexdigest()
        self.save()


class UserResetPwMail(models.Model):
    user = models.OneToOneField(User, models.CASCADE, verbose_name='用户')
    send_time = models.DateTimeField('请求时间')
    check_hash = models.CharField('校验hash', max_length=256)
    activate = UserMailCheck.activate
