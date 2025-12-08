from aiogram import Router, types, F, Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database.models import Room, Player
from ..services.gemini import ai_service
from ..utils.game_utils import generate_characteristics

router = Router()

@router.callback_query(F.data.startswith("start_game_"))
async def start_game(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    code = callback.data.split("_")[2]
    
    # Fetch room with players
    result = await session.execute(
        select(Room).options(selectinload(Room.players)).where(Room.code == code)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return
        
    if room.creator_id != callback.from_user.id:
        await callback.answer("Тільки творець може почати гру!", show_alert=True)
        return

    if len(room.players) < 1: # For testing allow 1, usually need more
        await callback.answer("Замало гравців!", show_alert=True)
        return

    await callback.message.edit_text("⏳ Генерую світ та характеристики... Зачекайте.")

    # Generate Scenario
    try:
        scenario = await ai_service.generate_scenario()
    except Exception as e:
        scenario = "Сталася помилка генерації сценарію. Уявіть, що настав зомбі-апокаліпсис."
        print(f"AI Error: {e}")

    room.scenario = scenario
    room.is_active = True
    
    # Assign characteristics
    for player in room.players:
        chars = generate_characteristics()
        player.profession = chars["profession"]
        player.health = chars["health"]
        player.hobby = chars["hobby"]
        player.phobia = chars["phobia"]
        player.inventory = chars["inventory"]
        player.fact = chars["fact"]
    
    await session.commit()
    
    # Notify all players
    bots_info = []

    for player in room.players:
        msg = (
            f"☢️ **ГРА ПОЧАЛАСЯ!** ☢️\n\n"
            f"📜 **Сценарій:**\n{scenario}\n\n"
            f"👤 **Твоя характеристика:**\n"
            f"🛠 Професія: {player.profession}\n"
            f"❤️ Здоров'я: {player.health}\n"
            f"🎨 Хобі: {player.hobby}\n"
            f"😱 Фобія: {player.phobia}\n"
            f"🎒 Інвентар: {player.inventory}\n"
            f"ℹ️ Факт: {player.fact}"
        )

        if player.user_id < 0:
            # It's a bot
            bot_info = (
                f"🤖 **Бот {abs(player.user_id)}**:\n"
                f"🛠 {player.profession}, ❤️ {player.health}, 🎨 {player.hobby}, "
                f"😱 {player.phobia}, 🎒 {player.inventory}, ℹ️ {player.fact}\n"
            )
            bots_info.append(bot_info)
            continue

        try:
            await bot.send_message(player.user_id, msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send to {player.user_id}: {e}")

    if bots_info:
        bots_summary = "\n".join(bots_info)
        try:
            await bot.send_message(
                room.creator_id, 
                f"📋 **Інформація про ботів:**\n\n{bots_summary}", 
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send bot summary to creator: {e}")

    await callback.message.answer("✅ Гра почалася! Всім розіслано характеристики.")

@router.callback_query(F.data.startswith("my_status_"))
async def my_status(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    
    result = await session.execute(
        select(Player).join(Room).where(Player.user_id == callback.from_user.id, Room.code == code)
    )
    player = result.scalar_one_or_none()
    
    if not player:
        await callback.answer("Ви не в грі.", show_alert=True)
        return
        
    if not player.profession: # Game hasn't started or chars not assigned
        await callback.answer("Гра ще не почалася або характеристики не роздані.", show_alert=True)
        return

    msg = (
        f"👤 **Твоя характеристика:**\n"
        f"🛠 Професія: {player.profession}\n"
        f"❤️ Здоров'я: {player.health}\n"
        f"🎨 Хобі: {player.hobby}\n"
        f"😱 Фобія: {player.phobia}\n"
        f"🎒 Інвентар: {player.inventory}\n"
        f"ℹ️ Факт: {player.fact}"
    )
    await callback.message.answer(msg, parse_mode="Markdown")
