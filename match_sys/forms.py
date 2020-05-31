from django import forms
from django.conf import settings
from django.utils import timezone
from .models import Code, PairMatch
from external.factory import Factory
from external.ai_osmo.src.consts import Consts
from external.ai_2048.src import constants as c_2048


# 上传代码表单
class CodeUploadForm(forms.ModelForm):
    def clean_content(self):
        ai_type = self.cleaned_data.get('ai_type', None)
        if ai_type not in settings.AI_TYPES:
            raise forms.ValidationError('请填写正确的AI类型')
        file = self.cleaned_data['content']
        try:
            Factory(ai_type).load_code(file.read(), True)  # 试加载代码内容
        except Exception as e:
            raise forms.ValidationError(str(e))
        return file

    def clean_name(self):
        raw_name = self.cleaned_data.get('name', '未命名')
        name = raw_name.strip()
        return name or '未命名'

    class Meta:
        model = Code
        fields = ['name', 'ai_type', 'content', 'public']
        widgets = {
            'name':
            forms.TextInput({
                'class': 'form-control'
            }),
            'content':
            forms.FileInput({
                'class': 'form-control'
            }),
            'public':
            forms.CheckboxInput({
                'class': 'form-control',
                'title': '是否可以被其他人查看代码及复制'
            }),
            'ai_type':
            forms.Select({
                'class': 'form-control'
            }),
        }


# 比赛设置参数表单
class PairMatch_Base(forms.Form):
    '''基础参数表单'''
    rounds = forms.IntegerField(
        label='比赛局数',
        max_value=30,
        min_value=1,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': settings.DEFAULT_PAIRMATCH_ROUNDS,
        }))

    who_first = forms.ChoiceField(
        label='发起人先手',
        choices=settings.MATCH_TYPES.items(),
        widget=forms.Select({
            'class': 'form-control',
        }))


class PairMatch_PaperIO(PairMatch_Base):
    '''paper.io参数'''
    # k = forms.IntegerField(
    #     label='场地半宽',
    #     max_value=51,
    #     min_value=9,
    #     widget=forms.NumberInput({
    #         'class': 'form-control',
    #         'value': 51
    #     }))
    # h = forms.IntegerField(
    #     label='场地高度',
    #     max_value=101,
    #     min_value=9,
    #     widget=forms.NumberInput({
    #         'class': 'form-control',
    #         'value': 101
    #     }))
    max_turn = forms.IntegerField(
        label='总回合数',
        max_value=2000,
        min_value=100,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 2000
        }))
    max_time = forms.FloatField(
        label='总思考时间（秒）',
        max_value=30,
        min_value=5,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': 30
        }))


class PairMatch_Osmo(PairMatch_Base):
    '''osmo参数'''
    MAX_TIME = forms.FloatField(
        label='总思考时间（秒）',
        max_value=30,
        min_value=0.1,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': Consts['MAX_TIME']
        }))
    MAX_FRAME = forms.IntegerField(
        label='最大帧数',
        max_value=10000,
        min_value=100,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': Consts['MAX_FRAME']
        }))
    extra_mode = forms.ChoiceField(
        required=False,
        label='额外模式',
        choices=(
            ('0', '默认'),
            ('a', '喷泉模式'),
            # ('b', '磁铁模式'),
            # ('c', '捉兔子'),
        ),
        widget=forms.Select({
            'class': 'form-control',
            'value': ''
        }))


class PairMatch_2048(PairMatch_Base):
    '''osmo参数'''
    max_time = forms.FloatField(
        label='总思考时间（秒）',
        max_value=10,
        min_value=0.1,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': c_2048.MAXTIME
        }))
    max_turn = forms.IntegerField(
        label='最大帧数',
        max_value=10000,
        min_value=100,
        widget=forms.NumberInput({
            'class': 'form-control',
            'value': c_2048.ROUNDS
        }))


class PairMatchFormFactory:
    '''分发表单工厂类'''
    mapper = {
        2: PairMatch_PaperIO,
        3: PairMatch_Osmo,
        4: PairMatch_2048,
    }

    @staticmethod
    def get(id, *args, **kwargs):
        form_class = PairMatchFormFactory.mapper.get(id, PairMatch_Base)
        return form_class(*args, **kwargs)
