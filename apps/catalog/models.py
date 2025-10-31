from django.db import models


class Segment(models.Model):
    """Сегмент клиентов"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'segments'
        verbose_name = 'Сегмент'
        verbose_name_plural = 'Сегменты'

    def __str__(self):
        return self.name


class BranchCity(models.Model):
    """Город филиала"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    
    class Meta:
        db_table = 'branch_cities'
        verbose_name = 'Город филиала'
        verbose_name_plural = 'Города филиалов'

    def __str__(self):
        return self.name


class OrderSource(models.Model):
    """Источник заказа"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    
    class Meta:
        db_table = 'order_sources'
        verbose_name = 'Источник заказа'
        verbose_name_plural = 'Источники заказов'

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """Способ оплаты"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Способ оплаты'
        verbose_name_plural = 'Способы оплаты'

    def __str__(self):
        return self.name


class OrderStatus(models.Model):
    """Статус заказа"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет')
    
    class Meta:
        db_table = 'order_statuses'
        verbose_name = 'Статус заказа'
        verbose_name_plural = 'Статусы заказов'

    def __str__(self):
        return self.name


class ProductSegment(models.Model):
    """Сегмент товаров (Шины, Диски, Запчасти и т.д.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    class Meta:
        db_table = 'product_segments'
        verbose_name = 'Сегмент товара'
        verbose_name_plural = 'Сегменты товаров'

    def __str__(self):
        return self.name


class ClientCity(models.Model):
    """Город клиента"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    
    class Meta:
        db_table = 'client_cities'
        verbose_name = 'Город клиента'
        verbose_name_plural = 'Города клиентов'

    def __str__(self):
        return self.name