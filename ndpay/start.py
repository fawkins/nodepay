import asyncio
import time
import uuid
import aiohttp
from aiohttp import web
from loguru import logger


ascii_art = """
.·:'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''':·.
: :  __  __                                                                : :
: : /  |/  |                                                               : :
: : $$ |$$ |                                                               : :
: : $$ |$$ |                                                               : :
: : $$/ $$/                                                                : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
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
: :                                                                        : :
: :                                                                        : :
: :                                                              __  __    : :
: :                                                             /  |/  |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$ |$$ |   : :
: :                                                             $$/ $$/    : :
: :                                                                        : :
: :                                                                        : :
: :                                                                        : :
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

async def call_api(session, url, data, proxy, token):
    """Perform API request using the given data and proxy."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    }

    try:
        async with session.post(url, json=data, headers=headers, proxy=f"http://{proxy}", timeout=10) as response:
            response.raise_for_status()  
            return await response.json()
    except aiohttp.ClientResponseError as e:
        logger.error(f"API call failed with status {e.status} for proxy {proxy}: {e.message}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout error when calling API with proxy {proxy}")
    except Exception as e:
        logger.error(f"Unexpected error during API call with proxy {proxy}: {e}")
    return None

async def ping(session, proxy, token):
    """Ping the server to check the session."""
    global last_ping_time, status_connect

    current_time = time.time()

    
    if proxy in last_ping_time and (current_time - last_ping_time[proxy]) < PING_INTERVAL:
        return

    last_ping_time[proxy] = current_time
    data = {
        "id": account_info.get("uid"),
        "browser_id": browser_id,
        "timestamp": int(current_time)
    }

    response = await call_api(session, DOMAIN_API["PING"], data, proxy, token)

    if response and response.get("code") == 0:
        logger.info(f"Ping successful via proxy {proxy}")
        status_connect = CONNECTION_STATES["CONNECTED"]
    else:
        logger.error(f"Ping failed via proxy {proxy}")
        status_connect = CONNECTION_STATES["DISCONNECTED"]

async def render_profile_info(session, proxy, token, semaphore):
    """Check session info, or create a new session if needed."""
    async with semaphore:  
        global browser_id, account_info

        session_info = load_session_info(proxy)

        if session_info:
            account_info = session_info
            logger.info(f"Loaded session info for proxy {proxy}")
        else:
            browser_id = str(uuid.uuid4())  
            logger.info(f"Generated new browser_id for proxy {proxy}: {browser_id}")
            response = await call_api(session, DOMAIN_API["SESSION"], {}, proxy, token)
            if response and response.get("code") == 0:
                account_info = response["data"]
                save_session_info(proxy, account_info)
                logger.info(f"Session created and saved for proxy {proxy}")
            else:
                logger.error(f"Failed to create session for proxy {proxy}")

        if account_info:
            await ping(session, proxy, token)

def load_proxies(filename):
    """Load proxy list from file."""
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
            logger.info(f"Loaded {len(proxies)} proxies.")
            return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        return []

def load_tokens(filename):
    """Load tokens from file."""
    try:
        with open(filename, 'r') as file:
            tokens = file.read().splitlines()
            logger.info(f"Loaded {len(tokens)} tokens.")
            return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        return []

def save_session_info(proxy, data):
    """Placeholder to save session info."""
    logger.info(f"Saving session info for proxy {proxy}")

def load_session_info(proxy):
    """Placeholder to load session info from storage."""
    return None


async def status(request):
    """Endpoint to check the status of the connection."""
    status_msg = {
        "status": status_connect,
        "account_info": account_info
    }
    return web.json_response(status_msg)

async def start_http_server():
    """Start the HTTP server."""
    app = web.Application()
    app.add_routes([web.get('/status', status)])
    return app

async def main():
    proxies = load_proxies(proxy_np)
    tokens = load_tokens(token_np)

    if not proxies or not tokens:
        logger.error("No proxies or tokens available.")
        return

    semaphore = asyncio.Semaphore(10)  

    
    app = await start_http_server()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []
            for token in tokens:
                
                tasks.extend([asyncio.create_task(render_profile_info(session, proxy, token, semaphore)) for proxy in proxies[:100]])
                await asyncio.gather(*tasks)
                tasks.clear() 
                await asyncio.sleep(10)  

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
