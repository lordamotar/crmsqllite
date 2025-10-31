from django.core.management.base import BaseCommand
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.clients.models import Client
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Создает тестовый заказ для проверки'

    def handle(self, *args, **options):
        # Получаем первый товар с заполненными данными
        product = Product.objects.exclude(assortment_group='').first()
        if not product:
            self.stdout.write("❌ Нет товаров с ассортиментной группой")
            return
            
        # Получаем первого клиента
        client = Client.objects.first()
        if not client:
            self.stdout.write("❌ Нет клиентов")
            return
            
        # Получаем первого пользователя
        user = User.objects.first()
        if not user:
            self.stdout.write("❌ Нет пользователей")
            return
            
        # Создаем заказ
        order = Order.objects.create(
            client=client,
            responsible=user,
            price_level='retail',
            created_by=user,
            updated_by=user,
        )
        
        # Создаем позицию заказа
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            branch_city='Алматы',  # Указываем город явно
        )
        
        self.stdout.write(f"Создан заказ {order.order_number}")
        self.stdout.write(f"Товар: {order_item.product_name}")
        self.stdout.write(f"Сегмент: '{order_item.segment}'")
        self.stdout.write(f"Город филиала: '{order_item.branch_city}'")
        self.stdout.write(f"Цена: {order_item.price}")
        self.stdout.write(f"Сумма: {order_item.amount}")
