import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.clients.models import Client, IndividualClientData, LegalEntityClientData, ClientPhone, ClientAddress
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Импорт клиентов из Excel файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Путь к Excel файлу с данными клиентов'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Номер или название листа Excel (по умолчанию первый лист)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        sheet_name = options['sheet']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден')
            )
            return

        try:
            # Читаем Excel файл
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self.stdout.write(f'Загружен файл: {file_path}')
            self.stdout.write(f'Найдено строк: {len(df)}')
            
            # Проверяем наличие необходимых колонок
            required_columns = ['Телефон', 'Тип клиента', 'ФИО/Компания']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.stdout.write(
                    self.style.ERROR(f'Отсутствуют обязательные колонки: {missing_columns}')
                )
                return
            
            # Показываем доступные колонки
            self.stdout.write(f'Доступные колонки: {list(df.columns)}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка чтения файла: {str(e)}')
            )
            return

        # Получаем системного пользователя для created_by
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        imported_count = 0
        skipped_count = 0
        errors = []
        duplicate_names = 0
        duplicate_phones = 0
        empty_rows = 0
        invalid_type = 0

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Получаем данные из строки
                    phone = str(row.get('Телефон', '')).strip() if pd.notna(row.get('Телефон')) else ''
                    phone2 = str(row.get('Телефон 2', '')).strip() if pd.notna(row.get('Телефон 2')) else ''
                    email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else ''
                    client_type_raw = str(row.get('Тип клиента', '')).strip() if pd.notna(row.get('Тип клиента')) else ''
                    full_name = str(row.get('ФИО/Компания', '')).strip() if pd.notna(row.get('ФИО/Компания')) else ''
                    last_name = str(row.get('Фамилия', '')).strip() if pd.notna(row.get('Фамилия')) else ''
                    first_name = str(row.get('Имя', '')).strip() if pd.notna(row.get('Имя')) else ''
                    middle_name = str(row.get('Отчество', '')).strip() if pd.notna(row.get('Отчество')) else ''
                    city = str(row.get('Город', '')).strip() if pd.notna(row.get('Город')) else ''
                    
                    # Проверяем что строка не пустая
                    if not phone and not full_name:
                        empty_rows += 1
                        skipped_count += 1
                        continue
                    
                    # Определяем тип клиента
                    if client_type_raw in ['Физическое лицо', 'Физ. лицо', 'Физическое', 'individual']:
                        client_type = 'individual'
                    elif client_type_raw in ['Юридическое лицо', 'Юр. лицо', 'Юридическое', 'legal_entity']:
                        client_type = 'legal_entity'
                    else:
                        invalid_type += 1
                        skipped_count += 1
                        continue

                    # Нормализуем телефон (убираем все кроме цифр и добавляем +7)
                    def normalize_phone(phone_str):
                        if not phone_str:
                            return None
                        # Убираем все кроме цифр
                        digits = ''.join(filter(str.isdigit, phone_str))
                        if len(digits) == 10:
                            return f"+7{digits}"
                        elif len(digits) == 11 and digits.startswith('7'):
                            return f"+{digits}"
                        elif len(digits) == 11 and digits.startswith('8'):
                            return f"+7{digits[1:]}"
                        return None

                    normalized_phone = normalize_phone(phone)
                    normalized_phone2 = normalize_phone(phone2) if phone2 else None

                    # Проверяем существующих клиентов по телефону
                    existing_client = None
                    if normalized_phone:
                        existing_client = Client.objects.filter(phones__phone=normalized_phone).first()
                    
                    # Если клиент не найден по телефону, проверяем по имени
                    if not existing_client and full_name:
                        existing_client = Client.objects.filter(name=full_name).first()
                    
                    # Если клиент существует, обновляем его данные
                    if existing_client:
                        # Обновляем основные данные клиента
                        existing_client.name = full_name
                        existing_client.first_name = first_name
                        existing_client.last_name = last_name
                        existing_client.middle_name = middle_name
                        existing_client.email = email if email else existing_client.email
                        existing_client.modified_by = admin_user
                        existing_client.save()
                        
                        # Обновляем дополнительные данные в зависимости от типа
                        if client_type == 'individual':
                            try:
                                individual_data = existing_client.individual_data
                                individual_data.first_name = first_name
                                individual_data.last_name = last_name
                                individual_data.middle_name = middle_name if middle_name else None
                                individual_data.save()
                            except:
                                IndividualClientData.objects.create(
                                    client=existing_client,
                                    first_name=first_name,
                                    last_name=last_name,
                                    middle_name=middle_name if middle_name else None
                                )
                        else:  # legal_entity
                            try:
                                legal_data = existing_client.legal_entity_data
                                legal_data.company_name = full_name
                                legal_data.save()
                            except:
                                LegalEntityClientData.objects.create(
                                    client=existing_client,
                                    company_name=full_name
                                )
                        
                        # Обновляем или добавляем дополнительные телефоны
                        if normalized_phone2:
                            phone2_obj, created = ClientPhone.objects.get_or_create(
                                client=existing_client,
                                phone=normalized_phone2,
                                defaults={
                                    'is_primary': False,
                                    'description': "Дополнительный номер",
                                    'created_by': admin_user,
                                    'modified_by': admin_user
                                }
                            )
                        
                        # Обновляем или добавляем адрес/город
                        if city:
                            address_obj, created = ClientAddress.objects.get_or_create(
                                client=existing_client,
                                is_primary=True,
                                defaults={
                                    'city': city,
                                    'address': None,
                                    'comment': None
                                }
                            )
                            if not created:
                                address_obj.city = city
                                address_obj.save()
                        
                        imported_count += 1
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
                    if normalized_phone:
                        ClientPhone.objects.create(
                            client=client,
                            phone=normalized_phone,
                            is_primary=True,
                            created_by=admin_user,
                            modified_by=admin_user
                        )

                    if normalized_phone2:
                        ClientPhone.objects.create(
                            client=client,
                            phone=normalized_phone2,
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
                    errors.append(f'Строка {index + 2}: {str(e)}')
                    skipped_count += 1

        # Выводим результаты
        self.stdout.write(
            self.style.SUCCESS(f'Импорт завершен:')
        )
        self.stdout.write(f'  Импортировано: {imported_count}')
        self.stdout.write(f'  Пропущено: {skipped_count}')
        self.stdout.write(f'    - Дубликаты по имени: {duplicate_names}')
        self.stdout.write(f'    - Дубликаты по телефону: {duplicate_phones}')
        self.stdout.write(f'    - Пустые строки: {empty_rows}')
        self.stdout.write(f'    - Неверный тип: {invalid_type}')
        
        if errors:
            self.stdout.write(
                self.style.WARNING(f'Ошибки ({len(errors)}):')
            )
            for error in errors[:10]:  # Показываем только первые 10 ошибок
                self.stdout.write(f'  {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... и еще {len(errors) - 10} ошибок')
