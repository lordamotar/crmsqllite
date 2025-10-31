from django.core.management.base import BaseCommand
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.clients.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Тестирует создание заказа с разными уровнями цен'

    def handle(self, *args, **options):
        self.stdout.write('Тестирование уровней цен в заказах:')
        
        # Получаем первый товар с ценами
        product = Product.objects.filter(
            wholesale_price__isnull=False,
            promotional_price__isnull=False,
            retail_price__isnull=False
        ).first()
        
        if not product:
            self.stdout.write(self.style.ERROR('Нет товаров с полными ценами'))
            return
            
        self.stdout.write(f'\nТовар: {product.name}')
        self.stdout.write(f'  Оптовая цена: {product.wholesale_price}')
        self.stdout.write(f'  Акционная цена: {product.promotional_price}')
        self.stdout.write(f'  Розничная цена: {product.retail_price}')
        
        # Получаем клиента и пользователя
        client = Client.objects.first()
        user = User.objects.first()
        
        if not client or not user:
            self.stdout.write(self.style.ERROR('Нет клиентов или пользователей'))
            return
        
        # Тестируем разные уровни цен
        price_levels = ['wholesale', 'promotional', 'retail']
        
        for level in price_levels:
            self.stdout.write(f'\n--- Тест уровня цен: {level} ---')
            
            # Создаем заказ
            order = Order.objects.create(
                client=client,
                responsible=user,
                price_level=level,
                source='website',
                payment_method='cash',
                delivery_method='pickup',
                created_by=user,
                updated_by=user
            )
            
            # Добавляем товар
            item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1
            )
            
            self.stdout.write(f'Заказ создан: {order.order_number}')
            self.stdout.write(f'Цена в заказе: {item.price}')
            self.stdout.write(f'Общая сумма: {order.total_amount}')
            
            # Удаляем тестовый заказ
            order.delete()
        
        self.stdout.write(
            self.style.SUCCESS('\nТестирование завершено!')
        )
