
import os
import logging
import pandas as pd

from dotenv import load_dotenv
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Загружаем ключи из .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Подключаем Groq
client = Groq(api_key=GROQ_API_KEY)

# Настраиваем журнал ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    keyboard = [
        [KeyboardButton("📊 Анализ данных")],
        [KeyboardButton("💬 Задать вопрос")],
        [KeyboardButton("📚 Помощь"), KeyboardButton("🧹 Очистить историю")],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
    welcome_text = (
        "Привет! 👋 Я Data Assistant — твой помощник по аналитике данных.\n\n"
        "Я умею:\n"
        "🐍 Объяснять Python и Pandas\n"
        "🗄 Помогать с SQL и базами данных\n"
        "📊 Разбирать метрики и статистику\n"
        "🧪 Объяснять A/B-тесты\n"
        "💡 Помогать с аналитическими задачами\n\n"
        "Можешь задавать вопросы обычным сообщением.\n\n"
        "Команды:\n"
        "/help — справка\n"
        "/clear — очистить историю диалога"
    )

    await update.message.reply_text(
    welcome_text,
    reply_markup=reply_markup
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 Как пользоваться Data Assistant:\n\n"
        "1. Задавай вопросы по Python, SQL и аналитике.\n"
        "2. Можешь задавать уточняющие вопросы — я учитываю контекст.\n"
        "3. Проси объяснить код или помочь найти ошибку.\n\n"
        "Доступные команды:\n"
        "/start — начать новый диалог\n"
        "/help — показать эту справку\n"
        "/clear — очистить историю сообщений\n\n"
        "Пример вопроса:\n"
        "Как посчитать Retention Rate в Python?"
    )

    await update.message.reply_text(help_text)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text(
        "История диалога очищена. Можем начать заново! 😊"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    if user_message == "📚 Помощь":
        await help_command(update, context)
        return
    if user_message == "🧹 Очистить историю":
        await clear_history(update, context)
        return
    if user_message == "💬 Задать вопрос":
        await update.message.reply_text(
            "Задавай свой вопрос по Python, SQL или статистике. Я помогу! 😊"
        )
        return
    if user_message == "📊 Анализ данных":
        await update.message.reply_text(
            "📊 Давай проанализируем данные!\n\n"
            "Загрузи файл CSV или Excel, и я помогу:\n"
            "• изучить структуру данных;\n"
            "• проверить пропуски и дубликаты;\n"
            "• рассчитать основные показатели;\n"
            "• найти закономерности."
        )
        return
    # Получаем историю диалога пользователя
    history = context.user_data.setdefault("history", [])

    # Добавляем новое сообщение
    history.append({
        "role": "user",
        "content": user_message,
    })

    # Ограничиваем историю последними 20 сообщениями
    history = history[-20:]
    context.user_data["history"] = history

    messages = [
        {
            "role": "system",
            "content": (
                "Ты Data Assistant — помощник по аналитике данных. "
                "Отвечай на русском языке, простыми словами. "
                "Помогай с Python, SQL, Pandas и анализом данных. "
                "Учитывай контекст предыдущих сообщений."
            ),
        }
    ] + history

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
        )

        answer = response.choices[0].message.content

        # Сохраняем ответ в историю
        history.append({
            "role": "assistant",
            "content": answer,
        })

        context.user_data["history"] = history[-20:]

        await update.message.reply_text(answer)

    except Exception:
        logger.exception("Ошибка при обращении к Groq")
        await update.message.reply_text(
            "Не удалось получить ответ. Попробуй ещё раз."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file_name = document.file_name or ""
    extension = os.path.splitext(file_name)[1].lower()

    if extension not in [".csv", ".xlsx", ".xls"]:
        await update.message.reply_text(
            "Пожалуйста, отправь файл CSV или Excel."
        )
        return

    await update.message.reply_text("⏳ Получила файл! Начинаю анализ...")

    file = await context.bot.get_file(document.file_id)
    file_path = f"uploaded_{document.file_unique_id}{extension}"

    try:
        await file.download_to_drive(custom_path=file_path)

        if extension == ".csv":
            try:
                df = pd.read_csv(file_path)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="cp1251")
        else:
            df = pd.read_excel(file_path)

        numeric_stats = df.describe().round(2)

           
                # Анализ динамики по годам
        yearly_means = df.select_dtypes(include="number").mean()
        yearly_changes = yearly_means.pct_change() * 100

        yearly_dynamics = ""

        for year in yearly_means.index[1:]:
            change = yearly_changes[year]

            if change > 0:
                emoji = "📈"
                status = "рост"
            elif change < 0:
                emoji = "📉"
                status = "снижение"
            else:
                emoji = "➡️"
                status = "без изменений"

            yearly_dynamics += (
                f"{emoji} {year}: {change:+.2f}% ({status})\n"
            )
        min_year = yearly_means.idxmin()
        max_year = yearly_means.idxmax()

        min_value = yearly_means.min()
        max_value = yearly_means.max()

        first_year = yearly_means.index[0]
        last_year = yearly_means.index[-1]

        change = (
            (yearly_means.iloc[-1] - yearly_means.iloc[0])
            / yearly_means.iloc[0]
            * 100
        )

        stats_report = ""

        for column in numeric_stats.columns:
            stats_report += f"\n📌 {column}\n"
            stats_report += f"Среднее: {numeric_stats[column]['mean']:,.2f}\n"
            stats_report += f"Медиана: {numeric_stats[column]['50%']:,.2f}\n"
            stats_report += f"Минимум: {numeric_stats[column]['min']:,.2f}\n"
            stats_report += f"Максимум: {numeric_stats[column]['max']:,.2f}\n"
        
        insights_report = (
            f"💡 АНАЛИТИЧЕСКИЕ ВЫВОДЫ\n\n"
            f"📉 Минимальное среднее: {min_value:,.2f} ({min_year})\n"
            f"📈 Максимальное среднее: {max_value:,.2f} ({max_year})\n"
            f"📊 Изменение с {first_year} по {last_year}: {change:+.2f}%\n"
        )

        report = (
            f"📊 **Результаты анализа**\n\n"
            f"Строк: {df.shape[0]}\n"
            f"Столбцов: {df.shape[1]}\n\n"
            f"Названия столбцов:\n{', '.join(map(str, df.columns))}\n\n"
            f"Пропуски:\n{df.isna().sum().to_string()}\n\n"
            f"Дубликаты: {df.duplicated().sum()}\n\n"
            f"Типы данных:\n{df.dtypes.to_string()}\n\n"
            f"{insights_report}\n\n"
            f"📅 Динамика по годам:\n{yearly_dynamics}\n\n"
            f"📈 Статистика числовых столбцов:\n{stats_report}"
        )

        await update.message.reply_text(report)

    except Exception:
        logger.exception("Ошибка при анализе файла")
        await update.message.reply_text(
            "Не удалось прочитать файл. Проверь его формат."
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        raise ValueError("Не найдены ключи в файле .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_handler(
    MessageHandler(filters.Document.ALL, handle_document)
)

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
