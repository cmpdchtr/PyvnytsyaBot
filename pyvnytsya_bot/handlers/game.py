from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest
from contextlib import suppress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import random
import asyncio
import logging

logger = logging.getLogger(__name__)

from ..database.models import Room, Player
from ..services.gemini import ai_service
from ..utils.game_utils import generate_characteristics, format_player_card
from ..keyboards.inline import game_dashboard, reveal_menu, voting_menu, admin_game_menu, main_menu

router = Router()

async def get_room_with_players(session, code):
    result = await session.execute(
        select(Room).options(selectinload(Room.players).selectinload(Player.user)).where(Room.code == code)
    )
    return result.scalar_one_or_none()

@router.callback_query(F.data.startswith("start_game_"))
async def start_game(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room or room.creator_id != callback.from_user.id:
        await callback.answer("Помилка доступу.", show_alert=True)
        return

    players_count = len(room.players)
    if players_count < 2: # Allow 2 for testing
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
    room.phase = "revealing"
    room.round_number = 1
    room.survivors_count = max(1, players_count // 2) # Half survive
    
    # Assign characteristics
    for player in room.players:
        chars = generate_characteristics()
        player.profession = chars["profession"]
        player.health = chars["health"]
        player.hobby = chars["hobby"]
        player.phobia = chars["phobia"]
        player.inventory = chars["inventory"]
        player.fact = chars["fact"]
        player.age = chars["age"]
        player.bio = chars["bio"]
        player.is_alive = True
        player.revealed_traits = ""
        player.has_revealed_card = False
    
    await session.commit()
    
    # Notify all players
    for player in room.players:
        if player.user_id < 0: continue # Skip bots
        
        is_admin = (player.user_id == room.creator_id)
        
        msg = (
            f"☢️ **ГРА ПОЧАЛАСЯ!** ☢️\n\n"
            f"📜 **Сценарій:**\n{scenario}\n\n"
            f"🎯 **Ціль:** Вижити має {room.survivors_count} людей.\n"
            f"🔢 **Раунд 1:** Відкрийте одну характеристику!"
        )
        try:
            await bot.send_message(player.user_id, msg, parse_mode="Markdown", reply_markup=game_dashboard(code, is_admin=is_admin))
        except Exception as e:
            print(f"Failed to send to {player.user_id}: {e}")

    await callback.message.delete() # Remove old admin panel message

# --- Reveal Logic ---

@router.callback_query(F.data.startswith("reveal_menu_"))
async def open_reveal_menu(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    if not player or not player.is_alive:
        await callback.answer("Ви не у грі або мертві.", show_alert=True)
        return

    if room.phase != "revealing":
        await callback.answer("Зараз не час відкривати карти!", show_alert=True)
        return

    if player.has_revealed_card:
        await callback.answer("Ви вже відкрили карту в цьому раунді!", show_alert=True)
        return

    revealed = player.revealed_traits.split(",") if player.revealed_traits else []
    await callback.message.edit_text("Виберіть характеристику для відкриття:", reply_markup=reveal_menu(code, revealed))

@router.callback_query(F.data.startswith("reveal_"))
async def process_reveal(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    # data format: reveal_{trait}_{code}
    parts = callback.data.split("_")
    trait = parts[1]
    code = parts[2]
    
    if trait == "menu": return # Handle edge case if pattern matches reveal_menu

    room = await get_room_with_players(session, code)
    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    
    if not player or player.has_revealed_card:
        await callback.answer("Дія недоступна.", show_alert=True)
        return

    # Update DB
    current_revealed = player.revealed_traits.split(",") if player.revealed_traits else []
    if trait not in current_revealed:
        current_revealed.append(trait)
        player.revealed_traits = ",".join(current_revealed)
        player.has_revealed_card = True
        await session.commit()
        
        trait_name = {
            "profession": "Професію", "health": "Здоров'я", "hobby": "Хобі",
            "phobia": "Фобію", "inventory": "Інвентар", "fact": "Факт",
            "bio": "Стать", "age": "Вік"
        }.get(trait, trait)

        # Notify everyone
        notification = f"📢 **{player.user.full_name}** відкрив **{trait_name}**!"
        for p in room.players:
            if p.user_id > 0:
                try:
                    await bot.send_message(p.user_id, notification, parse_mode="Markdown")
                except: pass
    
    await callback.message.edit_text("✅ Карта відкрита!", reply_markup=game_dashboard(code, is_admin=(player.user_id == room.creator_id)))
    
    # Check if all alive players revealed
    alive_players = [p for p in room.players if p.is_alive and p.user_id > 0] # Only real players need to act manually? 
    
    # Auto-reveal for bots ONLY if creator revealed
    if player.user_id == room.creator_id:
        bots = [p for p in room.players if p.is_alive and p.user_id < 0 and not p.has_revealed_card]
        for bot_player in bots:
            # Bot reveals random unrevealed trait
            all_traits = ["profession", "health", "hobby", "phobia", "inventory", "fact", "bio", "age"]
            bot_revealed = bot_player.revealed_traits.split(",") if bot_player.revealed_traits else []
            available = [t for t in all_traits if t not in bot_revealed]
            
            if available:
                chosen = random.choice(available)
                bot_revealed.append(chosen)
                bot_player.revealed_traits = ",".join(bot_revealed)
                bot_player.has_revealed_card = True
                # Notify
                # await bot.send_message(room.creator_id, f"🤖 Бот відкрив {chosen}") 

    await session.commit()

@router.callback_query(F.data.startswith("my_status_"))
async def my_status(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    if not player:
        await callback.answer("Ви не у грі.", show_alert=True)
        return
        
    card_text = format_player_card(player, show_hidden=True)
    is_admin = (room.creator_id == callback.from_user.id)
    
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            f"👤 **Ваші характеристики:**\n\n{card_text}", 
            reply_markup=game_dashboard(code, is_alive=player.is_alive, is_admin=is_admin),
            parse_mode="Markdown"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("view_scenario_"))
async def view_scenario(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    is_alive = player.is_alive if player else False
    is_admin = (room.creator_id == callback.from_user.id)

    msg = (
        f"📜 **Сценарій:**\n{room.scenario}\n\n"
        f"🎯 **Ціль:** Вижити має {room.survivors_count} людей.\n"
        f"🔢 **Раунд:** {room.round_number}"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(msg, reply_markup=game_dashboard(code, is_alive=is_alive, is_admin=is_admin), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_game_"))
async def back_to_game(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[3]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    is_alive = player.is_alive if player else False
    is_admin = (room.creator_id == callback.from_user.id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text("🎮 Панель гравця:", reply_markup=game_dashboard(code, is_alive=is_alive, is_admin=is_admin))
    await callback.answer()

# --- View Table ---

@router.callback_query(F.data.startswith("view_table_"))
async def view_table(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    is_alive = player.is_alive if player else False
    is_admin = (room.creator_id == callback.from_user.id)

    report = f"📋 **Стіл гравців (Раунд {room.round_number})**\n\n"
    
    for p in room.players:
        report += format_player_card(p, show_hidden=False) + "\n"
        
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(report, reply_markup=game_dashboard(code, is_alive=is_alive, is_admin=is_admin), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("refresh_game_"))
async def refresh_game(callback: types.CallbackQuery, session: AsyncSession):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    is_alive = player.is_alive if player else False
    is_admin = (room.creator_id == callback.from_user.id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text("🎮 Панель гравця:", reply_markup=game_dashboard(code, is_alive=is_alive, is_admin=is_admin))
    await callback.answer()

# --- Voting Logic ---

@router.callback_query(F.data.startswith("force_vote_"))
async def start_voting_phase(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if room.creator_id != callback.from_user.id:
        await callback.answer("Тільки адмін може почати голосування.", show_alert=True)
        return

    room.phase = "voting"
    # Reset votes
    for p in room.players:
        p.has_voted = False
        p.votes_received = 0
    
    await session.commit()
    
    # Notify
    for p in room.players:
        if p.user_id > 0 and p.is_alive:
            try:
                await bot.send_message(
                    p.user_id, 
                    "🗳 **Час голосування!** Оберіть, кого вигнати з бункера.", 
                    reply_markup=voting_menu(code, room.players)
                )
            except: pass
            
    await callback.message.answer("🗳 Голосування розпочато!")

@router.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    # vote_{target_id}_{code}
    parts = callback.data.split("_")
    target_id = int(parts[1])
    code = parts[2]
    
    room = await get_room_with_players(session, code)
    voter = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    
    if not voter or not voter.is_alive or voter.has_voted:
        await callback.answer("Ви не можете голосувати.", show_alert=True)
        return

    # Register vote
    target = next((p for p in room.players if p.id == target_id), None)
    if target:
        target.votes_received += 1
        voter.has_voted = True
        
        # If creator voted, bots follow
        if voter.user_id == room.creator_id:
            alive_bots = [p for p in room.players if p.is_alive and p.user_id < 0]
            for bot_p in alive_bots:
                if not bot_p.has_voted:
                    target.votes_received += 1
                    bot_p.has_voted = True
            await callback.message.answer(f"🤖 Боти підтримали ваш вибір!")

        await session.commit()
        await callback.message.edit_text(f"✅ Ви проголосували проти {target.user.full_name or target.user.username}.")
    
    # Check if all voted (bots vote randomly)
    alive_real_players = [p for p in room.players if p.is_alive and p.user_id > 0]
    if all(p.has_voted for p in alive_real_players):
        await finish_voting(room, session, bot)

async def finish_voting(room, session, bot):
    # Bots vote randomly
    alive_bots = [p for p in room.players if p.is_alive and p.user_id < 0]
    alive_targets = [p for p in room.players if p.is_alive]
    
    for bot_player in alive_bots:
        if not bot_player.has_voted and alive_targets:
            target = random.choice(alive_targets)
            target.votes_received += 1
            bot_player.has_voted = True
    
    await session.commit()
    
    # Calculate loser
    loser = max(alive_targets, key=lambda p: p.votes_received)
    # Handle ties? For now, just pick one.
    
    loser.is_alive = False
    room.round_number += 1
    room.phase = "revealing"
    
    # Reset round state
    for p in room.players:
        p.has_revealed_card = False
        p.has_voted = False
        p.votes_received = 0
        
    await session.commit()
    
    # Notify result
    msg = (
        f"💀 **Голосування завершено!**\n"
        f"Бункер покидає: **{loser.user.full_name or loser.user.username}**.\n\n"
        f"🔢 **Раунд {room.round_number} почався!**"
    )
    
    # Check Game Over
    alive_count = len([p for p in room.players if p.is_alive])
    if alive_count <= room.survivors_count:
        await end_game(room, session, bot)
        return

    for p in room.players:
        if p.user_id > 0:
            try:
                is_admin = (p.user_id == room.creator_id)
                await bot.send_message(p.user_id, msg, parse_mode="Markdown", reply_markup=game_dashboard(room.code, p.is_alive, is_admin=is_admin))
            except: pass

async def end_game(room, session, bot):
    room.is_finished = True
    room.phase = "finished"
    await session.commit()
    
    survivors = [p for p in room.players if p.is_alive]
    survivors_desc = "\n".join([format_player_card(p, show_hidden=True) for p in survivors])
    
    try:
        await bot.send_message(room.creator_id, "🏁 Гра завершена! Генерую кінцівку...")
    except Exception as e:
        logger.error(f"Failed to send status message: {e}")
    
    ending = None
    try:
        # Add timeout to prevent hanging (30 seconds max)
        ending = await asyncio.wait_for(ai_service.generate_ending(survivors_desc), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"AI ending generation timed out after 30 seconds")
        ending = "Час кінчився, а кінцівка ще генерується. Вибачте, дещо пішло не так."
    except Exception as e:
        logger.error(f"AI ending generation failed: {e}")
        ending = "Всі вижили... або ні. AI втомився."
        
    final_msg = (
        f"🏁 **ГРА ЗАВЕРШЕНА!** 🏁\n\n"
        f"📜 **Історія виживання:**\n{ending}\n\n"
        f"Дякую за гру!"
    )
    
    for p in room.players:
        if p.user_id > 0:
            try:
                await bot.send_message(p.user_id, final_msg, parse_mode="Markdown", reply_markup=main_menu())
            except Exception as e:
                logger.error(f"Failed to send final message to {p.user_id}: {e}")
