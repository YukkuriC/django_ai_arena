from django import forms
from .models import User


class FormStyle:
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class RegisterForm(FormStyle, forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'email_field', 'real_name', 'stu_code', 'nickname'
        ]
        widgets = {
            'username':
            forms.TextInput(attrs={'placeholder': '仅包含数字、字母与下划线，区分大小写'}),
            'email_field':
            forms.EmailInput(attrs={'placeholder': '电子邮箱'}),
            'real_name':
            forms.TextInput(attrs={'placeholder': '真实姓名，用于身份验证'}),
            'stu_code':
            forms.TextInput(
                attrs={
                    "oninput": "value=value.substr(0,10)",
                    'placeholder': '学号，用于身份验证',
                }),
            'nickname':
            forms.TextInput(attrs={'placeholder': '(可选) 向其他人显示的名称'}),
        }

    passwd = forms.CharField(
        label="密码 (最少6位)",
        min_length=6,
        max_length=128,
    )
    pw2 = forms.CharField(
        label="确认密码",
        max_length=128,
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        has_alpha = False
        for c in username.upper():
            if c == '_' or 'A' <= c <= 'Z':
                has_alpha = True
            elif not '0' <= c <= '9':
                raise forms.ValidationError('包含非法字符 "%s"' % c)
        if not has_alpha:
            raise forms.ValidationError('请勿使用学号作为用户名')
        return username

    def clean_stu_code(self):
        code = self.cleaned_data.get('stu_code')
        if len(code) != 10 or not all('0' <= c <= '9' for c in code):
            raise forms.ValidationError('学号非法')
        return code


class LoginForm(FormStyle, forms.Form):
    username = forms.CharField(
        label="用户名/学号/邮箱",
        required=True,
        widget=forms.TextInput(),
    )
    passwd = forms.CharField(
        label="密码",
        required=True,
        widget=forms.PasswordInput(),
    )


class ChangePasswdForm(FormStyle, forms.Form):
    old_passwd = forms.CharField(
        label="原密码",
        required=True,
        widget=forms.PasswordInput(),
    )
    new_passwd = forms.CharField(
        label="新密码 (最少6位)",
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(),
    )
    new_pw2 = forms.CharField(
        label="确认新密码",
        max_length=128,
        widget=forms.PasswordInput(),
    )


class SettingsForm(FormStyle, forms.Form):
    nickname = forms.CharField(
        label="昵称 (不超过20字符)",
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            "oninput": "value=value.substr(0,20)",
            'title': '向其他人显示的名称'
        }))
    real_name = forms.CharField(
        label="真实姓名",
        required=True,
        max_length=32,
        widget=forms.TextInput(attrs={
            "oninput": "value=value.substr(0,32)",
        }))


class ForgotPasswdForm(FormStyle, forms.Form):
    username = forms.CharField(
        label="用户名",
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            "oninput": "value=value.substr(0,20)",
        }))

    stu_code = forms.CharField(
        label="学号 (10位数字)",
        min_length=10,
        max_length=10,
        widget=forms.TextInput(
            attrs={
                "oninput": "value=value.replace(/[^\d]/g,'').substr(0,10)",
            }))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        try:
            user = User.objects.get(username=username)
        except:
            raise forms.ValidationError('用户不存在')
        return username

    def clean_stu_code(self):
        code = self.cleaned_data.get('stu_code')
        try:
            user = User.objects.get(stu_code=code)
        except:
            raise forms.ValidationError('用户不存在')
        return code


class ResetPasswdForm(forms.Form):
    new_passwd = forms.CharField(
        label="新密码 (最少6位)",
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(),
    )
    new_pw2 = forms.CharField(
        label="确认新密码",
        max_length=128,
        widget=forms.PasswordInput(),
    )
