from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
        f"✅ Кімната створена!\n\n🔑 Код кімнати: `{code}`\n\n"
        "Поділіться цим кодом з друзями. Коли всі приєднаються, натисніть 'Почати гру'.",
        reply_markup=room_creator_menu(code),
        parse_mode="Markdown"
    )

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
