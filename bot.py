"""
Логика бота для записи на замер окон
"""
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
                "Я ваш умный помощник от компании ОкнаПрофи!\n\n"
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
            
            # Простая валидация даты
            try:
                datetime.strptime(date_text, "%d.%m.%Y")
                await state.update_data(date=date_text)
                await state.set_state(AppointmentStates.waiting_for_time)
                await message.answer(
                    "⏰ Отлично! Теперь укажите удобное время (например, 14:00):"
                )
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2024):"
                )
        
        # Обработчик времени
        @self.dp.message(AppointmentStates.waiting_for_time)
        async def process_time(message: Message, state: FSMContext):
            time_text = message.text.strip()
            
            # Простая валидация времени
            try:
                datetime.strptime(time_text, "%H:%M")
                await state.update_data(time=time_text)
                await state.set_state(AppointmentStates.waiting_for_address)
                await message.answer(
                    "🏠 Укажите адрес, куда должен приехать замерщик:"
                )
            except ValueError:
                await message.answer(
                    "❌ Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:00):"
                )
        
        # Обработчик адреса
        @self.dp.message(AppointmentStates.waiting_for_address)
        async def process_address(message: Message, state: FSMContext):
            address = message.text.strip()
            await state.update_data(address=address)
            await state.set_state(AppointmentStates.waiting_for_phone)
            await message.answer(
                "📞 Укажите ваш контактный телефон:"
            )
        
        # Обработчик телефона
        @self.dp.message(AppointmentStates.waiting_for_phone)
        async def process_phone(message: Message, state: FSMContext):
            phone = message.text.strip()
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
        @self.dp.message(F.text)
        async def process_text_message(message: Message, state: FSMContext):
            user = message.from_user
            
            # Проверяем, не находимся ли мы в процессе записи
            current_state = await state.get_state()
            if current_state is not None:
                # Если есть активное состояние, не обрабатываем как вопрос
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
            
            # Ищем ответ в базе знаний
            query = message.text
            answer = self.db.search_knowledge_base(query)
            
            if answer:
                await message.answer(answer)
            else:
                await message.answer(
                    "Извините, я не нашел ответ на ваш вопрос в базе знаний.\n\n"
                    "Вы можете:\n"
                    "• Записаться на бесплатный замер (/book) - наш специалист ответит на все вопросы\n"
                    "• Задать другой вопрос"
                )
    
    async def start(self):
        """Запуск бота"""
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Остановка бота"""
        await self.bot.session.close()


