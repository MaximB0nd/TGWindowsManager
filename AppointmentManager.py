import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

class AppointmentManager:
    """Менеджер для записи клиентов на услуги"""

    def __init__(self, db_path: str = "database.db"):
        """
        Инициализация менеджера записи

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

        # Улучшаем производительность
        self.cursor.execute("PRAGMA journal_mode = WAL")
        self.cursor.execute("PRAGMA synchronous = NORMAL")
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # Создаем таблицы
        self._create_tables()

    def _create_tables(self):
        """Создание всех необходимых таблиц"""

        # Таблица клиентов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                birth_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # Таблица сотрудников
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                position TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                specialization TEXT,
                work_schedule TEXT,  -- JSON с расписанием
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица услуг
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                duration INTEGER NOT NULL,  -- в минутах
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                required_employee_level TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица рабочих окон (слотов времени)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'available',  -- available, booked, blocked, completed
                max_capacity INTEGER DEFAULT 1,
                current_bookings INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id),
                FOREIGN KEY (service_id) REFERENCES services (service_id)
            )
        """)

        # Таблица записей/бронирований
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                appointment_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                status TEXT DEFAULT 'scheduled',  -- scheduled, confirmed, in_progress, completed, cancelled, no_show
                price DECIMAL(10, 2) NOT NULL,
                prepayment DECIMAL(10, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES clients (client_id),
                FOREIGN KEY (slot_id) REFERENCES time_slots (slot_id),
                FOREIGN KEY (service_id) REFERENCES services (service_id),
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            )
        """)

        # Таблица отзывов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id),
                FOREIGN KEY (client_id) REFERENCES clients (client_id),
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id),
                FOREIGN KEY (service_id) REFERENCES services (service_id)
            )
        """)

        # Таблица платежей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                payment_method TEXT NOT NULL,  -- cash, card, online
                status TEXT DEFAULT 'pending',  -- pending, completed, refunded
                transaction_id TEXT,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (appointment_id) REFERENCES appointments (appointment_id),
                FOREIGN KEY (client_id) REFERENCES clients (client_id)
            )
        """)

        # Индексы для ускорения поиска
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_client ON appointments(client_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_slots_start ON time_slots(start_time)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_slots_employee ON time_slots(employee_id)")

        self.connection.commit()

    def add_client(self, first_name: str, last_name: str, phone: str,
                   email: str = None, birth_date: str = None, notes: str = None) -> int:
        """
        Добавление нового клиента

        Args:
            first_name: Имя
            last_name: Фамилия
            phone: Телефон
            email: Email
            birth_date: Дата рождения (YYYY-MM-DD)
            notes: Заметки

        Returns:
            ID созданного клиента
        """
        self.cursor.execute("""
            INSERT INTO clients (first_name, last_name, phone, email, birth_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, phone, email, birth_date, notes))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_client(self, client_id: int = None, phone: str = None) -> Optional[Dict]:
        """
        Получение клиента по ID или телефону

        Args:
            client_id: ID клиента
            phone: Номер телефона

        Returns:
            Данные клиента или None
        """
        if client_id:
            self.cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        elif phone:
            self.cursor.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        else:
            return None

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_client(self, client_id: int, **kwargs) -> bool:
        """
        Обновление данных клиента

        Args:
            client_id: ID клиента
            **kwargs: Поля для обновления

        Returns:
            True если обновление успешно
        """
        if not kwargs:
            return False

        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        query = f"UPDATE clients SET {set_clause} WHERE client_id = ?"
        params = tuple(kwargs.values()) + (client_id,)

        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.rowcount > 0

    def search_clients(self, search_term: str = None,
                       limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Поиск клиентов по имени, фамилии или телефону

        Args:
            search_term: Строка для поиска
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список найденных клиентов
        """
        if search_term:
            search_pattern = f"%{search_term}%"
            self.cursor.execute("""
                SELECT * FROM clients 
                WHERE first_name LIKE ? 
                   OR last_name LIKE ? 
                   OR phone LIKE ?
                ORDER BY last_name, first_name
                LIMIT ? OFFSET ?
            """, (search_pattern, search_pattern, search_pattern, limit, offset))
        else:
            self.cursor.execute("""
                SELECT * FROM clients 
                ORDER BY last_name, first_name
                LIMIT ? OFFSET ?
            """, (limit, offset))

        return [dict(row) for row in self.cursor.fetchall()]

    def get_client_appointments(self, client_id: int,
                                upcoming_only: bool = True) -> List[Dict]:
        """
        Получение всех записей клиента

        Args:
            client_id: ID клиента
            upcoming_only: Только будущие записи

        Returns:
            Список записей клиента
        """
        if upcoming_only:
            self.cursor.execute("""
                SELECT a.*, s.name as service_name, 
                       e.first_name as employee_first_name, 
                       e.last_name as employee_last_name
                FROM appointments a
                JOIN services s ON a.service_id = s.service_id
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE a.client_id = ? 
                  AND DATE(a.appointment_date || ' ' || a.start_time) >= datetime('now')
                ORDER BY a.appointment_date, a.start_time
            """, (client_id,))
        else:
            self.cursor.execute("""
                SELECT a.*, s.name as service_name, 
                       e.first_name as employee_first_name, 
                       e.last_name as employee_last_name
                FROM appointments a
                JOIN services s ON a.service_id = s.service_id
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE a.client_id = ?
                ORDER BY a.appointment_date DESC, a.start_time DESC
            """, (client_id,))

        return [dict(row) for row in self.cursor.fetchall()]

    # ===== УСЛУГИ =====

    def add_service(self, name: str, category: str, duration: int,
                    price: float, description: str = None) -> int:
        """
        Добавление новой услуги

        Args:
            name: Название услуги
            category: Категория
            duration: Продолжительность в минутах
            price: Цена
            description: Описание

        Returns:
            ID созданной услуги
        """
        self.cursor.execute("""
            INSERT INTO services (name, category, duration, price, description)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category, duration, price, description))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_services(self, category: str = None, active_only: bool = True) -> List[Dict]:
        """
        Получение списка услуг

        Args:
            category: Фильтр по категории
            active_only: Только активные услуги

        Returns:
            Список услуг
        """
        query = "SELECT * FROM services"
        params = []

        conditions = []
        if active_only:
            conditions.append("is_active = 1")
        if category:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY category, name"

        self.cursor.execute(query, tuple(params))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_service_categories(self) -> List[str]:
        """
        Получение уникальных категорий услуг

        Returns:
            Список категорий
        """
        self.cursor.execute("SELECT DISTINCT category FROM services WHERE is_active = 1")
        return [row['category'] for row in self.cursor.fetchall()]

    # ===== СОТРУДНИКИ =====

    def add_employee(self, first_name: str, last_name: str, position: str,
                     phone: str, email: str, specialization: str = None) -> int:
        """
        Добавление нового сотрудника

        Args:
            first_name: Имя
            last_name: Фамилия
            position: Должность
            phone: Телефон
            email: Email
            specialization: Специализация

        Returns:
            ID созданного сотрудника
        """
        self.cursor.execute("""
            INSERT INTO employees (first_name, last_name, position, phone, email, specialization)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, position, phone, email, specialization))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_employees(self, position: str = None, active_only: bool = True) -> List[Dict]:
        """
        Получение списка сотрудников

        Args:
            position: Фильтр по должности
            active_only: Только активные сотрудники

        Returns:
            Список сотрудников
        """
        query = "SELECT * FROM employees"
        params = []

        conditions = []
        if active_only:
            conditions.append("is_active = 1")
        if position:
            conditions.append("position = ?")
            params.append(position)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY last_name, first_name"

        self.cursor.execute(query, tuple(params))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_employee_schedule(self, employee_id: int, date: str = None) -> List[Dict]:
        """
        Получение расписания сотрудника

        Args:
            employee_id: ID сотрудника
            date: Дата в формате YYYY-MM-DD (если None - на все время)

        Returns:
            Расписание сотрудника
        """
        if date:
            self.cursor.execute("""
                SELECT ts.*, s.name as service_name
                FROM time_slots ts
                JOIN services s ON ts.service_id = s.service_id
                WHERE ts.employee_id = ? 
                  AND DATE(ts.start_time) = ?
                ORDER BY ts.start_time
            """, (employee_id, date))
        else:
            self.cursor.execute("""
                SELECT ts.*, s.name as service_name
                FROM time_slots ts
                JOIN services s ON ts.service_id = s.service_id
                WHERE ts.employee_id = ?
                ORDER BY ts.start_time
            """, (employee_id,))

        return [dict(row) for row in self.cursor.fetchall()]

    # ===== РАБОЧИЕ ОКНА (СЛОТЫ) =====

    def create_time_slots(self, employee_id: int, service_id: int,
                          start_datetime: str, end_datetime: str,
                          interval_minutes: int = 60) -> List[int]:
        """
        Создание рабочих окон для сотрудника

        Args:
            employee_id: ID сотрудника
            service_id: ID услуги
            start_datetime: Начало периода (YYYY-MM-DD HH:MM)
            end_datetime: Конец периода (YYYY-MM-DD HH:MM)
            interval_minutes: Интервал между слотами

        Returns:
            Список созданных слотов
        """
        start = datetime.fromisoformat(start_datetime.replace(' ', 'T'))
        end = datetime.fromisoformat(end_datetime.replace(' ', 'T'))

        # Получаем продолжительность услуги
        self.cursor.execute("SELECT duration FROM services WHERE service_id = ?", (service_id,))
        service_duration = self.cursor.fetchone()['duration']

        created_slots = []
        current = start

        while current + timedelta(minutes=service_duration) <= end:
            slot_end = current + timedelta(minutes=service_duration)

            self.cursor.execute("""
                INSERT INTO time_slots (employee_id, service_id, start_time, end_time)
                VALUES (?, ?, ?, ?)
            """, (employee_id, service_id, current.isoformat(), slot_end.isoformat()))

            created_slots.append(self.cursor.lastrowid)
            current += timedelta(minutes=interval_minutes)

        self.connection.commit()
        return created_slots

    def get_available_slots(self, service_id: int, date: str,
                            employee_id: int = None) -> List[Dict]:
        """
        Получение доступных окон для записи

        Args:
            service_id: ID услуги
            date: Дата (YYYY-MM-DD)
            employee_id: ID сотрудника (если None - все сотрудники)

        Returns:
            Список доступных слотов
        """
        if employee_id:
            self.cursor.execute("""
                SELECT ts.*, e.first_name, e.last_name, s.name as service_name
                FROM time_slots ts
                JOIN employees e ON ts.employee_id = e.employee_id
                JOIN services s ON ts.service_id = s.service_id
                WHERE ts.service_id = ?
                  AND ts.employee_id = ?
                  AND DATE(ts.start_time) = ?
                  AND ts.status = 'available'
                  AND ts.current_bookings < ts.max_capacity
                ORDER BY ts.start_time
            """, (service_id, employee_id, date))
        else:
            self.cursor.execute("""
                SELECT ts.*, e.first_name, e.last_name, s.name as service_name
                FROM time_slots ts
                JOIN employees e ON ts.employee_id = e.employee_id
                JOIN services s ON ts.service_id = s.service_id
                WHERE ts.service_id = ?
                  AND DATE(ts.start_time) = ?
                  AND ts.status = 'available'
                  AND ts.current_bookings < ts.max_capacity
                ORDER BY ts.start_time
            """, (service_id, date))

        return [dict(row) for row in self.cursor.fetchall()]

    # ===== ЗАПИСИ НА УСЛУГИ =====

    def create_appointment(self, client_id: int, slot_id: int,
                           notes: str = None, prepayment: float = 0) -> int:
        """
        Создание записи на услугу

        Args:
            client_id: ID клиента
            slot_id: ID временного слота
            notes: Заметки
            prepayment: Предоплата

        Returns:
            ID созданной записи
        """
        # Получаем информацию о слоте
        self.cursor.execute("""
            SELECT ts.*, s.price, s.duration 
            FROM time_slots ts
            JOIN services s ON ts.service_id = s.service_id
            WHERE ts.slot_id = ?
        """, (slot_id,))

        slot = self.cursor.fetchone()
        if not slot:
            raise ValueError("Слот не найден")

        # Проверяем доступность
        if slot['status'] != 'available' or slot['current_bookings'] >= slot['max_capacity']:
            raise ValueError("Слот недоступен для записи")

        # Создаем запись
        self.cursor.execute("""
            INSERT INTO appointments 
            (client_id, slot_id, service_id, employee_id, appointment_date, 
             start_time, end_time, price, prepayment, notes)
            VALUES (?, ?, ?, ?, DATE(?), TIME(?), TIME(?), ?, ?, ?)
        """, (
            client_id, slot_id, slot['service_id'], slot['employee_id'],
            slot['start_time'], slot['start_time'], slot['end_time'],
            slot['price'], prepayment, notes
        ))

        appointment_id = self.cursor.lastrowid

        # Обновляем слот
        self.cursor.execute("""
            UPDATE time_slots 
            SET current_bookings = current_bookings + 1,
                status = CASE 
                    WHEN current_bookings + 1 >= max_capacity THEN 'booked'
                    ELSE 'available'
                END
            WHERE slot_id = ?
        """, (slot_id,))

        self.connection.commit()
        return appointment_id

    def update_appointment_status(self, appointment_id: int, status: str) -> bool:
        """
        Обновление статуса записи

        Args:
            appointment_id: ID записи
            status: Новый статус

        Returns:
            True если обновление успешно
        """
        valid_statuses = ['scheduled', 'confirmed', 'in_progress',
                          'completed', 'cancelled', 'no_show']

        if status not in valid_statuses:
            raise ValueError(f"Недопустимый статус. Допустимые: {valid_statuses}")

        self.cursor.execute("""
            UPDATE appointments 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = ?
        """, (status, appointment_id))

        self.connection.commit()
        return self.cursor.rowcount > 0

    def get_appointment(self, appointment_id: int) -> Optional[Dict]:
        """
        Получение информации о записи

        Args:
            appointment_id: ID записи

        Returns:
            Данные записи или None
        """
        self.cursor.execute("""
            SELECT a.*, 
                   c.first_name as client_first_name, c.last_name as client_last_name,
                   e.first_name as employee_first_name, e.last_name as employee_last_name,
                   s.name as service_name
            FROM appointments a
            JOIN clients c ON a.client_id = c.client_id
            JOIN employees e ON a.employee_id = e.employee_id
            JOIN services s ON a.service_id = s.service_id
            WHERE a.appointment_id = ?
        """, (appointment_id,))

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_daily_appointments(self, date: str = None,
                               employee_id: int = None) -> List[Dict]:
        """
        Получение записей на день

        Args:
            date: Дата (YYYY-MM-DD), если None - сегодня
            employee_id: ID сотрудника (если None - все)

        Returns:
            Список записей
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        if employee_id:
            self.cursor.execute("""
                SELECT a.*, 
                       c.first_name as client_first_name, c.last_name as client_last_name,
                       e.first_name as employee_first_name, e.last_name as employee_last_name,
                       s.name as service_name
                FROM appointments a
                JOIN clients c ON a.client_id = c.client_id
                JOIN employees e ON a.employee_id = e.employee_id
                JOIN services s ON a.service_id = s.service_id
                WHERE a.appointment_date = ? 
                  AND a.employee_id = ?
                ORDER BY a.start_time
            """, (date, employee_id))
        else:
            self.cursor.execute("""
                SELECT a.*, 
                       c.first_name as client_first_name, c.last_name as client_last_name,
                       e.first_name as employee_first_name, e.last_name as employee_last_name,
                       s.name as service_name
                FROM appointments a
                JOIN clients c ON a.client_id = c.client_id
                JOIN employees e ON a.employee_id = e.employee_id
                JOIN services s ON a.service_id = s.service_id
                WHERE a.appointment_date = ?
                ORDER BY a.employee_id, a.start_time
            """, (date,))

        return [dict(row) for row in self.cursor.fetchall()]

    def cancel_appointment(self, appointment_id: int, reason: str = None) -> bool:
        """
        Отмена записи

        Args:
            appointment_id: ID записи
            reason: Причина отмены

        Returns:
            True если отмена успешна
        """
        # Получаем слот для обновления
        self.cursor.execute("SELECT slot_id FROM appointments WHERE appointment_id = ?",
                            (appointment_id,))
        result = self.cursor.fetchone()
        if not result:
            return False

        slot_id = result['slot_id']

        # Отменяем запись
        self.cursor.execute("""
            UPDATE appointments 
            SET status = 'cancelled', 
                notes = COALESCE(notes || '\nОтмена: ' || ?, ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE appointment_id = ?
        """, (reason, reason, appointment_id))

        # Обновляем слот
        self.cursor.execute("""
            UPDATE time_slots 
            SET current_bookings = GREATEST(0, current_bookings - 1),
                status = CASE 
                    WHEN current_bookings - 1 <= 0 THEN 'available'
                    ELSE 'available'
                END
            WHERE slot_id = ?
        """, (slot_id,))

        self.connection.commit()
        return self.cursor.rowcount > 0

    # ===== ПЛАТЕЖИ =====

    def add_payment(self, appointment_id: int, amount: float,
                    payment_method: str, transaction_id: str = None) -> int:
        """
        Добавление платежа

        Args:
            appointment_id: ID записи
            amount: Сумма
            payment_method: Способ оплаты
            transaction_id: ID транзакции

        Returns:
            ID созданного платежа
        """
        # Получаем клиента
        self.cursor.execute("SELECT client_id FROM appointments WHERE appointment_id = ?",
                            (appointment_id,))
        result = self.cursor.fetchone()
        if not result:
            raise ValueError("Запись не найдена")

        client_id = result['client_id']

        self.cursor.execute("""
            INSERT INTO payments (appointment_id, client_id, amount, 
                                 payment_method, transaction_id)
            VALUES (?, ?, ?, ?, ?)
        """, (appointment_id, client_id, amount, payment_method, transaction_id))

        payment_id = self.cursor.lastrowid

        # Обновляем предоплату в записи, если нужно
        if payment_method != 'refund':
            self.cursor.execute("""
                UPDATE appointments 
                SET prepayment = prepayment + ?
                WHERE appointment_id = ?
            """, (amount, appointment_id))

        self.connection.commit()
        return payment_id

    def get_appointment_payments(self, appointment_id: int) -> List[Dict]:
        """
        Получение платежей по записи

        Args:
            appointment_id: ID записи

        Returns:
            Список платежей
        """
        self.cursor.execute("""
            SELECT * FROM payments 
            WHERE appointment_id = ?
            ORDER BY payment_date DESC
        """, (appointment_id,))

        return [dict(row) for row in self.cursor.fetchall()]

    # ===== ОТЧЕТЫ И СТАТИСТИКА =====

    def get_daily_summary(self, date: str = None) -> Dict:
        """
        Получение сводки за день

        Args:
            date: Дата (YYYY-MM-DD), если None - сегодня

        Returns:
            Сводка за день
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_appointments,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) as no_show,
                SUM(price) as total_revenue,
                SUM(prepayment) as total_prepayment
            FROM appointments 
            WHERE appointment_date = ?
        """, (date,))

        result = dict(self.cursor.fetchone())

        # Получаем платежи за день
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_payments,
                SUM(amount) as total_paid,
                payment_method,
                COUNT(*) as count
            FROM payments 
            WHERE DATE(payment_date) = ?
            GROUP BY payment_method
        """, (date,))

        result['payments'] = [dict(row) for row in self.cursor.fetchall()]

        return result

    def get_client_statistics(self, client_id: int) -> Dict:
        """
        Статистика по клиенту

        Args:
            client_id: ID клиента

        Returns:
            Статистика клиента
        """
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_appointments,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(price) as total_spent,
                MIN(appointment_date) as first_appointment,
                MAX(appointment_date) as last_appointment
            FROM appointments 
            WHERE client_id = ?
        """, (client_id,))

        return dict(self.cursor.fetchone())

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====

    def check_availability(self, service_id: int, employee_id: int,
                           date: str, time: str) -> bool:
        """
        Проверка доступности времени

        Args:
            service_id: ID услуги
            employee_id: ID сотрудника
            date: Дата (YYYY-MM-DD)
            time: Время (HH:MM)

        Returns:
            True если время доступно
        """
        datetime_str = f"{date} {time}"

        self.cursor.execute("""
            SELECT COUNT(*) as count
            FROM time_slots
            WHERE service_id = ?
              AND employee_id = ?
              AND start_time <= ?
              AND end_time > ?
              AND status = 'available'
              AND current_bookings < max_capacity
        """, (service_id, employee_id, datetime_str, datetime_str))

        return self.cursor.fetchone()['count'] > 0

    def send_reminders(self, hours_before: int = 24) -> List[int]:
        """
        Отправка напоминаний о предстоящих записях

        Args:
            hours_before: За сколько часов напоминать

        Returns:
            Список ID записей, по которым отправлены напоминания
        """
        reminder_time = (datetime.now() + timedelta(hours=hours_before)).strftime('%Y-%m-%d %H:%M')

        self.cursor.execute("""
            SELECT appointment_id, client_id, 
                   c.first_name, c.last_name, c.phone,
                   a.appointment_date, a.start_time, s.name as service_name
            FROM appointments a
            JOIN clients c ON a.client_id = c.client_id
            JOIN services s ON a.service_id = s.service_id
            WHERE a.status IN ('scheduled', 'confirmed')
              AND a.reminder_sent = 0
              AND datetime(a.appointment_date || ' ' || a.start_time) <= ?
        """, (reminder_time,))

        appointments = [dict(row) for row in self.cursor.fetchall()]
        reminded_appointments = []

        for app in appointments:
            # Здесь должна быть логика отправки SMS/email
            print(f"Напоминание для {app['first_name']} {app['last_name']}: "
                  f"{app['service_name']} на {app['appointment_date']} {app['start_time']}")

            # Отмечаем как отправленное
            self.cursor.execute("""
                UPDATE appointments 
                SET reminder_sent = 1
                WHERE appointment_id = ?
            """, (app['appointment_id'],))

            reminded_appointments.append(app['appointment_id'])

        self.connection.commit()
        return reminded_appointments

    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # Добавьте этот метод в класс AppointmentManager в файле AppointmentManager.py

    def get_client_by_tg_id(self, tg_id: int):
        """
        Получение клиента по ID Telegram

        Args:
            tg_id: ID пользователя Telegram

        Returns:
            Данные клиента или None
        """
        # Ищем клиента по телефону в формате tg_123456789
        phone = f"tg_{tg_id}"
        self.cursor.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def add_client_with_tg_id(self, first_name: str, last_name: str, tg_id: int,
                              email: str = None, birth_date: str = None, notes: str = None) -> int:
        """
        Добавление нового клиента с ID Telegram

        Args:
            first_name: Имя
            last_name: Фамилия
            tg_id: ID Telegram
            email: Email
            birth_date: Дата рождения (YYYY-MM-DD)
            notes: Заметки

        Returns:
            ID созданного клиента
        """
        phone = f"tg_{tg_id}"
        return self.add_client(first_name, last_name, phone, email, birth_date, notes)
