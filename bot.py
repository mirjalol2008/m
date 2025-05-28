# bot.py
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, Text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import sqlite3
import os

API_TOKEN = os.getenv("BOT_TOKEN")  # Tokenni environmentdan oling

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_NAME = "bot_database.db"

# --- Database functions ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        group_title TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

def add_group(group_id: int, group_title: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (group_id, group_title) VALUES (?, ?)", (group_id, group_title))
    conn.commit()
    conn.close()

def remove_group(group_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
    conn.commit()
    conn.close()

def get_groups():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT group_id, group_title FROM groups")
    groups = c.fetchall()
    conn.close()
    return groups

def is_admin(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE admin_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return bool(result)

def add_admin(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- FSM states ---
class AdminStates(StatesGroup):
    waiting_for_group_id = State()

# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("Salom Admin! /admin orqali admin panelga kirishingiz mumkin.")
    else:
        await message.answer("Salom! Siz admin emassiz.")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Sizda admin huquqlari yo'q.")
        return

    groups = get_groups()
    if not groups:
        await message.answer("Hozircha guruhlar ro'yxati bo'sh.")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for group_id, group_title in groups:
        kb.insert(InlineKeyboardButton(text=group_title[:40], callback_data=f"grp_{group_id}"))

    await message.answer("Guruhlar ro'yxati:", reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("grp_"))
async def process_group_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    group_id = int(callback.data[4:])
    groups = dict(get_groups())
    group_title = groups.get(group_id, "Noma'lum guruh")

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("❌ Guruhni o'chirish", callback_data=f"del_{group_id}"),
        InlineKeyboardButton("⬅ Orqaga", callback_data="admin_back")
    )

    await callback.message.edit_text(f"Guruh: {group_title}\nID: {group_id}", reply_markup=kb)
    await callback.answer()

@dp.callback_query(Text(startswith="del_"))
async def delete_group(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    group_id = int(callback.data[4:])
    remove_group(group_id)
    await callback.answer("Guruh ro'yxatdan o'chirildi.")
    # Yangilangan ro'yxatni ko'rsatish uchun /admin komandasi qo'yish mumkin

@dp.callback_query(Text("admin_back"))
async def admin_back(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz.", show_alert=True)
        return

    groups = get_groups()
    if not groups:
        await callback.message.edit_text("Hozircha guruhlar ro'yxati bo'sh.")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for group_id, group_title in groups:
        kb.insert(InlineKeyboardButton(text=group_title[:40], callback_data=f"grp_{group_id}"))

    await callback.message.edit_text("Guruhlar ro'yxati:", reply_markup=kb)
    await callback.answer()

@dp.message(Command("addgroup"))
async def cmd_addgroup(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    await message.answer("Guruh ID va nomini yuboring (misol: 1234567 Guruh nomi):")
    await AdminStates.waiting_for_group_id.set()

@dp.message(AdminStates.waiting_for_group_id)
async def process_group_input(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split(maxsplit=1)
        group_id = int(parts[0])
        group_title = parts[1] if len(parts) > 1 else "Noma'lum guruh"
        add_group(group_id, group_title)
        await message.answer(f"Guruh ro'yxatga qo'shildi: {group_title} (ID: {group_id})")
    except Exception as e:
        await message.answer("Noto'g'ri format! Iltimos, qaytadan yuboring.")
    await state.clear()

if __name__ == "__main__":
    init_db()
    add_admin(YOUR_TELEGRAM_ADMIN_ID)  # Bu yerga admin telegram ID yozing
    import asyncio
    asyncio.run(dp.start_polling())