"""
Главный файл для запуска бота
"""
import asyncio
from bot import WindowBot


def read_token() -> str:
    """Чтение токена из файла"""
    try:
        with open("token.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError("Файл token.txt не найден! Создайте файл и укажите в нем токен бота.")


async def main():
    """Основная функция"""
    token = read_token()
    bot = WindowBot(token)
    
    print("Бот запущен...")
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\nОстановка бота...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

