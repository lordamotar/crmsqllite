from django.db import models
from django.conf import settings
from django.db.models import Sum


class Order(models.Model):
    """Модель заказа"""

    # Статусы заказа
    STATUS_NEW = 'new'
    STATUS_NEW_PAID = 'new_paid'
    STATUS_RESERVE = 'reserve'
    STATUS_TRANSFER = 'transfer'
    STATUS_DELIVERY = 'delivery'
    STATUS_CALLBACK = 'callback'
    STATUS_COMPLETED = 'completed'
    STATUS_REFUND = 'refund'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CANCEL_NO_ANSWER = 'cancel_no_answer'
    STATUS_CANCEL_NOT_SUITABLE_YEAR = 'cancel_not_suitable_year'
    STATUS_CANCEL_WRONG_ORDER = 'cancel_wrong_order'
    STATUS_CANCEL_FOUND_OTHER = 'cancel_found_other'
    STATUS_CANCEL_DELIVERY_TERMS = 'cancel_delivery_terms'
    STATUS_CANCEL_NO_QUANTITY = 'cancel_no_quantity'
    STATUS_CANCEL_INCOMPLETE = 'cancel_incomplete'

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('new_paid', 'Новый оплаченный'),
        ('reserve', 'Резерв'),
        ('transfer', 'Перемещение'),
        ('delivery', 'Доставка'),
        ('callback', 'Перезвонить'),
        ('completed', 'Выполнен'),
        ('refund', 'Возврат средств'),
        ('cancelled', 'Отменён (указать причину)'),
        ('cancel_no_answer', 'Отменен — не дозвонился'),
        ('cancel_not_suitable_year', 'Отменен — не устроил год'),
        ('cancel_wrong_order', 'Отменен — ошибочный заказ'),
        ('cancel_found_other', 'Отменен — нашел другие'),
        ('cancel_delivery_terms', 'Отменен — условия доставки'),
        ('cancel_no_quantity', 'Отменен — нет нужного кол-ва'),
        ('cancel_incomplete', 'Отменен — не комплект'),
    ]

    # Откуда заказ
    # Приводим к значениям, используемым в order_form.html (sourceSelect)
    SOURCE_CHOICES = [
        ('callcentr', 'Call-центр 2710'),
        ('2gis', '2GIS WhatsApp'),
        ('email', 'E-mail'),
        ('instagram', 'Instagram'),
        ('kaspi', 'Kaspi'),
        ('whatsapp', 'WhatsApp'),
        ('website', 'Сайт'),
    ]

    # Способ оплаты
    # Приводим к значениям, используемым в order_form.html (paymentSelect)
    PAYMENT_CHOICES = [
        ('airba', 'Airba Pay'),
        ('halyk', 'Halyk'),
        ('kaspi', 'Kaspi'),
        ('woopay', 'Wooppay'),
        ('bcc', 'БЦК'),
        ('cassa', 'На кассе'),
        ('account', 'По счету'),
        ('installment', 'Рассрочка (сайт)'),
        ('site', 'Сайт'),
        ('card', 'Карта'),
        ('transfer', 'Перевод'),
        ('cash', 'Наличные'),
    ]

    # Способ доставки
    DELIVERY_CHOICES = [
        ('pickup', 'Самовывоз'),
        ('delivery', 'Доставка'),
        ('courier', 'Курьер'),
    ]

    # Уровень цен
    PRICE_LEVEL_CHOICES = [
        ('wholesale', 'Оптовая'),
        ('promotional', 'Акционная'),
        ('retail', 'Розничная'),
    ]

    # Основные поля
    order_number = models.CharField(
        'Номер заказа', max_length=50, unique=True, blank=True
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_orders',
        null=True,
        verbose_name='Кем создан'
    )
    updated_at = models.DateTimeField('Дата изменения', auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='updated_orders',
        null=True,
        blank=True,
        verbose_name='Кем изменён'
    )

    # Связи
    client = models.ForeignKey(
        'clients.Client', on_delete=models.PROTECT, verbose_name='Клиент'
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='responsible_orders',
        verbose_name='Ответственный'
    )

    # Параметры заказа
    status = models.CharField(
        'Статус', max_length=30, choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    source = models.CharField(
        'Откуда заказ', max_length=20, choices=SOURCE_CHOICES
    )
    payment_method = models.CharField(
        'Способ оплаты', max_length=20, choices=PAYMENT_CHOICES
    )
    delivery_method = models.CharField(
        'Способ доставки', max_length=20, choices=DELIVERY_CHOICES,
        default='pickup'
    )
    price_level = models.CharField(
        'Уровень цен', max_length=20, choices=PRICE_LEVEL_CHOICES,
        default='retail'
    )

    # Дополнительно
    is_promo = models.BooleanField('По акции -10%', default=False)
    sale_number = models.CharField(
        'Номер реализации', max_length=50, blank=True
    )
    notes = models.TextField('Комментарий', blank=True)

    # Итоги
    total_amount = models.DecimalField(
        'Общая сумма', max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        date_str = self.created_at.strftime("%d.%m.%Y")
        return f'Заказ №{self.order_number} от {date_str}'

    def recalculate_total_amount(self):
        """Пересчитывает общую сумму заказа на основе позиций"""
        total = self.items.aggregate(s=Sum('amount'))['s'] or 0
        if self.total_amount != total:
            self.total_amount = total
            super().save(update_fields=['total_amount'])

    def save(self, *args, **kwargs):
        """Генерация номера заказа: только цифры, без префикса/даты.

        Номер = zero-padded ID записи (например, 000001, 000245).
        Сначала сохраняем для получения ID, затем обновляем поле.
        """
        if not self.order_number:
            # Сначала сохраним, чтобы получить первичный ключ
            super().save(*args, **kwargs)
            # Затем выставим номер как нулёво-падированный pk
            self.order_number = f"{self.pk:06d}"
            # Обновим только поле номера, избегая рекурсии
            super().save(update_fields=['order_number'])
            return
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа - snapshot данных товара на момент заказа"""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT,
        verbose_name='Товар'
    )

    # Snapshot данных товара на момент заказа
    product_code = models.CharField(
        'Код товара', max_length=50, blank=True, default=''
    )
    product_name = models.CharField('Номенклатура', max_length=255)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    segment = models.CharField(
        'Сегмент', max_length=20, blank=True, default=''
    )
    tire_type = models.CharField(
        'Тип шины', max_length=50, blank=True, default=''
    )
    branch_city = models.CharField(
        'Город филиала', max_length=100, blank=True, default=''
    )

    # Данные заказа
    quantity = models.PositiveIntegerField('Количество', default=1)
    amount = models.DecimalField('Сумма', max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'

    def __str__(self):
        return f'{self.product_code} - {self.product_name} x {self.quantity}'

    def save(self, *args, **kwargs):
        """Автоматическое копирование данных товара и расчёт суммы"""
        if self.product and not self.product_code:
            self.product_code = self.product.code
            self.product_name = self.product.name
            # Выбираем цену в зависимости от уровня цен заказа
            self.price = self._get_price_by_level()
            self.segment = self.product.assortment_group or ''
            self.tire_type = self.product.tire_type or ''
            # Город филиала заполняется только если не задан явно
            if not self.branch_city:
                # Берём город: приоритет у филиала->город, затем legacy branch_city
                if (
                    getattr(self.product, 'branch', None)
                    and self.product.branch
                    and self.product.branch.city
                ):
                    self.branch_city = self.product.branch.city.name
                elif getattr(self.product, 'branch_city', None):
                    self.branch_city = self.product.branch_city.name
        self.amount = self.price * self.quantity
        super().save(*args, **kwargs)
        # Пересчитываем общую сумму заказа
        self.order.recalculate_total_amount()

    def _get_price_by_level(self):
        """Возвращает цену в зависимости от уровня цен заказа"""
        if not self.product:
            return 0
        
        price_level = self.order.price_level
        
        if price_level == 'wholesale' and self.product.wholesale_price:
            return self.product.wholesale_price
        elif price_level == 'promotional' and self.product.promotional_price:
            return self.product.promotional_price
        elif price_level == 'retail' and self.product.retail_price:
            return self.product.retail_price
        else:
            # Fallback на основную цену
            return self.product.price
