import asyncio
import time
import uuid
import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
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

# Konstanta
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

async def panggil_api(session, url, data, proxy, token):
    """Melakukan permintaan API menggunakan data dan proxy yang diberikan."""
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
            logger.error(f"Gagal memanggil API dengan status {e.status} untuk proxy {proxy}: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Waktu habis saat memanggil API dengan proxy {proxy}")
        except Exception as e:
            logger.error(f"Error tak terduga saat memanggil API dengan proxy {proxy}: {e}")
    return None

async def ping(session, proxy, token):
    """Ping server untuk mengecek sesi."""
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

    response = await panggil_api(session, DOMAIN_API["PING"], data, proxy, token)

    if response and response.get("code") == 0:
        logger.info(f"Ping berhasil melalui proxy {proxy}")
        status_connect = CONNECTION_STATES["CONNECTED"]
    else:
        logger.error(f"Ping gagal melalui proxy {proxy}")
        status_connect = CONNECTION_STATES["DISCONNECTED"]

async def tampilkan_info_profil(session, proxy, token, semaphore):
    """Cek info sesi atau buat sesi baru jika diperlukan."""
    async with semaphore:
        global browser_id, account_info

        sesi_info = muat_info_sesi(proxy)
        if sesi_info:
            account_info = sesi_info
            logger.info(f"Info sesi dimuat untuk proxy {proxy}")
        else:
            browser_id = str(uuid.uuid4())
            logger.info(f"Membuat browser_id baru untuk proxy {proxy}: {browser_id}")
            response = await panggil_api(session, DOMAIN_API["SESSION"], {}, proxy, token)
            if response and response.get("code") == 0:
                account_info = response["data"]
                simpan_info_sesi(proxy, account_info)
                logger.info(f"Sesi dibuat dan disimpan untuk proxy {proxy}")
            else:
                logger.error(f"Gagal membuat sesi untuk proxy {proxy}")

        if account_info:
            await ping(session, proxy, token)

def muat_proxies(filename):
    """Muat daftar proxy dari file."""
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
            logger.info(f"{len(proxies)} proxy berhasil dimuat.")
            return proxies
    except Exception as e:
        logger.error(f"Gagal memuat proxy: {e}")
        return []

def muat_token(filename):
    """Muat daftar token dari file."""
    try:
        with open(filename, 'r') as file:
            tokens = file.read().splitlines()
            logger.info(f"{len(tokens)} token berhasil dimuat.")
            return tokens
    except Exception as e:
        logger.error(f"Gagal memuat token: {e}")
        return []

async def status(request):
    """Endpoint untuk cek status koneksi."""
    status_msg = {
        "status": status_connect,
        "account_info": account_info
    }
    return web.json_response(status_msg)

async def mulai_server_http():
    """Mulai server HTTP."""
    app = web.Application()
    app.add_routes([web.get('/status', status)])
    return app

async def main():
    proxies = muat_proxies(proxy_np)
    tokens = muat_token(token_np)

    if not proxies or not tokens:
        logger.error("Tidak ada proxy atau token yang tersedia.")
        return

    semaphore = asyncio.Semaphore(10)
    app = await mulai_server_http()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []
            for token in tokens:
                tasks.extend([
                    asyncio.create_task(tampilkan_info_profil(session, proxy, token, semaphore)) for proxy in proxies[:100]
                ])
                await asyncio.gather(*tasks)
                tasks.clear()
                await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program dihentikan oleh pengguna.")
