from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    """Форма профиля пользователя"""
    # Поля из таблицы users
    first_name = forms.CharField(max_length=100, required=False, label='Имя')
    last_name = forms.CharField(max_length=100, required=False, label='Фамилия')
    middle_name = forms.CharField(max_length=100, required=False, label='Отчество')
    email = forms.EmailField(required=False, label='Email')
    phone = forms.CharField(max_length=20, required=False, label='Телефон')
    bio = forms.CharField(max_length=500, required=False, label='О себе', widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone', 'bio', 'language', 'timezone', 'currency', 'theme', 'email_notifications', 'sms_notifications', 'push_notifications']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите фамилию'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите отчество'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (xxx) xxx-xx-xx'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Расскажите о себе'}),
            'language': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('ru', 'Русский'),
                ('en', 'English'),
                ('kk', 'Қазақша'),
            ]),
            'timezone': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('Asia/Almaty', 'Алматы (UTC+6)'),
                ('Asia/Aqtobe', 'Актобе (UTC+5)'),
                ('Asia/Aqtau', 'Актау (UTC+5)'),
                ('Asia/Oral', 'Уральск (UTC+5)'),
                ('Asia/Qyzylorda', 'Кызылорда (UTC+6)'),
                ('Asia/Atyrau', 'Атырау (UTC+5)'),
            ]),
            'currency': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('KZT', 'Тенге (KZT)'),
                ('USD', 'Доллар (USD)'),
                ('EUR', 'Евро (EUR)'),
                ('RUB', 'Рубль (RUB)'),
            ]),
            'theme': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('light', 'Светлая'),
                ('dark', 'Темная'),
                ('system', 'Системная'),
            ]),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Заполняем поля из таблицы users
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['middle_name'].initial = user.middle_name
            self.fields['email'].initial = user.email
            self.fields['phone'].initial = user.phone
            self.fields['bio'].initial = user.bio

    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if commit:
            # Сохраняем профиль
            profile.save()
            
            # Обновляем данные пользователя
            user = profile.user
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.middle_name = self.cleaned_data.get('middle_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.phone = self.cleaned_data.get('phone', '')
            user.bio = self.cleaned_data.get('bio', '')
            user.save()
        
        return profile
