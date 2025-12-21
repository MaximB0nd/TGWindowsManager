"""
Логика бота для записи на замер окон
"""
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from database import Database
from models import Client, Appointment
from datetime import datetime


class AppointmentStates(StatesGroup):
    """Состояния для записи на встречу"""
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_notes = State()


class WindowBot:
    """Основной класс бота"""
    
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.db = Database()
        self.setup_handlers()
    
    async def send_welcome_message(self, message: Message, is_new_user: bool = True, is_returning: bool = False) -> bool:
        """
        Отправляет приветственное сообщение пользователю
        
        Args:
            message: Объект сообщения от Telegram
            is_new_user: Является ли пользователь новым
            is_returning: Возвращается ли пользователь после долгого отсутствия
        
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            user = message.from_user
            user_name = user.first_name or "клиент"
            
            # Формируем приветствие в зависимости от типа пользователя
            if is_returning:
                greeting = f"С возвращением, {user_name}! 👋"
            elif is_new_user:
                greeting = f"Привет, {user_name}! 👋\nРады видеть вас впервые!"
            else:
                greeting = f"Добро пожаловать, {user_name}! 👋"
            
            # Основной текст приветствия
            welcome_text = (
                f"{greeting}\n\n"
                "Я ваш умный помощник от компании Народные Окна!\n\n"
                "Я помогу вам:\n"
                "🪟 Подобрать пластиковые окна и профили\n"
                "📅 Записаться на бесплатный замер\n"
                "💬 Ответить на вопросы по монтажу и ценам\n"
                "📍 Выбрать оптимальное решение для вашего помещения\n\n"
                "Вы можете спросить меня:\n"
                "• Какие окна лучше для квартиры?\n"
                "• Сколько стоит установка?\n"
                "• Как записаться на замер?\n\n"
                "Напишите ваш вопрос или выберите команду:\n"
                "/help - справка по командам\n"
                "/book - запись на замер\n"
                "/my_appointments - мои записи\n\n"
                "Готовы подобрать идеальные окна? ☀️"
            )
            
            # Создаем клавиатуру
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Записаться на замер")],
                    [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                ],
                resize_keyboard=True
            )
            
            # Отправляем сообщение
            await message.answer(welcome_text, reply_markup=keyboard)
            
            # Логируем отправку
            self.db.mark_welcome_sent(user.id, is_new_user)
            print(f"Приветственное сообщение отправлено пользователю {user.id} ({user_name})")
            
            return True
        except Exception as e:
            print(f"Ошибка при отправке приветственного сообщения: {e}")
            return False
    
    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Обработчик команды /start
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            user = message.from_user
            
            # Регистрируем или обновляем клиента
            client = Client(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            self.db.add_client(client)
            
            # Проверяем, новый ли пользователь или возвращается
            is_new = self.db.is_new_user(user.id)
            should_welcome_again = self.db.should_send_welcome_again(user.id)
            is_returning = not is_new and should_welcome_again
            
            # Отправляем приветственное сообщение
            await self.send_welcome_message(message, is_new_user=is_new, is_returning=is_returning)
            
            # Обновляем активность
            self.db.update_user_activity(user.id)
        
        # Обработчик команды /help
        @self.dp.message(Command("help"))
        async def cmd_help(message: Message):
            user = message.from_user
            
            # Проверяем, новый ли пользователь
            is_new = self.db.is_new_user(user.id)
            
            # Если новый пользователь, отправляем полное приветствие
            if is_new:
                await self.send_welcome_message(message, is_new_user=True)
            else:
                # Для существующих пользователей - краткая справка
                help_text = (
                    "📋 Доступные команды:\n\n"
                    "/start - Начать работу с ботом\n"
                    "/book - Записаться на замер\n"
                    "/my_appointments - Показать мои записи\n"
                    "/faq - Часто задаваемые вопросы\n"
                    "/ask - Задать вопрос\n"
                    "/cancel - Отменить текущую операцию\n\n"
                    "Также вы можете просто написать вопрос, и я постараюсь на него ответить!"
                )
                await message.answer(help_text)
            
            # Обновляем активность
            self.db.update_user_activity(user.id)
        
        # Обработчик команды /book (запись на замер)
        @self.dp.message(Command("book"))
        @self.dp.message(F.text == "Записаться на замер")
        async def cmd_book(message: Message, state: FSMContext):
            await state.set_state(AppointmentStates.waiting_for_date)
            await message.answer(
                "📅 Для записи на замер мне нужна некоторая информация.\n\n"
                "Введите желаемую дату в формате ДД.ММ.ГГГГ (например, 25.12.2024):",
                reply_markup=ReplyKeyboardRemove()
            )
        
        # Обработчик даты
        @self.dp.message(AppointmentStates.waiting_for_date)
        async def process_date(message: Message, state: FSMContext):
            date_text = message.text.strip()
            
            # ВАЖНО: Проверяем вопрос ПЕРЕД валидацией даты
            # Это должно быть первым делом, чтобы не парсить вопросы как даты
            if self._is_question(date_text):
                await state.clear()  # Очищаем состояние
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                await message.answer(
                    "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                    reply_markup=keyboard
                )
                # Обрабатываем как вопрос
                await self._process_question(message, date_text)
                return  # ВАЖНО: возвращаемся, чтобы не продолжать обработку
            
            # Простая валидация даты (только если это не вопрос)
            try:
                datetime.strptime(date_text, "%d.%m.%Y")
                await state.update_data(date=date_text)
                await state.set_state(AppointmentStates.waiting_for_time)
                await message.answer(
                    "⏰ Отлично! Теперь укажите удобное время (например, 14:00):"
                )
            except ValueError:
                # Если не удалось распарсить как дату, проверяем еще раз, не вопрос ли это
                if self._is_question(date_text):
                    await state.clear()
                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[
                            [KeyboardButton(text="Записаться на замер")],
                            [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                        ],
                        resize_keyboard=True
                    )
                    await message.answer(
                        "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                        reply_markup=keyboard
                    )
                    await self._process_question(message, date_text)
                else:
                    await message.answer(
                        "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2024):"
                    )
        
        # Обработчик времени
        @self.dp.message(AppointmentStates.waiting_for_time)
        async def process_time(message: Message, state: FSMContext):
            time_text = message.text.strip()
            
            # ВАЖНО: Проверяем вопрос ПЕРЕД валидацией времени
            if self._is_question(time_text):
                await state.clear()
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                await message.answer(
                    "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                    reply_markup=keyboard
                )
                await self._process_question(message, time_text)
                return
            
            # Простая валидация времени (только если это не вопрос)
            try:
                datetime.strptime(time_text, "%H:%M")
                await state.update_data(time=time_text)
                await state.set_state(AppointmentStates.waiting_for_address)
                await message.answer(
                    "🏠 Укажите адрес, куда должен приехать замерщик:"
                )
            except ValueError:
                # Если не удалось распарсить как время, проверяем еще раз, не вопрос ли это
                if self._is_question(time_text):
                    await state.clear()
                    keyboard = ReplyKeyboardMarkup(
                        keyboard=[
                            [KeyboardButton(text="Записаться на замер")],
                            [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                        ],
                        resize_keyboard=True
                    )
                    await message.answer(
                        "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                        reply_markup=keyboard
                    )
                    await self._process_question(message, time_text)
                else:
                    await message.answer(
                        "❌ Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:00):"
                    )
        
        # Обработчик адреса
        @self.dp.message(AppointmentStates.waiting_for_address)
        async def process_address(message: Message, state: FSMContext):
            address = message.text.strip()
            
            # Проверяем, не является ли это вопросом
            if self._is_question(address):
                await state.clear()
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                await message.answer(
                    "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                    reply_markup=keyboard
                )
                # Обрабатываем как вопрос
                await self._process_question(message, address)
                return
            
            await state.update_data(address=address)
            await state.set_state(AppointmentStates.waiting_for_phone)
            await message.answer(
                "📞 Укажите ваш контактный телефон:"
            )
        
        # Обработчик телефона
        @self.dp.message(AppointmentStates.waiting_for_phone)
        async def process_phone(message: Message, state: FSMContext):
            phone = message.text.strip()
            
            # Проверяем, не является ли это вопросом
            if self._is_question(phone):
                await state.clear()
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                await message.answer(
                    "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                    reply_markup=keyboard
                )
                # Обрабатываем как вопрос
                await self._process_question(message, phone)
                return
            
            await state.update_data(phone=phone)
            await state.set_state(AppointmentStates.waiting_for_notes)
            await message.answer(
                "💬 Если у вас есть дополнительные пожелания или комментарии, напишите их. "
                "Или отправьте 'нет' или '-' чтобы пропустить:"
            )
        
        # Обработчик комментариев и финальное сохранение
        @self.dp.message(AppointmentStates.waiting_for_notes)
        async def process_notes(message: Message, state: FSMContext):
            notes = message.text.strip()
            
            # Проверяем, не является ли это вопросом (но пропускаем стандартные ответы для пропуска)
            if notes.lower() not in ['нет', '-', 'пропустить', 'skip'] and self._is_question(notes):
                await state.clear()
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                await message.answer(
                    "ℹ️ Запись отменена. Отвечаю на ваш вопрос:",
                    reply_markup=keyboard
                )
                # Обрабатываем как вопрос
                await self._process_question(message, notes)
                return
            
            if notes.lower() in ['нет', '-', 'пропустить', 'skip']:
                notes = None
            
            data = await state.get_data()
            
            # Создаем запись
            appointment = Appointment(
                id=None,
                user_id=message.from_user.id,
                date=data['date'],
                time=data['time'],
                address=data['address'],
                phone=data['phone'],
                notes=notes
            )
            
            # Сохраняем в БД
            if self.db.add_appointment(appointment):
                # Обновляем данные клиента
                client = self.db.get_client(message.from_user.id)
                if client:
                    client.phone = data['phone']
                    client.address = data['address']
                    self.db.add_client(client)
                
                success_text = (
                    "✅ Запись успешно создана!\n\n"
                    f"📅 Дата: {data['date']}\n"
                    f"⏰ Время: {data['time']}\n"
                    f"🏠 Адрес: {data['address']}\n"
                    f"📞 Телефон: {data['phone']}\n"
                )
                if notes:
                    success_text += f"💬 Комментарий: {notes}\n"
                
                success_text += "\nМы свяжемся с вами для подтверждения записи."
                
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Записаться на замер")],
                        [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                    ],
                    resize_keyboard=True
                )
                
                await message.answer(success_text, reply_markup=keyboard)
            else:
                await message.answer(
                    "❌ Произошла ошибка при сохранении записи. Попробуйте еще раз.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[
                            [KeyboardButton(text="Записаться на замер")],
                            [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                        ],
                        resize_keyboard=True
                    )
                )
            
            await state.clear()
        
        # Обработчик команды /my_appointments
        @self.dp.message(Command("my_appointments"))
        @self.dp.message(F.text == "Мои записи")
        async def cmd_my_appointments(message: Message):
            appointments = self.db.get_user_appointments(message.from_user.id)
            
            if not appointments:
                await message.answer("📋 У вас пока нет записей. Используйте /book для создания новой записи.")
                return
            
            text = "📋 Ваши записи:\n\n"
            for i, app in enumerate(appointments, 1):
                text += f"{i}. 📅 {app.date} в {app.time}\n"
                text += f"   🏠 Адрес: {app.address}\n"
                text += f"   📞 Телефон: {app.phone}\n"
                if app.notes:
                    text += f"   💬 {app.notes}\n"
                text += "\n"
            
            await message.answer(text)
        
        # Обработчик команды /ask
        @self.dp.message(Command("ask"))
        @self.dp.message(F.text == "Консультация")
        async def cmd_ask(message: Message):
            await message.answer(
                "💬 Задайте ваш вопрос о пластиковых окнах, и я постараюсь помочь!"
            )
        
        # Обработчик команды /faq
        @self.dp.message(Command("faq"))
        async def cmd_faq(message: Message):
            faq_text = (
                "📋 Часто задаваемые вопросы:\n\n"
                "💰 **О стоимости:**\n"
                "• Цена зависит от размера, профиля и стеклопакета\n"
                "• Минимальная цена от 5000 рублей\n"
                "• Точную стоимость рассчитает замерщик бесплатно\n\n"
                "📅 **О замере:**\n"
                "• Замер производится бесплатно\n"
                "• Используйте /book для записи\n"
                "• Специалист приедет в удобное время\n\n"
                "⏱️ **О сроках:**\n"
                "• Изготовление: 5-7 рабочих дней\n"
                "• Установка: 1-2 дня после изготовления\n\n"
                "🛡️ **О гарантии:**\n"
                "• Гарантия на окна до 5 лет\n"
                "• Гарантия на установку\n\n"
                "🪟 **О выборе окон:**\n"
                "• Работаем с профилями Rehau, KBE, Veka\n"
                "• Подберем оптимальный вариант при замере\n\n"
                "💬 Для сложных вопросов (сравнение, отличия) рекомендую записаться на бесплатный замер - наш специалист даст детальную консультацию!"
            )
            await message.answer(faq_text)
        
        # Обработчик команды /cancel
        @self.dp.message(Command("cancel"))
        async def cmd_cancel(message: Message, state: FSMContext):
            current_state = await state.get_state()
            if current_state is None:
                await message.answer("Нет активных операций для отмены.")
                return
            
            await state.clear()
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Записаться на замер")],
                    [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                ],
                resize_keyboard=True
            )
            await message.answer(
                "❌ Операция отменена.",
                reply_markup=keyboard
            )
        
        # Обработчик текстовых сообщений (консультация)
        # ВАЖНО: Этот обработчик имеет НИЗКИЙ приоритет, так как обработчики состояний FSM срабатывают первыми
        # Поэтому здесь обрабатываются только сообщения БЕЗ активного состояния
        @self.dp.message(F.text)
        async def process_text_message(message: Message, state: FSMContext):
            user = message.from_user
            query = message.text.strip()
            
            # Проверяем, не находимся ли мы в процессе записи
            current_state = await state.get_state()
            if current_state is not None:
                # Если есть активное состояние, НЕ обрабатываем здесь
                # Обработка будет в соответствующих обработчиках состояний
                # Они проверят, является ли это вопросом, и отменят процесс если нужно
                return
            
            # Проверяем, новый ли пользователь (первое сообщение)
            is_new = self.db.is_new_user(user.id)
            if is_new:
                # Регистрируем клиента
                client = Client(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name
                )
                self.db.add_client(client)
                
                # Отправляем приветственное сообщение
                await self.send_welcome_message(message, is_new_user=True)
                # Обновляем активность
                self.db.update_user_activity(user.id)
                return
            
            # Обновляем активность пользователя
            self.db.update_user_activity(user.id)
            
            # Проверяем, является ли вопрос сложным (сравнение, отличие, цена/количество и т.д.)
            if self.db.is_complex_question(query):
                complex_response = (
                    "Этот вопрос сложный, я не могу ответить.\n\n"
                    "Это можно узнать:\n"
                    "• 📋 В разделе /faq с часто задаваемыми вопросами\n"
                    "• 📅 Записавшись на бесплатный замер (/book) - наш специалист даст детальную консультацию и ответит на все вопросы\n"
                    "• 💬 Задав более простой вопрос, на который я смогу ответить"
                )
                await message.answer(complex_response)
                return
            
            # Ищем ответ в базе знаний
            answer = self.db.search_knowledge_base(query)
            
            if answer:
                await message.answer(answer)
            else:
                # Если не нашли ответ, предлагаем варианты
                no_answer_response = (
                    "Извините, я не нашел точный ответ на ваш вопрос в базе знаний.\n\n"
                    "Попробуйте:\n"
                    "• Переформулировать вопрос более просто\n"
                    "• Посмотреть /faq с часто задаваемыми вопросами\n"
                    "• Записаться на бесплатный замер (/book) - наш специалист ответит на все вопросы\n"
                    "• Задать другой вопрос"
                )
                await message.answer(no_answer_response)
    
    async def start(self):
        """Запуск бота"""
        await self.dp.start_polling(self.bot)
    
    def _is_question(self, text: str) -> bool:
        """
        Проверяет, является ли текст вопросом
        """
        text_lower = text.lower().strip()
        
        # Если текст пустой - не вопрос
        if not text_lower:
            return False
        
        # Вопросительные слова и фразы в начале или в тексте
        question_words = [
            "что", "как", "сколько", "когда", "где", "почему", "зачем", 
            "какой", "какая", "какие", "чем", "кто", "откуда", "куда", 
            "отчего", "каков", "какова", "каково",
            "расскажи", "объясни", "подскажи", "помоги", "посоветуй",
            "интересно", "хочу узнать", "можно узнать", "подскажите", 
            "расскажите", "что такое", "что значит", "что умеешь", "что можешь"
        ]
        
        # Проверяем наличие вопросительного знака
        if "?" in text:
            return True
        
        # Проверяем, начинается ли с вопросительного слова
        for word in question_words:
            if text_lower.startswith(word) or text_lower.startswith(f"{word} "):
                return True
        
        # Проверяем, содержит ли текст вопросительные слова (но не в начале)
        for word in question_words:
            if f" {word} " in f" {text_lower} " or text_lower.endswith(f" {word}"):
                # Но только если это не данные формы
                if not self._is_form_data(text):
                    return True
        
        # Если текст содержит вопросительные конструкции
        question_phrases = [
            "можно ли", "можно ли узнать", "можно узнать", 
            "хочу узнать", "хотел бы узнать", "интересует",
            "цена", "стоимость", "сколько стоит"
        ]
        for phrase in question_phrases:
            if phrase in text_lower:
                # Проверяем, не является ли это данными формы
                if not self._is_form_data(text):
                    return True
        
        return False
    
    def _is_form_data(self, text: str) -> bool:
        """
        Проверяет, является ли текст данными для формы (дата, время, телефон, адрес)
        """
        
        # Паттерны для данных формы
        date_pattern = r'\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4}'  # Дата (например, 25.12.2024)
        time_pattern = r'^\d{1,2}:\d{2}$'  # Время (например, 14:00)
        phone_pattern = r'^[\d\s\+\-\(\)]{7,15}$'  # Телефон (7-15 символов, только цифры и спецсимволы)
        
        # Если текст очень короткий и содержит только цифры/спецсимволы - вероятно данные формы
        if len(text) < 30:
            if re.match(phone_pattern, text.replace(" ", "")):
                return True
            if re.search(time_pattern, text):
                return True
            if re.search(date_pattern, text):
                return True
        
        # Если текст содержит только адресные данные (короткий текст с цифрами и буквами)
        if len(text) < 100 and re.search(r'\d+', text) and not any(q in text.lower() for q in ["что", "как", "сколько", "?"]):
            # Проверяем, не является ли это вопросом об адресе
            if not any(word in text.lower() for word in ["где", "какой адрес", "какой адрес"]):
                return True
        
        return False
    
    async def _process_question(self, message: Message, query: str):
        """
        Обрабатывает вопрос пользователя
        """
        user = message.from_user
        
        # Обновляем активность пользователя
        self.db.update_user_activity(user.id)
        
        # Проверяем, является ли вопрос сложным (сравнение, отличие, цена/количество и т.д.)
        if self.db.is_complex_question(query):
            complex_response = (
                "Этот вопрос сложный, я не могу ответить.\n\n"
                "Это можно узнать:\n"
                "• 📋 В разделе /faq с часто задаваемыми вопросами\n"
                "• 📅 Записавшись на бесплатный замер (/book) - наш специалист даст детальную консультацию и ответит на все вопросы\n"
                "• 💬 Задав более простой вопрос, на который я смогу ответить"
            )
            await message.answer(complex_response)
            return
        
        # Ищем ответ в базе знаний
        answer = self.db.search_knowledge_base(query)
        
        if answer:
            await message.answer(answer)
        else:
            # Если не нашли ответ, предлагаем варианты
            no_answer_response = (
                "Извините, я не нашел точный ответ на ваш вопрос в базе знаний.\n\n"
                "Попробуйте:\n"
                "• Переформулировать вопрос более просто\n"
                "• Посмотреть /faq с часто задаваемыми вопросами\n"
                "• Записаться на бесплатный замер (/book) - наш специалист ответит на все вопросы\n"
                "• Задать другой вопрос"
            )
            await message.answer(no_answer_response)
    
    async def stop(self):
        """Остановка бота"""
        await self.bot.session.close()


