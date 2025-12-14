# bot.py
import telebot
from telebot import types
from Answer import FAQManager

def read_token(file_path='token.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            token = file.read().strip()
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

# Создаем менеджер FAQ
faq_manager = FAQManager('faq_database.db')

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn1 = types.KeyboardButton("📋 Показать FAQ")
    btn2 = types.KeyboardButton("❓ Поиск в FAQ")
    btn3 = types.KeyboardButton("ℹ️ Информация")
    
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}!\n"
        "Добро пожаловать в бот компании *Народные Окна*!\n\n"
        "Я помогу вам найти ответы на частые вопросы об окнах.",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def help_message(message):
    help_text = (
        "📋 *Помощь по боту*\n\n"
        "Основные команды:\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/faq - Показать все вопросы\n"
        "/faq1 - Показать вопрос №1\n"
        "/faq2 - Показать вопрос №2 и т.д.\n"
        "/search - Поиск в FAQ\n\n"
        "Используйте кнопки меню для удобства!"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['faq'])
def show_all_faq(message):
    try:
        faq_text = faq_manager.get_faq_list()
        
        # Если текст слишком длинный, разбиваем на части
        if len(faq_text) > 4000:
            # Отправляем короткую версию
            bot.send_message(message.chat.id, 
                           faq_manager.get_faq_list_short(), 
                           parse_mode='Markdown')
            
            # Показываем вопросы по одному
            bot.send_message(message.chat.id, 
                           "📖 *Выберите номер вопроса, который вас интересует:*\n"
                           "Напишите номер от 1 до 12", 
                           parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, faq_text, parse_mode='Markdown')
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при получении FAQ: {str(e)}")

@bot.message_handler(commands=['faq1', 'faq2', 'faq3', 'faq4', 'faq5', 
                              'faq6', 'faq7', 'faq8', 'faq9', 'faq10',
                              'faq11', 'faq12'])
def show_specific_faq(message):
    try:
        # Извлекаем номер из команды (например, /faq5 -> 5)
        command = message.text.replace('/', '')
        number = int(command.replace('faq', ''))
        
        faq_text = faq_manager.get_faq_by_number(number)
        bot.send_message(message.chat.id, faq_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['search'])
def search_faq_command(message):
    msg = bot.send_message(message.chat.id, "🔍 *Введите текст для поиска в FAQ:*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    try:
        search_text = message.text.strip()
        if not search_text:
            bot.send_message(message.chat.id, "❌ Вы не ввели текст для поиска.")
            return
            
        result = faq_manager.search_faq_text(search_text)
        bot.send_message(message.chat.id, result, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при поиске: {str(e)}")

@bot.message_handler(commands=['addfaq'])
def add_faq_command(message):
    # Проверяем, является ли пользователь администратором
    ADMIN_IDS = [123456789]  # Замените на ваш ID
    
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ У вас нет доступа к этой команде.")
        return
    
    msg = bot.send_message(message.chat.id, 
                         "📝 *Добавление нового вопроса в FAQ*\n\n"
                         "Введите вопрос:", 
                         parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_add_question)

def process_add_question(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "❌ Вопрос не может быть пустым.")
        return
    
    # Сохраняем вопрос в временное хранилище или передаем дальше
    bot.send_message(message.chat.id, 
                   f"✅ Вопрос сохранен: '{question}'\n\n"
                   "Теперь введите ответ:",
                   parse_mode='Markdown')
    
    # Передаем ID чата и вопрос в следующий шаг
    bot.register_next_step_handler(message, process_add_answer, question)

def process_add_answer(message, question):
    answer = message.text.strip()
    if not answer:
        bot.send_message(message.chat.id, "❌ Ответ не может быть пустым.")
        return
    
    # Добавляем FAQ в базу данных
    result = faq_manager.add_new_faq(question, answer)
    bot.send_message(message.chat.id, result, parse_mode='Markdown')
    
    # Показываем обновленный FAQ
    show_all_faq(message)

# ========== ОБРАБОТКА КНОПОК ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    
    # Обработка кнопок меню
    if text == "📋 Показать FAQ":
        show_all_faq(message)
    
    elif text == "❓ Поиск в FAQ":
        search_faq_command(message)
    
    elif text == "ℹ️ Информация":
        faq_count = faq_manager.get_faq_count()
        user_info = (
            f"👤 *Информация о вас*\n\n"
            f"ID: `{message.from_user.id}`\n"
            f"Имя: {message.from_user.first_name}\n"
            f"Фамилия: {message.from_user.last_name or 'не указана'}\n"
            f"Username: @{message.from_user.username or 'не указан'}\n\n"
            f"📊 В базе FAQ: {faq_count} вопросов"
        )
        bot.send_message(chat_id, user_info, parse_mode='Markdown')
    
    # Обработка номеров вопросов (если пользователь ввел число)
    elif text.isdigit():
        number = int(text)
        if 1 <= number <= 20:  # Предполагаем максимум 20 вопросов
            faq_text = faq_manager.get_faq_by_number(number)
            bot.send_message(chat_id, faq_text, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, "❌ Пожалуйста, введите число от 1 до 20")
    
    # Поиск по ключевым словам
    elif any(keyword in text.lower() for keyword in ['окно', 'окна', 'установка', 'монтаж', 'замер']):
        bot.send_message(chat_id, 
                       "🔍 *Кажется, вы ищете информацию об окнах.*\n\n"
                       "Используйте:\n"
                       "• Кнопку '📋 Показать FAQ' для всех вопросов\n"
                       "• Кнопку '❓ Поиск в FAQ' для поиска по ключевым словам",
                       parse_mode='Markdown')
    
    else:
        # Если сообщение не распознано
        responses = {
            "привет": "Привет! Чем могу помочь? Используйте меню ниже 👇",
            "здравствуйте": "Здравствуйте! Выберите действие в меню.",
            "спасибо": "Пожалуйста! Обращайтесь еще!",
        }
        
        text_lower = text.lower()
        for key in responses:
            if key in text_lower:
                bot.send_message(chat_id, responses[key])
                return
        
        # Если не нашли совпадение
        bot.send_message(
            chat_id,
            "🤔 Я не совсем понял ваш запрос.\n\n"
            "Используйте кнопки меню:\n"
            "• 📋 Показать FAQ - все вопросы\n"
            "• ❓ Поиск в FAQ - поиск по ключевым словам\n"
            "• ℹ️ Информация - информация о вас\n\n"
            "Или введите номер вопроса (например: 1, 2, 3...)"
        )

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("=" * 50)
    print("Бот 'Народные Окна - FAQ' запущен...")
    print(f"База данных: faq_database.db")
    print(f"Количество вопросов в FAQ: {faq_manager.get_faq_count()}")
    print("=" * 50)
    
    bot.remove_webhook()
    bot.infinity_polling()