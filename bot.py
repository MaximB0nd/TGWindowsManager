import telebot
from telebot import types

# Получи токен у @BotFather
def read_token(file_path='token.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            token = file.read().strip()  # .strip() убирает пробелы и переносы строк
            if not token:
                raise ValueError("Файл token.txt пустой!")
            return token
    except FileNotFoundError:
        print(f"Ошибка: Файл {file_path} не найден!")
        print("Создайте файл token.txt и запишите в него токен бота")
        exit(1)
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        exit(1)

# Создаем бота
bot = telebot.TeleBot(read_token())

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_message(message):
    # Отправка простого сообщения
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}!\n"
        "Я работающий бот на telebot!\n"
        "Команды:\n"
        "/start - начать\n"
        "/help - помощь\n"
        "/menu - меню\n"
        "/photo - получить фото"
    )


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, "Помощь: я просто отвечаю на сообщения")


@bot.message_handler(commands=['menu'])
def show_menu(message):
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    btn1 = types.KeyboardButton("📋 Кнопка 1")
    btn2 = types.KeyboardButton("📷 Кнопка 2")
    btn3 = types.KeyboardButton("ℹ️ Информация")

    markup.add(btn1, btn2, btn3)

    bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=markup
    )


@bot.message_handler(commands=['photo'])
def send_photo(message):
    # Отправка фото из интернета
    bot.send_photo(
        message.chat.id,
        "https://picsum.photos/400/300",  # случайное фото
        caption="Вот случайное фото!"
    )


# ========== ТЕКСТОВЫЕ СООБЩЕНИЯ ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.lower()

    # Простые ответы на текст
    responses = {
        "привет": "И тебе привет! 😊",
        "как дела": "Отлично, как у тебя?",
        "пока": "До свидания! 👋",
        "меню": "Используй /menu для меню",
    }

    # Проверяем, есть ли ответ
    for key in responses:
        if key in text:
            bot.send_message(chat_id, responses[key])
            return

    # Если не нашли совпадение - эхо
    if message.text.startswith("/"):
        bot.send_message(chat_id, "Неизвестная команда")
    else:
        bot.send_message(chat_id, f"Вы написали: {message.text}")


# ========== РАБОТА С КНОПКАМИ ==========
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "📋 Кнопка 1":
        # Inline-кнопки
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Сайт", url="https://google.com")
        btn2 = types.InlineKeyboardButton("Нажми меня", callback_data="test")
        markup.add(btn1, btn2)

        bot.send_message(
            message.chat.id,
            "Выбрана кнопка 1!\nДоступные действия:",
            reply_markup=markup
        )

    elif message.text == "📷 Кнопка 2":
        # Отправка документа
        with open('bot.py', 'rb') as file:
            bot.send_document(
                message.chat.id,
                file,
                caption="Вот исходный код бота!"
            )

    elif message.text == "ℹ️ Информация":
        user_info = f"""
        📊 Информация о вас:
        ID: {message.from_user.id}
        Имя: {message.from_user.first_name}
        Фамилия: {message.from_user.last_name or 'не указана'}
        Username: @{message.from_user.username or 'не указан'}
        """
        bot.send_message(message.chat.id, user_info)


# ========== ОБРАБОТКА INLINE-КНОПОК ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "test":
        # Ответ на callback (уведомление)
        bot.answer_callback_query(
            call.id,
            "Вы нажали на кнопку!",
            show_alert=False
        )
        # Редактируем сообщение
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы нажали на кнопку! ✅"
        )


# ========== ОБРАБОТКА ДРУГИХ ТИПОВ СООБЩЕНИЙ ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(
        message.chat.id,
        "Классное фото! Я его сохранил (нет)"
    )


@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    bot.send_sticker(
        message.chat.id,
        "CAACAgIAAxkBAAIB..."  # ID стикера
    )


# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("Бот запущен...")

    # Опционально: удалить webhook
    bot.remove_webhook()

    # Бесконечный опрос сервера
    bot.infinity_polling()