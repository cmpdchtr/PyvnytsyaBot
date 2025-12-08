import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from pyvnytsya_bot.config import config
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def reset_db():
    print(f"🗑️  Dropping all tables in {config.DB_NAME}...")
    
    engine = create_async_engine(config.DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # Disable foreign key checks temporarily to drop in any order
            await conn.execute(text("DROP TABLE IF EXISTS players CASCADE;"))
            await conn.execute(text("DROP TABLE IF EXISTS rooms CASCADE;"))
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            
            print("\n✅ All tables dropped successfully!")
            print("🚀 Restart the bot to recreate them with the new schema.")
            
    except Exception as e:
        print("\n❌ Failed to drop tables!")
        print(f"   Error: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_db())
