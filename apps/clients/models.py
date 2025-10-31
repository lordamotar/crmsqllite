from django.db import models
from apps.accounts.models import User
import uuid


class Client(models.Model):
    """Базовая модель клиента"""
    CLIENT_TYPES = (
        ('individual', 'Физическое лицо'),
        ('legal_entity', 'Юридическое лицо'),
    )

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    client_type = models.CharField(
        max_length=20, choices=CLIENT_TYPES, verbose_name='Тип клиента'
    )
    name = models.CharField(
        max_length=255, verbose_name='ФИО/Название', default='Клиент'
    )
    first_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Фамилия'
    )
    middle_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Отчество'
    )
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_clients', verbose_name='Создан'
    )
    modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='modified_clients', verbose_name='Изменен'
    )

    def get_primary_phone_number(self):
        """Возвращает номер основного телефона без кода страны (+7)"""
        phone = self.phones.filter(is_primary=True).first()
        if not phone or not phone.phone:
            return ""
        p = phone.phone
        return p[2:] if p.startswith('+7') and len(p) > 2 else p

    def __str__(self):
        if self.client_type == 'individual':
            try:
                individual_data = self.individual_data
                return (
                    f"{individual_data.last_name} "
                    f"{individual_data.first_name} "
                    f"{individual_data.middle_name or ''}"
                ).strip()
            except IndividualClientData.DoesNotExist:
                return self.name
        return self.name

    def get_modifier_name(self):
        """Безопасно получает имя пользователя, который изменил запись"""
        if self.modified_by:
            return self.modified_by.get_full_name() or self.modified_by.username
        return "Не указано"

    class Meta:
        db_table = 'clients'
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'


class IndividualClientData(models.Model):
    """Подтаблица для физических лиц"""
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]

    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='individual_data'
    )
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    middle_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Отчество'
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, null=True, blank=True,
        verbose_name='Пол'
    )
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Дата рождения'
    )
    iin = models.CharField(
        max_length=12, null=True, blank=True, verbose_name='ИИН'
    )
    passport_number = models.CharField(
        max_length=20, null=True, blank=True, verbose_name='Номер паспорта'
    )
    passport_issued = models.DateField(
        null=True, blank=True, verbose_name='Дата выдачи паспорта'
    )
    passport_issuer = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name='Кем выдан паспорт'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = 'individual_client_data'
        verbose_name = 'Данные физического лица'
        verbose_name_plural = 'Данные физических лиц'


class LegalEntityClientData(models.Model):
    """Подтаблица для юридических лиц"""
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='legal_entity_data'
    )
    company_name = models.CharField(
        max_length=255, verbose_name='Название компании'
    )
    bin = models.CharField(
        max_length=12, unique=True, null=True, blank=True,
        verbose_name='БИН'
    )
    tax_number = models.CharField(
        max_length=12, null=True, blank=True,
        verbose_name='Налоговый номер'
    )
    registration_date = models.DateField(
        null=True, blank=True, verbose_name='Дата регистрации'
    )
    director_name = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name='ФИО директора'
    )
    bank_account = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name='Банковский счет'
    )
    bank_name = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name='Название банка'
    )

    def __str__(self):
        return self.company_name

    class Meta:
        db_table = 'legal_entity_client_data'
        verbose_name = 'Данные юридического лица'
        verbose_name_plural = 'Данные юридических лиц'


class ClientPhone(models.Model):
    """Телефоны клиента (может быть несколько)"""
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='phones',
        verbose_name='Клиент'
    )
    phone = models.CharField(
        max_length=20, null=True, blank=True, verbose_name='Телефон'
    )
    is_primary = models.BooleanField(default=False, verbose_name='Основной')
    description = models.CharField(
        max_length=100, blank=True, verbose_name='Описание'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_phones', verbose_name='Создан'
    )
    modified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='modified_phones', verbose_name='Изменен'
    )

    def __str__(self):
        return f"{self.phone} ({self.client})"

    class Meta:
        db_table = 'client_phones'
        verbose_name = 'Телефон клиента'
        verbose_name_plural = 'Телефоны клиентов'


class ClientAddress(models.Model):
    """Адреса клиента (может быть несколько)"""
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Клиент'
    )
    address = models.TextField(
        null=True, blank=True, verbose_name='Адрес'
    )
    city = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Город'
    )
    comment = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Комментарий'
    )
    is_primary = models.BooleanField(default=False, verbose_name='Основной')

    def __str__(self):
        return f"{self.city}: {self.address}"

    class Meta:
        db_table = 'client_addresses'
        verbose_name = 'Адрес клиента'
        verbose_name_plural = 'Адреса клиентов'


class ClientCar(models.Model):
    """Автомобили клиента (может быть несколько, только для физлиц)"""
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='cars',
        verbose_name='Клиент'
    )
    brand = models.CharField(max_length=100, verbose_name='Марка')
    model = models.CharField(max_length=100, verbose_name='Модель')
    year = models.IntegerField(
        null=True, blank=True, verbose_name='Год'
    )
    license_plate = models.CharField(
        max_length=20, null=True, blank=True, verbose_name='Госномер'
    )
    vin_number = models.CharField(
        max_length=20, null=True, blank=True, verbose_name='VIN номер'
    )
    color = models.CharField(
        max_length=50, null=True, blank=True, verbose_name='Цвет'
    )
    is_primary = models.BooleanField(default=False, verbose_name='Основной')

    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"

    class Meta:
        db_table = 'client_cars'
        verbose_name = 'Автомобиль клиента'
        verbose_name_plural = 'Автомобили клиентов'