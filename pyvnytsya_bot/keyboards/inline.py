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
    builder.button(text="⚙️ Налаштування", callback_data=f"settings_{room_code}")
    builder.button(text="🤖 Додати бота", callback_data=f"add_bot_{room_code}")
    builder.button(text="❌ Видалити кімнату", callback_data=f"delete_room_{room_code}")
    builder.adjust(1, 2, 1)
    return builder.as_markup()

def room_player_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Мій статус", callback_data=f"my_status_{room_code}")
    builder.button(text="🚪 Вийти", callback_data=f"leave_room_{room_code}")
    builder.adjust(2)
    return builder.as_markup()

def back_to_main() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 На головну", callback_data="main_menu")
    return builder.as_markup()

# --- Game Keyboards ---

def game_dashboard(room_code: str, phase: str = "revealing", is_alive: bool = True, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    sizes = []
    
    # Row 1: Player Actions
    row1 = 0
    if is_alive:
        if phase == "revealing":
            builder.button(text="🃏 Відкрити карту", callback_data=f"reveal_menu_{room_code}")
            row1 += 1
        builder.button(text="👤 Мої характеристики", callback_data=f"my_status_{room_code}")
        row1 += 1
    if row1 > 0: sizes.append(row1)
    
    # Row 1.5: Action Cards
    if is_alive:
        builder.button(text="⚡ Картки дій", callback_data=f"action_cards_{room_code}")
        sizes.append(1)
    
    # Row 2: Info
    builder.button(text="👀 Стіл гравців", callback_data=f"view_table_{room_code}")
    builder.button(text="📜 Інфо про бункер", callback_data=f"view_scenario_{room_code}")
    sizes.append(2)
    
    # Row 3: Admin
    if is_admin:
        if phase == "revealing":
            builder.button(text="🗣 Почати обговорення", callback_data=f"start_discuss_{room_code}")
            sizes.append(1)
        elif phase == "discussion":
            builder.button(text="📢 Почати голосування", callback_data=f"force_vote_{room_code}")
            sizes.append(1)
        
    # Row 4: Refresh
    builder.button(text="🔄 Оновити", callback_data=f"refresh_game_{room_code}")
    sizes.append(1)
    
    builder.adjust(*sizes)
    return builder.as_markup()

def reveal_menu(room_code: str, revealed_traits: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Ordered for better layout
    traits = {
        "bio": "⚧ Стать",
        "age": "🎂 Вік",
        "profession": "🛠 Професія",
        "health": "❤️ Здоров'я",
        "hobby": "🎨 Хобі",
        "phobia": "😱 Фобія",
        "inventory": "🎒 Інвентар",
        "fact": "ℹ️ Факт"
    }
    
    for key, label in traits.items():
        if key not in revealed_traits:
            builder.button(text=label, callback_data=f"reveal_{key}_{room_code}")
            
    builder.button(text="🔙 Назад", callback_data=f"back_to_game_{room_code}")
    
    # Adjust 2 columns for traits, 1 for back button
    # We need to calculate how many traits are left to know how to adjust
    count = len([k for k in traits if k not in revealed_traits])
    
    # If count is even: 2, 2, ..., 1
    # If count is odd: 2, 2, ..., 1, 1 (last trait alone, then back)
    # Or just adjust(2) and the last row will handle itself?
    # Yes, adjust(2) will fill rows. The last button (Back) might end up sharing a row if we are not careful.
    # To force Back to be on its own row, we can append 1 to sizes.
    
    # But adjust() repeats the pattern. adjust(2) -> 2, 2, 2...
    # If we want the last one to be 1, we need to be specific.
    
    sizes = [2] * (count // 2)
    if count % 2 != 0:
        sizes.append(1)
    sizes.append(1) # Back button
    
    builder.adjust(*sizes)
    return builder.as_markup()

def voting_menu(room_code: str, players: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for player in players:
        if player.is_alive:
            name = player.user.full_name or player.user.username
            builder.button(text=f"💀 {name}", callback_data=f"vote_{player.id}_{room_code}")
    builder.adjust(2) # 2 players per row looks better
    return builder.as_markup()

def admin_game_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Почати голосування", callback_data=f"force_vote_{room_code}")
    builder.button(text="👀 Стіл гравців", callback_data=f"view_table_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def settings_menu(room_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 Обрати Пак (Пресет)", callback_data=f"choose_pack_{room_code}")
    builder.button(text="🔙 Назад", callback_data=f"back_to_room_{room_code}")
    builder.adjust(1)
    return builder.as_markup()

def packs_menu(room_code: str, packs: list, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Стандартний", callback_data=f"set_pack_default_{room_code}")
    
    for pack in packs:
        builder.button(text=f"📦 {pack.name}", callback_data=f"set_pack_{pack.id}_{room_code}")
        if pack.user_id == user_id:
             builder.button(text="❌", callback_data=f"delete_pack_{pack.id}_{room_code}")
        
    builder.button(text="📥 Завантажити шаблон", callback_data=f"get_template_{room_code}")
    builder.button(text="📤 Завантажити свій пак", callback_data=f"upload_pack_{room_code}")
    builder.button(text="🔙 Назад", callback_data=f"settings_{room_code}")
    
    # Adjust layout: 1 for default, then 2 for custom packs (select + delete) or 1 if public, then 1 for actions
    # This is tricky with dynamic adjust. Let's try to be smart.
    # We can't easily mix 1 and 2 columns with simple .adjust() if the pattern is irregular.
    # But we can add them row by row? No, builder accumulates.
    # Let's use a simpler approach: just set adjust to 2, and make "Standard" span 2 columns? No.
    # Let's just use adjust(2) for the packs part?
    
    # Actually, let's manually manage the grid.
    # But builder.adjust() takes a list of integers for row sizes.
    
    sizes = [1] # Standard
    for pack in packs:
        if pack.user_id == user_id:
            sizes.append(2) # Select + Delete
        else:
            sizes.append(1) # Select only
            
    sizes.extend([1, 1, 1]) # Actions
    
    builder.adjust(*sizes)
    return builder.as_markup()

def action_cards_menu(room_code: str, cards: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sizes = []
    
    for i, card in enumerate(cards):
        status = "" if not card["used"] else " (Використано)"
        # Name button shows info
        builder.button(text=f"{card['name']}{status}", callback_data=f"info_card_{i}_{room_code}")
        sizes.append(1)
        
        if not card["used"] and card["type"] == "active":
             builder.button(text="⚡ Використати", callback_data=f"use_card_{i}_{room_code}")
             sizes.append(1)
             
    builder.button(text="🔙 Назад", callback_data=f"back_to_game_{room_code}")
    sizes.append(1)
    
    builder.adjust(*sizes)
    return builder.as_markup()

def target_selection_menu(room_code: str, players: list, action_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for player in players:
        if player.is_alive:
            name = player.user.full_name or player.user.username
            builder.button(text=f"🎯 {name}", callback_data=f"target_{player.id}_{action_index}_{room_code}")
    builder.button(text="🔙 Назад", callback_data=f"action_cards_{room_code}")
    builder.adjust(2)
    return builder.as_markup()
