import os
import requests
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio

# Загрузка переменных окружения
load_dotenv()

# Инициализация базы данных
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

# Функция для добавления "Сухарики"
def suhariki(text):
    return f"Сухарики {text} Сухарики"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with sqlite3.connect('users.db') as conn:
        conn.execute('INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (user.id, user.username, user.first_name, user.last_name))
    
    await update.message.reply_text(suhariki(
        f"Привет, {user.first_name}! Я бот погоды и новостей.\n"
        "Доступные команды:\n"
        "/weather <город> - Узнать погоду\n"
        "/news <категория> - Последние новости\n"
        "/help - Помощь"
    ))

# Команда /weather
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(suhariki("Укажите город: /weather Москва"))
        return

    city = " ".join(context.args)
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                'q': city,
                'appid': os.getenv('WEATHER_API_KEY'),
                'units': 'metric',
                'lang': 'ru'
            }
        )
        data = response.json()

        if response.status_code == 200:
            weather_info = suhariki(
                f"🌤 Погода в {city}:\n"
                f"🌡 Температура: {data['main']['temp']}°C\n"
                f"💧 Влажность: {data['main']['humidity']}%\n"
                f"🌬 Ветер: {data['wind']['speed']} м/с\n"
                f"📝 {data['weather'][0]['description'].capitalize()}"
            )
            await update.message.reply_text(weather_info)
        else:
            await update.message.reply_text(suhariki(f"Ошибка: {data.get('message', 'Город не найден')}"))
    except Exception as e:
        await update.message.reply_text(suhariki(f"Ошибка: {str(e)}"))


#/News 
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Доступные темы с примерами новостей
        topics = {
            'tech': {
                'name': 'технологии',
                'articles': [
                    {"title": "ИИ научился предсказывать погоду", "url": "https://example.com/ai-weather"},
                    {"title": "Новый смартфон выйдет в этом месяце", "url": "https://example.com/new-phone"}
                ]
            },
            'business': {
                'name': 'бизнес',
                'articles': [
                    {"title": "Курс доллара обновил максимум", "url": "https://example.com/usd-rate"},
                    {"title": "Налоги для IT-компаний изменятся", "url": "https://example.com/tax-changes"}
                ]
            }
        }
        
        # Получаем выбранную тему
        topic = context.args[0].lower() if context.args else 'tech'
        
        if topic not in topics:
            await update.message.reply_text(suhariki(
                f"Тема '{topic}' не поддерживается.\n"
                "Доступные темы: " + ", ".join([f"/news {t}" for t in topics.keys()])
            ))
            return

        # 1. Пробуем получить реальные новости (если API доступен)
        try:
            response = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    'apiKey': os.getenv('NEWS_API_KEY'),
                    'category': topic if topic != 'tech' else 'technology',
                    'language': 'en',
                    'pageSize': 3
                },
                timeout=5
            )
            api_articles = response.json().get('articles', [])
        except:
            api_articles = []

        # 2. Объединяем с резервными новостями
        all_articles = api_articles + topics[topic]['articles']
        
        if not all_articles:
            await update.message.reply_text(suhariki(
                f"Новости в категории '{topics[topic]['name']}' не найдены."
            ))
            return

        # Отправляем заголовок категории
        await update.message.reply_text(suhariki(
            f"📰 Последние новости ({topics[topic]['name']}):"
        ))

        # Отправляем каждую новость отдельным сообщением
        for article in all_articles[:3]:  # Не более 3 новостей
            try:
                await update.message.reply_text(suhariki(
                    f"📌 {article['title']}\n"
                    f"🔗 {article['url']}"
                ))
                await asyncio.sleep(0.5)  # Пауза между сообщениями
            except Exception as e:
                print(f"Ошибка отправки новости: {e}")
                continue

    except Exception as e:
        await update.message.reply_text(suhariki(
            f"Произошла ошибка: {str(e)}"
        ))
        

# Команда /help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(suhariki(
        "📌 Помощь:\n"
        "/weather <город> - Погода\n"
        "/news <категория> - Новости (general, business, technology)\n"
        "/start - Перезапустить бота"
    ))

# Запуск бота
def main():
    init_db()
    app = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("help", help))
    
    print("Бот запущен 🚀")
    app.run_polling()

if __name__ == '__main__':
    main()