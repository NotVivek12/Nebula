import asyncio
import asyncpg
import sys

async def main():
    # Attempt to connect to the default 'postgres' database first to create the test db
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password='root',
            database='postgres',
            host='127.0.0.1',
            port=5432
        )
        print("Connected successfully to native postgres.")
        
        # Check if nebula_test exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'nebula_test'")
        if not exists:
            await conn.execute("CREATE DATABASE nebula_test")
            print("Created nebula_test database.")
        else:
            print("nebula_test database already exists.")
            
        await conn.close()
    except asyncpg.exceptions.InvalidPasswordError:
        print("ERROR: InvalidPasswordError. Make sure the native postgres password for user 'postgres' is 'postgres'.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
