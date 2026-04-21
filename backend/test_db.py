import asyncio
import os
from dotenv import load_dotenv, find_dotenv
import redis.asyncio as aioredis
import asyncpg

load_dotenv(find_dotenv(usecwd=True), override=True)

async def test_redis():
    print("Testing Redis...")
    r = aioredis.from_url(os.getenv('REDIS_URL'), decode_responses=True, ssl_cert_reqs=None)
    res = await r.ping()
    print("Redis PING:", res)
    await r.aclose()

async def test_pg():
    print("Testing Postgres...")
    dsn = os.getenv("DATABASE_URL")
    ssl = "sslmode=require" in dsn
    if ssl:
        dsn = dsn.replace("?sslmode=require", "").replace("&sslmode=require", "")
    conn = await asyncpg.connect(dsn=dsn, ssl=ssl)
    res = await conn.fetchval("SELECT 1")
    print("Postgres SELECT 1:", res)
    await conn.close()

async def main():
    try:
        await test_redis()
    except Exception as e:
        print("Redis Error:", e)
        
    try:
        await test_pg()
    except Exception as e:
        print("Postgres Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
