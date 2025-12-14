# Answer.py
import json
import datetime
from enum import Enum
from dataclasses import dataclass, asdict


class UserState(Enum):
    """Состояния пользователя в диалоге"""
    MAIN_MENU = "main_menu"
    ORDERING_MEASUREMENT = "ordering_measurement"
    VIEWING_FAQ = "viewing_faq"


@dataclass
class MeasurementOrder:
    """Данные заявки на замер"""
    # Контактные данные
    full_name: str = ""
    phone: str = ""
    address: str = ""
    floor: str = ""
    
    # Параметры окон
    window_count: int = 0
    approximate_sizes: str = ""
    house_type: str = ""
    has_quarter: Optional[bool] = None
    
    # Дополнительные услуги
    need_sills: bool = False
    need_slopes: bool = False
    need_mosquito_nets: bool = False
    need_additional_hardware: str = ""
    
    # Желаемое время
    preferred_date: str = ""
    preferred_time: str = ""
    
    # Комментарий
    comment: str = ""
    
    # Технические поля
    order_date: str = ""
    order_id: str = ""
    
    def to_dict(self):
        return asdict(self)


class WindowBot:
    """Класс для управления логикой бота по установке окон"""
    
    def __init__(self, storage_file="orders.json"):
        self.storage_file = storage_file
        self.user_states = {}
        self.user_orders = {}
        self.faq_data = self._load_faq()
        
    def _load_faq(self):
        return [
            "1. Зачем нужен замерщик? Можно я сам измерю?\n"
            "Настоятельно рекомендуем бесплатный выезд замерщика. Он оценивает перекосы, материал стен и состояние проёма.",
            
            "2. Сколько времени делается окно?\n"
            "От 3 до 10 рабочих дней после заказа.",
            
            "3. Как привезут и поднимут окно?\n"
            "Доставка по городу включена. Бесплатный подъём — если есть лифт.",
            
            "4. Можно ли ставить окна зимой?\n"
            "Да. Используем зимние материалы для монтажа до –15°C.",
            
            "5. Сколько времени займёт установка?\n"
            "Монтаж одного окна «под ключ» — 2–4 часа.",
            
            "6. Как подготовить комнату к установке?\n"
            "Отодвиньте мебель, освободите подоконники, обеспечьте доступ к розетке.",
            
            "7. Будет ли много грязи?\n"
            "Мы уберём строительный мусор, но генеральную уборку не проводим.",
            
            "8. Кто должен демонтировать старое окно?\n"
            "Это делают наши мастера. Самостоятельный демонтаж не рекомендуется.",
            
            "9. Чем отличаются окна «эконом», «стандарт» и «премиум»?\n"
            "Разница в толщине профиля, классе фурнитуры и типе стеклопакета.",
            
            "10. Что такое качественный монтаж?\n"
            "Трёхслойный шов: крепёж к стене, гидроизоляция, пена и пароизоляция.",
            
            "11. На что распространяется гарантия?\n"
            "На профиль — 5-10 лет. На монтаж — 2-5 лет.",
            
            "12. Что делать, если из нового окна дует?\n"
            "Проверьте прижим створки. Если проблема остаётся — звоните для гарантийного обслуживания."
        ]
    
    def get_main_menu(self):
        return (
            "🏠 *Народные Окна* — Главное меню\n\n"
            "Выберите действие:\n\n"
            "1️⃣ *Запись на бесплатный замер* — выезд специалиста, точный расчёт\n"
            "2️⃣ *Частые вопросы* — ответы на популярные вопросы об окнах\n"
            "3️⃣ *Контакты* — как с нами связаться\n\n"
            "Выберите цифру (1, 2 или 3):"
        )
    
    def start_measurement_order(self, user_id):
        self.user_states[user_id] = UserState.ORDERING_MEASUREMENT
        self.user_orders[user_id] = MeasurementOrder()
        
        return (
            "📝 *Оформление заявки на бесплатный замер*\n\n"
            "Сейчас я задам несколько вопросов, чтобы наш специалист приехал максимально подготовленным.\n\n"
            "Для начала, как вас зовут? (ФИО или имя):"
        )
    
    def process_user_input(self, user_id, text):
        state = self.user_states.get(user_id, UserState.MAIN_MENU)
        
        if state == UserState.MAIN_MENU:
            return self._handle_main_menu(user_id, text)
        elif state == UserState.ORDERING_MEASUREMENT:
            return self._handle_measurement_order(user_id, text)
        elif state == UserState.VIEWING_FAQ:
            return self._handle_faq_return(user_id, text)
        
        return "Пожалуйста, выберите действие из меню."
    
    def _handle_main_menu(self, user_id, text):
        text = text.strip()
        
        if text == "1":
            return self.start_measurement_order(user_id)
        elif text == "2":
            return self.show_faq(user_id)
        elif text == "3":
            return self.show_contacts()
        else:
            return self.get_main_menu()
    
    def _handle_measurement_order(self, user_id, text):
        order = self.user_orders[user_id]
        
        if not order.full_name:
            order.full_name = text
            return "📱 Отлично! Теперь укажите ваш номер телефона для связи:"
        
        elif not order.phone:
            order.phone = text
            return "🏠 Укажите адрес, куда приехать замерщику:\n(Город, улица, дом, квартира)"
        
        elif not order.address:
            order.address = text
            return "📏 Сколько окон планируете заменить? (укажите цифру):"
        
        elif order.window_count == 0:
            try:
                order.window_count = int(text)
                return (
                    "🏗️ *Какой у вас тип дома?*\n\n"
                    "1. Панельный (хрущевка, панелька)\n"
                    "2. Кирпичный\n"
                    "3. Монолитный / Новостройка\n"
                    "4. Частный дом (дерево, газобетон)\n\n"
                    "Ответьте цифрой (1-4):"
                )
            except ValueError:
                return "Пожалуйста, укажите количество окон цифрой:"
        
        elif not order.house_type:
            house_types = {"1": "Панельный", "2": "Кирпичный", "3": "Монолитный", "4": "Частный дом"}
            if text in house_types:
                order.house_type = house_types[text]
                return "🪟 Есть ли у вас «четверть» в оконном проёме?\n1. Да\n2. Нет\n3. Не знаю\n\nОтветьте цифрой:"
            return "Пожалуйста, выберите цифру от 1 до 4:"
        
        elif order.has_quarter is None:
            if text == "1":
                order.has_quarter = True
            elif text == "2":
                order.has_quarter = False
            else:
                order.has_quarter = None
            
            return (
                "📋 *Какие дополнительные услуги нужны?*\n\n"
                "1. Подоконники\n2. Откосы\n3. Москитные сетки\n4. Всё из перечисленного\n5. Только окна\n\n"
                "Можно выбрать несколько цифр через запятую (например: 1,2,3):"
            )
        
        elif not order.need_sills:
            if "1" in text or "4" in text:
                order.need_sills = True
            if "2" in text or "4" in text:
                order.need_slopes = True
            if "3" in text or "4" in text:
                order.need_mosquito_nets = True
            
            return "📅 Когда вам удобно принять замерщика?\nУкажите дату (например: 15.12.2024 или 'завтра'):"
        
        elif not order.preferred_date:
            order.preferred_date = text
            return "⏰ В какое время?\nУкажите интервал (например: 'с 10 до 14' или 'вечер после 18'):"
        
        elif not order.preferred_time:
            order.preferred_time = text
            order.order_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            order.order_id = f"ORD{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            self._save_order(order)
            self.user_states[user_id] = UserState.MAIN_MENU
            
            return (
                "✅ *Заявка успешно оформлена!*\n\n"
                f"{self._format_order_confirmation(order)}\n\n"
                "📞 Наш менеджер свяжется с вами в течение 30 минут.\n\n"
                "Вернуться в главное меню: /start"
            )
        
        return "Пожалуйста, ответьте на предыдущий вопрос."
    
    def _format_order_confirmation(self, order):
        services = []
        if order.need_sills: services.append("подоконники")
        if order.need_slopes: services.append("откосы")
        if order.need_mosquito_nets: services.append("москитные сетки")
        
        return (
            f"*Номер заявки:* {order.order_id}\n"
            f"*Дата:* {order.order_date}\n"
            f"*Имя:* {order.full_name}\n"
            f"*Телефон:* {order.phone}\n"
            f"*Адрес:* {order.address}\n"
            f"*Окон:* {order.window_count} шт.\n"
            f"*Тип дома:* {order.house_type}\n"
            f"*Доп. услуги:* {', '.join(services) if services else 'нет'}\n"
            f"*Время:* {order.preferred_date}, {order.preferred_time}"
        )
    
    def show_faq(self, user_id):
        self.user_states[user_id] = UserState.VIEWING_FAQ
        faq_text = "\n\n".join(self.faq_data)
        return f"❓ *Часто задаваемые вопросы*\n\n{faq_text}\n\nДля возврата напишите 'меню' или /start"
    
    def _handle_faq_return(self, user_id, text):
        if text.lower() in ['меню', 'start', '/start']:
            self.user_states[user_id] = UserState.MAIN_MENU
            return self.get_main_menu()
        return "Для возврата в меню напишите 'меню' или /start"
    
    def show_contacts(self):
        return (
            "📞 *Контакты*\n\n"
            "🏢 *Народные Окна*\n\n"
            "📍 Адрес: г. Москва, ул. Примерная, д. 1\n"
            "📱 Телефон: 8 (800) 123-45-67\n"
            "🕒 Время работы: Пн-Вс с 9:00 до 21:00\n\n"
            "Для возврата в меню: /start"
        )
    
    def _save_order(self, order):
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        
        data.append(order.to_dict())
        
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_state(self, user_id):
        return self.user_states.get(user_id, UserState.MAIN_MENU)
    
    def reset_user_state(self, user_id):
        self.user_states.pop(user_id, None)
        self.user_orders.pop(user_id, None)