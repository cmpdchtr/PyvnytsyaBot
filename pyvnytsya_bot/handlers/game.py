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
from ..utils.game_utils import generate_characteristics, format_player_card, escape_markdown
from ..keyboards.inline import game_dashboard, reveal_menu, voting_menu, admin_game_menu, main_menu

router = Router()

async def send_long_message(bot: Bot, chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup=None):
    """Splits long messages into chunks of 4096 characters."""
    MAX_LENGTH = 4096
    
    if len(text) <= MAX_LENGTH:
        await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        return

    # Split by chunks
    chunks = [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
    
    for i, chunk in enumerate(chunks):
        # Only attach markup to the last chunk
        markup = reply_markup if i == len(chunks) - 1 else None
        await bot.send_message(chat_id, chunk, parse_mode=parse_mode, reply_markup=markup)

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

    # Load Pack Data if exists
    pack_data = None
    pack_prompts = {}
    if room.pack_id:
        from ..database.models import GamePack
        import json
        pack_res = await session.execute(select(GamePack).where(GamePack.id == room.pack_id))
        pack = pack_res.scalar_one_or_none()
        if pack:
            try:
                full_pack = json.loads(pack.data)
                pack_data = full_pack.get("data", {})
                pack_prompts = full_pack.get("ai_prompts", {})
            except:
                print("Failed to load pack data")

    # Generate Scenario
    try:
        scenario_prompt = pack_prompts.get("scenario_prompt")
        scenario = await ai_service.generate_scenario(custom_prompt=scenario_prompt)
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
        chars = generate_characteristics(pack_data)
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
        player.revealed_count_round = 0
    
    await session.commit()
    
    # Notify all players
    for player in room.players:
        if player.user_id < 0: continue # Skip bots
        
        is_admin = (player.user_id == room.creator_id)
        
        try:
            # Send scenario separately to avoid message length limits
            # Convert AI double asterisks to single for legacy Markdown
            safe_scenario = scenario.replace("**", "*")
            await send_long_message(bot, player.user_id, f"📜 *Сценарій:*\n{safe_scenario}", parse_mode="Markdown")
            
            msg = (
                f"☢️ *ГРА ПОЧАЛАСЯ!* ☢️\n\n"
                f"🎯 *Ціль:* Вижити має {room.survivors_count} людей.\n"
                f"🔢 *Раунд 1:* Відкрийте 2 характеристики!"
            )
            await bot.send_message(player.user_id, msg, parse_mode="Markdown", reply_markup=game_dashboard(code, phase="revealing", is_admin=is_admin))
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

    limit = 2 if room.round_number == 1 else 1
    if player.revealed_count_round >= limit:
        await callback.answer(f"Ви вже відкрили {limit} карт(и) в цьому раунді!", show_alert=True)
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
    
    if not player:
        await callback.answer("Дія недоступна.", show_alert=True)
        return

    limit = 2 if room.round_number == 1 else 1
    if player.revealed_count_round >= limit:
        await callback.answer(f"Ліміт відкриття карт на цей раунд вичерпано ({limit}).", show_alert=True)
        return

    # Update DB
    current_revealed = player.revealed_traits.split(",") if player.revealed_traits else []
    if trait not in current_revealed:
        current_revealed.append(trait)
        player.revealed_traits = ",".join(current_revealed)
        player.revealed_count_round += 1
        await session.commit()
        
        trait_name = {
            "profession": "Професію", "health": "Здоров'я", "hobby": "Хобі",
            "phobia": "Фобію", "inventory": "Інвентар", "fact": "Факт",
            "bio": "Стать", "age": "Вік"
        }.get(trait, trait)

        # Notify everyone
        safe_name = escape_markdown(player.user.full_name or player.user.username)
        notification = f"📢 *{safe_name}* відкрив *{trait_name}*!"
        for p in room.players:
            if p.user_id > 0:
                try:
                    await bot.send_message(p.user_id, notification, parse_mode="Markdown")
                except: pass
    
    is_admin = (player.user_id == room.creator_id)
    await callback.message.edit_text("✅ Карта відкрита!", reply_markup=game_dashboard(code, phase=room.phase, is_admin=is_admin))
    
    # Check if all alive players revealed
    alive_players = [p for p in room.players if p.is_alive and p.user_id > 0] # Only real players need to act manually? 
    
    # Auto-reveal for bots ONLY if creator revealed
    if player.user_id == room.creator_id:
        bots = [p for p in room.players if p.is_alive and p.user_id < 0]
        for bot_player in bots:
            if bot_player.revealed_count_round < limit:
                # Bot reveals random unrevealed trait
                all_traits = ["profession", "health", "hobby", "phobia", "inventory", "fact", "bio", "age"]
                bot_revealed = bot_player.revealed_traits.split(",") if bot_player.revealed_traits else []
                available = [t for t in all_traits if t not in bot_revealed]
                
                if available:
                    chosen = random.choice(available)
                    bot_revealed.append(chosen)
                    bot_player.revealed_traits = ",".join(bot_revealed)
                    bot_player.revealed_count_round += 1
                    # Notify
                    # await bot.send_message(room.creator_id, f"🤖 Бот відкрив {chosen}") 

    await session.commit()

@router.callback_query(F.data.startswith("start_discuss_"))
async def start_discuss(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if room.creator_id != callback.from_user.id:
        await callback.answer("Тільки адмін може почати обговорення.", show_alert=True)
        return

    room.phase = "discussion"
    await session.commit()
    
    msg = "🗣 *Етап обговорення!*\nАргументуйте, чому ви маєте вижити, і хто має піти."
    
    for p in room.players:
        if p.user_id > 0:
            try:
                is_admin = (p.user_id == room.creator_id)
                await bot.send_message(p.user_id, msg, parse_mode="Markdown", reply_markup=game_dashboard(code, phase="discussion", is_alive=p.is_alive, is_admin=is_admin))
            except: pass
            
    await callback.message.answer("🗣 Обговорення розпочато!")

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
            f"👤 *Ваші характеристики:*\n\n{card_text}", 
            reply_markup=game_dashboard(code, phase=room.phase, is_alive=player.is_alive, is_admin=is_admin),
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

    safe_scenario = room.scenario.replace("**", "*")
    msg = (
        f"📜 *Сценарій:*\n{safe_scenario}\n\n"
        f"🎯 *Ціль:* Вижити має {room.survivors_count} людей.\n"
        f"🔢 *Раунд:* {room.round_number}"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(msg, reply_markup=game_dashboard(code, phase=room.phase, is_alive=is_alive, is_admin=is_admin), parse_mode="Markdown")
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
        await callback.message.edit_text("🎮 Панель гравця:", reply_markup=game_dashboard(code, phase=room.phase, is_alive=is_alive, is_admin=is_admin))
    await callback.answer()

# --- View Table ---

@router.callback_query(F.data.startswith("view_table_"))
async def view_table(callback: types.CallbackQuery, session: AsyncSession, bot: Bot):
    code = callback.data.split("_")[2]
    room = await get_room_with_players(session, code)
    
    if not room:
        await callback.answer("Кімнату не знайдено.", show_alert=True)
        return

    player = next((p for p in room.players if p.user_id == callback.from_user.id), None)
    is_alive = player.is_alive if player else False
    is_admin = (room.creator_id == callback.from_user.id)

    report = f"📋 *Стіл гравців (Раунд {room.round_number})*\n\n"
    
    for p in room.players:
        report += format_player_card(p, show_hidden=False) + "\n"
        
    with suppress(TelegramBadRequest):
        # Use send_long_message logic but for edit_text it's harder.
        # If report is too long, we can't edit_text easily into multiple messages.
        # We should probably send a new message if it's too long, or just truncate.
        # For now, let's try to send as new message if too long? No, that breaks flow.
        # Let's just hope table isn't > 4096 chars. 
        # If it is, we can split it.
        if len(report) > 4096:
             # Fallback: send as new messages
             await send_long_message(bot, callback.from_user.id, report, parse_mode="Markdown")
             # And update the original message to say "Table sent below"
             await callback.message.edit_text("📋 Стіл гравців надіслано окремим повідомленням 👇", reply_markup=game_dashboard(code, phase=room.phase, is_alive=is_alive, is_admin=is_admin))
        else:
             await callback.message.edit_text(report, reply_markup=game_dashboard(code, phase=room.phase, is_alive=is_alive, is_admin=is_admin), parse_mode="Markdown")
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
        await callback.message.edit_text("🎮 Панель гравця:", reply_markup=game_dashboard(code, phase=room.phase, is_alive=is_alive, is_admin=is_admin))
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
                    "🗳 *Час голосування!* Оберіть, кого вигнати з бункера.", 
                    reply_markup=voting_menu(code, room.players),
                    parse_mode="Markdown"
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
        safe_target_name = escape_markdown(target.user.full_name or target.user.username)
        await callback.message.edit_text(f"✅ Ви проголосували проти {safe_target_name}.")
    
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
    # Reveal all traits for loser
    all_traits = ["profession", "health", "hobby", "phobia", "inventory", "fact", "bio", "age"]
    loser.revealed_traits = ",".join(all_traits)
    
    room.round_number += 1
    room.phase = "revealing"
    
    # Reset round state
    for p in room.players:
        p.revealed_count_round = 0
        p.has_voted = False
        p.votes_received = 0
        
    await session.commit()
    
    # Notify result
    safe_loser_name = escape_markdown(loser.user.full_name or loser.user.username)
    msg = (
        f"💀 *Голосування завершено!*\n"
        f"Бункер покидає: *{safe_loser_name}*.\n\n"
        f"🔢 *Раунд {room.round_number} почався!*\n"
        f"Відкрийте 1 характеристику!"
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
                await bot.send_message(p.user_id, msg, parse_mode="Markdown", reply_markup=game_dashboard(room.code, phase="revealing", is_alive=p.is_alive, is_admin=is_admin))
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
    
    # Load Pack Data for Ending Prompt
    ending_prompt = None
    if room.pack_id:
        from ..database.models import GamePack
        import json
        pack_res = await session.execute(select(GamePack).where(GamePack.id == room.pack_id))
        pack = pack_res.scalar_one_or_none()
        if pack:
            try:
                full_pack = json.loads(pack.data)
                ending_prompt = full_pack.get("ai_prompts", {}).get("ending_prompt")
            except:
                pass

    ending = None
    try:
        # Add timeout to prevent hanging (30 seconds max)
        ending = await asyncio.wait_for(ai_service.generate_ending(survivors_desc, room.scenario, custom_prompt=ending_prompt), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"AI ending generation timed out after 30 seconds")
        ending = "Час кінчився, а кінцівка ще генерується. Вибачте, дещо пішло не так."
    except Exception as e:
        logger.error(f"AI ending generation failed: {e}")
        ending = "Всі вижили... або ні. AI втомився."
        
    for p in room.players:
        if p.user_id > 0:
            try:
                # Send ending separately
                safe_ending = ending.replace("**", "*")
                await send_long_message(bot, p.user_id, f"📜 *Історія виживання:*\n{safe_ending}", parse_mode="Markdown")
                
                final_msg = (
                    f"🏁 *ГРА ЗАВЕРШЕНА!* 🏁\n\n"
                    f"Дякую за гру!"
                )
                await bot.send_message(p.user_id, final_msg, parse_mode="Markdown", reply_markup=main_menu())
            except Exception as e:
                logger.error(f"Failed to send final message to {p.user_id}: {e}")

@router.message(F.text & ~F.text.startswith("/"))
async def game_chat(message: types.Message, session: AsyncSession, bot: Bot):
    """Handles in-game chat messages."""
    # Find active room for user
    stmt = (
        select(Room)
        .join(Player)
        .options(selectinload(Room.players).selectinload(Player.user))
        .where(
            Player.user_id == message.from_user.id,
            Room.is_active == True,
            Room.is_finished == False
        )
        .order_by(Room.id.desc())
    )
    result = await session.execute(stmt)
    room = result.scalars().first()

    if not room:
        return

    sender = next((p for p in room.players if p.user_id == message.from_user.id), None)
    
    # Optional: Check if dead players can talk. For now, allow it.
    # if not sender.is_alive:
    #    await message.reply("💀 Мертві не говорять...")
    #    return

    sender_name = message.from_user.full_name or message.from_user.username
    safe_sender_name = escape_markdown(sender_name)
    safe_text = escape_markdown(message.text)
    
    chat_msg = f"💬 *{safe_sender_name}*: {safe_text}"

    for p in room.players:
        if p.user_id > 0 and p.user_id != message.from_user.id: # Send to others
            try:
                await bot.send_message(p.user_id, chat_msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to send chat message to {p.user_id}: {e}")
