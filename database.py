"""
Работа с базой данных SQLite
"""
import sqlite3
import os
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
        
        conn.commit()
        conn.close()
    
    def init_knowledge_base(self):
        """Инициализация базы знаний начальными данными"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Базовые вопросы и ответы
        default_qa = [
            ("сколько стоит", "Стоимость окон зависит от размера, типа профиля и стеклопакета. Замерщик бесплатно приедет и рассчитает точную стоимость."),
            ("цена", "Цена на пластиковые окна начинается от 5000 рублей. Точную стоимость можно узнать после бесплатного замера."),
            ("стоимость", "Стоимость рассчитывается индивидуально. Мы предлагаем бесплатный выезд замерщика для точного расчета."),
            ("замер", "Замер производится бесплатно. Наш специалист приедет в удобное для вас время, рассчитает стоимость и оформит заказ."),
            ("сколько стоит замер", "Замер совершенно бесплатный! Наш специалист приедет, сделает все замеры и рассчитает стоимость."),
            ("гарантия", "Мы предоставляем гарантию на пластиковые окна до 5 лет. Также гарантируем качество установки."),
            ("сроки", "Изготовление окон занимает 5-7 рабочих дней. Установка производится в течение 1-2 дней после изготовления."),
            ("как записаться", "Для записи на замер используйте команду /book или просто напишите нам, и мы согласуем удобное время."),
            ("записаться", "Для записи используйте команду /book. Наш менеджер свяжется с вами для подтверждения времени."),
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
        """Поиск ответа в базе знаний"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query_lower = query.lower()
        # Ищем по ключевым словам в вопросе
        cursor.execute("""
            SELECT answer FROM knowledge_base 
            WHERE question LIKE ?
            LIMIT 1
        """, (f"%{query_lower}%",))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['answer']
        
        # Если точного совпадения нет, ищем по отдельным словам
        words = query_lower.split()
        for word in words:
            if len(word) > 3:  # Игнорируем короткие слова
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT answer FROM knowledge_base 
                    WHERE question LIKE ?
                    LIMIT 1
                """, (f"%{word}%",))
                row = cursor.fetchone()
                conn.close()
                if row:
                    return row['answer']
        
        return None
    
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


