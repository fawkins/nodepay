import asyncio
import time
import uuid
import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
from loguru import logger
from itertools import cycle

# ASCII art
ascii_art = """
.·:'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''':·.
: :  __  __                                                                : :
: : /  |/  |                                                               : :
: : $$ |$$ |                                                               : :
: : $$ |$$ |                                                               : :
: : $$/ $$/                                                                : :
: :                                                                        : :
: :  ________  ______   __       __  __    __  ______  __    __   ______   : :
: : /        |/      \ /  |  _  /  |/  |  /  |/      |/  \  /  | /      \  : :
: : $$$$$$$$//$$$$$$  |$$ | / \ $$ |$$ | /$$/ $$$$$$/ $$  \ $$ |/$$$$$$  | : :
: : $$ |__   $$ |__$$ |$$ |/$  \$$ |$$ |/$$/    $$ |  $$$  \$$ |$$ \__$$/  : :
: : $$    |  $$    $$ |$$ /$$$  $$ |$$  $$<     $$ |  $$$$  $$ |$$      \  : :
: : $$$$$/   $$$$$$$$ |$$ $$/$$ $$ |$$$$$  \    $$ |  $$ $$ $$ | $$$$$$  | : :
: : $$ |     $$ |  $$ |$$$$/  $$$$ |$$ |$$  \  _$$ |_ $$ |$$$$ |/  \__$$ | : :
: : $$ |     $$ |  $$ |$$$/    $$$ |$$ | $$  |/ $$   |$$ | $$$ |$$    $$/  : :
: : $$/      $$/   $$/ $$/      $$/ $$/   $$/ $$$$$$/ $$/   $$/  $$$$$$/   : :
: :                                                                        : :
: :                                                              __  __    : :
: :                                                             /  |/  |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$/ $$/    : :
: :                                                                        : :
'·:........................................................................:·'
"""

print(ascii_art)

# Constants
PING_INTERVAL = 60
RETRIES = 3
token_np = 'token.txt'
proxy_np = 'proxy.txt'

DOMAIN_API = {
    "SESSION": "https://api.nodepay.org/api/auth/session",
    "PING": "https://nw.nodepay.org/api/network/ping"
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}

async def panggil_api(session, url, data, token, proxy):
    """Make an API request using the provided data and proxy."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, seperti Gecko) Chrome/90.0.4430.212 Safari/537.36",
    }
    for attempt in range(RETRIES):
        try:
            async with session.post(url, json=data, headers=headers, proxy=proxy, timeout=ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"API call failed with status {e.status}: {e}")
        except asyncio.TimeoutError:
            logger.error("API call timed out")
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
    return None

async def ping(session, token, proxy):
    """Ping server to check the session."""
    global last_ping_time, status_connect

    current_time = time.time()
    if (current_time - last_ping_time.get("ping", 0)) < PING_INTERVAL:
        return

    last_ping_time["ping"] = current_time
    data = {
        "id": account_info.get("uid"),
        "browser_id": browser_id,
        "timestamp": int(current_time)
    }

    response = await panggil_api(session, DOMAIN_API["PING"], data, token, proxy)

    if response and response.get("code") == 0:
        logger.info("Ping successful")
        status_connect = CONNECTION_STATES["CONNECTED"]
    else:
        logger.error("Ping failed")
        status_connect = CONNECTION_STATES["DISCONNECTED"]

async def tampilkan_info_profil(session, token, proxy, semaphore):
    """Check session info or create a new session if needed."""
    async with semaphore:
        global browser_id, account_info

        sesi_info = muat_info_sesi()
        if sesi_info:
            account_info = sesi_info
            logger.info("Session info loaded")
        else:
            browser_id = str(uuid.uuid4())
            logger.info(f"Creating new browser_id: {browser_id}")
            response = await panggil_api(session, DOMAIN_API["SESSION"], {}, token, proxy)
            if response and response.get("code") == 0:
                account_info = response["data"]
                simpan_info_sesi(account_info)
                logger.info("Session created and saved")
            else:
                logger.error("Failed to create session")

        if account_info:
            await ping(session, token, proxy)

def muat_proxies(filename):
    """Load the proxy list from a file."""
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
            logger.info(f"{len(proxies)} proxies loaded successfully.")
            return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        return []

def muat_token(filename):
    """Load the token list from a file."""
    try:
        with open(filename, 'r') as file:
            tokens = file.read().splitlines()
            logger.info(f"{len(tokens)} tokens loaded successfully.")
            return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        return []

def muat_info_sesi():
    """Retrieve session information from storage."""
    return None

def simpan_info_sesi(data):
    """Save session information to storage."""
    logger.info("Session information saved")

async def status(request):
    """Endpoint to check connection status."""
    status_msg = {
        "status": status_connect,
        "account_info": account_info
    }
    return web.json_response(status_msg)

async def mulai_server_http():
    """Start HTTP server."""
    app = web.Application()
    app.add_routes([web.get('/status', status)])
    return app

async def main():
    tokens = muat_token(token_np)
    proxies = muat_proxies(proxy_np)
    if not tokens or not proxies:
        logger.error("No tokens or proxies available.")
        return

    proxy_cycle = cycle(proxies)  
    semaphore = asyncio.Semaphore(10)
    app = await mulai_server_http()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [
                asyncio.create_task(
                    tampilkan_info_profil(session, token, next(proxy_cycle), semaphore)
                ) for token in tokens
            ]
            await asyncio.gather(*tasks)
            await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program stopped by user.")
