import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.clients.models import Client, IndividualClientData, LegalEntityClientData, ClientPhone, ClientAddress
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Импорт клиентов из файла client.txt'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='client.txt',
            help='Путь к файлу с данными клиентов'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующих клиентов перед импортом'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
            return

        if options['clear']:
            self.stdout.write('Очистка существующих клиентов...')
            # Удаляем только клиентов без связанных заказов
            clients_with_orders = Client.objects.filter(order__isnull=False).distinct()
            clients_to_delete = Client.objects.exclude(id__in=clients_with_orders)
            deleted_count = clients_to_delete.count()
            clients_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Удалено {deleted_count} клиентов без заказов')
            )

        # Получаем системного пользователя для created_by
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        imported_count = 0
        skipped_count = 0
        errors = []
        duplicate_names = 0
        duplicate_phones = 0
        empty_lines = 0
        invalid_type = 0

        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Пропускаем заголовок
        data_lines = lines[1:]

        with transaction.atomic():
            for line_num, line in enumerate(data_lines, start=2):
                try:
                    # Разбиваем строку по табуляции
                    parts = line.strip().split('\t')
                    
                    # Проверяем только что строка не пустая
                    if not line.strip():
                        empty_lines += 1
                        skipped_count += 1
                        continue
                    
                    # Расширяем список до нужной длины, заполняя пустыми строками
                    while len(parts) < 9:
                        parts.append('')

                    phone = parts[0].strip() if parts[0] else None
                    phone2 = parts[1].strip() if parts[1] else None
                    email = parts[2].strip() if parts[2] else None
                    client_type_raw = parts[3].strip()
                    full_name = parts[4].strip()
                    last_name = parts[5].strip() if parts[5] else ''
                    first_name = parts[6].strip() if parts[6] else ''
                    middle_name = parts[7].strip() if parts[7] else ''
                    city = parts[8].strip() if parts[8] else ''

                    # Определяем тип клиента
                    if client_type_raw == 'Физическое лицо':
                        client_type = 'individual'
                    elif client_type_raw == 'Юридическое лицо':
                        client_type = 'legal_entity'
                    else:
                        invalid_type += 1
                        skipped_count += 1
                        continue

                    # Проверяем дубликаты по телефону и имени
                    if phone and Client.objects.filter(phones__phone=f"+7{phone}").exists():
                        duplicate_phones += 1
                        skipped_count += 1
                        continue
                    
                    if full_name and Client.objects.filter(name=full_name).exists():
                        duplicate_names += 1
                        skipped_count += 1
                        continue
                    
                    # Пропускаем если нет ни телефона, ни имени
                    if not phone and not full_name:
                        empty_lines += 1
                        skipped_count += 1
                        continue

                    # Создаем клиента
                    client = Client.objects.create(
                        client_type=client_type,
                        name=full_name,
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=middle_name,
                        email=email if email else None,
                        created_by=admin_user,
                        modified_by=admin_user
                    )

                    # Создаем дополнительные данные в зависимости от типа
                    if client_type == 'individual':
                        IndividualClientData.objects.create(
                            client=client,
                            first_name=first_name,
                            last_name=last_name,
                            middle_name=middle_name if middle_name else None
                        )
                    else:  # legal_entity
                        LegalEntityClientData.objects.create(
                            client=client,
                            company_name=full_name
                        )

                    # Добавляем телефоны
                    if phone:
                        ClientPhone.objects.create(
                            client=client,
                            phone=f"+{phone}",
                            is_primary=True,
                            created_by=admin_user,
                            modified_by=admin_user
                        )

                    if phone2:
                        ClientPhone.objects.create(
                            client=client,
                            phone=f"+{phone2}",
                            is_primary=False,
                            description="Дополнительный номер",
                            created_by=admin_user,
                            modified_by=admin_user
                        )

                    # Добавляем адрес/город как primary адрес, если указан
                    if city:
                        ClientAddress.objects.create(
                            client=client,
                            city=city,
                            address=None,
                            comment=None,
                            is_primary=True
                        )

                    imported_count += 1

                except Exception as e:
                    errors.append(f'Строка {line_num}: {str(e)}')
                    skipped_count += 1

        # Выводим результаты
        self.stdout.write(
            self.style.SUCCESS(f'Импорт завершен:')
        )
        self.stdout.write(f'  Импортировано: {imported_count}')
        self.stdout.write(f'  Пропущено: {skipped_count}')
        self.stdout.write(f'    - Дубликаты по имени: {duplicate_names}')
        self.stdout.write(f'    - Дубликаты по телефону: {duplicate_phones}')
        self.stdout.write(f'    - Пустые строки: {empty_lines}')
        self.stdout.write(f'    - Неверный тип: {invalid_type}')
        
        if errors:
            self.stdout.write(
                self.style.WARNING(f'Ошибки ({len(errors)}):')
            )
            for error in errors[:10]:  # Показываем только первые 10 ошибок
                self.stdout.write(f'  {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... и еще {len(errors) - 10} ошибок')
