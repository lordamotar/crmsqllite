from django import forms
from .models import Client, ClientPhone, IndividualClientData, LegalEntityClientData
from apps.cities.models import City


class ClientForm(forms.ModelForm):
    """Форма для создания/редактирования клиента"""
    name = forms.CharField(
        label='ФИО/Название компании',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Введите ФИО или название компании'})
    )
    
    client_type = forms.ChoiceField(
        label='Тип клиента',
        required=True,
        choices=Client.CLIENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'})
    )

    class Meta:
        model = Client
        fields = ['client_type', 'name', 'email']

    def save(self, commit=True, user=None):
        client = super().save(commit=False)
        if commit:
            client.save()
        return client


class IndividualClientForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label="Выберите город",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = IndividualClientData
        fields = ['first_name', 'last_name', 'middle_name', 'gender', 'birth_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'client') and self.instance.client:
            # Заполняем поле телефона из связанной модели Client
            primary_phone = self.instance.client.phones.filter(is_primary=True).first()
            if primary_phone:
                self.initial['phone'] = primary_phone.phone[1:] if primary_phone.phone.startswith('7') else primary_phone.phone
            # Заполняем поле email из связанной модели Client
            self.initial['email'] = self.instance.client.email
            # Заполняем поле города из связанной модели ClientAddress
            primary_address = self.instance.client.addresses.filter(is_primary=True).first()
            if primary_address and primary_address.city:
                try:
                    city = City.objects.get(name=primary_address.city)
                    self.initial['city'] = city.id
                except City.DoesNotExist:
                    pass

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        # Временно отключаем валидацию для редактирования
        if not phone:
            return phone
        return phone

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if commit:
            # Создаем или получаем основную запись клиента
            client = getattr(instance, 'client', None)
            if not client:
                client = Client.objects.create(
                    client_type='individual',
                    name=f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']} {self.cleaned_data.get('middle_name', '')}".strip(),
                    email=self.cleaned_data.get('email', ''),
                    created_by=user,
                    modified_by=user
                )
                instance.client = client
            else:
                client.name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']} {self.cleaned_data.get('middle_name', '')}".strip()
                client.email = self.cleaned_data.get('email', '')
                client.modified_by = user
                client.save()
            
            instance.save()
        return instance


class LegalEntityClientForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label="Выберите город",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = LegalEntityClientData
        fields = ['company_name', 'bin', 'tax_number', 'registration_date', 
                 'director_name', 'bank_account', 'bank_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'client') and self.instance.client:
            # Заполняем поле телефона из связанной модели Client
            primary_phone = self.instance.client.phones.filter(is_primary=True).first()
            if primary_phone:
                self.initial['phone'] = primary_phone.phone[1:] if primary_phone.phone.startswith('7') else primary_phone.phone
            # Заполняем поле email из связанной модели Client
            self.initial['email'] = self.instance.client.email
            # Заполняем поле города из связанной модели ClientAddress
            primary_address = self.instance.client.addresses.filter(is_primary=True).first()
            if primary_address and primary_address.city:
                try:
                    city = City.objects.get(name=primary_address.city)
                    self.initial['city'] = city.id
                except City.DoesNotExist:
                    pass

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        # Временно отключаем валидацию для редактирования
        if not phone:
            return phone
        return phone

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if commit:
            # Создаем или получаем основную запись клиента
            client = getattr(instance, 'client', None)
            if not client:
                client = Client.objects.create(
                    client_type='legal_entity',
                    name=self.cleaned_data['company_name'],
                    email=self.cleaned_data.get('email', ''),
                    created_by=user,
                    modified_by=user
                )
                instance.client = client
            else:
                client.name = self.cleaned_data['company_name']
                client.email = self.cleaned_data.get('email', '')
                client.modified_by = user
                client.save()
            
            instance.save()
        return instance
