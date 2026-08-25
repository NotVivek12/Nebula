import asyncio
import asyncpg
import sys

async def main():
    passwords = ['root', 'postgres', 'password', '', 'admin', '1234', '123456']
    
    for pwd in passwords:
        try:
            print(f"Trying password: '{pwd}'")
            conn = await asyncpg.connect(
                user='postgres',
                password=pwd,
                database='postgres',
                host='127.0.0.1',
                port=5432
            )
            print(f"SUCCESS! The correct password is '{pwd}'")
            await conn.close()
            sys.exit(0)
        except asyncpg.exceptions.InvalidPasswordError:
            continue
        except Exception as e:
            print(f"ERROR on {pwd}: {e}")
            sys.exit(1)
            
    print("Failed to find correct password.")
    sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
