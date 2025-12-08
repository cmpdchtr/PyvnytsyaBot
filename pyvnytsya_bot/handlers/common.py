from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.models import User
from ..keyboards.inline import main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    
    # Register user if not exists
    result = await session.execute(select(User).where(User.id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(id=message.from_user.id, username=message.from_user.username, full_name=message.from_user.full_name)
        session.add(user)
        await session.commit()
    
    await message.answer(
        "👋 Привіт! Я бот 'Пивниця' для гри в Бункер.\n"
        "Створи кімнату або приєднайся до існуючої, щоб почати гру.",
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
