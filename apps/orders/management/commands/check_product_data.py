from django.core.management.base import BaseCommand
from apps.orders.models import OrderItem


class Command(BaseCommand):
    help = 'Проверяет данные товара в OrderItem'

    def handle(self, *args, **options):
        item = OrderItem.objects.first()
        if not item:
            self.stdout.write("Нет позиций заказов")
            return
            
        self.stdout.write(f"Товар: {item.product.name if item.product else 'None'}")
        if item.product:
            self.stdout.write(f"Сегмент товара: '{item.product.segment}'")
            if hasattr(item.product, 'branch_city') and item.product.branch_city:
                self.stdout.write(f"Город товара: '{item.product.branch_city.name}'")
            else:
                self.stdout.write("Город товара: None")
        else:
            self.stdout.write("Товар не найден")
