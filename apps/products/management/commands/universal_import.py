import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.products.models import Product, ProductGroup
from apps.orders.models import OrderItem
from apps.clients.models import Client
from apps.accounts.models import User
import os


class Command(BaseCommand):
    help = 'Универсальная команда для импорта всех данных из Excel файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Путь к Excel файлу для импорта'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Максимальное количество строк для обработки'
        )
        parser.add_argument(
            '--clear-products',
            action='store_true',
            help='Очистить существующие товары перед импортом'
        )
        parser.add_argument(
            '--clear-orders',
            action='store_true',
            help='Очистить существующие заказы перед импортом'
        )
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Только анализ файла без импорта'
        )
        parser.add_argument(
            '--remove-missing',
            action='store_true',
            help='Удалить товары, которых нет в файле'
        )
        parser.add_argument(
            '--check-data',
            action='store_true',
            help='Проверить данные в базе после импорта'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        limit = options['limit']
        clear_products = options['clear_products']
        clear_orders = options['clear_orders']
        analyze_only = options['analyze_only']
        remove_missing = options['remove_missing']
        check_data = options['check_data']

        try:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                raise CommandError(f'Файл не найден: {file_path}')

            self.stdout.write(f'Чтение файла: {file_path}')
            
            # Читаем файл, пропуская 1 строку (правильная структура)
            df = pd.read_excel(file_path, skiprows=1)
            
            # Ограничиваем количество строк
            if limit:
                df = df.head(limit)
            
            self.stdout.write(f'Найдено строк: {len(df)}')
            
            # Анализ файла
            self._analyze_file(df)
            
            if analyze_only:
                self.stdout.write(self.style.SUCCESS('Анализ завершен!'))
                return
            
            # Очистка данных при необходимости
            if clear_orders:
                self._clear_orders()
            
            if clear_products:
                self._clear_products()
            
            # Импорт данных
            self._import_products(df, remove_missing)
            
            # Проверка данных
            if check_data:
                self._check_imported_data()
            
            self.stdout.write(
                self.style.SUCCESS('Импорт завершен успешно!')
            )
            
        except FileNotFoundError:
            raise CommandError(f'Файл не найден: {file_path}')
        except Exception as e:
            raise CommandError(f'Ошибка при импорте: {str(e)}')

    def _analyze_file(self, df):
        """Анализ структуры файла"""
        self.stdout.write('\n=== АНАЛИЗ ФАЙЛА ===')
        
        # Общая информация
        self.stdout.write(f'Общее количество строк: {len(df)}')
        self.stdout.write(f'Количество колонок: {len(df.columns)}')
        
        # Первые несколько строк
        self.stdout.write('\nПервые 3 строки:')
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            code = str(row.iloc[0]) if len(row) > 0 else ''
            name = str(row.iloc[1]) if len(row) > 1 else ''
            self.stdout.write(f'  {i+1}. Код: {code[:20]}... Название: {name[:50]}...')
        
        # Анализ колонок с ценами
        self.stdout.write('\nАнализ цен (колонки 129-132):')
        for i, col_idx in enumerate([129, 130, 131, 132]):
            if col_idx < len(df.columns):
                col_name = df.columns[col_idx] if col_idx < len(df.columns) else f'Col_{col_idx}'
                sample_values = df.iloc[:5, col_idx].tolist()
                self.stdout.write(f'  Колонка {col_idx} ({col_name}): {sample_values}')
        
        # Анализ дополнительных полей
        self.stdout.write('\nАнализ дополнительных полей (колонки 133-137):')
        for i, col_idx in enumerate([133, 134, 135, 136, 137]):
            if col_idx < len(df.columns):
                col_name = df.columns[col_idx] if col_idx < len(df.columns) else f'Col_{col_idx}'
                sample_values = df.iloc[:5, col_idx].tolist()
                self.stdout.write(f'  Колонка {col_idx} ({col_name}): {sample_values}')

    def _clear_orders(self):
        """Очистка заказов"""
        self.stdout.write('\n=== ОЧИСТКА ЗАКАЗОВ ===')
        
        # Удаляем позиции заказов
        order_items_count = OrderItem.objects.count()
        OrderItem.objects.all().delete()
        self.stdout.write(f'Удалено позиций заказов: {order_items_count}')
        
        # Удаляем заказы
        from apps.orders.models import Order
        orders_count = Order.objects.count()
        Order.objects.all().delete()
        self.stdout.write(f'Удалено заказов: {orders_count}')

    def _clear_products(self):
        """Очистка товаров"""
        self.stdout.write('\n=== ОЧИСТКА ТОВАРОВ ===')
        
        # Сначала удаляем позиции заказов
        from apps.orders.models import OrderItem
        order_items_count = OrderItem.objects.count()
        OrderItem.objects.all().delete()
        self.stdout.write(f'Удалено позиций заказов: {order_items_count}')
        
        # Затем удаляем заказы
        from apps.orders.models import Order
        orders_count = Order.objects.count()
        Order.objects.all().delete()
        self.stdout.write(f'Удалено заказов: {orders_count}')
        
        # Теперь удаляем товары
        products_count = Product.objects.count()
        Product.objects.all().delete()
        self.stdout.write(f'Удалено товаров: {products_count}')
        
        # Удаляем группы товаров
        groups_count = ProductGroup.objects.count()
        ProductGroup.objects.all().delete()
        self.stdout.write(f'Удалено групп товаров: {groups_count}')

    def _import_products(self, df, remove_missing=False):
        """Импорт товаров"""
        self.stdout.write('\n=== ИМПОРТ ТОВАРОВ ===')
        
        # Создаем группы товаров
        self._create_product_groups()
        
        # Собираем коды товаров из файла для проверки
        file_codes = set()
        
        # Обрабатываем товары
        products_created = 0
        products_updated = 0
        
        for index, row in df.iterrows():
            # Извлекаем данные из строки
            code = str(row.iloc[0]).strip() if len(row) > 0 else ''
            name = str(row.iloc[1]).strip() if len(row) > 1 else ''
            
            # Извлекаем дополнительные данные из правильных колонок
            sales_plan_selection = str(row.iloc[133]).strip() if len(row) > 133 else ''
            dimension = str(row.iloc[134]).strip() if len(row) > 134 else ''
            tire_type_raw = str(row.iloc[135]).strip() if len(row) > 135 else ''  # Легковая, Грузовая и т.д.
            seasonality_raw = str(row.iloc[136]).strip() if len(row) > 136 else ''  # Зимние, Летние, Всесезонные
            assortment_group = str(row.iloc[137]).strip() if len(row) > 137 else ''
            
            # Извлекаем цены из колонок 129-132
            wholesale_price = self._parse_price(row.iloc[129]) if len(row) > 129 else None
            promotional_price = self._parse_price(row.iloc[130]) if len(row) > 130 else None
            retail_price = self._parse_price(row.iloc[132]) if len(row) > 132 else None
            
            # Пропускаем пустые строки или строки с заголовками
            if (not code or not name or 
                code == 'nan' or name == 'nan' or
                code == 'Код' or name == 'Наименование' or
                'АВТОШИНЫ' in code or '07.10.2025' in code or
                '14.10.2025' in code):
                continue
            
            # Пропускаем если код не похож на код товара
            if not code.isdigit() and len(code) < 5:
                continue
            
            # Добавляем код в множество для проверки
            file_codes.add(code)
            
            # Определяем группу товара
            product_group = self._get_product_group(name)
            
            # Определяем тип шины из столбца 135 (тип шины)
            tire_type = self._determine_tire_type(tire_type_raw)
            
            # Создаем или обновляем товар
            product, created = Product.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'sales_plan_selection': sales_plan_selection if sales_plan_selection != 'nan' else '',
                    'dimension': dimension if dimension != 'nan' else self._extract_dimension(name),
                    'tire_type': tire_type,
                    'seasonality': self._normalize_choice(seasonality_raw, Product.SEASONALITY_CHOICES),
                    'assortment_group': assortment_group if assortment_group != 'nan' else '',
                    'product_group': product_group,
                    'price': retail_price or 0,  # Основная цена - розничная
                    'wholesale_price': wholesale_price,
                    'promotional_price': promotional_price,
                    'retail_price': retail_price,
                    'is_active': True,
                }
            )
            
            if created:
                products_created += 1
                if products_created % 100 == 0:
                    self.stdout.write(f'Создано товаров: {products_created}')
            else:
                products_updated += 1
        
        # Удаляем товары, которых нет в файле
        if remove_missing:
            self._remove_missing_products(file_codes)
        
        self.stdout.write(f'Создано товаров: {products_created}')
        self.stdout.write(f'Обновлено товаров: {products_updated}')

    def _remove_missing_products(self, file_codes):
        """Удаляет товары, которых нет в файле"""
        self.stdout.write('\n=== УДАЛЕНИЕ ОТСУТСТВУЮЩИХ ТОВАРОВ ===')
        
        # Находим товары в базе, которых нет в файле
        existing_products = Product.objects.all()
        products_to_delete = []
        
        for product in existing_products:
            if product.code not in file_codes:
                products_to_delete.append(product)
        
        if products_to_delete:
            self.stdout.write(f'Найдено товаров для удаления: {len(products_to_delete)}')
            
            # Удаляем товары
            deleted_count = 0
            for product in products_to_delete:
                try:
                    product.delete()
                    deleted_count += 1
                    if deleted_count % 100 == 0:
                        self.stdout.write(f'Удалено товаров: {deleted_count}')
                except Exception as e:
                    self.stdout.write(f'Ошибка при удалении товара {product.code}: {e}')
            
            self.stdout.write(f'Удалено товаров: {deleted_count}')
        else:
            self.stdout.write('Товары для удаления не найдены')

    def _check_imported_data(self):
        """Проверка импортированных данных"""
        self.stdout.write('\n=== ПРОВЕРКА ДАННЫХ ===')
        
        # Статистика товаров
        total_products = Product.objects.count()
        products_with_segment = Product.objects.exclude(assortment_group='').count()
        products_with_tire_type = Product.objects.exclude(tire_type='').count()
        products_with_seasonality = Product.objects.exclude(seasonality='').count()
        products_with_prices = Product.objects.exclude(wholesale_price__isnull=True).count()
        
        self.stdout.write(f'Всего товаров: {total_products}')
        self.stdout.write(f'С ассортиментной группой: {products_with_segment}')
        self.stdout.write(f'С типом шины: {products_with_tire_type}')
        self.stdout.write(f'С сезонностью: {products_with_seasonality}')
        self.stdout.write(f'С ценами: {products_with_prices}')
        
        # Статистика групп
        groups_count = ProductGroup.objects.count()
        self.stdout.write(f'Групп товаров: {groups_count}')
        
        # Примеры товаров
        self.stdout.write('\nПримеры товаров:')
        products = Product.objects.all()[:5]
        for i, product in enumerate(products, 1):
            self.stdout.write(f'  {i}. {product.name[:50]}...')
            self.stdout.write(f'     Код: {product.code}')
            self.stdout.write(f'     Ассортиментная группа: {product.assortment_group}')
            self.stdout.write(f'     Сезонность: {product.seasonality}')
            self.stdout.write(f'     Розничная цена: {product.retail_price}')

    def _create_product_groups(self):
        """Создает группы товаров"""
        
        # Предопределенные группы из задания
        predefined_groups = [
            ('1', 'АВТОШИНЫ ИМПОРТНЫЕ ЛЕГКОВЫЕ ЗИМНИЕ'),
            ('2', 'АВТОШИНЫ ЛЕГКОВЫЕ'),
            ('3', 'АВТОШИНЫ ЛЕГКОГРУЗОВЫЕ'),
            ('4', 'АВТОШИНЫ ИМПОРТНЫЕ ЛЕГКОВЫЕ'),
            ('5', 'АВТОШИНЫ ГРУЗОВЫЕ'),
            ('5.1', 'ШИНОКОМПЛЕКТ (ШИНЫ + ДИСКИ)'),
            ('6', 'АВТОШИНЫ ДЛЯ СПЕЦТЕХНИКИ-Б/Г'),
            ('7', 'СЕЛЬХОЗШИНЫ'),
            ('8', 'КАМЕРЫ'),
            ('9', 'ФЛИПЕРА'),
            ('9а', 'МОТО-ВЕЛОШИНЫ'),
            ('9г', 'ДИСКИ-КОЛПАКИ'),
        ]
        
        # Создаем предопределенные группы
        for code, name in predefined_groups:
            group, created = ProductGroup.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(f'Создана группа: {code} - {name}')

    def _get_product_group(self, name):
        """Определяет группу товара на основе названия"""
        
        name_lower = name.lower()
        
        # Определяем группу по ключевым словам в названии
        if 'зимн' in name_lower and 'импорт' in name_lower:
            return ProductGroup.objects.get(code='1')
        elif 'легкогруз' in name_lower:
            return ProductGroup.objects.get(code='3')
        elif 'грузов' in name_lower:
            return ProductGroup.objects.get(code='5')
        elif 'сельхоз' in name_lower:
            return ProductGroup.objects.get(code='7')
        elif 'камер' in name_lower:
            return ProductGroup.objects.get(code='8')
        elif 'флипер' in name_lower:
            return ProductGroup.objects.get(code='9')
        elif 'мото' in name_lower or 'вело' in name_lower:
            return ProductGroup.objects.get(code='9а')
        elif 'диск' in name_lower or 'колпак' in name_lower:
            return ProductGroup.objects.get(code='9г')
        elif 'спецтехник' in name_lower:
            return ProductGroup.objects.get(code='6')
        elif 'шинокомплект' in name_lower:
            return ProductGroup.objects.get(code='5.1')
        else:
            # По умолчанию - легковые шины
            return ProductGroup.objects.get(code='2')

    def _extract_dimension(self, name):
        """Извлекает размерность из названия товара"""
        import re
        # Ищем паттерн размерности типа 155/65R13
        match = re.search(r'\d{3}/\d{2}R\d{2}', name)
        return match.group() if match else ''

    def _determine_tire_type(self, tire_type_raw):
        """Определяет тип шины на основе столбца 135 (тип шины)"""
        if tire_type_raw and tire_type_raw != 'nan':
            return tire_type_raw.strip()
        
        # По умолчанию пустая строка
        return ''

    def _normalize_choice(self, value, choices):
        """Нормализует значение для полей с выбором"""
        if not value or value == 'nan':
            return ''
        
        value_lower = value.lower()
        
        # Обычная обработка для полей
        for choice_value, choice_label in choices:
            if value_lower in choice_label.lower():
                return choice_value
        return ''

    def _parse_price(self, value):
        """Парсит цену из значения"""
        if not value or str(value) == 'nan':
            return None
        
        try:
            # Преобразуем в число
            price = float(value)
            return price if price > 0 else None
        except (ValueError, TypeError):
            return None
