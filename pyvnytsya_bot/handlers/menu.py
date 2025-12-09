from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random

from ..database.models import Room, Player, User
from ..utils.codes import generate_room_code
from ..keyboards.inline import room_creator_menu, room_player_menu, back_to_main
from ..states.game_states import JoinRoom

router = Router()

@router.callback_query(F.data == "create_room")
async def create_room(callback: types.CallbackQuery, session: AsyncSession):
    # Generate unique code
    code = generate_room_code()
    # Check uniqueness (simplified for now, ideally loop until unique)
    
    new_room = Room(code=code, creator_id=callback.from_user.id)
    session.add(new_room)
    await session.flush() # to get ID
    
    # Add creator as player
    player = Player(user_id=callback.from_user.id, room_id=new_room.id)
    session.add(player)
    await session.commit()
    
    await callback.message.edit_text(
        f"✅ Кімната створена!\n\n🔑 Код кімнати: `{code}`\n"
        f"👥 Гравців: 1\n\n"
        "Поділіться цим кодом з друзями. Коли всі приєднаються, натисніть 'Почати гру'.",
        reply_markup=room_creator_menu(code),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("add_bot_"))
async def add_bot(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return
        
    if room.creator_id != callback.from_user.id:
        await callback.answer("Тільки творець може додавати ботів!", show_alert=True)
        return

    # Create fake user
    bot_id = -random.randint(1000, 999999)
    bot_name = f"Bot_{abs(bot_id)}"
    
    fake_user = User(id=bot_id, username=bot_name, full_name=bot_name)
    session.add(fake_user)
    
    # Add player
    player = Player(user_id=bot_id, room_id=room.id)
    session.add(player)
    
    await session.commit()
    
    # Count players
    players_res = await session.execute(select(Player).where(Player.room_id == room.id))
    players_count = len(players_res.scalars().all())
    
    await callback.message.edit_text(
        f"✅ Кімната створена!\n\n🔑 Код кімнати: `{code}`\n"
        f"👥 Гравців: {players_count}\n\n"
        "Поділіться цим кодом з друзями. Коли всі приєднаються, натисніть 'Почати гру'.",
        reply_markup=room_creator_menu(code),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("delete_room_"))
async def delete_room(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    
    if not room or room.creator_id != callback.from_user.id:
        await callback.answer("Помилка доступу.", show_alert=True)
        return

    await session.delete(room)
    await session.commit()
    await callback.message.edit_text("🗑️ Кімната видалена.", reply_markup=back_to_main())

@router.callback_query(F.data.startswith("settings_"))
async def room_settings(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[1]
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    
    if not room or room.creator_id != callback.from_user.id:
        await callback.answer("Помилка доступу.", show_alert=True)
        return

    from ..keyboards.inline import settings_menu
    await callback.message.edit_text(f"⚙️ Налаштування кімнати `{code}`", reply_markup=settings_menu(code), parse_mode="Markdown")

@router.callback_query(F.data.startswith("back_to_room_"))
async def back_to_room(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[3]
    await callback.message.edit_text(
        f"✅ Кімната створена!\n\n🔑 Код кімнати: `{code}`\n"
        "Поділіться цим кодом з друзями. Коли всі приєднаються, натисніть 'Почати гру'.",
        reply_markup=room_creator_menu(code),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("choose_pack_"))
async def choose_pack(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    
    # Get user's packs + public packs
    from ..database.models import GamePack
    stmt = select(GamePack).where((GamePack.user_id == callback.from_user.id) | (GamePack.is_public == True))
    result = await session.execute(stmt)
    packs = result.scalars().all()
    
    from ..keyboards.inline import packs_menu
    await callback.message.edit_text("📂 Оберіть пак для гри:", reply_markup=packs_menu(code, packs, callback.from_user.id))

@router.callback_query(F.data.startswith("set_pack_"))
async def set_pack(callback: types.CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    pack_id_str = parts[2]
    code = parts[3]
    
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    
    if not room: return

    if pack_id_str == "default":
        room.pack_id = None
        pack_name = "Стандартний"
    else:
        room.pack_id = int(pack_id_str)
        # Get pack name for confirmation
        from ..database.models import GamePack
        pack_res = await session.execute(select(GamePack).where(GamePack.id == int(pack_id_str)))
        pack = pack_res.scalar_one_or_none()
        pack_name = pack.name if pack else "Невідомий"

    await session.commit()
    await callback.answer(f"✅ Обрано пак: {pack_name}", show_alert=True)

@router.callback_query(F.data.startswith("delete_pack_"))
async def delete_pack(callback: types.CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    pack_id = int(parts[2])
    code = parts[3]

    from ..database.models import GamePack
    
    # Check if pack exists and belongs to user
    result = await session.execute(select(GamePack).where(GamePack.id == pack_id, GamePack.user_id == callback.from_user.id))
    pack = result.scalar_one_or_none()
    
    if not pack:
        await callback.answer("❌ Пак не знайдено або ви не є його власником.", show_alert=True)
        return

    # Check if the current room is using it and reset
    room_res = await session.execute(select(Room).where(Room.code == code))
    room = room_res.scalar_one_or_none()
    
    if room and room.pack_id == pack_id:
        room.pack_id = None
    
    await session.delete(pack)
    await session.commit()
    
    await callback.answer("🗑️ Пак видалено!", show_alert=True)
    
    # Refresh menu
    stmt = select(GamePack).where((GamePack.user_id == callback.from_user.id) | (GamePack.is_public == True))
    result = await session.execute(stmt)
    packs = result.scalars().all()
    
    from ..keyboards.inline import packs_menu
    await callback.message.edit_text("📂 Оберіть пак для гри:", reply_markup=packs_menu(code, packs, callback.from_user.id))
    
    from ..keyboards.inline import settings_menu
    await callback.message.edit_text(f"⚙️ Налаштування кімнати `{code}`\n📦 Поточний пак: *{pack_name}*", reply_markup=settings_menu(code), parse_mode="Markdown")

@router.callback_query(F.data.startswith("get_template_"))
async def get_template(callback: types.CallbackQuery):
    template_json = """{
  "name": "Мій крутий пак",
  "description": "Опис паку",
  "ai_prompts": {
    "scenario_prompt": "Ти ведучий...",
    "ending_prompt": "Ти ведучий..."
  },
  "data": {
    "professions": [
      {"name": "Лікар", "weight": 30},
      {"name": "Інженер", "weight": 30}
    ],
    "health": [
      {"name": "Здоровий", "weight": 40},
      {"name": "Хворий", "weight": 10}
    ],
    "hobby": [
       {"name": "Риболовля", "weight": 20}
    ],
    "phobia": [
       {"name": "Темрява", "weight": 20}
    ],
    "inventory": [
       {"name": "Ніж", "weight": 30}
    ],
    "fact": [
       {"name": "Знає азбуку Морзе", "weight": 10}
    ],
    "bio": [
       {"name": "Чоловік", "weight": 45},
       {"name": "Жінка", "weight": 45}
    ]
  }
}"""
    from aiogram.types import BufferedInputFile
    file = BufferedInputFile(template_json.encode(), filename="template.json")
    await callback.message.answer_document(file, caption="📥 Ось шаблон. Відредагуйте його та надішліть мені файл назад.")
    await callback.answer()

@router.callback_query(F.data.startswith("upload_pack_"))
async def upload_pack_instruction(callback: types.CallbackQuery):
    await callback.message.answer("📤 Надішліть мені `.json` файл з вашим паком. Я додам його у вашу бібліотеку.")
    await callback.answer()

@router.message(F.document)
async def handle_document(message: types.Message, session: AsyncSession, bot: Bot):
    if not message.document.file_name.endswith(".json"):
        return # Ignore non-json files
        
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    
    import json
    from io import BytesIO
    
    downloaded_file = await bot.download_file(file_path)
    content = downloaded_file.read().decode('utf-8')
    
    try:
        data = json.loads(content)
        # Basic validation
        if "name" not in data or "data" not in data:
            await message.reply("❌ Невірний формат файлу. Має бути поле 'name' та 'data'.")
            return
            
        from ..database.models import GamePack
        new_pack = GamePack(
            user_id=message.from_user.id,
            name=data["name"],
            description=data.get("description", ""),
            data=json.dumps(data["data"]), # Store data part as string
            is_public=False
        )
        session.add(new_pack)
        await session.commit()
        
        await message.reply(f"✅ Пак *{data['name']}* успішно додано! Тепер ви можете обрати його в налаштуваннях кімнати.", parse_mode="Markdown")
        
    except json.JSONDecodeError:
        await message.reply("❌ Помилка читання JSON файлу.")
    except Exception as e:
        await message.reply(f"❌ Сталася помилка: {e}")

@router.callback_query(F.data == "join_room")
async def join_room_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введіть код кімнати:",
        reply_markup=back_to_main()
    )
    await state.set_state(JoinRoom.waiting_for_code)

@router.message(JoinRoom.waiting_for_code)
async def join_room_process(message: types.Message, session: AsyncSession, state: FSMContext):
    code = message.text.upper().strip()
    
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    
    if not room:
        await message.answer("❌ Кімнату з таким кодом не знайдено. Спробуйте ще раз або поверніться в меню.", reply_markup=back_to_main())
        return

    if room.is_active or room.is_finished:
        await message.answer("⚠️ Гра в цій кімнаті вже почалася або закінчилася.", reply_markup=back_to_main())
        return

    # Check if already joined
    player_res = await session.execute(select(Player).where(Player.user_id == message.from_user.id, Player.room_id == room.id))
    if player_res.scalar_one_or_none():
        await message.answer("Ви вже в цій кімнаті!", reply_markup=room_player_menu(code))
        await state.clear()
        return

    # Add player
    new_player = Player(user_id=message.from_user.id, room_id=room.id)
    session.add(new_player)
    await session.commit()
    
    await message.answer(
        f"✅ Ви приєдналися до кімнати `{code}`!\nОчікуйте початку гри.",
        reply_markup=room_player_menu(code),
        parse_mode="Markdown"
    )
    await state.clear()
