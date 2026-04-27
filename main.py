import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from pymongo import MongoClient

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
TOKEN = os.getenv("BOT_TOKEN", "8428272271:AAHFXCueJnpqhbB869pt-oXeI4ET7flpMRg")
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://saidsharik21:YOUR_PASSWORD@cluster0.strvmpe.mongodb.net/?appName=Cluster0",
)

# ─── MongoDB ──────────────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db = client["rpg_bot"]
users_col = db["users"]

# ─── Classes / RPG stats ──────────────────────────────────────────────────────
CLASSES = {
    "⚔️ Воин":    {"hp": 150, "atk": 20, "def": 15},
    "🧙 Маг":     {"hp": 90,  "atk": 35, "def": 8},
    "🗡️ Разбойник": {"hp": 110, "atk": 28, "def": 10},
}
DEFAULT_CLASS = "⚔️ Воин"

# ─── Keyboard ─────────────────────────────────────────────────────────────────
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👤 Профиль"), KeyboardButton("💰 Баланс")],
        [KeyboardButton("⚔️ Сражаться"), KeyboardButton("🏪 Магазин")],
    ],
    resize_keyboard=True,
)

# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_user(user_id: int):
    return users_col.find_one({"user_id": user_id})


def create_user(telegram_user) -> dict:
    """Create and insert a new user document; return it."""
    stats = CLASSES[DEFAULT_CLASS].copy()
    doc = {
        "user_id":    telegram_user.id,
        "username":   telegram_user.username or "",
        "first_name": telegram_user.first_name or "",
        "class":      DEFAULT_CLASS,
        "level":      1,
        "xp":         0,
        "gold":       100,          # стартовый баланс
        "hp":         stats["hp"],
        "max_hp":     stats["hp"],
        "atk":        stats["atk"],
        "def":        stats["def"],
        "wins":       0,
        "losses":     0,
        "created_at": datetime.utcnow(),
    }
    users_col.insert_one(doc)
    logger.info("New user created: %s (%s)", telegram_user.id, telegram_user.first_name)
    return doc


def get_or_create_user(telegram_user) -> dict:
    user = get_user(telegram_user.id)
    if user is None:
        user = create_user(telegram_user)
    return user


def update_user(user_id: int, fields: dict):
    users_col.update_one({"user_id": user_id}, {"$set": fields})

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user = get_user(tg_user.id)

    if user is None:
        user = create_user(tg_user)
        text = (
            f"⚔️ *Добро пожаловать в RPG-мир, {tg_user.first_name}!*\n\n"
            f"Твой персонаж создан автоматически:\n"
            f"• Класс: {user['class']}\n"
            f"• Уровень: {user['level']}\n"
            f"• HP: {user['hp']}/{user['max_hp']}\n"
            f"• Золото: {user['gold']} 🪙\n\n"
            "Удачи в приключениях!"
        )
    else:
        text = (
            f"👋 С возвращением, *{tg_user.first_name}*!\n"
            f"Уровень {user['level']} • {user['class']}"
        )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user)

    xp_needed = user["level"] * 100
    bar_filled = int((user["xp"] / xp_needed) * 10)
    xp_bar = "█" * bar_filled + "░" * (10 - bar_filled)

    text = (
        f"👤 *Профиль*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏷 Имя: {update.effective_user.first_name}\n"
        f"⚔️ Класс: {user['class']}\n"
        f"🌟 Уровень: {user['level']}\n"
        f"✨ Опыт: `[{xp_bar}]` {user['xp']}/{xp_needed}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
        f"🗡 Атака: {user['atk']}\n"
        f"🛡 Защита: {user['def']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Золото: {user['gold']} 🪙\n"
        f"🏆 Победы: {user['wins']}  💀 Поражения: {user['losses']}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user)
    text = (
        f"💰 *Баланс*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Золото: *{user['gold']}* 🪙\n"
        f"Уровень: *{user['level']}*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"_Побеждай монстров, чтобы заработать больше золота!_"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple mock battle."""
    import random

    user = get_or_create_user(update.effective_user)

    monsters = [
        {"name": "🐀 Крыса",     "hp": 30,  "atk": 5,  "def": 2,  "xp": 20,  "gold": 10},
        {"name": "🐺 Волк",      "hp": 60,  "atk": 12, "def": 5,  "xp": 40,  "gold": 25},
        {"name": "🧟 Зомби",     "hp": 80,  "atk": 15, "def": 8,  "xp": 60,  "gold": 40},
        {"name": "🐉 Дракон",    "hp": 200, "atk": 35, "def": 20, "xp": 150, "gold": 100},
    ]
    monster = random.choice(monsters)

    # Simple probability-based outcome
    player_power = user["atk"] * user["level"] + user["def"]
    monster_power = monster["atk"] + monster["def"]
    win_chance = player_power / (player_power + monster_power)
    won = random.random() < win_chance

    if won:
        new_xp = user["xp"] + monster["xp"]
        new_gold = user["gold"] + monster["gold"]
        leveled_up = False

        xp_needed = user["level"] * 100
        new_level = user["level"]
        if new_xp >= xp_needed:
            new_xp -= xp_needed
            new_level += 1
            leveled_up = True
            # Boost stats on level up
            new_atk = user["atk"] + 2
            new_def = user["def"] + 1
            new_max_hp = user["max_hp"] + 10
        else:
            new_atk = user["atk"]
            new_def = user["def"]
            new_max_hp = user["max_hp"]

        update_user(update.effective_user.id, {
            "xp": new_xp, "gold": new_gold,
            "level": new_level, "wins": user["wins"] + 1,
            "atk": new_atk, "def": new_def,
            "max_hp": new_max_hp, "hp": new_max_hp,
        })

        text = (
            f"⚔️ *Сражение!*\n"
            f"Ты встретил {monster['name']}!\n\n"
            f"✅ *Победа!*\n"
            f"• +{monster['xp']} опыта\n"
            f"• +{monster['gold']} 🪙 золота\n"
        )
        if leveled_up:
            text += f"\n🎉 *Уровень повышен до {new_level}!*\n+2 атаки, +1 защиты, +10 HP"
    else:
        hp_loss = max(5, monster["atk"] - user["def"])
        new_hp = max(1, user["hp"] - hp_loss)
        update_user(update.effective_user.id, {"hp": new_hp, "losses": user["losses"] + 1})
        text = (
            f"⚔️ *Сражение!*\n"
            f"Ты встретил {monster['name']}!\n\n"
            f"💀 *Поражение!*\n"
            f"• -{hp_loss} HP\n"
            f"• Золото не получено\n"
            f"• HP: {new_hp}/{user['max_hp']}"
        )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user)
    text = (
        f"🏪 *Магазин*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Твоё золото: {user['gold']} 🪙\n\n"
        f"_Магазин в разработке. Скоро здесь появятся товары!_\n\n"
        f"🗡 Оружие • 🛡 Броня • 🧪 Зелья"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Неизвестная команда. Используй кнопки меню.",
        reply_markup=MAIN_KEYBOARD,
    )

# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    logger.info("Starting RPG bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))

    # Keyboard buttons (text messages)
    app.add_handler(MessageHandler(filters.Regex(r"^(👤 Профиль|Профиль|/profile)$"), show_profile))
    app.add_handler(MessageHandler(filters.Regex(r"^(💰 Баланс|Баланс|Б|/balance)$"), show_balance))
    app.add_handler(MessageHandler(filters.Regex(r"^(⚔️ Сражаться|Сражаться|/fight)$"), fight))
    app.add_handler(MessageHandler(filters.Regex(r"^(🏪 Магазин|Магазин|/shop)$"), shop))

    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Bot is polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
