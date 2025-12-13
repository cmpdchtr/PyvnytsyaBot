from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.models import User
from ..keyboards.inline import main_menu
from ..states.game_states import Registration

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    
    # Register user if not exists
    result = await session.execute(select(User).where(User.id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create user but ask for nickname immediately
        user = User(id=message.from_user.id, username=message.from_user.username, full_name=message.from_user.full_name)
        session.add(user)
        await session.commit()
        
        await state.set_state(Registration.waiting_for_nickname)
        await message.answer("👋 Привіт! Я бот 'Пивниця'.\nЯк тебе називати в грі? Введи свій нікнейм:")
        return
    
    await message.answer(
        f"👋 Привіт, {user.full_name}! Я бот 'Пивниця' для гри в Бункер.\n"
        "Створи кімнату або приєднайся до існуючої, щоб почати гру.",
        reply_markup=main_menu()
    )

@router.message(Registration.waiting_for_nickname)
async def process_nickname(message: types.Message, session: AsyncSession, state: FSMContext):
    nickname = message.text.strip()
    if len(nickname) > 50:
        await message.answer("Нікнейм занадто довгий. Спробуй коротший (до 50 символів):")
        return
        
    result = await session.execute(select(User).where(User.id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if user:
        user.full_name = nickname
        await session.commit()
        
    await state.clear()
    await message.answer(
        f"Чудово, {nickname}! Тепер ти в грі.\n"
        "Створи кімнату або приєднайся до існуючої.",
        reply_markup=main_menu()
    )

@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Головне меню:",
        reply_markup=main_menu()
    )

@router.callback_query(lambda c: c.data == "rules")
async def show_rules(callback: types.CallbackQuery):
    await callback.answer("Правила прості: вижити в бункері! (Деталі згодом)", show_alert=True)
