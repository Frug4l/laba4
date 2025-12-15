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
