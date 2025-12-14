# Answer.py
import sqlite3
from typing import List, Dict, Optional


class FAQDatabase:
    """Класс для работы с FAQ в SQLite базе данных"""
    
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблицы FAQ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица для FAQ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faq (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    order_index INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Проверяем, есть ли данные в таблице
            cursor.execute('SELECT COUNT(*) FROM faq')
            count = cursor.fetchone()[0]
            
            # Если таблица пуста, заполняем начальными данными
            if count == 0:
                self._load_initial_faq(cursor)
            
            conn.commit()
    
    def _load_initial_faq(self, cursor):
        """Загрузка начальных данных FAQ"""
        initial_faq = [
            ("Зачем нужен замерщик? Можно я сам измерю?", 
             "Настоятельно рекомендуем бесплатный выезд замерщика. Он оценивает перекосы, материал стен и состояние проёма."),
            
            ("Сколько времени делается окно?", 
             "От 3 до 10 рабочих дней после заказа."),
            
            ("Как привезут и поднимут окно?", 
             "Доставка по городу включена. Бесплатный подъём — если есть лифт."),
            
            ("Можно ли ставить окна зимой?", 
             "Да. Используем зимние материалы для монтажа до –15°C."),
            
            ("Сколько времени займёт установка?", 
             "Монтаж одного окна «под ключ» — 2–4 часа."),
            
            ("Как подготовить комнату к установке?", 
             "Отодвиньте мебель, освободите подоконники, обеспечьте доступ к розетке."),
            
            ("Будет ли много грязи?", 
             "Мы уберём строительный мусор, но генеральную уборку не проводим."),
            
            ("Кто должен демонтировать старое окно?", 
             "Это делают наши мастера. Самостоятельный демонтаж не рекомендуется."),
            
            ("Чем отличаются окна «эконом», «стандарт» и «премиум»?", 
             "Разница в толщине профиля, классе фурнитуры и типе стеклопакета."),
            
            ("Что такое качественный монтаж?", 
             "Трёхслойный шов: крепёж к стене, гидроизоляция, пена и пароизоляция."),
            
            ("На что распространяется гарантия?", 
             "На профиль — 5-10 лет. На монтаж — 2-5 лет."),
            
            ("Что делать, если из нового окна дует?", 
             "Проверьте прижим створки. Если проблема остаётся — звоните для гарантийного обслуживания.")
        ]
        
        for i, (question, answer) in enumerate(initial_faq):
            cursor.execute('''
                INSERT INTO faq (question, answer, order_index) 
                VALUES (?, ?, ?)
            ''', (question, answer, i + 1))
    
    def get_all_faq(self) -> List[Dict]:
        """Получение всех вопросов-ответов"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM faq 
                WHERE is_active = 1 
                ORDER BY order_index, id
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_faq_by_id(self, faq_id: int) -> Optional[Dict]:
        """Получение конкретного FAQ по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM faq WHERE id = ? AND is_active = 1', (faq_id,))
            row = cursor.fetchone()
            
            return dict(row) if row else None
    
    def get_faq_by_category(self, category: str) -> List[Dict]:
        """Получение FAQ по категории"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM faq 
                WHERE category = ? AND is_active = 1 
                ORDER BY order_index, id
            ''', (category,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_faq(self, question: str, answer: str, category: str = 'general') -> int:
        """Добавление нового FAQ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем максимальный order_index
            cursor.execute('SELECT MAX(order_index) FROM faq')
            max_order = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                INSERT INTO faq (question, answer, category, order_index) 
                VALUES (?, ?, ?, ?)
            ''', (question, answer, category, max_order + 1))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_faq(self, faq_id: int, question: str = None, answer: str = None, 
                   category: str = None, order_index: int = None) -> bool:
        """Обновление существующего FAQ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Подготовка данных для обновления
            update_fields = []
            params = []
            
            if question is not None:
                update_fields.append("question = ?")
                params.append(question)
            
            if answer is not None:
                update_fields.append("answer = ?")
                params.append(answer)
            
            if category is not None:
                update_fields.append("category = ?")
                params.append(category)
            
            if order_index is not None:
                update_fields.append("order_index = ?")
                params.append(order_index)
            
            if not update_fields:
                return False
            
            params.append(faq_id)
            
            query = f'''
                UPDATE faq 
                SET {', '.join(update_fields)} 
                WHERE id = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def delete_faq(self, faq_id: int) -> bool:
        """Удаление FAQ (мягкое удаление - деактивация)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE faq SET is_active = 0 WHERE id = ?', (faq_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def search_faq(self, search_text: str) -> List[Dict]:
        """Поиск FAQ по тексту"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            search_pattern = f'%{search_text}%'
            cursor.execute('''
                SELECT * FROM faq 
                WHERE (question LIKE ? OR answer LIKE ?) 
                AND is_active = 1 
                ORDER BY order_index, id
            ''', (search_pattern, search_pattern))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_faq_count(self) -> int:
        """Получение количества активных FAQ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM faq WHERE is_active = 1')
            return cursor.fetchone()[0]


class FAQManager:
    """Основной класс для управления FAQ"""
    
    def __init__(self, db_path='database.db'):
        self.db = FAQDatabase(db_path)
    
    def get_faq_list(self) -> str:
        """Получение форматированного списка FAQ"""
        faq_items = self.db.get_all_faq()
        
        if not faq_items:
            return "❓ На данный момент FAQ пуст."
        
        result = ["❓ *Часто задаваемые вопросы (FAQ)*\n"]
        
        for i, item in enumerate(faq_items, 1):
            question = item['question']
            answer = item['answer']
            
            # Форматируем каждый вопрос-ответ
            faq_entry = f"\n*{i}. {question}*\n{answer}"
            result.append(faq_entry)
        
        result.append(f"\n\n📊 Всего вопросов: {len(faq_items)}")
        
        return "\n".join(result)
    
    def get_faq_list_short(self) -> str:
        """Короткая версия FAQ (только вопросы)"""
        faq_items = self.db.get_all_faq()
        
        if not faq_items:
            return "❓ FAQ пуст."
        
        result = ["❓ *Частые вопросы:*\n"]
        
        for i, item in enumerate(faq_items, 1):
            result.append(f"{i}. {item['question']}")
        
        return "\n".join(result)
    
    def get_faq_by_number(self, number: int) -> str:
        """Получение конкретного FAQ по номеру"""
        faq_items = self.db.get_all_faq()
        
        if not 1 <= number <= len(faq_items):
            return f"❌ Вопрос с номером {number} не найден."
        
        item = faq_items[number - 1]
        return f"*{item['question']}*\n\n{item['answer']}"
    
    def search_faq_text(self, search_text: str) -> str:
        """Поиск в FAQ"""
        results = self.db.search_faq(search_text)
        
        if not results:
            return f"🔍 По запросу '{search_text}' ничего не найдено."
        
        result_text = [f"🔍 *Результаты поиска по '{search_text}':*\n"]
        
        for item in results:
            result_text.append(f"\n*{item['question']}*\n{item['answer'][:200]}...")
        
        return "\n".join(result_text)
    
    def add_new_faq(self, question: str, answer: str, category: str = 'general') -> str:
        """Добавление нового вопроса в FAQ"""
        try:
            faq_id = self.db.add_faq(question, answer, category)
            return f"✅ Вопрос успешно добавлен (ID: {faq_id})"
        except Exception as e:
            return f"❌ Ошибка при добавлении: {str(e)}"
    
    def get_faq_count(self) -> int:
        """Получение количества FAQ"""
        return self.db.get_faq_count()