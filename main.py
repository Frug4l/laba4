import os
import json
import logging
from datetime import datetime
from typing import Dict, List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройки
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


class NoteStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()


# Работа с данными
def load_notes() -> Dict[str, List[Dict]]:
    try:
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_notes(notes: Dict[str, List[Dict]]):
    try:
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")

def get_user_notes(user_id: str) -> List[Dict]:
    notes = load_notes()
    return notes.get(user_id, [])

def save_user_notes(user_id: str, notes_list: List[Dict]):
    notes = load_notes()
    notes[user_id] = notes_list
    save_notes(notes)

def get_next_id(user_id: str) -> int:
    notes = get_user_notes(user_id)
    if not notes:
        return 1
    return max(note.get('id', 0) for note in notes) + 1

# Клавиатуры
def main_kb():
    kb = [
        [KeyboardButton(text="📝 Новая заметка"), KeyboardButton(text="📋 Мои заметки")],
        [KeyboardButton(text="🗑️ Удалить заметку"), KeyboardButton(text="✨ Вдохновение")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def notes_kb(notes: List[Dict]):
    buttons = []
    for note in notes[:10]:
        title = note.get('title', 'Без заголовка')[:20]
        buttons.append([InlineKeyboardButton(
            text=f"📝 {title}...",
            callback_data=f"view_{note.get('id')}"
        )])
    buttons.append([
        InlineKeyboardButton(text="➕ Новая", callback_data="new_note"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def note_actions_kb(note_id: int):
    buttons = [
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{note_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команды
@dp.message(Command("start", "help"))
async def start_cmd(message: types.Message):
    await message.answer(
        "📚 <b>Бот для заметок</b>\n\n"
        "Основные команды:\n"
        "/new - Новая заметка\n"
        "/list - Мои заметки\n"
        "/delete - Удалить заметку\n"
        "/inspire - Цитата дня\n\n"
        "Или используйте кнопки:",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )

@dp.message(Command("new"))
@dp.message(F.text == "📝 Новая заметка")
async def new_note_cmd(message: types.Message, state: FSMContext):
    await message.reply("Введите заголовок заметки:", parse_mode="HTML")
    await state.set_state(NoteStates.waiting_title)

@dp.message(NoteStates.waiting_title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.reply("Теперь введите текст заметки:", parse_mode="HTML")
    await state.set_state(NoteStates.waiting_content)

@dp.message(NoteStates.waiting_content)
async def process_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get('title', 'Без заголовка')
    
    user_id = str(message.from_user.id)
    notes = get_user_notes(user_id)
    note_id = get_next_id(user_id)
    
    notes.append({
        'id': note_id,
        'title': title,
        'content': message.text,
        'created': datetime.now().isoformat()
    })
    
    save_user_notes(user_id, notes)
    
    await message.reply(
        f"✅ <b>Заметка создана!</b>\nID: <code>{note_id}</code>\nЗаголовок: {title}",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )
    await state.clear()

@dp.message(Command("list"))
@dp.message(F.text == "📋 Мои заметки")
async def list_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    notes = get_user_notes(user_id)
    
    if not notes:
        await message.reply("📭 У вас пока нет заметок.", reply_markup=main_kb())
        return
    
    notes.sort(key=lambda x: x.get('created', ''), reverse=True)
    
    text = f"📋 <b>Ваши заметки</b> ({len(notes)} шт.)\n\n"
    for i, note in enumerate(notes[:5], 1):
        text += f"{i}. <b>{note.get('title')}</b>\n"
        text += f"   🆔 {note.get('id')}\n\n"
    
    if len(notes) > 5:
        text += f"<i>... и еще {len(notes)-5}</i>\n\n"
    
    await message.reply(text, parse_mode="HTML", reply_markup=notes_kb(notes))

@dp.callback_query(F.data.startswith("view_"))
async def view_note(callback: types.CallbackQuery):
    note_id = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    
    notes = get_user_notes(user_id)
    note = next((n for n in notes if n.get('id') == note_id), None)
    
    if not note:
        await callback.answer("Заметка не найдена", show_alert=True)
        return
    
    created = datetime.fromisoformat(note.get('created')).strftime('%d.%m.%Y %H:%M')
    text = f"📝 <b>{note.get('title')}</b>\n\n{note.get('content')}\n\n📅 {created}\n🆔 {note_id}"
    
    if len(text) > 4000:
        text = text[:4000] + "..."
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=note_actions_kb(note_id))
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_to_list(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    notes = get_user_notes(user_id)
    notes.sort(key=lambda x: x.get('created', ''), reverse=True)
    
    text = f"📋 <b>Ваши заметки</b> ({len(notes)} шт.)\n\n"
    for i, note in enumerate(notes[:5], 1):
        text += f"{i}. <b>{note.get('title')}</b>\n"
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=notes_kb(notes))
    await callback.answer()

@dp.callback_query(F.data == "new_note")
async def new_note_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите заголовок заметки:", parse_mode="HTML")
    await state.set_state(NoteStates.waiting_title)
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_"))
async def delete_note(callback: types.CallbackQuery):
    note_id = int(callback.data.split("_")[1])
    user_id = str(callback.from_user.id)
    
    notes = get_user_notes(user_id)
    notes = [n for n in notes if n.get('id') != note_id]
    
    save_user_notes(user_id, notes)
    
    await callback.message.edit_text(f"✅ Заметка #{note_id} удалена.")
    await callback.answer()

@dp.message(Command("delete"))
@dp.message(F.text == "🗑️ Удалить заметку")
async def delete_cmd(message: types.Message):
    user_id = str(message.from_user.id)
    notes = get_user_notes(user_id)
    
    if not notes:
        await message.reply("У вас нет заметок для удаления.", reply_markup=main_kb())
        return
    
    text = "🗑️ <b>Удаление заметки</b>\n\nВведите ID заметки:\n\n"
    for note in notes[:10]:
        text += f"🆔 {note.get('id')} - {note.get('title')[:30]}...\n"
    
    await message.reply(text, parse_mode="HTML")

@dp.message(F.text.regexp(r'^\d+$'))
async def delete_by_id(message: types.Message):
    note_id = int(message.text)
    user_id = str(message.from_user.id)
    
    notes = get_user_notes(user_id)
    note = next((n for n in notes if n.get('id') == note_id), None)
    
    if not note:
        await message.reply(f"❌ Заметка #{note_id} не найдена.")
        return
    
    buttons = [
        [InlineKeyboardButton(text="✅ Да", callback_data=f"delete_{note_id}")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="back")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.reply(
        f"🗑️ Удалить заметку #{note_id}?\n<b>{note.get('title')}</b>",
        parse_mode="HTML",
        reply_markup=kb
    )
