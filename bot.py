"""
Логика бота для записи на замер окон
"""
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
from database import Database
from models import Client, Appointment
from datetime import datetime
import json


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

            welcome_text = (
                f"Здравствуйте, {user.first_name or 'клиент'}! 👋\n\n"
                "Я бот для записи на замер пластиковых окон.\n\n"
                "Что я умею:\n"
                "• Консультировать по услугам (/ask)\n"
                "• Записать вас на замер (/book)\n"
                "• Показать ваши записи (/my_appointments)\n\n"
                "Выберите действие или просто задайте вопрос!"
            )

            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Записаться на замер")],
                    [KeyboardButton(text="Мои записи"), KeyboardButton(text="Консультация")]
                ],
                resize_keyboard=True
            )

            await message.answer(welcome_text, reply_markup=keyboard)

        # Обработчик команды /help
        @self.dp.message(Command("help"))
        async def cmd_help(message: Message):
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

        # Обработчик для запуска записи с календарем (единственный!)
        @self.dp.message(Command("book"))
        @self.dp.message(F.text == "Записаться на замер")
        async def cmd_book_with_calendar(message: Message, state: FSMContext):
            web_app_button = KeyboardButton(
                text="Выбрать дату в календаре",
                web_app=WebAppInfo(url="https://hopixer.github.io/glass-install-calendar/")
            )

            keyboard = ReplyKeyboardMarkup(
                keyboard=[[web_app_button]],
                resize_keyboard=True,
                one_time_keyboard=True
            )

            await message.answer(
                "Отлично! Давайте запишем вас на бесплатный замер.\n\n"
                "Нажмите кнопку ниже, чтобы выбрать удобную дату в календаре:\n\n"
                "Или введите дату вручную в формате ДД.ММ.ГГГГ",
                reply_markup=keyboard
            )
            await state.set_state(AppointmentStates.waiting_for_date)

        # Обработчик данных из Web App (FullCalendar)
        @self.dp.message(F.web_app_data)
        async def handle_web_app_date(message: Message, state: FSMContext):
            print("!!! ПОЛУЧЕНЫ ДАННЫЕ ИЗ WEB APP !!!")
            print("Raw data:", message.web_app_data.data)

            try:
                data = json.loads(message.web_app_data.data)
                selected_date_iso = data.get("date")
                print("Распарсенная дата:", selected_date_iso)
            except Exception as e:
                print("Ошибка обработки web_app_data:", str(e))
                await message.answer("Ошибка получения даты из календаря. Попробуйте ещё раз.")
                return

            if not selected_date_iso:
                await message.answer("Дата не передана из календаря.")
                return

            try:
                dt = datetime.strptime(selected_date_iso, "%Y-%m-%d")
                date_str = dt.strftime("%d.%m.%Y")
            except ValueError:
                await message.answer("Неверный формат даты из календаря.")
                return

            await state.update_data(date=date_str)
            await state.set_state(AppointmentStates.waiting_for_time)

            await message.answer(
                f"✅ Дата выбрана: <b>{date_str}</b>\n\n"
                "Теперь укажите удобное время (например, 14:00):",
                reply_markup=ReplyKeyboardRemove()
            )

        # Обработчик даты (ручной ввод)
        @self.dp.message(AppointmentStates.waiting_for_date)
        async def process_date(message: Message, state: FSMContext):
            date_text = message.text.strip()

            try:
                datetime.strptime(date_text, "%d.%m.%Y")
                await state.update_data(date=date_text)
                await state.set_state(AppointmentStates.waiting_for_time)
                await message.answer(
                    "⏰ Отлично! Теперь укажите удобное время (например, 14:00):",
                    reply_markup=ReplyKeyboardRemove()
                )
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2024):"
                )

        # Обработчик времени
        @self.dp.message(AppointmentStates.waiting_for_time)
        async def process_time(message: Message, state: FSMContext):
            time_text = message.text.strip()

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

            appointment = Appointment(
                id=None,
                user_id=message.from_user.id,
                date=data['date'],
                time=data['time'],
                address=data['address'],
                phone=data['phone'],
                notes=notes
            )

            if self.db.add_appointment(appointment):
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
            current_state = await state.get_state()
            if current_state is not None:
                return

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