from django.db import models
from django.core.validators import MinValueValidator


class Branch(models.Model):
    """Филиал компании (привязан к городу)."""

    name = models.CharField(max_length=150, verbose_name='Название филиала')
    city = models.ForeignKey(
        'cities.City', on_delete=models.PROTECT, verbose_name='Город'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        db_table = 'products_branches'
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'
        ordering = ['city__name', 'name']

    def __str__(self):
        return f"{self.city.name} — {self.name}"


class Warehouse(models.Model):
    """Склад (привязан к филиалу)."""

    name = models.CharField(max_length=150, verbose_name='Название склада')
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='warehouses',
        verbose_name='Филиал'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        db_table = 'products_warehouses'
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
        ordering = ['branch__city__name', 'branch__name', 'name']

    def __str__(self):
        return f"{self.branch.city.name} — {self.branch.name} — {self.name}"


class ProductGroup(models.Model):
    """Группа товаров (например, АВТОШИНЫ ЛЕГКОВЫЕ)"""
    
    code = models.CharField(max_length=20, unique=True, verbose_name='Код группы')
    name = models.CharField(max_length=200, verbose_name='Название группы')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='subgroups', verbose_name='Родительская группа'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        db_table = 'product_groups'
        verbose_name = 'Группа товаров'
        verbose_name_plural = 'Группы товаров'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Product(models.Model):
    """Модель товара/номенклатуры"""

    SEGMENT_CHOICES = [
        ('retail', 'Розница'),
        ('wholesale', 'Опт'),
        ('vip', 'VIP'),
    ]
    
    TIRE_TYPE_CHOICES = [
        ('Легковая', 'Легковая'),
        ('Грузовая', 'Грузовая'),
        ('Легкогрузовая', 'Легкогрузовая'),
        ('Индустриальные', 'Индустриальные'),
        ('КГШ', 'КГШ'),
        ('Сельскохозяйственная', 'Сельскохозяйственная'),
        ('Мотошины', 'Мотошины'),
        ('Квадроциклы', 'Квадроциклы'),
    ]
    
    SEASONALITY_CHOICES = [
        ('summer', 'Летние'),
        ('winter', 'Зимние'),
        ('all_season', 'Всесезонные'),
    ]

    code = models.CharField(
        max_length=50, blank=True, verbose_name='Код товара', db_index=True
    )
    name = models.CharField(max_length=200, verbose_name='Наименование')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена',
        validators=[MinValueValidator(0)]
    )
    
    # Уровни цен
    wholesale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Оптовая цена',
        validators=[MinValueValidator(0)]
    )
    promotional_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Акционная цена',
        validators=[MinValueValidator(0)]
    )
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Розничная цена',
        validators=[MinValueValidator(0)]
    )
    segment = models.CharField(
        max_length=20, choices=SEGMENT_CHOICES,
        blank=True, verbose_name='Сегмент'
    )
    
    # Новые поля из Excel
    sales_plan_selection = models.CharField(
        max_length=100, blank=True, verbose_name='Отбор плана продаж'
    )
    dimension = models.CharField(
        max_length=50, blank=True, verbose_name='Размерность'
    )
    tire_type = models.CharField(
        max_length=20, choices=TIRE_TYPE_CHOICES,
        blank=True, verbose_name='Тип шины'
    )
    seasonality = models.CharField(
        max_length=20, choices=SEASONALITY_CHOICES,
        blank=True, verbose_name='Сезонность'
    )
    assortment_group = models.CharField(
        max_length=100, blank=True, verbose_name='Ассортиментная группа'
    )
    
    # Связь с группой товаров
    product_group = models.ForeignKey(
        ProductGroup, on_delete=models.PROTECT, null=True, blank=True,
        related_name='products', verbose_name='Группа товаров'
    )
    # Старое поле города филиала (оставляем для совместимости,
    # можно депрекейтнуть позже)
    branch_city = models.ForeignKey(
        'cities.City',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Город филиала'
    )

    # Новые связи
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Филиал'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Склад'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return f"{self.code} - {self.name} - {self.price}₸"
