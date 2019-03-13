from django import forms
from django.conf import settings
from .models import Code
from external.factory import Factory


# 上传代码表单
class CodeUploadForm(forms.ModelForm):
    def clean_content(self):
        ai_type = self.cleaned_data.get('ai_type', None)
        if ai_type not in settings.AI_TYPES:
            raise forms.ValidationError('请填写正确的AI类型')
        file = self.cleaned_data['content']
        try:
            Factory(ai_type).load_code(file)  # 试加载代码内容
        except Exception as e:
            raise forms.ValidationError(str(e))
        return file

    class Meta:
        model = Code
        fields = ['name', 'ai_type', 'content', 'public']
        widgets = {
            'name': forms.TextInput({
                'class': 'form-control'
            }),
            'content': forms.FileInput({
                'class': 'form-control'
            }),
            'public': forms.CheckboxInput({
                'class': 'form-control'
            }),
            'ai_type': forms.Select({
                'class': 'form-control'
            }),
        }


# 比赛设置参数表单
class PairMatch_Base(forms.Form):
    '''基础参数表单'''
    rounds = forms.IntegerField(
        label='比赛局数',
        max_value=50,
        min_value=1,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 10,
        }))

    who_first = forms.ChoiceField(
        label='发起人先手',
        choices=settings.MATCH_TYPES.items(),
        widget=forms.Select({
            'class': 'form-control',
        }))


class PairMatch_PaperIO(PairMatch_Base):
    '''paper.io参数'''
    k = forms.IntegerField(
        label='场地半宽',
        max_value=51,
        min_value=9,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 51
        }))
    h = forms.IntegerField(
        label='场地高度',
        max_value=101,
        min_value=9,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 101
        }))
    max_turn = forms.IntegerField(
        label='总回合数',
        max_value=2000,
        min_value=100,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 2000
        }))
    max_time = forms.IntegerField(
        label='总思考时间（秒）',
        max_value=30,
        min_value=5,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 30
        }))


class PairMatchFormFactory:
    '''分发表单工厂类'''
    mapper = {2: PairMatch_PaperIO}

    @staticmethod
    def get(id, *args, **kwargs):
        form_class = PairMatchFormFactory.mapper.get(id, PairMatch_Base)
        return form_class(*args, **kwargs)
