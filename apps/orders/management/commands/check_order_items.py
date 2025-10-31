from django.core.management.base import BaseCommand
from apps.orders.models import OrderItem


class Command(BaseCommand):
    help = 'Проверяет данные OrderItem'

    def handle(self, *args, **options):
        self.stdout.write("=== ПРОВЕРКА ДАННЫХ ORDERITEM ===\n")
        
        # Проверяем первые 5 позиций заказов
        items = OrderItem.objects.all()[:5]
        
        if not items:
            self.stdout.write("❌ Нет позиций заказов в базе")
            return
            
        for i, item in enumerate(items, 1):
            self.stdout.write(f"--- Позиция {i} ---")
            self.stdout.write(f"ID: {item.id}")
            self.stdout.write(f"Заказ: {item.order.order_number}")
            self.stdout.write(f"Товар: {item.product_name}")
            self.stdout.write(f"Код товара: {item.product_code}")
            self.stdout.write(f"Город филиала: '{item.branch_city}'")
            self.stdout.write(f"Сегмент: '{item.segment}'")
            self.stdout.write(f"Цена: {item.price}")
            self.stdout.write(f"Количество: {item.quantity}")
            self.stdout.write(f"Сумма: {item.amount}")
            self.stdout.write("")
        
        # Статистика
        total_items = OrderItem.objects.count()
        items_with_city = OrderItem.objects.exclude(branch_city='').count()
        items_with_segment = OrderItem.objects.exclude(segment='').count()
        
        self.stdout.write("=== СТАТИСТИКА ===")
        self.stdout.write(f"Всего позиций: {total_items}")
        self.stdout.write(f"С городом филиала: {items_with_city}")
        self.stdout.write(f"С сегментом: {items_with_segment}")
