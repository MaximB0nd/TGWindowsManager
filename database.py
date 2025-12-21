"""
Работа с базой данных SQLite
"""
import sqlite3
import os
import re
from typing import List, Optional
from models import Client, Appointment, KnowledgeBase


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_name: str = "appointments.db"):
        self.db_name = db_name
        self.init_database()
        self.init_knowledge_base()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализация таблиц БД"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица клиентов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица записей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES clients (user_id)
            )
        """)
        
        # Таблица базы знаний
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL UNIQUE,
                answer TEXT NOT NULL
            )
        """)
        
        # Таблица для отслеживания приветственных сообщений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_welcome_log (
                user_id INTEGER PRIMARY KEY,
                welcome_sent_at TEXT,
                last_activity_at TEXT,
                is_new_user INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES clients (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def init_knowledge_base(self):
        """Инициализация базы знаний начальными данными"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Базовые вопросы и ответы
        default_qa = [
            # Вопросы о стоимости
            ("сколько стоит", "Стоимость окон зависит от размера, типа профиля и стеклопакета. Замерщик бесплатно приедет и рассчитает точную стоимость."),
            ("цена", "Цена на пластиковые окна начинается от 5000 рублей. Точную стоимость можно узнать после бесплатного замера."),
            ("стоимость", "Стоимость рассчитывается индивидуально. Мы предлагаем бесплатный выезд замерщика для точного расчета."),
            ("сколько стоит окно", "Стоимость окна зависит от размера, профиля и стеклопакета. Минимальная цена от 5000 рублей. Для точного расчета нужен бесплатный замер."),
            ("цена окна", "Цена окна рассчитывается индивидуально. Замерщик бесплатно приедет и рассчитает точную стоимость."),
            
            # Вопросы о замере
            ("замер", "Замер производится бесплатно. Наш специалист приедет в удобное для вас время, рассчитает стоимость и оформит заказ."),
            ("сколько стоит замер", "Замер совершенно бесплатный! Наш специалист приедет, сделает все замеры и рассчитает стоимость."),
            ("бесплатный замер", "Да, замер абсолютно бесплатный! Наш специалист приедет в удобное для вас время."),
            ("как записаться", "Для записи на замер используйте команду /book или просто напишите нам, и мы согласуем удобное время."),
            ("записаться", "Для записи используйте команду /book. Наш менеджер свяжется с вами для подтверждения времени."),
            ("записаться на замер", "Используйте команду /book для записи на бесплатный замер. Наш менеджер свяжется с вами."),
            
            # Вопросы о возможностях бота
            ("что ты умеешь", "Я помогаю с выбором пластиковых окон, записываю на бесплатный замер, отвечаю на вопросы о ценах, монтаже и характеристиках окон. Используйте /help для списка команд."),
            ("что ты можешь", "Я могу помочь выбрать окна, записать на замер, ответить на вопросы о ценах и монтаже. Напишите ваш вопрос или используйте /help."),
            ("что ты делаешь", "Я консультирую по пластиковым окнам, записываю на бесплатный замер и отвечаю на ваши вопросы. Задайте вопрос или используйте /book для записи."),
            ("помощь", "Я помогу с выбором окон, запишу на замер, отвечу на вопросы. Используйте /help для списка команд или задайте вопрос."),
            
            # Вопросы о гарантии и сроках
            ("гарантия", "Мы предоставляем гарантию на пластиковые окна до 5 лет. Также гарантируем качество установки."),
            ("сроки", "Изготовление окон занимает 5-7 рабочих дней. Установка производится в течение 1-2 дней после изготовления."),
            ("сколько делается", "Изготовление окон занимает 5-7 рабочих дней. Установка производится в течение 1-2 дней после изготовления."),
            ("когда установят", "После изготовления (5-7 дней) установка производится в течение 1-2 дней. Точные сроки согласуются при заказе."),
            
            # Вопросы о типах окон
            ("какие окна", "Мы изготавливаем пластиковые окна различных профилей: Rehau, KBE, Veka. Подберем оптимальный вариант для вашего помещения."),
            ("какие окна лучше", "Выбор окон зависит от ваших потребностей: размера проема, климата, бюджета. Наш специалист поможет выбрать оптимальный вариант при бесплатном замере."),
            ("какой профиль", "Мы работаем с профилями Rehau, KBE, Veka. Выбор зависит от требований к теплоизоляции и прочности. Специалист поможет выбрать при замере."),
            ("какие окна для квартиры", "Для квартиры подойдут стандартные пластиковые окна с двухкамерным стеклопакетом. Точные рекомендации даст специалист при замере."),
            
            # Вопросы о монтаже
            ("монтаж", "Монтаж окон производится нашими опытными специалистами. Установка занимает 1-2 дня после изготовления окон."),
            ("установка", "Установка окон выполняется профессиональными монтажниками. Срок установки 1-2 дня после изготовления."),
            ("как устанавливают", "Установка производится профессиональными монтажниками с соблюдением всех технологий. Срок установки 1-2 дня."),
            
            # Вопросы о стеклопакетах
            ("стеклопакет", "Мы предлагаем одно-, двух- и трехкамерные стеклопакеты. Выбор зависит от требований к теплоизоляции. Специалист поможет выбрать при замере."),
            ("какой стеклопакет", "Выбор стеклопакета зависит от требований к теплоизоляции. Для квартиры обычно достаточно двухкамерного. Специалист даст рекомендации при замере."),
            
            # Вопросы о компании
            ("о компании", "Народные Окна - компания по производству и установке пластиковых окон. Мы предлагаем качественные окна с гарантией до 5 лет."),
            ("кто вы", "Я помощник компании Народные Окна. Помогаю с выбором окон, записываю на бесплатный замер и отвечаю на вопросы."),
        ]
        
        for question, answer in default_qa:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO knowledge_base (question, answer) VALUES (?, ?)",
                    (question.lower(), answer)
                )
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
    
    def add_client(self, client: Client) -> bool:
        """Добавить или обновить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO clients (user_id, username, first_name, phone, address, created_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """, (client.user_id, client.username, client.first_name, client.phone, 
                  client.address, client.created_at))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления клиента: {e}")
            return False
        finally:
            conn.close()
    
    def get_client(self, user_id: int) -> Optional[Client]:
        """Получить клиента по user_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM clients WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Client(
                user_id=row['user_id'],
                username=row['username'],
                first_name=row['first_name'],
                phone=row['phone'],
                address=row['address'],
                created_at=row['created_at']
            )
        return None
    
    def add_appointment(self, appointment: Appointment) -> bool:
        """Добавить запись на встречу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO appointments (user_id, date, time, address, phone, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """, (appointment.user_id, appointment.date, appointment.time,
                  appointment.address, appointment.phone, appointment.notes, appointment.created_at))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления записи: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_appointments(self, user_id: int) -> List[Appointment]:
        """Получить все записи пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM appointments 
            WHERE user_id = ? 
            ORDER BY date, time
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        appointments = []
        for row in rows:
            appointments.append(Appointment(
                id=row['id'],
                user_id=row['user_id'],
                date=row['date'],
                time=row['time'],
                address=row['address'],
                phone=row['phone'],
                notes=row['notes'],
                created_at=row['created_at']
            ))
        
        return appointments
    
    def search_knowledge_base(self, query: str) -> Optional[str]:
        """Поиск ответа в базе знаний с улучшенным алгоритмом"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query_lower = query.lower().strip()
        
        # Сначала ищем точное совпадение или полное вхождение
        cursor.execute("""
            SELECT answer FROM knowledge_base 
            WHERE question LIKE ? OR question = ?
            LIMIT 1
        """, (f"%{query_lower}%", query_lower))
        
        row = cursor.fetchone()
        if row:
            conn.close()
            return row['answer']
        
        # Удаляем знаки препинания и лишние слова
        cleaned_query = re.sub(r'[^\w\s]', '', query_lower)
        words = [w for w in cleaned_query.split() if len(w) > 2]  # Слова длиннее 2 символов
        
        # Ищем по ключевым словам (приоритет более длинным словам)
        words_sorted = sorted(words, key=len, reverse=True)
        
        for word in words_sorted:
            cursor.execute("""
                SELECT answer FROM knowledge_base 
                WHERE question LIKE ?
                LIMIT 1
            """, (f"%{word}%",))
            row = cursor.fetchone()
            if row:
                conn.close()
                return row['answer']
        
        # Если не нашли, пробуем комбинации из 2-3 слов
        if len(words) >= 2:
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                cursor.execute("""
                    SELECT answer FROM knowledge_base 
                    WHERE question LIKE ?
                    LIMIT 1
                """, (f"%{phrase}%",))
                row = cursor.fetchone()
                if row:
                    conn.close()
                    return row['answer']
        
        conn.close()
        return None
    
    def is_complex_question(self, query: str) -> bool:
        """Проверяет, является ли вопрос сложным (требует детального ответа)"""
        complex_keywords = [
            "отличие", "отличается", "разница", "различается", "различать",
            "сравнение", "сравнить", "сравни", "чем отличается",
            "что лучше", "какой лучше", "что выбрать между",
            "разница между", "отличие между", "сравни между"
        ]
        
        # Вопросы о цене/количестве тоже считаем сложными
        price_quantity_keywords = [
            "цена установки", "стоимость установки", "цена монтажа", "стоимость монтажа",
            "сколько стоит установка", "сколько стоит монтаж", "цена за", "стоимость за",
            "сколько окон", "сколько штук", "количество окон", "количество штук",
            "цена окна", "стоимость окна", "цена одного окна", "стоимость одного окна"
        ]
        
        query_lower = query.lower()
        
        # Проверяем сложные вопросы
        for keyword in complex_keywords:
            if keyword in query_lower:
                return True
        
        # Проверяем вопросы о цене/количестве
        for keyword in price_quantity_keywords:
            if keyword in query_lower:
                return True
        
        return False
    
    def add_to_knowledge_base(self, question: str, answer: str) -> bool:
        """Добавить вопрос-ответ в базу знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO knowledge_base (question, answer) VALUES (?, ?)",
                (question.lower(), answer)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления в базу знаний: {e}")
            return False
        finally:
            conn.close()
    
    def is_new_user(self, user_id: int) -> bool:
        """Проверить, является ли пользователь новым"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_new_user FROM user_welcome_log WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return True
        return bool(row['is_new_user'])
    
    def get_last_activity_time(self, user_id: int) -> Optional[str]:
        """Получить время последней активности пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_activity_at FROM user_welcome_log WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['last_activity_at']
        return None
    
    def mark_welcome_sent(self, user_id: int, is_new: bool = True):
        """Отметить, что приветственное сообщение отправлено"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO user_welcome_log 
                (user_id, welcome_sent_at, last_activity_at, is_new_user)
                VALUES (?, ?, ?, ?)
            """, (user_id, now, now, 1 if is_new else 0))
            conn.commit()
        except Exception as e:
            print(f"Ошибка при сохранении лога приветствия: {e}")
        finally:
            conn.close()
    
    def update_user_activity(self, user_id: int):
        """Обновить время последней активности пользователя"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        try:
            # Проверяем, существует ли запись
            cursor.execute("SELECT user_id FROM user_welcome_log WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE user_welcome_log 
                    SET last_activity_at = ?, is_new_user = 0
                    WHERE user_id = ?
                """, (now, user_id))
            else:
                cursor.execute("""
                    INSERT INTO user_welcome_log 
                    (user_id, last_activity_at, is_new_user)
                    VALUES (?, ?, 0)
                """, (user_id, now))
            conn.commit()
        except Exception as e:
            print(f"Ошибка при обновлении активности: {e}")
        finally:
            conn.close()
    
    def should_send_welcome_again(self, user_id: int) -> bool:
        """Проверить, нужно ли отправить приветствие снова (прошло более 24 часов)"""
        from datetime import datetime, timedelta
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_activity_at FROM user_welcome_log WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None or row['last_activity_at'] is None:
            return True
        
        try:
            last_activity = datetime.fromisoformat(row['last_activity_at'])
            time_diff = datetime.now() - last_activity
            return time_diff > timedelta(hours=24)
        except (ValueError, TypeError):
            return True


