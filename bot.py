# bot.py
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from AppointmentManager import AppointmentManager
from Answer import FAQManager

# Загрузка токена из файла
with open("token.txt", "r") as f:
    BOT_TOKEN = f.read().strip()

# Инициализация менеджеров
appointment_manager = AppointmentManager()
faq_manager = FAQManager()

# Список администраторов (замените на реальные ID)
ADMIN_IDS = [924455959] # Пример ID администраторов

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для временного хранения данных о пользователях
user_data: Dict[int, Dict[str, Any]] = {}


# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    registration_complete = State()


# Состояния для записи на услугу
class AppointmentStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_confirmation = State()


# Состояния для добавления услуги (только для администратора)
class AddServiceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_duration = State()
    waiting_for_price = State()
    waiting_for_description = State()


# Состояния для добавления слотов (только для администратора)
class AddSlotsStates(StatesGroup):
    waiting_for_employee = State()
    waiting_for_service = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_interval = State()


# ===== ХЕЛПЕР-ФУНКЦИИ =====

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


def get_main_menu_keyboard(user_id: int = None):
    """Клавиатура главного меню"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📅 Запись на услугу")
    builder.button(text="❓ FAQ")
    builder.button(text="👁 Просмотр записей")
    builder.button(text="📞 Контакты")

    # Добавляем кнопки администратора
    if user_id and is_admin(user_id):
        builder.button(text="⚙️ Админ-панель")

    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_menu_keyboard():
    """Клавиатура админ-панели"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Добавить услугу")
    builder.button(text="⏰ Добавить слоты")
    builder.button(text="👥 Просмотр клиентов")
    builder.button(text="📊 Статистика")
    builder.button(text="🔙 Назад в меню")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_service_keyboard():
    """Клавиатура выбора услуг"""
    services = appointment_manager.get_services()
    builder = InlineKeyboardBuilder()

    for service in services:
        builder.button(
            text=f"{service['name']} - {service['price']} руб.",
            callback_data=f"service_{service['service_id']}"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_employee_keyboard():
    """Клавиатура выбора сотрудника"""
    employees = appointment_manager.get_employees()
    builder = InlineKeyboardBuilder()

    for employee in employees:
        builder.button(
            text=f"{employee['first_name']} {employee['last_name']}",
            callback_data=f"employee_{employee['employee_id']}"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_cancel_keyboard():
    """Клавиатура отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)


def get_yes_no_keyboard():
    """Клавиатура да/нет"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Да")
    builder.button(text="❌ Нет")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# ===== ОБРАБОТЧИКИ КОМАНД =====

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Логируем ID пользователя для отладки
    logger.info(f"Пользователь {user_id} запустил бота")
    logger.info(f"Администраторы: {ADMIN_IDS}")
    logger.info(f"Это администратор? {is_admin(user_id)}")

    # Проверяем, зарегистрирован ли пользователь
    client_info = appointment_manager.get_client(phone=f"tg_{user_id}")

    # Если пользователь администратор, даем доступ к админ-панели даже без регистрации
    if is_admin(user_id):
        await message.answer(
            f"👋 Добро пожаловать, администратор!\n"
            f"Ваш ID: {user_id}\n\n"
            f"Вы можете использовать команду /admin для доступа к админ-панели.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return

    if user_id in user_data:
        await message.answer(
            f"👋 С возвращением, {user_data[user_id].get('first_name', 'друг')}!\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        # Начинаем регистрацию
        await message.answer(
            "👋 Добро пожаловать в сервис записи на услуги!\n"
            "Для начала нужно пройти быструю регистрацию.\n\n"
            "📝 Пожалуйста, введите ваше имя:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationStates.waiting_for_first_name)



@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    await message.answer(
        "⚙️ Административная панель",
        reply_markup=get_admin_menu_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    user_id = message.from_user.id
    help_text = "📋 *Доступные команды:*\n\n"

    if is_admin(user_id):
        help_text += "/admin - Административная панель\n"

    help_text += (
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/menu - Показать главное меню\n"
        "/cancel - Отменить текущее действие\n\n"
        "Вы также можете использовать кнопки меню для навигации."
    )

    await message.answer(help_text)


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    user_id = message.from_user.id
    if user_id in user_data:
        await message.answer(
            "🏠 Главное меню:",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        await message.answer(
            "⚠️ Вы не зарегистрированы. Используйте /start для регистрации."
        )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return

    await state.clear()
    user_id = message.from_user.id

    if user_id in user_data:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        await message.answer(
            "❌ Действие отменено.\n"
            "Используйте /start для регистрации."
        )


# ===== РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ =====

@dp.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка имени"""
    first_name = message.text.strip()

    if len(first_name) < 2:
        await message.answer("❌ Имя слишком короткое. Введите ваше имя:")
        return

    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['first_name'] = first_name

    await state.set_state(RegistrationStates.waiting_for_last_name)
    await message.answer(f"👌 Отлично, {first_name}!\nТеперь введите вашу фамилию:")


@dp.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка фамилии"""
    last_name = message.text.strip()

    if len(last_name) < 2:
        await message.answer("❌ Фамилия слишком короткая. Введите вашу фамилию:")
        return

    user_id = message.from_user.id
    user_data[user_id]['last_name'] = last_name

    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer(
        f"📱 Теперь введите ваш номер телефона:\n"
        f"(Формат: +7XXXXXXXXXX или 8XXXXXXXXXX)"
    )


@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    phone = message.text.strip()

    # Простая валидация номера телефона
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if not (phone.startswith('+7') and len(phone) == 12) and \
            not (phone.startswith('8') and len(phone) == 11) and \
            not (phone.startswith('7') and len(phone) == 11):
        await message.answer(
            "❌ Неверный формат номера.\n"
            "Пожалуйста, введите номер в формате:\n"
            "+7XXXXXXXXXX или 8XXXXXXXXXX"
        )
        return

    # Нормализуем номер телефона
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    elif phone.startswith('7'):
        phone = '+7' + phone[1:]

    user_id = message.from_user.id
    user_data[user_id]['phone'] = phone

    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer(
        "📧 Введите ваш email (необязательно):\n"
        "Если не хотите указывать email, введите 'пропустить'"
    )


@dp.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Обработка email"""
    email_input = message.text.strip().lower()

    user_id = message.from_user.id
    user_data[user_id]['email'] = None if email_input == 'пропустить' else email_input

    # Регистрируем пользователя в базе данных
    try:
        client_id = appointment_manager.add_client(
            first_name=user_data[user_id]['first_name'],
            last_name=user_data[user_id]['last_name'],
            phone=user_data[user_id]['phone'],
            email=user_data[user_id]['email']
        )

        user_data[user_id]['client_id'] = client_id

        await state.clear()

        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 *Ваши данные:*\n"
            f"Имя: {user_data[user_id]['first_name']}\n"
            f"Фамилия: {user_data[user_id]['last_name']}\n"
            f"Телефон: {user_data[user_id]['phone']}\n"
            f"Email: {user_data[user_id]['email'] or 'не указан'}\n\n"
            f"Теперь вы можете записываться на услуги.",
            reply_markup=get_main_menu_keyboard(user_id)
        )

    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        await message.answer(
            "❌ Произошла ошибка при регистрации. Попробуйте еще раз /start"
        )


# ===== ГЛАВНОЕ МЕНЮ =====

@dp.message(F.text == "📅 Запись на услугу")
async def start_appointment(message: Message, state: FSMContext):
    """Начало записи на услугу"""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer(
            "⚠️ Вы не зарегистрированы. Используйте /start для регистрации."
        )
        return

    await state.set_state(AppointmentStates.waiting_for_service)

    services = appointment_manager.get_services()

    if not services:
        await message.answer(
            "❌ В настоящий момент нет доступных услуг.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        await state.clear()
        return

    services_text = "📋 *Доступные услуги:*\n\n"
    for service in services:
        services_text += f"• {service['name']}\n"
        services_text += f"  Категория: {service['category']}\n"
        services_text += f"  Длительность: {service['duration']} мин.\n"
        services_text += f"  Цена: {service['price']} руб.\n"
        if service['description']:
            services_text += f"  Описание: {service['description']}\n"
        services_text += "\n"

    await message.answer(
        services_text + "\nВыберите услугу:",
        reply_markup=get_service_keyboard()
    )


@dp.callback_query(F.data.startswith("service_"))
async def process_service_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги"""
    service_id = int(callback.data.split("_")[1])

    # Получаем информацию об услуге
    services = appointment_manager.get_services()
    selected_service = None
    for service in services:
        if service['service_id'] == service_id:
            selected_service = service
            break

    if not selected_service:
        await callback.message.answer("❌ Услуга не найдена.")
        await state.clear()
        return

    await state.update_data(service_id=service_id)
    await state.update_data(service_name=selected_service['name'])
    await state.update_data(service_price=selected_service['price'])
    await state.update_data(service_duration=selected_service['duration'])

    await state.set_state(AppointmentStates.waiting_for_date)

    # Запрашиваем дату
    await callback.message.answer(
        f"📅 Вы выбрали: *{selected_service['name']}*\n"
        f"💰 Цена: {selected_service['price']} руб.\n"
        f"⏱ Длительность: {selected_service['duration']} мин.\n\n"
        f"Теперь введите дату для записи (в формате ГГГГ-ММ-ДД):\n"
        f"Например: {datetime.now().strftime('%Y-%m-%d')}",
        reply_markup=get_cancel_keyboard()
    )

    await callback.answer()


@dp.message(AppointmentStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты записи"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard(message.from_user.id)
        )
        return

    date_str = message.text.strip()

    try:
        # Проверяем формат даты
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        # Проверяем, что дата не в прошлом
        if date_obj.date() < datetime.now().date():
            await message.answer(
                "❌ Нельзя записаться на прошедшую дату.\n"
                "Введите дату в формате ГГГГ-ММ-ДД:"
            )
            return

        await state.update_data(appointment_date=date_str)
        await state.set_state(AppointmentStates.waiting_for_time)

        data = await state.get_data()
        service_id = data['service_id']

        # Получаем доступные слоты на выбранную дату
        available_slots = appointment_manager.get_available_slots(
            service_id=service_id,
            date=date_str
        )

        if not available_slots:
            await message.answer(
                f"❌ На {date_str} нет свободных окон для записи.\n"
                f"Пожалуйста, выберите другую дату:",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(AppointmentStates.waiting_for_date)
            return

        # Формируем список доступных времен
        times_text = "🕐 *Доступное время:*\n\n"
        time_slots = {}

        for i, slot in enumerate(available_slots, 1):
            start_time = datetime.fromisoformat(slot['start_time']).strftime('%H:%M')
            end_time = datetime.fromisoformat(slot['end_time']).strftime('%H:%M')
            employee_name = f"{slot['first_name']} {slot['last_name']}"

            times_text += f"{i}. {start_time} - {end_time} (мастер: {employee_name})\n"
            time_slots[str(i)] = {
                'slot_id': slot['slot_id'],
                'start_time': start_time,
                'end_time': end_time,
                'employee_id': slot['employee_id'],
                'employee_name': employee_name
            }

        await state.update_data(time_slots=time_slots)

        times_text += "\nВыберите время (введите номер):"

        await message.answer(
            times_text,
            reply_markup=get_cancel_keyboard()
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ГГГГ-ММ-ДД:"
        )


@dp.message(AppointmentStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени записи"""
    user_id = message.from_user.id

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return

    choice = message.text.strip()
    data = await state.get_data()
    time_slots = data.get('time_slots', {})

    if choice not in time_slots:
        await message.answer(
            "❌ Неверный выбор. Пожалуйста, введите номер из списка:"
        )
        return

    selected_slot = time_slots[choice]

    await state.update_data(
        slot_id=selected_slot['slot_id'],
        start_time=selected_slot['start_time'],
        end_time=selected_slot['end_time'],
        employee_id=selected_slot['employee_id'],
        employee_name=selected_slot['employee_name']
    )

    await state.set_state(AppointmentStates.waiting_for_confirmation)

    # Формируем подтверждение
    confirmation_text = (
        "✅ *Подтверждение записи:*\n\n"
        f"📋 Услуга: {data['service_name']}\n"
        f"💰 Цена: {data['service_price']} руб.\n"
        f"⏱ Длительность: {data['service_duration']} мин.\n"
        f"📅 Дата: {data['appointment_date']}\n"
        f"🕐 Время: {selected_slot['start_time']} - {selected_slot['end_time']}\n"
        f"👨‍🔧 Мастер: {selected_slot['employee_name']}\n\n"
        f"Для подтверждения введите 'да', для отмены - 'нет'"
    )

    await message.answer(
        confirmation_text,
        reply_markup=get_cancel_keyboard()
    )


@dp.message(AppointmentStates.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения записи"""
    user_id = message.from_user.id

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return

    confirmation = message.text.strip().lower()

    if confirmation not in ['да', 'нет']:
        await message.answer(
            "❌ Пожалуйста, введите 'да' для подтверждения или 'нет' для отмены:"
        )
        return

    if confirmation == 'нет':
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return

    # Создаем запись
    data = await state.get_data()

    if user_id not in user_data:
        await message.answer(
            "❌ Ошибка: данные пользователя не найдены.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        await state.clear()
        return

    try:
        appointment_id = appointment_manager.create_appointment(
            client_id=user_data[user_id]['client_id'],
            slot_id=data['slot_id']
        )

        # Получаем детали записи
        appointment = appointment_manager.get_appointment(appointment_id)

        await message.answer(
            f"🎉 *Запись успешно создана!*\n\n"
            f"📋 Номер записи: #{appointment_id}\n"
            f"📅 Дата: {data['appointment_date']}\n"
            f"🕐 Время: {data['start_time']} - {data['end_time']}\n"
            f"👨‍🔧 Мастер: {data['employee_name']}\n"
            f"💵 Сумма к оплате: {data['service_price']} руб.\n\n"
            f"Мы ждем вас в назначенное время!",
            reply_markup=get_main_menu_keyboard(user_id)
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        await message.answer(
            f"❌ Произошла ошибка при создании записи: {str(e)}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        await state.clear()


@dp.message(F.text == "❓ FAQ")
async def show_faq(message: Message):
    """Показать FAQ"""
    faq_text = faq_manager.get_faq_list()

    # Разбиваем на части, если текст слишком длинный
    if len(faq_text) > 4000:
        parts = [faq_text[i:i + 4000] for i in range(0, len(faq_text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(faq_text)


@dp.message(F.text == "👁 Просмотр записей")
async def show_appointments(message: Message):
    """Показать текущие записи пользователя"""
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer(
            "⚠️ Вы не зарегистрированы. Используйте /start для регистрации."
        )
        return

    client_id = user_data[user_id]['client_id']
    appointments = appointment_manager.get_client_appointments(
        client_id=client_id,
        upcoming_only=True
    )

    if not appointments:
        await message.answer(
            "📭 У вас нет предстоящих записей.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return

    appointments_text = "📅 *Ваши предстоящие записи:*\n\n"

    for i, appointment in enumerate(appointments, 1):
        status_emojis = {
            'scheduled': '📅',
            'confirmed': '✅',
            'cancelled': '❌',
            'completed': '✓',
            'no_show': '⏰'
        }

        status_emoji = status_emojis.get(appointment['status'], '📅')

        appointments_text += (
            f"{status_emoji} *Запись #{appointment['appointment_id']}*\n"
            f"📋 Услуга: {appointment['service_name']}\n"
            f"📅 Дата: {appointment['appointment_date']}\n"
            f"🕐 Время: {appointment['start_time']} - {appointment['end_time']}\n"
            f"👨‍🔧 Мастер: {appointment['employee_first_name']} {appointment['employee_last_name']}\n"
            f"💰 Сумма: {appointment['price']} руб.\n"
            f"📊 Статус: {appointment['status']}\n"
        )

        if appointment['notes']:
            appointments_text += f"📝 Примечание: {appointment['notes']}\n"

        appointments_text += "\n"

    await message.answer(
        appointments_text,
        reply_markup=get_main_menu_keyboard(user_id)
    )


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    """Показать контакты"""
    contacts_text = (
        "📞 *Наши контакты:*\n\n"
        "🏢 Адрес: ул. Примерная, д. 123\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: info@example.com\n"
        "🌐 Сайт: www.example.com\n\n"
        "🕐 *График работы:*\n"
        "Пн-Пт: 9:00 - 20:00\n"
        "Сб: 10:00 - 18:00\n"
        "Вс: 10:00 - 16:00\n\n"
        "Мы всегда рады помочь!"
    )

    await message.answer(contacts_text)


# ===== АДМИН-ПАНЕЛЬ =====

@dp.message(F.text == "⚙️ Админ-панель")
async def show_admin_panel(message: Message):
    """Показать админ-панель"""
    user_id = message.from_user.id

    logger.info(f"Пользователь {user_id} пытается открыть админ-панель")
    logger.info(f"Это администратор? {is_admin(user_id)}")

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    await message.answer(
        "⚙️ *Административная панель*\n\n"
        "Доступные действия:",
        reply_markup=get_admin_menu_keyboard()
    )


# В функции process_email в bot.py добавьте:

@dp.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Обработка email"""
    email_input = message.text.strip().lower()

    user_id = message.from_user.id
    user_data[user_id]['email'] = None if email_input == 'пропустить' else email_input

    # Регистрируем пользователя в базе данных
    try:
        # Для обычных пользователей используем их телефон, для администраторов - tg_id
        if is_admin(user_id):
            client_id = appointment_manager.add_client_with_tg_id(
                first_name=user_data[user_id]['first_name'],
                last_name=user_data[user_id]['last_name'],
                tg_id=user_id,
                email=user_data[user_id]['email']
            )
        else:
            client_id = appointment_manager.add_client(
                first_name=user_data[user_id]['first_name'],
                last_name=user_data[user_id]['last_name'],
                phone=user_data[user_id]['phone'],
                email=user_data[user_id]['email']
            )

        user_data[user_id]['client_id'] = client_id

        await state.clear()

        welcome_text = f"✅ Регистрация завершена!\n\n" \
                       f"👤 *Ваши данные:*\n" \
                       f"Имя: {user_data[user_id]['first_name']}\n" \
                       f"Фамилия: {user_data[user_id]['last_name']}\n"

        if is_admin(user_id):
            welcome_text += f"👑 Статус: Администратор\n"
        else:
            welcome_text += f"📱 Телефон: {user_data[user_id]['phone']}\n"

        welcome_text += f"📧 Email: {user_data[user_id]['email'] or 'не указан'}\n\n" \
                        f"Теперь вы можете записываться на услуги."

        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(user_id)
        )

    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        await message.answer(
            f"❌ Произошла ошибка при регистрации: {str(e)}\n"
            f"Попробуйте еще раз /start"
        )




@dp.message(F.text == "➕ Добавить услугу")
async def start_add_service(message: Message, state: FSMContext):
    """Начало добавления услуги"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    await state.set_state(AddServiceStates.waiting_for_name)
    await message.answer(
        "➕ *Добавление новой услуги*\n\n"
        "Введите название услуги:",
        reply_markup=get_cancel_keyboard()
    )


@dp.message(AddServiceStates.waiting_for_name)
async def process_service_name(message: Message, state: FSMContext):
    """Обработка названия услуги"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление услуги отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    await state.update_data(name=message.text.strip())
    await state.set_state(AddServiceStates.waiting_for_category)
    await message.answer(
        "Введите категорию услуги:\n"
        "(например: 'Окна', 'Двери', 'Ремонт')"
    )


@dp.message(AddServiceStates.waiting_for_category)
async def process_service_category(message: Message, state: FSMContext):
    """Обработка категории услуги"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление услуги отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    await state.update_data(category=message.text.strip())
    await state.set_state(AddServiceStates.waiting_for_duration)
    await message.answer(
        "Введите продолжительность услуги в минутах:\n"
        "(например: 60 для 1 часа, 90 для 1.5 часов)"
    )


@dp.message(AddServiceStates.waiting_for_duration)
async def process_service_duration(message: Message, state: FSMContext):
    """Обработка продолжительности услуги"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление услуги отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите положительное целое число (в минутах):"
        )
        return

    await state.update_data(duration=duration)
    await state.set_state(AddServiceStates.waiting_for_price)
    await message.answer("Введите цену услуги (в рублях):")


@dp.message(AddServiceStates.waiting_for_price)
async def process_service_price(message: Message, state: FSMContext):
    """Обработка цены услуги"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление услуги отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите положительное число (например: 1500.50):"
        )
        return

    await state.update_data(price=price)
    await state.set_state(AddServiceStates.waiting_for_description)
    await message.answer(
        "Введите описание услуги (необязательно):\n"
        "Для пропуска введите 'пропустить'"
    )


@dp.message(AddServiceStates.waiting_for_description)
async def process_service_description(message: Message, state: FSMContext):
    """Обработка описания услуги"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление услуги отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    description = None if message.text.strip().lower() == 'пропустить' else message.text.strip()

    data = await state.get_data()

    try:
        service_id = appointment_manager.add_service(
            name=data['name'],
            category=data['category'],
            duration=data['duration'],
            price=data['price'],
            description=description
        )

        await message.answer(
            f"✅ Услуга успешно добавлена!\n\n"
            f"📋 Название: {data['name']}\n"
            f"📁 Категория: {data['category']}\n"
            f"⏱ Длительность: {data['duration']} мин.\n"
            f"💰 Цена: {data['price']} руб.\n"
            f"📝 Описание: {description or 'нет'}\n"
            f"🆔 ID услуги: {service_id}",
            reply_markup=get_admin_menu_keyboard()
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при добавлении услуги: {e}")
        await message.answer(
            f"❌ Ошибка при добавлении услуги: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()


@dp.message(F.text == "⏰ Добавить слоты")
async def start_add_slots(message: Message, state: FSMContext):
    """Начало добавления слотов"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    await state.set_state(AddSlotsStates.waiting_for_employee)
    await message.answer(
        "⏰ *Добавление рабочих слотов*\n\n"
        "Выберите сотрудника:",
        reply_markup=get_employee_keyboard()
    )


@dp.callback_query(F.data.startswith("employee_"), AddSlotsStates.waiting_for_employee)
async def process_employee_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора сотрудника для добавления слотов"""
    employee_id = int(callback.data.split("_")[1])

    # Получаем информацию о сотруднике
    employees = appointment_manager.get_employees()
    selected_employee = None
    for employee in employees:
        if employee['employee_id'] == employee_id:
            selected_employee = employee
            break

    if not selected_employee:
        await callback.message.answer("❌ Сотрудник не найден.")
        await state.clear()
        return

    await state.update_data(employee_id=employee_id)
    await state.update_data(employee_name=f"{selected_employee['first_name']} {selected_employee['last_name']}")
    await state.set_state(AddSlotsStates.waiting_for_service)

    await callback.message.answer(
        f"👨‍🔧 Выбран сотрудник: {selected_employee['first_name']} {selected_employee['last_name']}\n\n"
        f"Теперь выберите услугу:",
        reply_markup=get_service_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("service_"), AddSlotsStates.waiting_for_service)
async def process_service_for_slots(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги для добавления слотов"""
    service_id = int(callback.data.split("_")[1])

    # Получаем информацию об услуге
    services = appointment_manager.get_services()
    selected_service = None
    for service in services:
        if service['service_id'] == service_id:
            selected_service = service
            break

    if not selected_service:
        await callback.message.answer("❌ Услуга не найдена.")
        await state.clear()
        return

    await state.update_data(service_id=service_id)
    await state.update_data(service_name=selected_service['name'])
    await state.update_data(service_duration=selected_service['duration'])
    await state.set_state(AddSlotsStates.waiting_for_start_date)

    await callback.message.answer(
        f"📋 Выбрана услуга: {selected_service['name']}\n"
        f"⏱ Длительность: {selected_service['duration']} мин.\n\n"
        f"Введите дату начала слотов (в формате ГГГГ-ММ-ДД):\n"
        f"Например: {datetime.now().strftime('%Y-%m-%d')}",
        reply_markup=get_cancel_keyboard()
    )

    await callback.answer()


@dp.message(AddSlotsStates.waiting_for_start_date)
async def process_start_date(message: Message, state: FSMContext):
    """Обработка даты начала слотов"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    start_date_str = message.text.strip()

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        # Проверяем, что дата не в прошлом
        if start_date.date() < datetime.now().date():
            await message.answer(
                "❌ Дата начала не может быть в прошлом.\n"
                "Введите дату в формате ГГГГ-ММ-ДД:"
            )
            return

        await state.update_data(start_date=start_date_str)
        await state.set_state(AddSlotsStates.waiting_for_end_date)

        # Предлагаем дату окончания (по умолчанию +7 дней)
        default_end_date = (start_date + timedelta(days=7)).strftime('%Y-%m-%d')

        await message.answer(
            f"Введите дату окончания слотов (в формате ГГГГ-ММ-ДД):\n"
            f"Рекомендуем: {default_end_date}\n"
            f"Можно ввести ту же дату для создания слотов на один день."
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ГГГГ-ММ-ДД:"
        )


@dp.message(AddSlotsStates.waiting_for_end_date)
async def process_end_date(message: Message, state: FSMContext):
    """Обработка даты окончания слотов"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    end_date_str = message.text.strip()

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        data = await state.get_data()
        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d")

        if end_date.date() < start_date.date():
            await message.answer(
                "❌ Дата окончания не может быть раньше даты начала.\n"
                "Введите дату в формате ГГГГ-ММ-ДД:"
            )
            return

        await state.update_data(end_date=end_date_str)
        await state.set_state(AddSlotsStates.waiting_for_start_time)

        await message.answer(
            "Введите время начала рабочего дня (в формате ЧЧ:ММ):\n"
            "Например: 09:00"
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ГГГГ-ММ-ДД:"
        )


@dp.message(AddSlotsStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    """Обработка времени начала рабочего дня"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    start_time_str = message.text.strip()

    try:
        # Проверяем формат времени
        datetime.strptime(start_time_str, "%H:%M")
        await state.update_data(start_time=start_time_str)
        await state.set_state(AddSlotsStates.waiting_for_end_time)

        await message.answer(
            "Введите время окончания рабочего дня (в формате ЧЧ:ММ):\n"
            "Например: 18:00"
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Введите время в формате ЧЧ:ММ:"
        )


@dp.message(AddSlotsStates.waiting_for_end_time)
async def process_end_time(message: Message, state: FSMContext):
    """Обработка времени окончания рабочего дня"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    end_time_str = message.text.strip()

    try:
        # Проверяем формат времени
        datetime.strptime(end_time_str, "%H:%M")

        data = await state.get_data()
        start_time = datetime.strptime(data['start_time'], "%H:%M")
        end_time = datetime.strptime(end_time_str, "%H:%M")

        if end_time <= start_time:
            await message.answer(
                "❌ Время окончания должно быть позже времени начала.\n"
                "Введите время в формате ЧЧ:ММ:"
            )
            return

        await state.update_data(end_time=end_time_str)
        await state.set_state(AddSlotsStates.waiting_for_interval)

        # Получаем длительность услуги
        service_duration = data['service_duration']

        await message.answer(
            f"⏱ Длительность услуги: {service_duration} минут\n\n"
            f"Введите интервал между слотами (в минутах):\n"
            f"Рекомендуем: {service_duration} (без перерывов) или {service_duration + 15} (с перерывом 15 минут)\n"
            f"Например: {service_duration}"
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Введите время в формате ЧЧ:ММ:"
        )


@dp.message(AddSlotsStates.waiting_for_interval)
async def process_interval(message: Message, state: FSMContext):
    """Обработка интервала между слотами"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    interval_str = message.text.strip()

    try:
        interval = int(interval_str)
        if interval <= 0:
            raise ValueError

        data = await state.get_data()
        service_duration = data['service_duration']

        if interval < service_duration:
            await message.answer(
                f"❌ Интервал ({interval} мин.) меньше длительности услуги ({service_duration} мин.).\n"
                f"Это приведет к наложению слотов.\n"
                f"Введите интервал не менее {service_duration} минут:"
            )
            return

        await state.update_data(interval=interval)

        # Показываем сводку
        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(data['end_date'], "%Y-%m-%d")
        days_count = (end_date.date() - start_date.date()).days + 1

        summary_text = (
            "📋 *Сводка по добавляемым слотам:*\n\n"
            f"👨‍🔧 Сотрудник: {data['employee_name']}\n"
            f"📋 Услуга: {data['service_name']}\n"
            f"⏱ Длительность услуги: {service_duration} мин.\n"
            f"📅 Период: с {data['start_date']} по {data['end_date']} ({days_count} дней)\n"
            f"🕐 Время работы: {data['start_time']} - {data['end_time']}\n"
            f"⏰ Интервал: {interval} мин.\n\n"
            f"Подтвердить создание слотов?"
        )

        await message.answer(
            summary_text,
            reply_markup=get_yes_no_keyboard()
        )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите положительное целое число (в минутах):"
        )


@dp.message(F.text.in_(["✅ Да", "❌ Нет"]), AddSlotsStates.waiting_for_interval)
async def process_slots_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения создания слотов"""
    if message.text == "❌ Нет":
        await state.clear()
        await message.answer(
            "❌ Добавление слотов отменено.",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    data = await state.get_data()

    try:
        # Создаем слоты для каждого дня
        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(data['end_date'], "%Y-%m-%d")

        total_slots_created = 0
        days_with_slots = 0

        current_date = start_date
        while current_date <= end_date:
            # Формируем datetime строки
            start_datetime = f"{current_date.strftime('%Y-%m-%d')} {data['start_time']}"
            end_datetime = f"{current_date.strftime('%Y-%m-%d')} {data['end_time']}"

            # Создаем слоты на текущий день
            slot_ids = appointment_manager.create_time_slots(
                employee_id=data['employee_id'],
                service_id=data['service_id'],
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                interval_minutes=data['interval']
            )

            if slot_ids:
                total_slots_created += len(slot_ids)
                days_with_slots += 1

            current_date += timedelta(days=1)

        await message.answer(
            f"✅ Слоты успешно созданы!\n\n"
            f"📊 *Результат:*\n"
            f"• Дней обработано: {(end_date.date() - start_date.date()).days + 1}\n"
            f"• Дней со слотами: {days_with_slots}\n"
            f"• Всего создано слотов: {total_slots_created}\n\n"
            f"Слоты доступны для записи клиентов.",
            reply_markup=get_admin_menu_keyboard()
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании слотов: {e}")
        await message.answer(
            f"❌ Ошибка при создании слотов: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()


@dp.message(F.text == "👥 Просмотр клиентов")
async def show_clients(message: Message):
    """Показать список клиентов"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    try:
        clients = appointment_manager.search_clients(limit=50)

        if not clients:
            await message.answer(
                "📭 В базе данных нет клиентов.",
                reply_markup=get_admin_menu_keyboard()
            )
            return

        clients_text = "👥 *Список клиентов:*\n\n"

        for i, client in enumerate(clients, 1):
            clients_text += (
                f"{i}. {client['last_name']} {client['first_name']}\n"
                f"   📱 {client['phone']}\n"
                f"   📧 {client['email'] or 'нет'}\n"
                f"   🆔 ID: {client['client_id']}\n"
            )

            if i % 10 == 0 and i < len(clients):
                clients_text += f"\n... и еще {len(clients) - i} клиентов\n"
                break

            if i < len(clients):
                clients_text += "\n"

        await message.answer(
            clients_text,
            reply_markup=get_admin_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при получении клиентов: {e}")
        await message.answer(
            f"❌ Ошибка при получении списка клиентов: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )


@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать статистику"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    try:
        # Получаем статистику за сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        daily_summary = appointment_manager.get_daily_summary(date=today)

        # Получаем общее количество клиентов
        clients = appointment_manager.search_clients(limit=1000)
        total_clients = len(clients)

        # Получаем сегодняшние записи
        daily_appointments = appointment_manager.get_daily_appointments(date=today)

        statistics_text = (
            f"📊 *Статистика за {today}:*\n\n"
            f"👥 Всего клиентов: {total_clients}\n"
            f"📅 Записей сегодня: {daily_summary.get('total_appointments', 0)}\n"
            f"✅ Завершено: {daily_summary.get('completed', 0)}\n"
            f"❌ Отменено: {daily_summary.get('cancelled', 0)}\n"
            f"⏰ Неявок: {daily_summary.get('no_show', 0)}\n"
            f"💰 Выручка: {daily_summary.get('total_revenue', 0) or 0} руб.\n"
            f"💳 Предоплата: {daily_summary.get('total_prepayment', 0) or 0} руб.\n"
        )

        # Добавляем информацию о сегодняшних записях
        if daily_appointments:
            statistics_text += f"\n📅 *Записи на сегодня ({len(daily_appointments)}):*\n"

            for i, appointment in enumerate(daily_appointments[:5], 1):  # Показываем первые 5
                time_str = appointment['start_time'][:5]
                client_name = f"{appointment['client_first_name']} {appointment['client_last_name']}"
                service_name = appointment['service_name']
                employee_name = f"{appointment['employee_first_name']} {appointment['employee_last_name']}"

                statistics_text += f"{i}. {time_str} - {client_name} ({service_name}, {employee_name})\n"

            if len(daily_appointments) > 5:
                statistics_text += f"... и еще {len(daily_appointments) - 5} записей\n"

        await message.answer(
            statistics_text,
            reply_markup=get_admin_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer(
            f"❌ Ошибка при получении статистики: {str(e)}",
            reply_markup=get_admin_menu_keyboard()
        )


@dp.message(F.text == "🔙 Назад в меню")
async def back_to_main_menu(message: Message):
    """Вернуться в главное меню"""
    user_id = message.from_user.id
    await message.answer(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard(user_id)
    )


# ===== ЗАПУСК БОТА =====

async def main():
    """Основная функция запуска бота"""
    logger.info("Бот запускается...")

    # Удаляем вебхук (если был)
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        # Закрываем соединение с базой данных
        appointment_manager.close()