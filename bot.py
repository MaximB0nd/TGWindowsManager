# bot.py
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

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


# ===== ХЕЛПЕР-ФУНКЦИИ =====

def get_main_menu_keyboard():
    """Клавиатура главного меню"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📅 Запись на услугу")
    builder.button(text="❓ FAQ")
    builder.button(text="👁 Просмотр записей")
    builder.button(text="📞 Контакты")
    builder.adjust(2, 2)
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


def get_cancel_keyboard():
    """Клавиатура отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)


# ===== ОБРАБОТЧИКИ КОМАНД =====

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Проверяем, зарегистрирован ли пользователь
    # Для демонстрации проверяем по user_id
    # В реальном приложении нужно проверять в базе данных
    if user_id in user_data:
        await message.answer(
            f"👋 С возвращением, {user_data[user_id].get('first_name', 'друг')}!\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
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


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📋 *Доступные команды:*\n\n"
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
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
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

        await state.set_state(RegistrationStates.registration_complete)
        await state.clear()

        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 *Ваши данные:*\n"
            f"Имя: {user_data[user_id]['first_name']}\n"
            f"Фамилия: {user_data[user_id]['last_name']}\n"
            f"Телефон: {user_data[user_id]['phone']}\n"
            f"Email: {user_data[user_id]['email'] or 'не указан'}\n\n"
            f"Теперь вы можете записываться на услуги.",
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
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
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard()
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
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена.",
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Создаем запись
    data = await state.get_data()
    user_id = message.from_user.id

    if user_id not in user_data:
        await message.answer(
            "❌ Ошибка: данные пользователя не найдены.",
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        await message.answer(
            f"❌ Произошла ошибка при создании записи: {str(e)}",
            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard()
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
        reply_markup=get_main_menu_keyboard()
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