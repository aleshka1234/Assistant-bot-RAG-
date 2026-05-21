import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from openai import AsyncOpenAI
import logging

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Убедитесь, что TELEGRAM_TOKEN и OPENROUTER_API_KEY добавлены в файл .env")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

try:
    with open("company_knowledge_base.txt", "r", encoding="utf-8") as file:
        company_info = file.read()
except FileNotFoundError:
    company_info = "Информация о компании пока не добавлена."

SYSTEM_PROMPT = f"""Ты — полезный AI-ассистент компании "Центр Красок" (centr-krasok.kz).
Твоя задача — отвечать на вопросы пользователей ТОЛЬКО на основе предоставленной ниже информации.
Отвечай вежливо, кратко и по делу. Не выдумывай цены, услуги или адреса, которых нет в тексте.
Если ответа на вопрос нет в тексте, честно скажи: "К сожалению, у меня нет точной информации об этом. Пожалуйста, обратитесь по контактам на сайте."

Информация о компании:
{company_info}
"""

user_contexts = {}
MAX_HISTORY_LENGTH = 10


@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(chat_id=message.chat.id, action='typing')

    if user_id not in user_contexts:
        user_contexts[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    user_contexts[user_id].append({"role": "user", "content": user_text})

    if len(user_contexts[user_id]) > MAX_HISTORY_LENGTH + 1:
        user_contexts[user_id] = [user_contexts[user_id][0]] + user_contexts[user_id][-MAX_HISTORY_LENGTH:]

    try:
        response = await client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=user_contexts[user_id],
            temperature=0.3
        )

        ai_response = response.choices[0].message.content
        user_contexts[user_id].append({"role": "assistant", "content": ai_response})
        await message.reply(ai_response)

    except Exception as e:
        await message.reply("Извините, произошла ошибка при формировании ответа. Попробуйте еще раз.")
        print(f"Ошибка API: {e}")


async def main():
    print("Бот (OpenRouter) запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
