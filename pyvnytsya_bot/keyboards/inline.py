from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Створити кімнату", callback_data="create_room")
    builder.button(text="🔑 Приєднатися", callback_data="join_room")
    builder.button(text="📜 Правила", callback_data="rules")
    builder.adjust(1)
    return builder.as_markup()

def room_creator_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Почати гру", callback_data=f"start_game_{room_code}")
    builder.button(text="🤖 Додати бота", callback_data=f"add_bot_{room_code}")
    builder.button(text="⚙️ Налаштування", callback_data=f"settings_{room_code}")
    builder.button(text="❌ Видалити кімнату", callback_data=f"delete_room_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def room_player_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Мій статус", callback_data=f"my_status_{room_code}")
    builder.button(text="🚪 Вийти", callback_data=f"leave_room_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 На головну", callback_data="main_menu")
    return builder.as_markup()
