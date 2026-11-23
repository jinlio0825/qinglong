#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 电信全任务（金豆/爱音乐/话费兑换）
定时规则
cron: 5 9,13,23 * * *

电信全任务（单文件，青龙可直接用）

依赖:
    requests pycryptodome certifi aiohttp curl_cffi
    playwright（金豆短视频需要，首次运行自动装并下载 chromium）

  以上全部会首次运行时自动安装（见 _ensure_deps）。

环境变量见下文「账号配置」。

═══════════════════════════════════════════════════════════════
包含任务
═══════════════════════════════════════════════════════════════
  jinyu        金豆权益    （源：0点权益.py）
  qiandao      金豆签到    成长乐园每日签到
  renwu        金豆任务    金豆商城任务（访问类自动完成）
  duanshipin   金豆短视频  星播客社区看视频（需 playwright）
  aiyinyue     爱音乐     （源：爱音乐领取奖励.py）
  huafei       话费兑换    （源：话费兑换.py）

已移除：
  zhiling      天翼智铃    活动已下线（服务端返回「活动已结束」/「接口不存在」）
  choujiang    天天抽奖    活动已下线（服务端返回「无进行中期数」）

未包含（需瑞数动态签名，纯脚本无法复现）：
  517换新礼 / 517集卡

═══════════════════════════════════════════════════════════════
账号配置（二选一）
═══════════════════════════════════════════════════════════════
【Token 模式】推荐，跳过账密，不需要模拟器
    CT_TOKEN = 手机号#token#userId
    多账号用 & 分隔：
    CT_TOKEN = 手机号1#token1#userId1&手机号2#token2#userId2

【账密模式】需要电信服务密码（6位数字）
    CT_ACCOUNT = 手机号#服务密码

有 Token 就优先用 Token。
兼容旧变量名 chinaTelecomToken / chinaTelecomAccount（青龙会禁以 china 开头的变量名，
所以青龙里请用 CT_TOKEN / CT_ACCOUNT）。

═══════════════════════════════════════════════════════════════
其它环境变量
═══════════════════════════════════════════════════════════════
  reqNUM                金豆兑换次数（默认 50）
  INVITE_TASK           爱音乐邀请任务
  UNICOM_TELECOM_NOWAIT 设 1 跳过金豆权益的等待

═══════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════
  python 电信全任务.py            跑全部
  python 电信全任务.py jinyu      只跑一个
  python 电信全任务.py --list     列出任务

═══════════════════════════════════════════════════════════════
代码结构
═══════════════════════════════════════════════════════════════
每个源脚本包成一个函数 mod_xxx，函数体内真实展开它的全部代码。
调用时返回 locals()，外面按名字取 main / run 入口。

为什么用函数作用域：
  1. 同名函数不冲突
     encrypt / decrypt / md5 / rsa_encrypt / do_login 在多脚本里都有，
     实现完全不同。闭包作用域天然隔离。
  2. import 不冲突
     爱音乐用 curl_cffi.requests，会覆盖全局 requests。
     函数内 import 只在本作用域生效。
  3. 可读可改
     代码真实展开，traceback 指向真实行号。

限制：函数内不能有 global。源脚本里唯一的 global（话费兑换的
rs/h/wt）都是只读，已在生成时注释掉。
"""
import asyncio
import base64
import binascii
import datetime
import hashlib
import json
import os
import random
import re
import ssl
import string
import sys
import time
import urllib.parse
from collections import OrderedDict
from http import cookiejar

try:
    import requests
except ImportError:
    raise SystemExit('缺少依赖: pip install requests')


def _ensure_deps():
    """缺依赖时尝试自动安装（青龙环境常见）。"""
    import subprocess
    missing = []
    for mod, pkg in [('requests', 'requests'),
                     ('Crypto', 'pycryptodome'),
                     ('certifi', 'certifi'),
                     ('aiohttp', 'aiohttp'),
                     ('curl_cffi', 'curl_cffi')]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f'[*] 缺少依赖 {missing}，尝试自动安装...')
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '-q'] + missing)
            print('[*] 安装完成')
        except Exception as e:
            raise SystemExit(
                '缺少依赖: %s\n自动安装失败(%s)，请手动执行: pip install %s'
                % (missing, e, ' '.join(missing)))

    # playwright 是可选的（只有 duanshipin 模块需要）
    try:
        import playwright  # noqa: F401
    except ImportError:
        print('[*] 未安装 playwright（金豆短视频模块需要），尝试安装...')
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '-q', 'playwright'])
            print('[*] playwright 安装完成')
        except Exception:
            print('[!] playwright 安装失败，duanshipin 模块将跳过')


def install_browser_once():
    """首次运行时下载 chromium（约 130MB），已存在则跳过。

    `playwright install` 会按当前操作系统自动选择平台包：
      Windows → win64，Linux（青龙）→ linux64
    无需手动区分。
    """
    import glob
    import subprocess
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    def _try_launch():
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch(headless=True)
                b.close()
            return True, ''
        except Exception as e:
            return False, str(e)

    ok, err = _try_launch()
    if ok:
        return True

    # 浏览器二进制是否已下载过？（已下载就别再下一遍 199MB）
    cache_dirs = [
        os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''),
        os.path.expanduser('~/.cache/ms-playwright'),
        os.path.expanduser('~/AppData/Local/ms-playwright'),
    ]
    already = False
    for d in cache_dirs:
        if not d:
            continue
        try:
            if glob.glob(os.path.join(d, 'chromium-*')) or \
                    glob.glob(os.path.join(d, 'chromium_headless_shell-*')):
                already = True
                break
        except Exception:
            pass

    if already:
        # 浏览器在，但起不来 → 缺系统库，不再重复下载
        print('[!] chromium 已下载但无法启动:', err[:160])
        _print_lib_hint(err)
        return False

    # 真没下载过，才走下载
    env = dict(os.environ)
    if not env.get('PLAYWRIGHT_DOWNLOAD_HOST'):
        env['PLAYWRIGHT_DOWNLOAD_HOST'] = \
            'https://npmmirror.com/mirrors/playwright'
        print('[*] 使用国内镜像下载 chromium')

    print('[*] 首次使用，正在下载 chromium（约 130MB，只下一次）...')
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'playwright', 'install', 'chromium'],
            env=env)
        print('[*] chromium 下载完成')
    except Exception as e:
        print('[!] chromium 下载失败:', str(e)[:200])
        return False

    ok, err = _try_launch()
    if ok:
        return True
    print('[!] chromium 无法启动:', err[:200])
    _print_lib_hint(err)
    return False


def _print_lib_hint(err_msg):
    """缺系统库时给出准确指引。"""
    keys = ('libnss3', 'libatk', 'libcups', 'libgbm', 'libxkbcommon',
            'libxcomposite', 'libxdamage', 'libxrandr', 'libasound',
            'shared librar', 'cannot open shared', 'Missing X server',
            'error while loading shared libraries')
    if any(k in err_msg for k in keys):
        print('    这是缺系统库，不是缺浏览器。Debian/Ubuntu 执行:')
        print('      python -m playwright install-deps chromium')
        print('    或手动:')
        print('      apt-get update && apt-get install -y libnss3 '
              'libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 '
              'libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 '
              'libxrandr2 libgbm1 libasound2')


_ensure_deps()

try:
    from Crypto.Cipher import AES, DES, DES3, PKCS1_v1_5
    from Crypto.PublicKey import RSA
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    raise SystemExit('缺少依赖: pip install pycryptodome')


# ============================================================
# Token 模式支持
# ============================================================
# 电信账密登录要「服务密码」，很多人没设过或忘了。
# 登录成功返回 loginSuccessResult.token + userId，这两个可复用，
# 直接跳过账密验证。
#
# 环境变量 chinaTelecomToken = 手机号#token#userId
# 多账号用 & 或 @ 分隔

def get_env_accounts_raw():
    """账密原始串, 兼容 CT_ACCOUNT / chinaTelecomAccount"""
    return (os.environ.get('CT_ACCOUNT', '').strip()
            or os.environ.get('chinaTelecomAccount', '').strip())


def parse_token_accounts():
    """解析 chinaTelecomToken → {手机号: (token, userId)}

    格式: 手机号#token#userId
    多账号用 & 或 @ 或换行分隔。

    青龙环境变量名建议用 CT_TOKEN（青龙会禁用以 china 开头的变量名），
    两个名字都认，CT_TOKEN 优先。

    注意 token 里可能含 # 吗? 不会 —— token 是 Base64, 字符集 A-Za-z0-9+/=,
    不含 #。所以按 # 切分是安全的。
    """
    out = {}
    raw = (os.environ.get('CT_TOKEN', '').strip()
           or os.environ.get('chinaTelecomToken', '').strip())
    if not raw:
        return out
    for item in re.split(r'[&@\n,]', raw):
        item = item.strip()
        if not item:
            continue
        parts = item.split('#')
        if len(parts) >= 3:
            out[parts[0].strip()] = (parts[1].strip(), parts[2].strip())
        elif len(parts) == 2:
            out[parts[0].strip()] = (parts[1].strip(), '')
    return out


def get_token_for(phone):
    """取指定手机号的 (token, userId)"""
    return parse_token_accounts().get(str(phone).strip(), (None, None))


def parse_account_sources():
    """
    合并两种账号来源, 返回 {手机号: 密码} 字典。
    - chinaTelecomAccount : 手机号#密码  (账密模式, 多账号用 & 或换行分隔)
    - chinaTelecomToken   : 手机号#token#userId (Token 模式, 密码留空)

    Token 模式优先级更高: 同一手机号若两边都有, 以 Token 模式为准
    (登录时 get_token_for 会优先命中)。
    """
    out = {}
    raw = get_env_accounts_raw()
    if raw:
        normalized = raw.replace("\r", "\n").replace("&", "\n")
        for part in normalized.split("\n"):
            item = part.strip()
            if not item or "#" not in item:
                continue
            phone, password = item.split("#", 1)
            phone, password = phone.strip(), password.strip()
            if phone:
                out[phone] = password
    for phone in parse_token_accounts().keys():
        out[phone] = ""
    return out


# ============================================================
# 客户端标识常量
# ============================================================
# App 实际下发的 clientType（从 com.ct.base.common.Variable.mAppVersion 读取）:
#   #<版本>#<渠道>#<机型>#
# 渠道号是渠道包决定的：华为/小米等不同渠道包渠道号不同。
# 默认取本机安装的渠道包（channel45）。如换渠道包请改这里。
CT_CLIENT_TYPE = os.environ.get(
    "CT_CLIENT_TYPE", "#13.5.0#channel45#Samsung SM-A5260#").strip()

# getSingle 请求里的 Url 字段: App 侧是 UtilEncryption.encode("4a6862274835b451")
# 即 3DES/CBC/全零IV + 小写 hex，明文直接发会返回 ResultCode=1「服务器发生异常」。
CT_TARGET_URL_PLAIN = "4a6862274835b451"

# ---- 终端颜色（源脚本合并时丢失，此处补回）----
class Color:
    ENDC = "[0m"
    MINT = "[92m"
    LIGHT_PINK = "[95m"
    YELLOW = "[93m"
    RED = "[91m"
    CYAN = "[96m"


# ---- 成长乐园（wappark）加密参数 ----
# 逆向自 hlt1995/qlScripts 的 ChinaTelecomyyt.js
QD_AES_KEY = b"34d7cb0bcdf07523"          # sign 接口 encode 用
QD_PUB_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+ugG5A8cZ3FqUKDwM57GM4io6"
    "JGcStivT8UdGt67PEOihLZTw3P7371+N47PrmsCpnTRzbTgcupKtUv8ImZalYk65d"
    "U8rjC/ridwhw9ffW2LBwvkEnDkkKKRi2liWIItDftJVBiWOh17o6gfbPoNrWORcAd"
    "cbpk2L+udld5kZNwIDAQAB"
)                                          # para 参数用（RSA-1024）
QD_PUB_PEM = ("-----BEGIN PUBLIC KEY-----\n" + QD_PUB_B64
              + "\n-----END PUBLIC KEY-----")
# 成长乐园页面用这个 UA（App 的 CtClient UA 会被瑞数拦）
QD_UA = ("Mozilla/5.0 (Linux; U; Android 12; zh-cn; ONEPLUS A9000 "
         "Build/QKQ1.190716.003) AppleWebKit/533.1 (KHTML, like Gecko) "
         "Version/5.0 Mobile Safari/533.1")
QD_BASE = "https://wappark.189.cn"


def qd_encode(obj):
    """sign 接口 encode: AES-128-ECB/PKCS7 -> 小写 hex"""
    if not isinstance(obj, str):
        obj = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    return AES.new(QD_AES_KEY, AES.MODE_ECB).encrypt(pad(obj.encode(), 16)).hex()


def qd_para(obj):
    """所有 para 参数: RSA-1024/PKCS1 -> 小写 hex"""
    if not isinstance(obj, str):
        obj = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    key = RSA.import_key(QD_PUB_PEM)
    return binascii.hexlify(PKCS1_v1_5.new(key).encrypt(obj.encode())).decode()

# 话费兑换的去重记录（内容是 JSON，不是日志，故用 .json）。
# 记录「哪个号兑过哪个面额」，防止重复兑换。
# 青龙里脚本目录可能只读，写失败不影响主流程。
CT_HUAFEI_STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "chinaTelecom_huafei_state.json")
# 旧版本用 .log 后缀存同一份数据，保留读取以兼容已运行的机器
CT_HUAFEI_LOG_LEGACY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "电信金豆换话费.log")


def huafei_log_read():
    for path in (CT_HUAFEI_STATE, CT_HUAFEI_LOG_LEGACY):
        try:
            with open(path, encoding="utf-8") as fr:
                return json.load(fr)
        except Exception:
            continue
    return {}


def huafei_log_write(data):
    for path in (CT_HUAFEI_STATE, CT_HUAFEI_LOG_LEGACY):
        try:
            with open(path, "w", encoding="utf-8") as fw:
                json.dump(data, fw, ensure_ascii=False)
            return
        except Exception:
            continue


def mod_jinyu():
    """金豆权益"""

    # ---- 本模块的 import ----
    import os
    import re
    import sys
    import ssl
    import time
    import json
    import base64
    import random
    import certifi
    import aiohttp
    import asyncio
    import datetime
    import requests
    import binascii
    from http import cookiejar
    from Crypto.Cipher import DES3
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.Util.Padding import pad, unpad
    from aiohttp import ClientSession, TCPConnector

    stop_all_event = asyncio.Event()  # 控制所有任务停止

    LOGO = f'''
      ✧･ﾟ: *✧･ﾟ:*  电信金豆换话费脚本  ✧･ﾟ: *✧･ﾟ:*
    '''

    run_num = os.environ.get('reqNUM') or "50"

    MAX_RETRIES = 3

    RATE_LIMIT = 15  # 每秒请求数限制

    yf = datetime.datetime.now().strftime("%Y%m")

    dhjl = huafei_log_read()

    if yf not in dhjl:
        dhjl[yf] = {}

    # ---- class RateLimiter ----
    class RateLimiter:
        def __init__(self, rate_limit):
            self.rate_limit = rate_limit
            self.tokens = rate_limit
            self.updated_at = time.monotonic()

        async def acquire(self):
            while self.tokens < 1:
                self.add_new_tokens()
                await asyncio.sleep(0.1)
            self.tokens -= 1

        def add_new_tokens(self):
            now = time.monotonic()
            time_since_update = now - self.updated_at
            new_tokens = time_since_update * self.rate_limit
            if new_tokens > 1:
                self.tokens = min(self.tokens + new_tokens, self.rate_limit)
                self.updated_at = now

    # ---- class AsyncSessionManager ----
    class AsyncSessionManager:
        def __init__(self):
            self.session = None
            self.connector = None

        async def __aenter__(self):
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
            self.connector = TCPConnector(ssl=ssl_context, limit=1000)
            self.session = ClientSession(connector=self.connector)
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.session.close()
            await self.connector.close()

    # ---- def retry_request ----
    async def retry_request(session, method, url, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                await asyncio.sleep(1)
                async with session.request(method, url, **kwargs) as response:
                    return await response.json()

            except (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError) as e:
                print(f"{Color.LIGHT_PINK}💔 请求失败，第 {attempt + 1} 次重试: {e}{Color.ENDC}")
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    # ---- class BlockAll ----
    class BlockAll(cookiejar.CookiePolicy):
        return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
        netscape = True
        rfc2965 = hide_cookie2 = False

    # ---- def printn ----
    def printn(m):
        current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f'\n🌸 [{current_time} {m}]')

    context = ssl.create_default_context()

    context.set_ciphers('DEFAULT@SECLEVEL=1')  # 低安全级别0/1

    context.check_hostname = False  # 禁用主机

    context.verify_mode = ssl.CERT_NONE  # 禁用证书

    # ---- class DESAdapter ----
    class DESAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs['ssl_context'] = context
            return super().init_poolmanager(*args, **kwargs)

    requests.packages.urllib3.disable_warnings()

    ss = requests.session()

    ss.headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36",
        "Referer": "https://wapact.189.cn:9001/JinDouMall/JinDouMall_independentDetails.html"}

    ss.mount('https://', DESAdapter())

    ss.cookies.set_policy(BlockAll())

    runTime = 0

    key = b'1234567`90koiuyhgtfrdews'

    iv = 8 * b'\0'

    public_key_b64 = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBkLT15ThVgz6/NOl6s8GNPofdWzWbCkWnkaAm7O2LjkM1H7dMvzkiqdxU02jamGRHLX/ZNMCXHnPcW/sDhiFCBN18qFvy8g6VYb9QtroI09e176s+ZCtiv7hbin2cCTj99iUpnEloZm19lwHyo69u5UMiPMpq0/XKBO8lYhN/gwIDAQAB
    -----END PUBLIC KEY-----'''

    public_key_data = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+ugG5A8cZ3FqUKDwM57GM4io6JGcStivT8UdGt67PEOihLZTw3P7371+N47PrmsCpnTRzbTgcupKtUv8ImZalYk65dU8rjC/ridwhw9ffW2LBwvkEnDkkKKRi2liWIItDftJVBiWOh17o6gfbPoNrWORcAdcbpk2L+udld5kZNwIDAQAB
    -----END PUBLIC KEY-----'''

    # ---- def get_first_three ----
    def get_first_three(value):
        if isinstance(value, (int, float)):
            return f"{str(value)[:3]}****{str(value)[-4:]}"
        elif isinstance(value, str):
            return f"{value[:3]}****{value[-4:]}"
        else:
            raise TypeError("error")

    # ---- def run_Time ----
    def run_Time(hour, miute, second):
        date = datetime.datetime.now()
        date_zero = datetime.datetime.now().replace(year=date.year, month=date.month, day=date.day, hour=hour, minute=miute,
                                                    second=second)
        date_zero_time = int(time.mktime(date_zero.timetuple()))
        return date_zero_time

    # ---- def encrypt ----
    def encrypt(text):
        cipher = DES3.new(key, DES3.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(text.encode(), DES3.block_size))
        return ciphertext.hex()

    # ---- def decrypt ----
    def decrypt(text):
        ciphertext = bytes.fromhex(text)
        cipher = DES3.new(key, DES3.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), DES3.block_size)
        return plaintext.decode()

    # ---- def b64 ----
    def b64(plaintext):
        public_key = RSA.import_key(public_key_b64)
        cipher = PKCS1_v1_5.new(public_key)
        ciphertext = cipher.encrypt(plaintext.encode())
        return base64.b64encode(ciphertext).decode()

    # ---- def encrypt_para ----
    def encrypt_para(plaintext):
        if not isinstance(plaintext, str):
            plaintext = json.dumps(plaintext)
        public_key = RSA.import_key(public_key_data)
        cipher = PKCS1_v1_5.new(public_key)
        key_size = public_key.size_in_bytes()
        max_chunk_size = key_size - 11
        plaintext_bytes = plaintext.encode()
        ciphertext = b''
        for i in range(0, len(plaintext_bytes), max_chunk_size):
            chunk = plaintext_bytes[i:i + max_chunk_size]
            encrypted_chunk = cipher.encrypt(chunk)
            ciphertext += encrypted_chunk
        return binascii.hexlify(ciphertext).decode()

    # ---- def encode_phone ----
    def encode_phone(text):
        encoded_chars = []
        for char in text:
            encoded_chars.append(chr(ord(char) + 2))
        return ''.join(encoded_chars)

    # ---- def getApiTime ----
    def getApiTime(api_url):
        try:
            with requests.get(api_url) as response:
                if (not response or not response.text):
                    return time.time()
                json_data = json.loads(response.text)
                if (json_data.get("api") and json_data.get("api") not in ("time")):
                    timestamp_str = json_data.get('data', {}).get('t', '')
                else:
                    timestamp_str = json_data.get('currentTime', {})
                timestamp = int(timestamp_str) / 1000.0  # 将毫秒转为秒
                difftime = time.time() - timestamp
                return difftime;
        except Exception as e:
            print(f"💔 获取时间失败: {e}")
            return 0;

    # ---- def userLoginNormal ----
    def userLoginNormal(phone, password):
        # ---- Token 模式: 跳过账密, 直接用已有 token 换 ticket ----
        _tk, _uid = get_token_for(phone)
        if _tk:
            if not _uid:
                print("❌ Token 模式需要 userId，格式：手机号#token#userId")
                return False
            print("✓ 使用 Token 登录（跳过账密）")
            return get_ticket(phone, _uid, _tk)

        alphabet = 'abcdef0123456789'
        uuid = [''.join(random.sample(alphabet, 8)), ''.join(random.sample(alphabet, 4)),
                '4' + ''.join(random.sample(alphabet, 3)), ''.join(random.sample(alphabet, 4)),
                ''.join(random.sample(alphabet, 12))]
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        loginAuthCipherAsymmertric = 'iPhone 14 15.4.' + uuid[0] + uuid[1] + phone + timestamp + password[:6] + '0$$$0.'
        try:
            r = ss.post('https://appgologin.189.cn:9031/login/client/userLoginNormal', json={
                "headerInfos": {"code": "userLoginNormal", "timestamp": timestamp, "broadAccount": "", "broadToken": "",
                                "clientType": CT_CLIENT_TYPE, "shopId": "20002",
                                "source": "110003", "sourcePassword": "Sid98s", "token": "",
                                "userLoginName": encode_phone(phone)}, "content": {"attach": "test",
                                                                                   "fieldData": {"loginType": "4",
                                                                                                 "accountType": "",
                                                                                                 "loginAuthCipherAsymmertric": b64(
                                                                                                     loginAuthCipherAsymmertric),
                                                                                                 "deviceUid": uuid[0] +
                                                                                                              uuid[1] +
                                                                                                              uuid[2],
                                                                                                 "phoneNum": encode_phone(
                                                                                                     phone),
                                                                                                 "isChinatelecom": "0",
                                                                                                 "systemVersion": "12",
                                                                                                 "authentication": encode_phone(
                                                                                                     password)}}}).json()
            l = r['responseData']['data']['loginSuccessResult']
            if l:
                ticket = get_ticket(phone, l['userId'], l['token'])
                return ticket
            return False
        except Exception as e:
            print(f"💔 登录失败: {e}")
            return False

    # ---- def exchangeForDay ----
    async def exchangeForDay(phone, session, run_num, rid, stime, accId):
        async def delayed_conversion(delay):
            await asyncio.sleep(delay)
            await conversionRights(phone, rid, session, accId)

        tasks = [asyncio.create_task(delayed_conversion(i * stime)) for i in range(int(run_num))]
        await asyncio.gather(*tasks)

    # ---- def get_ticket ----
    def get_ticket(phone, userId, token):
        try:
            r = ss.post('https://appgologin.189.cn:9031/map/clientXML',
                        data='<Request><HeaderInfos><Code>getSingle</Code><Timestamp>' + datetime.datetime.now().strftime(
                            "%Y%m%d%H%M%S") + '</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken><ClientType>' + CT_CLIENT_TYPE + '</ClientType><ShopId>20002</ShopId><Source>110003</Source><SourcePassword>Sid98s</SourcePassword><Token>' + token + '</Token><UserLoginName>' + encode_phone(phone) + '</UserLoginName></HeaderInfos><Content><Attach>test</Attach><FieldData><TargetId>' + encrypt(
                            userId) + '</TargetId><Url>' + encrypt(CT_TARGET_URL_PLAIN) + '</Url></FieldData></Content></Request>',
                        headers={'user-agent': 'CtClient;10.4.1;Android;13;22081212C;NTQzNzgx!#!MTgwNTg1'},
                        verify=certifi.where())
            tk = re.findall('<Ticket>(.*?)</Ticket>', r.text)
            if len(tk) == 0:
                return False
            return decrypt(tk[0])
        except Exception as e:
            print(f"💔 获取ticket失败: {e}")
            return False

    # ---- def exchange ----
    async def exchange(s, phone, title, aid, jsexec, ckvalue):
        try:
            url = "https://wapact.189.cn:9001/gateway/standExchange/detailNew/exchange"
            get_url = await asyncio.to_thread(jsexec.call, "getUrl", "POST", url)
            async with s.post(get_url, cookies=ckvalue, json={"activityId": aid}) as response:
                pass
        except Exception as e:
            print(f"💔 兑换出错: {e}")

    # ---- def check ----
    async def check(s, item, ckvalue):
        checkGoods = s.get('https://wapact.189.cn:9001/gateway/stand/detailNew/check?activityId=' + item,
                           cookies=ckvalue).json()
        return checkGoods

    # ---- def conversionRights ----
    async def conversionRights(phone, aid, session, accId):
        try:
            value = {
                "id": aid,
                "accId": accId,
                "showType": "9003",
                "showEffect": "8",
                "czValue": "0"
            }
            paraV = encrypt_para(value)

            printn(f"{get_first_three(phone)}: 开始兑换啦～ ✨")

            response = await asyncio.to_thread(
                session.post,
                'https://wappark.189.cn/jt-sign/paradise/receiverRights',
                json={"para": paraV}
            )

            login = response.json()
            printn(f"💔 {get_first_three(phone)}: 结果是 {login} 💬")
            if '兑换成功' in response.text:
                printn(f"{Color.MINT}🎉 恭喜呀！{get_first_three(phone)} 兑换成功啦！🎉")
                dhjl[yf]['等级话费'] += "#" + phone
                huafei_log_write(dhjl)
                return
            elif '已兑换' in response.text:
                printn(f"💖 {get_first_three(phone)} 已经兑换过咯～")
                dhjl[yf]['等级话费'] += "#" + phone
                huafei_log_write(dhjl)
                return

        except Exception as e:
            printn(f"💔 {get_first_three(phone)} 兑换时出错了: {str(e)}")

    # ---- def getLevelRightsList ----
    async def getLevelRightsList(phone, session, accId):
        try:
            value = {
                "type": "hg_qd_djqydh",
                "accId": accId,
                "shopId": "20001"
            }
            paraV = encrypt_para(value)

            response = session.post(
                'https://wappark.189.cn/jt-sign/paradise/queryLevelRightInfo',
                json={"para": paraV}
            )

            data = response.json()
            if data.get('code') == 401:
                print(f"💔 获取失败: {data}, 可能是sign过期了呢")
                return None

            current_level = int(data['currentLevel'])
            key_name = 'V' + str(current_level)
            ids = [item['activityId'] for item in data.get(key_name, []) if '话费' in item.get('title', '')]
            return ids

        except Exception as e:
            print(f"💔 获取失败, 重试一次: {str(e)}")
            try:
                paraV = encrypt_para(value)
                response = session.post(
                    'https://wappark.189.cn/jt-sign/paradise/queryLevelRightInfo',
                    json={"para": paraV}
                )

                data = response.json()
                if data.get('code') == 401:
                    print(f"💔 重试获取失败: {data}, 可能是sign过期了呢")
                    return None

                current_level = int(data['currentLevel'])
                key_name = 'V' + str(current_level)
                ids = [item['id'] for item in data.get(key_name, []) if item.get('name') == '话费']
                return ids

            except Exception as e:
                print(f"💔 重试也失败了: {str(e)}")
                return None

    # ---- def getSign ----
    async def getSign(ticket, session):
        try:
            response = session.get(
                'https://wappark.189.cn/jt-sign/ssoHomLogin?ticket=' + ticket,
                headers={
                    'User-Agent': "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36"}
            ).json()

            if response.get('resoultCode') == '0':
                sign = response.get('sign')
                accId = response.get('accId')
                return sign, accId
            else:
                print(f"💔 获取sign失败[{response.get('resoultCode')}]: {response}")
        except Exception as e:
            print(f"💔 getSign 出错了: {str(e)}")
        return None, None

    # ---- def qgNight ----
    async def qgNight(phone, ticket, timeDiff, isTrue):
        if isTrue:
            runTime = run_Time(23, 58, 30)
        else:
            runTime = 0

        if runTime > (time.time() + timeDiff):
            difftime = runTime - time.time() - timeDiff
            print(f"⏰ 当前时间: {str(datetime.datetime.now())[11:23]}, 要等一会儿哦～ 还要等 {difftime:.2f} 秒")
            await asyncio.sleep(difftime)

        session = requests.Session()
        session.mount('https://', DESAdapter())
        session.verify = False  # 禁用证书验证
        sign, accId = await getSign(ticket, session)

        if sign:
            session.headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36",
                "sign": sign}
            printn(f"{get_first_three(phone)} 获取到sign啦～ 太好了！😊")
        else:
            print(f"{get_first_three(phone)} 💔 没有获取到sign呢...")
            return

        rightsId = await getLevelRightsList(phone, session, accId)
        if rightsId:
            printn(f"{get_first_three(phone)} 找到rightsId了: {rightsId[0]} 🌟")
        else:
            print(f"{get_first_three(phone)} 💔 没找到rightsId呢...")
            return

        if isTrue:
            runTime2 = run_Time(23, 59, 59) + 0.5
            difftime = runTime2 - time.time() - timeDiff
            printn(f"再等 {difftime:.2f} 秒就开始啦～ ⏳")
            await asyncio.sleep(difftime)
        else:
            # 测试模式：不等待，直接执行
            printn(f"测试模式，执行兑换测试～ 🧪")

        await exchangeForDay(phone, session, run_num, rightsId[0], 0.05, accId)

    # ---- def qgDay ----
    async def qgDay(phone, ticket, timeDiff, isTrue):
        async with AsyncSessionManager() as s:
            pass

    # ---- def main ----
    async def main(timeDiff, isTRUE, hour):
        print(LOGO)
        print(f"✨ 脚本启动中～ 准备开始兑换话费啦！✨\n")

        tasks = []
        accounts = []
        for key, value in os.environ.items():
         if key == 'chinaTelecomAccount':
            accounts.extend(re.split(r'@|&',value))
        if not accounts:
            print(f"💔 错误: 没有设置 chinaTelecomAccount 环境变量哦～ 要写成 账号#密码 的格式呀 多账号用@分开～")
            return
        account_count = len(accounts)
        print(f"💖 发现 {len(accounts)} 个账号呢，准备开始处理啦～")

        for phoneV in accounts:
            value = phoneV.split('#')
            if len(value) != 2:
                print(f"💔 跳过无效格式: {phoneV}，要写成 账号#密码 哦 多账号用@分开～")
                continue

            phone, password = value[0], value[1]
            if '等级话费' not in dhjl[yf]:
                dhjl[yf]['等级话费'] = ""
            if phone in dhjl[yf]['等级话费']:
                printn(f"{get_first_three(phone)} 的等级话费已经兑换过啦～ 不用再弄咯～ 💖")
                continue

            printn(f'{get_first_three(phone)} 开始登录啦～ 🌸')
            ticket = userLoginNormal(phone, password)
            if ticket:
                printn(f'{get_first_three(phone)} 登录成功！太棒啦！🎉')
                if hour > 15:
                    tasks.append(qgNight(phone, ticket, timeDiff, isTRUE))
                else:
                    tasks.append(qgNight(phone, ticket, timeDiff, isTRUE))
            else:
                printn(f'{get_first_three(phone)} 登录失败了... 有点小伤心呢 💔')
        await asyncio.gather(*tasks)

    def main():
        return True

    return locals()


def mod_aiyinyue():
    """爱音乐"""

    # ---- 本模块的 import ----
    import os
    import time
    import json
    import base64
    import hashlib
    import random
    import string
    import urllib.parse
    import re
    from collections import OrderedDict
    from curl_cffi import requests
    from Crypto.Cipher import AES, DES3, PKCS1_v1_5
    from Crypto.Util.Padding import pad, unpad
    from Crypto.PublicKey import RSA

    # 账号来源: 账密(chinaTelecomAccount) + Token(chinaTelecomToken) 合并
    TEST_ACCOUNTS = get_env_accounts_raw()
    _tok_accounts = parse_token_accounts()
    if _tok_accounts:
        _parts = []
        for _ph in _tok_accounts.keys():
            _parts.append(f"{_ph}#")   # 空密码 = Token 模式
        _tok_str = "\n".join(_parts)
        TEST_ACCOUNTS = (TEST_ACCOUNTS + "\n" + _tok_str).strip() if TEST_ACCOUNTS else _tok_str

    CHANNEL_ID = "156000008364"

    ACTIVITY_ID = "ai096"

    TEMPLATE_ID = "ve_3949"

    TEMPLATE_CONF_ID = "2JCg"

    FAKE_VIDEO_ID = ""

    LOTTERY_COST_SCORE = 20

    INVITE_TASK_ENABLED = os.environ.get('INVITE_TASK', 'False').lower() == 'true'

    FIXED_INVITER_CODE = os.environ.get('FIXED_INVITER_CODE', '')

    # ---- def md5 ----
    def md5(t): return hashlib.md5(t.encode()).hexdigest()

    # ---- def rsa_encrypt ----
    def rsa_encrypt(t):
        pub = """-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBkLT15ThVgz6/NOl6s8GNPofdWzWbCkWnkaAm7O2LjkM1H7dMvzkiqdxU02jamGRHLX/ZNMCXHnPcW/sDhiFCBN18qFvy8g6VYb9QtroI09e176s+ZCtiv7hbin2cCTj99iUpnEloZm19lwHyo69u5UMiPMpq0/XKBO8lYhN/gwIDAQAB
    -----END PUBLIC KEY-----"""
        return base64.b64encode(PKCS1_v1_5.new(RSA.import_key(pub)).encrypt(t.encode())).decode()

    # ---- def des3_op ----
    def des3_op(t, decrypt=False):
        key = b"1234567`90koiuyhgtfrdews"
        c = DES3.new(key, DES3.MODE_CBC, b"\x00"*8)
        if decrypt: 
            try: return unpad(c.decrypt(bytes.fromhex(t)), 8).decode()
            except: return t
        return c.encrypt(pad(t.encode(), 8)).hex()

    # ---- class ImCrypto ----
    class ImCrypto:
        def __init__(self):
            self.ts = str(int(time.time() * 1000))
            self.rdm = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            m_ts = md5(self.ts)
            self.key_h = md5(base64.b64encode((m_ts + self.rdm).encode()).decode() + self.rdm)
            self.e_k = md5(base64.b64encode(self.rdm.encode()).decode() + m_ts + self.key_h)[:16]
            self.e_i = md5(base64.b64encode(self.ts.encode()).decode() + md5(self.rdm) + self.key_h)[:16]

        def encrypt(self, d):
            s = json.dumps(d, separators=(',', ':'), ensure_ascii=False)
            c = AES.new(self.e_k.encode(), AES.MODE_CBC, self.e_i.encode())
            return base64.b64encode(c.encrypt(pad(s.encode('utf-8'), 16))).decode()

        def decrypt(self, t):
            try:
                d_k = md5(base64.b64encode(self.ts.encode()).decode() + self.key_h + md5(self.rdm))[:16]
                d_i = md5(base64.b64encode(self.rdm.encode()).decode() + self.key_h + md5(self.ts))[:16]
                c = AES.new(d_k.encode(), AES.MODE_CBC, d_i.encode())
                return unpad(c.decrypt(base64.b64decode(t)), 16).decode('utf-8')
            except: return t

    # ---- def check_and_update_token ----
    def check_and_update_token(res, current_token):
        new_auth = res.headers.get("authorization") or res.headers.get("Authorization")
        if new_auth:
            new_token = new_auth.replace("Bearer ", "").strip()
            if new_token and new_token != current_token:
                print("🔄 [拦截器] 捕获到下发的刷新 Token，已动态更新凭证！")
                return new_token
        return current_token

    # ---- def get_headers ----
    def get_headers(crypto_inst, token="", is_share=False):
        ref = f"https://ai.imusic.cn/h5v/fusion/ai-luck-win-share?videoId={FAKE_VIDEO_ID}&cc={CHANNEL_ID}" if is_share else f"https://ai.imusic.cn/h5v/fusion/ai-luck-win?cc={CHANNEL_ID}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://ai.imusic.cn",
            "Referer": ref,
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "imencrypt": "1",
            "imtimestamp": crypto_inst.ts,
            "imrandomnum": crypto_inst.rdm,
            "imencryptkey": crypto_inst.key_h,
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # ---- def parse_accounts ----
    def parse_accounts(raw_text):
        accounts = []
        normalized = raw_text.replace("\r", "\n").replace("&", "\n")
        for part in normalized.split("\n"):
            item = part.strip()
            if not item:
                continue
            if "#" not in item:
                raise ValueError(f"账号格式错误，必须为 手机号#密码: {item}")
            phone, password = item.split("#", 1)
            phone = phone.strip()
            password = password.strip()
            if not phone:
                raise ValueError(f"账号格式错误，手机号为空: {item}")
            # 密码为空 = Token 模式（凭据走 chinaTelecomToken），允许通过
            if not password and not get_token_for(phone)[0]:
                raise ValueError(f"账号格式错误，手机号或密码为空: {item}")
            accounts.append((phone, password))
        if not accounts:
            raise ValueError("未解析到有效账号，请按 手机号#密码 输入，多个账号可用 & 或换行分隔")
        return accounts

    # ---- def parse_invite_accounts ----
    def parse_invite_accounts(raw_text):
        """
        解析邀请任务账号对格式
        格式: 邀请人手机#密码,被邀请人手机#密码
        或多对: 邀请人1#密码1,被邀请人1#密码1 & 邀请人2#密码2,被邀请人2#密码2
        """
        invite_pairs = []
        normalized = raw_text.replace("\r", "\n").replace("&", "\n")
        for part in normalized.split("\n"):
            pair = part.strip()
            if not pair:
                continue
            if "," not in pair:
                raise ValueError(f"邀请任务格式错误，请使用: 邀请人手机#密码,被邀请人手机#密码")
            inviter_str, invitee_str = pair.split(",", 1)
            inviter_str = inviter_str.strip()
            invitee_str = invitee_str.strip()

            if "#" not in inviter_str or "#" not in invitee_str:
                raise ValueError(f"邀请任务格式错误，每个账号需要 手机号#密码 格式")

            inviter_phone, inviter_pwd = inviter_str.split("#", 1)
            invitee_phone, invitee_pwd = invitee_str.split("#", 1)

            inviter_phone, inviter_pwd = inviter_phone.strip(), inviter_pwd.strip()
            invitee_phone, invitee_pwd = invitee_phone.strip(), invitee_pwd.strip()

            if not all([inviter_phone, inviter_pwd, invitee_phone, invitee_pwd]):
                raise ValueError(f"邀请任务账号信息不完整")

            invite_pairs.append({
                "inviter": (inviter_phone, inviter_pwd),
                "invitee": (invitee_phone, invitee_pwd)
            })

        if not invite_pairs:
            raise ValueError("未解析到有效邀请任务账号对")
        return invite_pairs

    # ---- def do_login ----
    def _login_with_token(session, crypto_inst, phone, tk_val, uid):
        """用已有 token + userId 换 Ticket，跳过账密验证"""
        ts_l = time.strftime("%Y%m%d%H%M%S")
        if not uid:
            raise Exception("Token 模式需要 userId，格式：手机号#token#userId")
        print("✓ Token 模式，正在换取 Ticket...")
        # UserLoginName 必须是 UtilEncryption.encrypt 编码后的值(每字符+2);
        # 传明文会返回 ResultCode=1001「校验失败,缺少必要参数」。
        # ClientType 用 App 实际下发的 #13.5.0#channel45#<机型># 。
        enc_login_name = "".join(chr(ord(c) + 2) for c in str(phone))
        xml = (f"<Request><HeaderInfos><Code>getSingle</Code>"
               f"<Timestamp>{ts_l}</Timestamp><BroadAccount></BroadAccount>"
               f"<BroadToken></BroadToken>"
               f"<ClientType>{CT_CLIENT_TYPE}</ClientType>"
               f"<ShopId>20002</ShopId><Source>110003</Source>"
               f"<SourcePassword>Sid98s</SourcePassword>"
               f"<Token>{tk_val}</Token><UserLoginName>{enc_login_name}</UserLoginName>"
               f"</HeaderInfos><Content><Attach>test</Attach><FieldData>"
               f"<TargetId>{des3_op(str(uid))}</TargetId>"
               f"<Url>{des3_op(CT_TARGET_URL_PLAIN)}</Url></FieldData></Content></Request>")
        res_xml = session.post("https://appgologin.189.cn:9031/map/clientXML",
                               data=xml,
                               headers={"Content-Type": "application/xml"}).text
        tk_match = re.search(r'<Ticket>(.*?)</Ticket>', res_xml)
        if not tk_match:
            print("❌ Ticket 获取失败（token 可能已过期）")
            print(f"   响应: {res_xml[:200]}")
            raise Exception("Ticket Match Fail")
        ticket = des3_op(tk_match.group(1), decrypt=True)
        print("--- SSO 登录 & 身份指纹激活 ---")
        sso = {"portal": "45", "channelId": CHANNEL_ID,
               "ticket": ticket, "user118100cn": "user118100cn"}
        r = session.post("https://ai.imusic.cn/vapi/vue_login/sso_login_v2",
                         json=sso).json()
        return (r.get("token"), r.get("mobile"), r.get("enDataCode"), ticket)

    def do_login(session, crypto_inst, phone, password):
        # ---- 【合并版】优先用 Token，跳过账密 ----
        _tk, _uid = get_token_for(phone)
        if _tk:
            print("✓ 使用 Token 登录（跳过账密）")
            return _login_with_token(session, crypto_inst, phone, _tk, _uid)

        ts_l = time.strftime("%Y%m%d%H%M%S")
        en_p = "".join(chr(ord(c)+2) for c in phone)
        en_pwd = "".join(chr(ord(c)+2) for c in password)

        login_body = {
            "headerInfos": {"code": "userLoginNormal", "timestamp": ts_l, "shopId": "20002", "source": "110003", "sourcePassword": "Sid98s", "userLoginName": en_p, "clientType": CT_CLIENT_TYPE},
            "content": {"fieldData": {"loginType": "4", "loginAuthCipherAsymmertric": rsa_encrypt(f"iPhone 14 15.4.{crypto_inst.rdm[:12]}{phone}{ts_l}{password}0$$$0."), "deviceUid": crypto_inst.rdm, "phoneNum": en_p, "authentication": en_pwd}}
        }
        res_l = session.post("https://appgologin.189.cn:9031/login/client/userLoginNormal", json=login_body).json()

        if res_l.get("responseData", {}).get("resultCode") != "0000":
            print(f"❌ 登录失败: {res_l}")
            raise Exception("Telecom Login Fail")

        l_succ = res_l["responseData"]["data"]["loginSuccessResult"]
        tk_val, uid = l_succ['token'], l_succ['userId']

        xml = f"<Request><HeaderInfos><Code>getSingle</Code><Timestamp>{ts_l}</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken><ClientType>{CT_CLIENT_TYPE}</ClientType><ShopId>20002</ShopId><Source>110003</Source><SourcePassword>Sid98s</SourcePassword><Token>{tk_val}</Token><UserLoginName>{en_p}</UserLoginName></HeaderInfos><Content><Attach>test</Attach><FieldData><TargetId>{des3_op(str(uid))}</TargetId><Url>{des3_op(CT_TARGET_URL_PLAIN)}</Url></FieldData></Content></Request>"
        res_xml = session.post("https://appgologin.189.cn:9031/map/clientXML", data=xml, headers={"Content-Type": "application/xml"}).text

        tk_match = re.search(r'<Ticket>(.*?)</Ticket>', res_xml)
        if not tk_match:
            print("❌ Ticket 获取失败！")
            raise Exception("Ticket Regex Match Fail")

        ticket = des3_op(tk_match.group(1), decrypt=True)

        sso_data = {"portal":"45","channelId":CHANNEL_ID,"ticket":ticket,"user118100cn":"user118100cn"}
        res_sso = session.post("https://ai.imusic.cn/vapi/vue_login/sso_login_v2", json=sso_data).json()

        return res_sso.get("token"), res_sso.get("mobile"), res_sso.get("enDataCode"), ticket

    # ---- def warmup_session ----
    def warmup_session(session, crypto_inst, token, mobile):
        active_token = token

        h_share = get_headers(crypto_inst, active_token, is_share=True)
        res1 = session.post(f"https://ai.imusic.cn/vapi/new_member/get_user_info?channelId={CHANNEL_ID}&portal=45&mobile={mobile}", headers=h_share, data="")
        active_token = check_and_update_token(res1, active_token)

        h_share = get_headers(crypto_inst, active_token, is_share=True)
        res2 = session.post(f"https://ai.imusic.cn/vapi/vrbt/check_user_state?mobile={mobile}&is4G=1&is5G=1&isDX=1&channelId={CHANNEL_ID}&portal=45", headers=h_share, data="")
        active_token = check_and_update_token(res2, active_token)

        en_init = crypto_inst.encrypt({"channelId": CHANNEL_ID, "portal": "45", "mobile": mobile, "method": "init"})
        h_share = get_headers(crypto_inst, active_token, is_share=True)
        res3 = session.post(f"https://ai.imusic.cn/hapi/en/api?formData={urllib.parse.quote(en_init)}", headers=h_share, data="")
        active_token = check_and_update_token(res3, active_token)

        ugc_p = crypto_inst.encrypt({"channelId": CHANNEL_ID, "portal": "45", "mobile": mobile})
        h_share = get_headers(crypto_inst, active_token, is_share=True)
        res4 = session.post(f"https://ai.imusic.cn/hapi/diy_ugc/imu/get_ugc_info?formData={urllib.parse.quote(ugc_p)}", headers=h_share, data="")
        active_token = check_and_update_token(res4, active_token)

        time.sleep(0.5)
        return active_token

    # ---- def query_template_meta ----
    def query_template_meta(session, token):
        h = get_headers(ImCrypto(), token, is_share=False)
        res = session.post(
            f"https://ai.imusic.cn/hapi/de/api?pageNo=1&pageSize=50&activityId={ACTIVITY_ID}&apiName=diy%2FDiyVideoApi%2FqueryActRecommendTemplateList&channelId={CHANNEL_ID}&portal=45",
            headers=h,
            data=""
        )
        data = res.json()
        for item in data.get("data", {}).get("list", []):
            if item.get("templateId") == TEMPLATE_ID:
                return {
                    "templateConfId": item.get("templateConfId") or TEMPLATE_CONF_ID,
                    "userWords": item.get("userWords") or "古风插画，姐姐坐在秋千上。",
                    "videoName": item.get("videoName") or "创作",
                    "background": item.get("background") or "",
                    "isAI": 1 if str(item.get("isAI", 0)) == "1" else 0,
                    "arrangeId": item.get("arrangeId") or "",
                }
        return {
            "templateConfId": TEMPLATE_CONF_ID,
            "userWords": "古风插画，姐姐坐在秋千上。",
            "videoName": "创作",
            "background": "",
            "isAI": 0,
            "arrangeId": "",
        }

    # ---- def post_encrypted_api ----
    def post_encrypted_api(session, crypto_inst, token, api_path, payload, is_share=False):
        enc_str = crypto_inst.encrypt(payload)
        api_url = f"https://ai.imusic.cn{api_path}?formData={urllib.parse.quote(enc_str)}"
        h = get_headers(crypto_inst, token, is_share=is_share)
        res = session.post(api_url, headers=h, data="")
        return res, check_and_update_token(res, token)

    # ---- def send_stat_message ----
    def send_stat_message(session, crypto_inst, token, mobile, actname, actparam):
        payload = OrderedDict([
            ("channelId", CHANNEL_ID),
            ("portal", "45"),
            ("mobile", mobile),
            ("actname", actname),
            ("actparam", actparam),
            ("sid", "")
        ])
        return post_encrypted_api(session, crypto_inst, token, "/vapi/vue_stat/sendMessage", payload, is_share=False)

    # ---- def query_fun_play_score ----
    def query_fun_play_score(session, crypto_inst, token, mobile):
        res, active_token = post_encrypted_api(
            session,
            crypto_inst,
            token,
            "/hapi/en/api",
            OrderedDict([
                ("activityId", ACTIVITY_ID),
                ("mobile", mobile),
                ("apiName", "act/LaborApi/getFunPlayTotalScoreOrRemainingScore"),
                ("channelId", CHANNEL_ID),
                ("portal", "45")
            ]),
            is_share=False
        )
        dec_text = crypto_inst.decrypt(res.text)
        score_data = {}
        try:
            score_data = json.loads(dec_text).get("data", {}) or {}
            print(f"📊 当前积分: totalScore={score_data.get('totalScore', '')}, remainingScore={score_data.get('remainingScore', '')}")
        except Exception:
            pass
        return active_token, score_data

    # ---- def query_rewards ----
    def query_rewards(session, crypto_inst, token, mobile):
        """查询用户可领取的奖励"""
        try:
            # 使用正确的API查询中奖列表
            res, active_token = post_encrypted_api(
                session,
                crypto_inst,
                token,
                "/hapi/en/api",
                OrderedDict([
                    ("activityId", ACTIVITY_ID),
                    ("mobile", mobile),
                    ("pageNo", 1),
                    ("pageSize", 10),
                    ("apiName", "act/LaborApi/funPlayFestivalPointsAwardList"),
                    ("channelId", CHANNEL_ID),
                    ("portal", "45")
                ]),
                is_share=False
            )
            dec_text = crypto_inst.decrypt(res.text)
            try:
                data = json.loads(dec_text)
                if data.get("code") != "0000":
                    print(f"⚠️  奖励查询失败: {data.get('desc')}")
                    return active_token, {}
                reward_list = data.get("data", {}).get("list", [])
                if reward_list:
                    print(f"🎁 发现 {len(reward_list)} 个奖励")
                    for reward in reward_list:
                        if isinstance(reward, dict):
                            print(f"   - {reward.get('awardName', '未知奖励')} (状态: {'可领取' if reward.get('status') == '-1' else '已领取'})")
                return active_token, data.get("data", {})
            except Exception as e:
                print(f"⚠️  解析奖励列表失败: {str(e)}")
                return active_token, {}
        except Exception as e:
            print(f"⚠️  调用奖励查询接口失败: {str(e)}")
            return token, {}

    # ---- def claim_reward ----
    def claim_reward(session, crypto_inst, token, mobile, reward_id):
        """领取指定奖励"""
        try:
            # 使用正确的API和参数格式领取奖励
            res, active_token = post_encrypted_api(
                session,
                crypto_inst,
                token,
                "/hapi/en/api",
                OrderedDict([
                    ("mobile", mobile),
                    ("awardId", reward_id),
                    ("activityId", ACTIVITY_ID),
                    ("apiName", "act/LaborApi/funPlayEggCostRedeem"),
                    ("channelId", CHANNEL_ID),
                    ("portal", "45")
                ]),
                is_share=False
            )
            dec_text = crypto_inst.decrypt(res.text)
            try:
                data = json.loads(dec_text)
                if data.get("code") == "0000":
                    print(f"✅ 领取成功")
                else:
                    print(f"❌ 领取失败: {data.get('desc', '未知错误')}")
            except Exception:
                print(f"📥 领取结果: {dec_text}")
            return active_token
        except Exception as e:
            print(f"⚠️  调用奖励领取接口失败: {str(e)}")
            return token

    # ---- def claim_all_rewards ----
    def claim_all_rewards(session, crypto_inst, token, mobile):
        """专门用于领取所有可领取的奖励"""
        print("\n=== 开始领取奖励 ===")
        active_token, rewards = query_rewards(session, crypto_inst, token, mobile)
        claimed = False
        failed_awards = []
        if rewards and isinstance(rewards, dict) and rewards.get("list"):
            for reward in rewards.get("list", []):
                if isinstance(reward, dict):
                    # 检查是否是1元电信话费奖励
                    award_name = reward.get('awardName', '')
                    award_id = reward.get("awardId")
                    if '1元' in award_name and '话费' in award_name and award_id not in failed_awards:
                        print(f"📋 领取: {award_name}")
                        # 尝试领取
                        try:
                            active_token = claim_reward(session, crypto_inst, active_token, mobile, award_id)
                            claimed = True
                            # 领取后再次查询奖励状态
                            active_token, updated_rewards = query_rewards(session, crypto_inst, active_token, mobile)
                            # 检查奖励状态是否已更新（简化逻辑，只要能查询到奖励就认为状态已更新）
                            updated_list = updated_rewards.get("list", [])
                            reward_updated = False
                            for updated_reward in updated_list:
                                if isinstance(updated_reward, dict) and updated_reward.get("awardId") == award_id:
                                    reward_updated = True
                                    break
                            if not reward_updated:
                                # 如果状态未更新，添加到失败列表
                                failed_awards.append(award_id)
                                print(f"⚠️  奖励状态未更新，将避免重复尝试")
                        except Exception as e:
                            print(f"⚠️  领取过程出错: {str(e)}")
                            failed_awards.append(award_id)
                        time.sleep(0.5)
            if claimed:
                print("✅ 奖励领取完成")
            else:
                print("📭 没有可领取的奖励")
        else:
            print("📭 没有可领取的奖励")
        return active_token

    # ---- def run_lottery ----
    def run_lottery(session, crypto_inst, token, mobile):
        active_token, score_data = query_fun_play_score(session, crypto_inst, token, mobile)
        try:
            remaining_score = int(score_data.get("remainingScore") or 0)
        except Exception:
            remaining_score = 0

        lottery_count = remaining_score // LOTTERY_COST_SCORE
        print(f"🎰 可用积分={remaining_score}，按每次{LOTTERY_COST_SCORE}积分计算，可抽奖 {lottery_count} 次")
        if lottery_count <= 0:
            # 即使没有积分抽奖，也检查是否有未领取的奖励
            active_token, rewards = query_rewards(session, crypto_inst, active_token, mobile)
            if rewards and isinstance(rewards, dict) and rewards.get("rewards"):
                for reward in rewards.get("rewards", []):
                    if isinstance(reward, dict) and reward.get("status") == "1":  # 假设1表示可领取
                        reward_id = reward.get("rewardId")
                        if reward_id:
                            print(f"📋 发现可领取奖励: {reward.get('rewardName', '未知奖励')}")
                            active_token = claim_reward(session, crypto_inst, active_token, mobile, reward_id)
                            time.sleep(0.5)
            return active_token

        for index in range(1, lottery_count + 1):
            res, active_token = post_encrypted_api(
                session,
                crypto_inst,
                active_token,
                "/hapi/en/api",
                OrderedDict([
                    ("activityId", ACTIVITY_ID),
                    ("mobile", mobile),
                    ("apiName", "act/LaborApi/funPlayFestivalLottery"),
                    ("channelId", CHANNEL_ID),
                    ("portal", "45")
                ]),
                is_share=False
            )
            dec_text = crypto_inst.decrypt(res.text)
            print(f"🎁 第{index}次抽奖结果: {dec_text}")
            time.sleep(0.2)

        # 抽奖完成后检查并领取奖励
        active_token, rewards = query_rewards(session, crypto_inst, active_token, mobile)
        if rewards and isinstance(rewards, dict) and rewards.get("rewards"):
            for reward in rewards.get("rewards", []):
                if isinstance(reward, dict) and reward.get("status") == "1":  # 假设1表示可领取
                    reward_id = reward.get("rewardId")
                    if reward_id:
                        print(f"📋 发现可领取奖励: {reward.get('rewardName', '未知奖励')}")
                        active_token = claim_reward(session, crypto_inst, active_token, mobile, reward_id)
                        time.sleep(0.5)

        return active_token

    # ---- def premake_prepare ----
    def premake_prepare(session, crypto_inst, token, mobile, template_meta):
        active_token = token

        res_pkg, active_token = post_encrypted_api(
            session,
            crypto_inst,
            active_token,
            "/hapi/en/api",
            OrderedDict([
                ("channelId", CHANNEL_ID),
                ("portal", "45"),
                ("mobile", mobile),
                ("templateId", TEMPLATE_ID),
                ("aid", ACTIVITY_ID),
                ("apiName", "ismp/IsmpApi/queryAiMakePkgInfo")
            ]),
            is_share=False
        )

        stat_events = [
            ("page_vring_index", f"玩转AI赢手机_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}"),
            ("activity_vring_make_1.9", f"_activityID_{ACTIVITY_ID}_templateID_{TEMPLATE_ID}_entrance_{CHANNEL_ID}_templateconfID_{template_meta['templateConfId']}"),
            ("activity_2603AI-meet_25.1", f"activityID_{ACTIVITY_ID}_undefined_templateID_{TEMPLATE_ID}_entrance_{CHANNEL_ID}_templateconfID_{template_meta['templateConfId']}"),
            ("page_2511AI-makeonekey_9", f"activityID_{ACTIVITY_ID}_templateID_{TEMPLATE_ID}_entrance_{CHANNEL_ID}_templateConfID_{template_meta['templateConfId']}"),
            ("page_2511AI-makeonekey_3", f"activityID_{ACTIVITY_ID}_templateID_{TEMPLATE_ID}_entrance_{CHANNEL_ID}_templateConfID_{template_meta['templateConfId']}"),
        ]
        for actname, actparam in stat_events:
            _, active_token = send_stat_message(session, crypto_inst, active_token, mobile, actname, actparam)
            time.sleep(0.08)

        return active_token

    # ---- def make_request ----
    def make_request(session, crypto_inst, token, mobile, en_code, template_meta):
        rand_name = f"{template_meta['videoName']}{random.randint(100000, 999999)}"
        payload = OrderedDict([
            ("channelId", CHANNEL_ID), ("portal", "45"), ("mobile", mobile),
            ("openId", ""), ("makeId", ""), ("background", template_meta.get("background", "")), ("userPhotos", ""),
            ("userWords", template_meta["userWords"]),
            ("templateName", rand_name), ("videoName", rand_name),
            ("templateId", TEMPLATE_ID), ("templateConfId", template_meta["templateConfId"]), ("aid", ACTIVITY_ID),
            ("inviterMobile", en_code), ("isAI", template_meta.get("isAI", 0)), ("aiPack", 0), ("arrangeId", template_meta.get("arrangeId", "")),
            ("autoOrderUgc", 0), ("aiGatewayImagMakeId", ""), ("fromType", ""),
            ("sessionId", ""), ("voice", ""), ("invitationCode", en_code)
        ])
        print(f"🧩 当前模板参数: templateId={TEMPLATE_ID}, templateConfId={template_meta['templateConfId']}, isAI={template_meta.get('isAI', 0)}, arrangeId={template_meta.get('arrangeId', '')!s}, background={template_meta.get('background', '')!r}")
        enc_str = crypto_inst.encrypt(payload)
        api_url = f"https://ai.imusic.cn/hapi/diy_video/au/template_make_add_v2?formData={urllib.parse.quote(enc_str)}"

        h = get_headers(crypto_inst, token, is_share=False)
        return session.post(api_url, headers=h, data="")

    # ---- def run_single_account ----
    def run_single_account(phone, password):
        print(f"\n{'=' * 20} 开始处理账号 {phone} {'=' * 20}")

        session = requests.Session(impersonate="chrome120")

        global_crypto = ImCrypto()

        session.cookies.set('cc', CHANNEL_ID, domain='ai.imusic.cn')
        session.cookies.set('imusic', f'118100{int(time.time()*1000)}', domain='ai.imusic.cn')
        session.cookies.set('loginState', 'true', domain='ai.imusic.cn')

        try:
            token, mobile, en_code, ticket = do_login(session, global_crypto, phone, password)
            if not en_code:
                en_code = "7c254a3c19d2b314d5d4415d9a0961e27729b5b7eb2c111f7856d33bb552acce"

            active_token = warmup_session(session, global_crypto, token, mobile)
            template_meta = query_template_meta(session, active_token)
            active_token = premake_prepare(session, global_crypto, active_token, mobile, template_meta)

            res = make_request(session, global_crypto, active_token, mobile, en_code, template_meta)
            active_token = check_and_update_token(res, active_token)

            resp_text = global_crypto.decrypt(res.text)

            if "10013" in resp_text:
                trace_id = json.loads(resp_text).get("imuTraceId")
                h_rem = get_headers(global_crypto, active_token, True)

                _, active_token = send_stat_message(
                    session,
                    global_crypto,
                    active_token,
                    mobile,
                    "page_vring_index",
                    f"玩转AI赢手机_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}"
                )
                time.sleep(0.05)
                _, active_token = send_stat_message(
                    session,
                    global_crypto,
                    active_token,
                    mobile,
                    "activity_vring_make_1.9",
                    f"_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}"
                )

                rem_en = global_crypto.encrypt({"method": "remedy", "traceId": trace_id, "mobile": mobile})
                res_rem = session.post(f"https://ai.imusic.cn/hapi/en/api?formData={urllib.parse.quote(rem_en)}", headers=h_rem, data="")
                active_token = check_and_update_token(res_rem, active_token)

                res_refresh = session.post("https://ai.imusic.cn/vapi/vue_login/sso_login_v2", json={"portal":"45","channelId":CHANNEL_ID,"ticket":ticket,"user118100cn":"user118100cn"}).json()
                active_token = res_refresh.get("token")
                active_token = premake_prepare(session, global_crypto, active_token, mobile, template_meta)

                time.sleep(1)

                res_final = make_request(session, global_crypto, active_token, mobile, en_code, template_meta)
                final_text = global_crypto.decrypt(res_final.text)
                print(f"🎉 最终响应结果: {final_text}")
                if '"code":"0000"' in final_text:
                    active_token = check_and_update_token(res_final, active_token)
                    active_token = run_lottery(session, global_crypto, active_token, mobile)
            else:
                print("✅ 任务提交成功！")
                active_token = run_lottery(session, global_crypto, active_token, mobile)

            print(f"✅ 账号 {phone} 处理完成")
        except Exception as e:
            print(f"💥 账号 {phone} 程序崩溃，原因: {str(e)}")

    # ---- def run_invite_task ----
    def run_invite_task(invite_pair):
        """执行单个邀请任务"""
        inviter_phone, inviter_pwd = invite_pair["inviter"]
        invitee_phone, invitee_pwd = invite_pair["invitee"]

        print(f"\n{'=' * 25} 邀请任务 {'=' * 25}")
        print(f"👤 邀请人: {inviter_phone}")
        print(f"👤 被邀请人: {invitee_phone}")

        session = requests.Session(impersonate="chrome120")
        global_crypto = ImCrypto()
        session.cookies.set('cc', CHANNEL_ID, domain='ai.imusic.cn')
        session.cookies.set('imusic', f'118100{int(time.time()*1000)}', domain='ai.imusic.cn')
        session.cookies.set('loginState', 'true', domain='ai.imusic.cn')

        # 1. 邀请人登录获取 en_code
        print(f"\n--- 步骤1: 邀请人 {inviter_phone} 登录 ---")
        try:
            token_inviter, mobile_inviter, en_code, ticket_inviter = do_login(session, global_crypto, inviter_phone, inviter_pwd)
            if not en_code:
                en_code = "7c254a3c19d2b314d5d4415d9a0961e27729b5b7eb2c111f7856d33bb552acce"
            print(f"✓ 邀请人登录成功，en_code: {en_code[:20]}...")
        except Exception as e:
            print(f"❌ 邀请人登录失败: {str(e)}")
            return

        # 2. 被邀请人登录
        print(f"\n--- 步骤2: 被邀请人 {invitee_phone} 登录 ---")
        try:
            token_invitee, mobile_invitee, _, ticket_invitee = do_login(session, global_crypto, invitee_phone, invitee_pwd)
            print(f"✓ 被邀请人登录成功")
        except Exception as e:
            print(f"❌ 被邀请人登录失败: {str(e)}")
            return

        # 3. 被邀请人环境预热
        print(f"\n--- 步骤3: 被邀请人环境预热 ---")
        active_token = warmup_session(session, global_crypto, token_invitee, mobile_invitee)
        template_meta = query_template_meta(session, active_token)
        active_token = premake_prepare(session, global_crypto, active_token, mobile_invitee, template_meta)

        # 4. 被邀请人做任务（使用邀请人的 en_code）
        print(f"\n--- 步骤4: 被邀请人完成任务（邀请码: {en_code[:20]}...）---")
        res = make_request(session, global_crypto, active_token, mobile_invitee, en_code, template_meta)
        active_token = check_and_update_token(res, active_token)
        resp_text = global_crypto.decrypt(res.text)

        if "10013" in resp_text:
            trace_id = json.loads(resp_text).get("imuTraceId")
            h_rem = get_headers(global_crypto, active_token, True)
            _, active_token = send_stat_message(session, global_crypto, active_token, mobile_invitee, "page_vring_index", f"玩转AI赢手机_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}")
            time.sleep(0.05)
            _, active_token = send_stat_message(session, global_crypto, active_token, mobile_invitee, "activity_vring_make_1.9", f"_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}")
            rem_en = global_crypto.encrypt({"method": "remedy", "traceId": trace_id, "mobile": mobile_invitee})
            res_rem = session.post(f"https://ai.imusic.cn/hapi/en/api?formData={urllib.parse.quote(rem_en)}", headers=h_rem, data="")
            active_token = check_and_update_token(res_rem, active_token)
            res_refresh = session.post("https://ai.imusic.cn/vapi/vue_login/sso_login_v2", json={"portal":"45","channelId":CHANNEL_ID,"ticket":ticket_invitee,"user118100cn":"user118100cn"}).json()
            active_token = res_refresh.get("token")
            active_token = premake_prepare(session, global_crypto, active_token, mobile_invitee, template_meta)
            time.sleep(1)
            res_final = make_request(session, global_crypto, active_token, mobile_invitee, en_code, template_meta)
            final_text = global_crypto.decrypt(res_final.text)
            print(f"🎉 最终响应结果: {final_text}")
            if '"code":"0000"' in final_text:
                active_token = check_and_update_token(res_final, active_token)
                run_lottery(session, global_crypto, active_token, mobile_invitee)
        else:
            print("✅ 任务提交成功！")
            run_lottery(session, global_crypto, active_token, mobile_invitee)

        print(f"\n✅ 邀请任务完成: {inviter_phone} 邀请 {invitee_phone}")

    # ---- def run ----
    def run():
        # 检查是否有固定邀请码
        if FIXED_INVITER_CODE:
            print(f"\n📌 使用固定邀请码模式: {FIXED_INVITER_CODE[:20]}...")
            # 普通账号+固定邀请码模式
            accounts = parse_accounts(TEST_ACCOUNTS)
            print(f"共 {len(accounts)} 个账号将使用固定邀请码")
            for idx, (phone, password) in enumerate(accounts, start=1):
                print(f"\n#### [{idx}/{len(accounts)}] ####")
                # 使用固定邀请码
                run_single_account_with_inviter(phone, password, FIXED_INVITER_CODE)
        elif INVITE_TASK_ENABLED:
            # 邀请任务模式
            invite_pairs = parse_invite_accounts(TEST_ACCOUNTS)
            print(f"共 {len(invite_pairs)} 对邀请任务")
            for idx, pair in enumerate(invite_pairs, start=1):
                print(f"\n====== [{idx}/{len(invite_pairs)}] ======")
                run_invite_task(pair)
        else:
            # 普通模式
            accounts = parse_accounts(TEST_ACCOUNTS)
            print(f"共解析到 {len(accounts)} 个账号")
            for idx, (phone, password) in enumerate(accounts, start=1):
                print(f"\n#### [{idx}/{len(accounts)}] ####")
                run_single_account(phone, password)

    # ---- def run_single_account_with_inviter ----
    def run_single_account_with_inviter(phone, password, inviter_code):
        """单账号使用指定邀请码"""
        print(f"\n{'=' * 20} 使用指定邀请码处理账号 {phone} {'=' * 20}")
        session = requests.Session(impersonate="chrome120")
        global_crypto = ImCrypto()
        session.cookies.set('cc', CHANNEL_ID, domain='ai.imusic.cn')
        session.cookies.set('imusic', f'118100{int(time.time()*1000)}', domain='ai.imusic.cn')
        session.cookies.set('loginState', 'true', domain='ai.imusic.cn')

        try:
            token, mobile, _, ticket = do_login(session, global_crypto, phone, password)
            active_token = warmup_session(session, global_crypto, token, mobile)
            template_meta = query_template_meta(session, active_token)
            active_token = premake_prepare(session, global_crypto, active_token, mobile, template_meta)

            res = make_request(session, global_crypto, active_token, mobile, inviter_code, template_meta)
            active_token = check_and_update_token(res, active_token)
            resp_text = global_crypto.decrypt(res.text)

            if "10013" in resp_text:
                trace_id = json.loads(resp_text).get("imuTraceId")
                h_rem = get_headers(global_crypto, active_token, True)
                _, active_token = send_stat_message(session, global_crypto, active_token, mobile, "page_vring_index", f"玩转AI赢手机_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}")
                time.sleep(0.05)
                _, active_token = send_stat_message(session, global_crypto, active_token, mobile, "activity_vring_make_1.9", f"_activityID_{ACTIVITY_ID}_entrance_{CHANNEL_ID}")
                rem_en = global_crypto.encrypt({"method": "remedy", "traceId": trace_id, "mobile": mobile})
                res_rem = session.post(f"https://ai.imusic.cn/hapi/en/api?formData={urllib.parse.quote(rem_en)}", headers=h_rem, data="")
                active_token = check_and_update_token(res_rem, active_token)
                res_refresh = session.post("https://ai.imusic.cn/vapi/vue_login/sso_login_v2", json={"portal":"45","channelId":CHANNEL_ID,"ticket":ticket,"user118100cn":"user118100cn"}).json()
                active_token = res_refresh.get("token")
                active_token = premake_prepare(session, global_crypto, active_token, mobile, template_meta)
                time.sleep(1)
                res_final = make_request(session, global_crypto, active_token, mobile, inviter_code, template_meta)
                final_text = global_crypto.decrypt(res_final.text)
                print(f"🎉 最终响应结果: {final_text}")
                if '"code":"0000"' in final_text:
                    active_token = check_and_update_token(res_final, active_token)
                    run_lottery(session, global_crypto, active_token, mobile)
            else:
                print("✅ 任务提交成功！")
                run_lottery(session, global_crypto, active_token, mobile)

            print(f"✅ 账号 {phone} 处理完成")
        except Exception as e:
            print(f"💥 账号 {phone} 程序崩溃，原因: {str(e)}")

    # ---- def run_only_claim_rewards ----
    def run_only_claim_rewards():
        """只领取奖励，不执行其他任务"""
        accounts = parse_accounts(TEST_ACCOUNTS)
        print(f"共解析到 {len(accounts)} 个账号，将执行奖励领取")
        for idx, (phone, password) in enumerate(accounts, start=1):
            print(f"\n#### [{idx}/{len(accounts)}] 开始领取奖励: {phone} ####")
            session = requests.Session(impersonate="chrome120")
            global_crypto = ImCrypto()
            session.cookies.set('cc', CHANNEL_ID, domain='ai.imusic.cn')
            session.cookies.set('imusic', f'118100{int(time.time()*1000)}', domain='ai.imusic.cn')
            session.cookies.set('loginState', 'true', domain='ai.imusic.cn')
            try:
                token, mobile, en_code, ticket = do_login(session, global_crypto, phone, password)
                if not en_code:
                    en_code = "7c254a3c19d2b314d5d4415d9a0961e27729b5b7eb2c111f7856d33bb552acce"
                active_token = warmup_session(session, global_crypto, token, mobile)
                active_token = claim_all_rewards(session, global_crypto, active_token, mobile)
                print(f"✅ 账号 {phone} 奖励领取完成")
            except Exception as e:
                print(f"💥 账号 {phone} 程序崩溃，原因: {str(e)}")

    def main():
        return True

    return locals()


def mod_qiandao():
    """金豆签到（成长乐园）

    链路：token -> ticket -> ssoHomLogin(拿 sign) -> webSign/sign(签到)
    加密：encode = AES-128-ECB(QD_AES_KEY, json).hex()
    注意：必须用 QD_UA（App 的 CtClient UA 会被瑞数拦 412）
    """
    import datetime
    import json
    import re
    import time

    import requests
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import pad, unpad

    _K = b"1234567`90koiuyhgtfrdews"
    _IV = bytes(8)

    def _enc(s):
        return DES3.new(_K, DES3.MODE_CBC, _IV).encrypt(
            pad(str(s).encode(), 8)).hex()

    def _dec(h):
        return unpad(DES3.new(_K, DES3.MODE_CBC, _IV).decrypt(
            bytes.fromhex(h)), 8).decode()

    def _pq(p):
        return "".join(chr(ord(c) + 2) for c in str(p))

    def _ticket(phone, tk, uid):
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        body = ("<Request><HeaderInfos><Code>getSingle</Code><Timestamp>" + now
                + "</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken>"
                "<ClientType>" + CT_CLIENT_TYPE + "</ClientType><ShopId>20002</ShopId>"
                "<Source>110003</Source><SourcePassword>Sid98s</SourcePassword>"
                "<Token>" + tk + "</Token>"
                "<UserLoginName>" + _pq(phone) + "</UserLoginName></HeaderInfos>"
                "<Content><Attach>test</Attach><FieldData>"
                "<TargetId>" + _enc(uid) + "</TargetId>"
                "<Url>" + _enc(CT_TARGET_URL_PLAIN) + "</Url>"
                "</FieldData></Content></Request>")
        r = requests.post("https://appgologin.189.cn:9031/map/clientXML",
                          data=body.encode("utf-8"), verify=False, timeout=30,
                          headers={"user-agent":
                                   "CtClient;10.4.1;Android;13;22081212C;NTQzNzgx!#!MTgwNTg1"})
        m = re.findall("<Ticket>(.*?)</Ticket>", r.text)
        return _dec(m[0]) if m else None

    accounts = parse_account_sources()
    if not accounts:
        print("⚠️  没有账号")
        return locals()

    ok = 0
    for phone in accounts:
        tk, uid = get_token_for(phone)
        masked = phone[:3] + "****" + phone[-4:]
        print(f"\n===== 金豆签到 {masked} =====")
        if not tk or not uid:
            print("  ⚠️  缺少 token/userId，跳过")
            continue
        try:
            t = _ticket(phone, tk, uid)
            if not t:
                print("  ❌ 换 ticket 失败（token 可能过期）")
                continue
            s = requests.Session()
            s.verify = False
            s.headers.update({
                "User-Agent": QD_UA,
                "Referer": QD_BASE + "/resources/dist/signNew.html?ticket=" + t,
                "Content-Type": "application/json;charset=utf-8",
            })
            j = s.get(QD_BASE + "/jt-sign/ssoHomLogin",
                      params={"ticket": t}, timeout=20).json()
            if str(j.get("resoultCode")) != "0":
                print("  ❌ SSO 失败:", str(j)[:150])
                continue
            s.headers["sign"] = j["sign"]

            # 先查状态
            r = s.post(QD_BASE + "/jt-sign/paradise/getParadiseInfo",
                       json={"para": qd_para({"phone": phone})}, timeout=20)
            pj = r.json()
            if isinstance(pj, dict) and "userInfo" in pj:
                pass

            # 签到
            enc = qd_encode({"phone": phone, "sysType": "20002",
                             "date": int(time.time() * 1000)})
            r = s.post(QD_BASE + "/jt-sign/webSign/sign",
                       json={"encode": enc}, timeout=20)
            res = r.json()
            data = res.get("data") or {}
            msg = data.get("msg") or res.get("resoultMsg", "")
            if str(res.get("resoultCode")) == "0":
                print(f"  ✅ 签到: {msg or '成功'}"
                      + (f"（+{data.get('coin')} 金豆）" if data.get('coin') else ""))
                ok += 1
            else:
                print(f"  ⚠️  签到失败: {str(res)[:150]}")

            # 查余额 + 连续天数
            try:
                r = s.post(QD_BASE + "/jt-sign/api/home/userCoinInfo",
                           json={"para": qd_para({"phone": phone})}, timeout=20)
                cj = r.json()
                if "totalCoin" in cj:
                    print(f"  💰 金豆余额: {cj['totalCoin']}")
                r = s.post(QD_BASE + "/jt-sign/webSign/continueSignDays",
                           json={"para": qd_para({"phone": phone})}, timeout=20)
                dj = r.json()
                if "continueSignDays" in dj:
                    print(f"  📅 连续签到: {dj['continueSignDays']} 天"
                          f"（等级 {dj.get('level')}）")
            except Exception:
                pass

        except Exception as e:
            print(f"  ❌ 出错: {e}")

    print(f"\n金豆签到完成：{ok}/{len(accounts)}")

    def main():
        return ok > 0

    return locals()


def mod_renwu():
    """金豆任务（成长乐园）—— 自动完成访问类任务赚金豆

    核心接口：
      homepage(type=hg_qd_zrwzjd)  取 33 个任务
      polymerize(jobId)            完成访问类任务（contentOne=18/16）
      paradise/openMsg             打开消息任务（+100）
      paradise/food                云宝喂食

    加密：para = RSA-1024/PKCS1(json).hex()
    """
    import datetime
    import json
    import random
    import re
    import time

    import requests
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import pad, unpad

    _K = b"1234567`90koiuyhgtfrdews"
    _IV = bytes(8)

    def _enc(s):
        return DES3.new(_K, DES3.MODE_CBC, _IV).encrypt(
            pad(str(s).encode(), 8)).hex()

    def _dec(h):
        return unpad(DES3.new(_K, DES3.MODE_CBC, _IV).decrypt(
            bytes.fromhex(h)), 8).decode()

    def _pq(p):
        return "".join(chr(ord(c) + 2) for c in str(p))

    def _ticket(phone, tk, uid):
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        body = ("<Request><HeaderInfos><Code>getSingle</Code><Timestamp>" + now
                + "</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken>"
                "<ClientType>" + CT_CLIENT_TYPE + "</ClientType><ShopId>20002</ShopId>"
                "<Source>110003</Source><SourcePassword>Sid98s</SourcePassword>"
                "<Token>" + tk + "</Token>"
                "<UserLoginName>" + _pq(phone) + "</UserLoginName></HeaderInfos>"
                "<Content><Attach>test</Attach><FieldData>"
                "<TargetId>" + _enc(uid) + "</TargetId>"
                "<Url>" + _enc(CT_TARGET_URL_PLAIN) + "</Url>"
                "</FieldData></Content></Request>")
        r = requests.post("https://appgologin.189.cn:9031/map/clientXML",
                          data=body.encode("utf-8"), verify=False, timeout=30,
                          headers={"user-agent":
                                   "CtClient;10.4.1;Android;13;22081212C;NTQzNzgx!#!MTgwNTg1"})
        m = re.findall("<Ticket>(.*?)</Ticket>", r.text)
        return _dec(m[0]) if m else None

    accounts = parse_account_sources()
    if not accounts:
        print("⚠️  没有账号")
        return locals()

    ok = 0
    for phone in accounts:
        tk, uid = get_token_for(phone)
        masked = phone[:3] + "****" + phone[-4:]
        print(f"\n===== 金豆任务 {masked} =====")
        if not tk or not uid:
            print("  ⚠️  缺少 token/userId，跳过")
            continue
        try:
            t = _ticket(phone, tk, uid)
            if not t:
                print("  ❌ 换 ticket 失败（token 可能过期）")
                continue

            s = requests.Session()
            s.verify = False
            s.headers.update({
                "User-Agent": QD_UA,
                "Referer": QD_BASE + "/resources/dist/signNew.html?ticket=" + t,
                "Content-Type": "application/json;charset=utf-8",
            })
            j = s.get(QD_BASE + "/jt-sign/ssoHomLogin",
                      params={"ticket": t}, timeout=20).json()
            if str(j.get("resoultCode")) != "0":
                print("  ❌ SSO 失败:", str(j)[:120])
                continue
            s.headers["sign"] = j["sign"]

            def para(d):
                return qd_para(d)

            def coin():
                try:
                    r = s.post(QD_BASE + "/jt-sign/api/home/userCoinInfo",
                               json={"para": para({"phone": phone})}, timeout=20)
                    return r.json().get("totalCoin")
                except Exception:
                    return None

            start_coin = coin()
            print(f"  💰 起始金豆: {start_coin}")

            # ---- 1. 取任务列表 ----
            r = s.post(QD_BASE + "/jt-sign/webSign/homepage",
                       json={"para": para({"phone": phone, "shopId": "20001",
                                           "type": "hg_qd_zrwzjd"})}, timeout=20)
            ads = (((r.json().get("data") or {}).get("biz")) or {}).get("adItems") or []
            if not ads:
                print("  ⚠️  没取到任务列表")
            todo = [a for a in ads
                    if str(a.get("contentOne")) in ("18", "16")
                    and str(a.get("taskState")) == "0"]
            print(f"  📋 共 {len(ads)} 个任务，访问类待做 {len(todo)} 个")

            # ---- 2. 逐个完成访问类任务 ----
            done = 0
            for idx, a in enumerate(todo, 1):
                name = (a.get("title") or "").split(" ")[0]
                jid = a.get("taskId")
                if not jid:
                    continue
                try:
                    rr = s.post(QD_BASE + "/jt-sign/webSign/polymerize",
                                json={"para": para({"phone": phone, "jobId": jid})},
                                timeout=20)
                    dj = rr.json()
                    if str(dj.get("resoultCode")) == "0":
                        biz = (dj.get("data") or {}).get("biz") or {}
                        if str(biz.get("code")) == "0":
                            print(f"    ✅ [{idx}/{len(todo)}] {name}")
                            done += 1
                        else:
                            print(f"    ℹ️  [{idx}/{len(todo)}] {name}: "
                                  f"{biz.get('err') or '已做过'}")
                    else:
                        print(f"    ⚠️  [{idx}/{len(todo)}] {name}: "
                              f"{str(dj)[:80]}")
                except Exception as e:
                    print(f"    ❌ {name}: {str(e)[:50]}")
                # 模拟真人节奏，避免触发风控
                time.sleep(3 + random.random() * 2)

            # ---- 3. 打开消息任务（+100 金豆） ----
            try:
                r = s.post(QD_BASE + "/jt-sign/paradise/openMsg",
                           json={"para": para({"phone": phone})}, timeout=20)
                oj = r.json()
                if str(oj.get("resoultCode")) == "0":
                    print("  ✅ 打开消息任务（+100 金豆）")
            except Exception:
                pass

            # ---- 4. 云宝喂食（消耗 10 金豆，默认关闭） ----
            # 喂食会扣 10 金豆换成长值，对"攒金豆"目标是负收益，默认不做。
            # 需要时设 CT_FEED=1 开启。
            if str(os.environ.get("CT_FEED", "")).strip() in ("1", "true", "yes"):
                try:
                    r = s.post(QD_BASE + "/jt-sign/paradise/food",
                               json={"para": para({"phone": phone})}, timeout=20)
                    fj = r.json()
                    if str(fj.get("resoultCode")) == "0":
                        print("  🍚 云宝喂食成功（消耗 10 金豆）")
                except Exception:
                    pass
            else:
                print("  ⏭️  跳过云宝喂食（会扣 10 金豆，设 CT_FEED=1 开启）")

            end_coin = coin()
            diff = (end_coin - start_coin) if (end_coin is not None
                                               and start_coin is not None) else 0
            print(f"  💰 结束金豆: {end_coin}  本轮 +{diff}")
            ok += 1

        except Exception as e:
            print(f"  ❌ 出错: {e}")

    print(f"\n金豆任务完成：{ok}/{len(accounts)}")

    def main():
        return ok > 0

    return locals()


def mod_duanshipin():
    """金豆短视频 + 转盘抽奖（星播客 + 金豆商城）

    两个功能共用**同一个浏览器会话**，只启停一次：
      ticket → 建 browser → 短视频任务 → 转盘抽奖 → 关 browser

    短视频链路：
      redirect.do → getLoginInfo → getTiktok.do → gold/watchVideo.do

    转盘链路（wapact）：
      打开 JinDouMall 页面 → queryTurnTable → gold/api/lottery × N

    环境变量：
      CT_MAX_VIDEOS  每次最多尝试的视频数，默认 20
      CT_WHEEL       设 1 开启转盘抽奖（默认关，因为消耗金豆）
      CT_WHEEL_MIN   金豆低于此值不抽奖，默认 200
    """
    import datetime
    import json
    import os
    import random
    import re
    import time
    import uuid

    import requests
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import pad, unpad

    APP_UA = ("Mozilla/5.0 (Linux; U; Android 12; zh-cn; ONEPLUS A9000 "
              "Build/QKQ1.190716.003) AppleWebKit/533.1 (KHTML, like Gecko) "
              "Version/5.0 Mobile Safari/533.1")
    _K = b"1234567`90koiuyhgtfrdews"
    _IV = bytes(8)

    try:
        MAX_VIDEOS = int(os.environ.get("CT_MAX_VIDEOS", "20"))
    except Exception:
        MAX_VIDEOS = 20
    WHEEL_ON = str(os.environ.get("CT_WHEEL", "")).strip() in ("1", "true", "yes")
    try:
        WHEEL_MIN = int(os.environ.get("CT_WHEEL_MIN", "200"))
    except Exception:
        WHEEL_MIN = 200
    WHEEL_MAX = 3          # 每天最多 3 次
    WHEEL_COST = 20        # 每次消耗 20 金豆

    def _enc(s):
        return DES3.new(_K, DES3.MODE_CBC, _IV).encrypt(
            pad(str(s).encode(), 8)).hex()

    def _dec(h):
        return unpad(DES3.new(_K, DES3.MODE_CBC, _IV).decrypt(
            bytes.fromhex(h)), 8).decode()

    def _pq(p):
        return "".join(chr(ord(c) + 2) for c in str(p))

    def _ticket(phone, tk, uid):
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        body = ("<Request><HeaderInfos><Code>getSingle</Code><Timestamp>" + now
                + "</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken>"
                "<ClientType>" + CT_CLIENT_TYPE + "</ClientType><ShopId>20002</ShopId>"
                "<Source>110003</Source><SourcePassword>Sid98s</SourcePassword>"
                "<Token>" + tk + "</Token>"
                "<UserLoginName>" + _pq(phone) + "</UserLoginName></HeaderInfos>"
                "<Content><Attach>test</Attach><FieldData>"
                "<TargetId>" + _enc(uid) + "</TargetId>"
                "<Url>" + _enc(CT_TARGET_URL_PLAIN) + "</Url>"
                "</FieldData></Content></Request>")
        r = requests.post("https://appgologin.189.cn:9031/map/clientXML",
                          data=body.encode("utf-8"), verify=False, timeout=30,
                          headers={"user-agent":
                                   "CtClient;10.4.1;Android;13;22081212C;NTQzNzgx!#!MTgwNTg1"})
        m = re.findall("<Ticket>(.*?)</Ticket>", r.text)
        return _dec(m[0]) if m else None

    _skip = [False]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⏭️  未安装 playwright，跳过本模块")
        print("     安装: pip install playwright && python -m playwright install chromium")
        def main():
            return 'skip'
        return locals()

    if not install_browser_once():
        print("  ⏭️  chromium 不可用，跳过本模块")
        def main():
            return 'skip'
        return locals()

    accounts = parse_account_sources()
    if not accounts:
        print("⚠️  没有账号")
        return locals()

    def _watch_videos(page, xuid, uid_val, tag):
        """短视频：返回完成数"""
        aids = []
        for pgno in range(1, 4):
            try:
                vl = page.evaluate(
                    "async(n)=>{const r=await fetch('/luntanSafe/article/getTiktok.do"
                    "?page='+n+'&type=7&size=10&label=&vUserId=',"
                    "{credentials:'include'});return await r.json();}", pgno)
            except Exception:
                break
            for v in (vl.get("data") or []):
                if v.get("id"):
                    aids.append(v["id"])
            if len(aids) >= MAX_VIDEOS:
                break
        aids = aids[:MAX_VIDEOS]
        seen = set()
        aids = [a for a in aids if not (a in seen or seen.add(a))]
        print(f"  📋 待看视频 {len(aids)} 个")

        done = 0
        exhausted = False
        for idx, aid in enumerate(aids, 1):
            if exhausted:
                break
            body = {"userId": str(xuid), "uid": str(uuid.uuid4()),
                    "dqUserId": uid_val, "dsource": "客户端",
                    "articleId": aid}
            try:
                r = page.evaluate(
                    "async(b)=>{const r=await fetch('/luntanSafe/gold/watchVideo.do',"
                    "{method:'POST',credentials:'include',"
                    "headers:{'Content-Type':'application/json'},"
                    "body:JSON.stringify(b)});return {s:r.status,t:await r.text()};}",
                    body)
            except Exception as e:
                print(f"    ❌ [{idx}/{len(aids)}] {str(e)[:50]}")
                continue
            txt = str(r.get("t") or "")
            ok_flag = ('"code":10000' in txt) and ('\\"code\\":0' in txt
                                                   or '"code":0' in txt)
            if r.get("s") == 200 and ok_flag:
                done += 1
                print(f"    ✅ [{idx}/{len(aids)}] articleId={aid} +5 金豆")
            elif "资格已用完" in txt:
                print(f"    ⏹️  今日观看次数已用完（第 {idx} 个）")
                exhausted = True
            elif '"code":10001' in txt:
                print(f"    ℹ️  [{idx}/{len(aids)}] articleId={aid} 今日已看过")
            else:
                print(f"    ⚠️  [{idx}/{len(aids)}] articleId={aid}: {txt[:80]}")
            time.sleep(2 + random.random() * 2)
        return done

    def _do_wheel(page, ticket):
        """转盘抽奖：返回 (抽了几次, 获得列表)"""
        WACT = "https://wapact.189.cn:9001"
        # 打开金豆商城页（让瑞数在该域生效）
        try:
            page.goto(WACT + "/JinDouMall/JinDouMall_luckDraw.html?ticket=" + ticket,
                      wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass
        time.sleep(8)

        # 先登录拿 Authorization，存进页面变量
        login_js = """async (a) => {
            // AES-128-ECB(telecom_wap_2018) 加密登录体
            const enc = (txt) => {
                const key = CryptoJS.enc.Utf8.parse('telecom_wap_2018');
                const data = CryptoJS.enc.Utf8.parse(txt);
                const out = CryptoJS.AES.encrypt(data, key,
                    {mode: CryptoJS.mode.ECB, padding: CryptoJS.pad.Pkcs7});
                return out.toString();
            };
            const body = enc(JSON.stringify(a.ld));
            const r = await fetch('/unified/user/login', {
                method:'POST', credentials:'include',
                headers:{'Content-Type':'application/json;charset=UTF-8'},
                body: body
            });
            const j = await r.json();
            if (j.code === 0 && j.biz && j.biz.token) {
                window.__CT_TOKEN__ = j.biz.token;
                return {ok:true, token: j.biz.token.slice(0,20)};
            }
            return {ok:false, resp: JSON.stringify(j).slice(0,200)};
        }"""

        try:
            # CryptoJS 可能没加载，兜底从 CDN 注入
            has_cjs = page.evaluate("() => typeof CryptoJS !== 'undefined'")
            if not has_cjs:
                try:
                    page.add_script_tag(
                        url="https://img.189.cn/appclient/xbk/vue.min.js")
                except Exception:
                    pass
                page.add_script_tag(
                    url="https://cdn.jsdelivr.net/npm/crypto-js@4.1.1/crypto-js.min.js")
                time.sleep(1)
            ld = {"ticket": ticket,
                  "backUrl": "https%3A%2F%2Fwapact.189.cn%3A9001",
                  "platformCode": "P201010301", "loginType": 2}
            lr = page.evaluate(login_js, {"ld": ld})
            if not lr.get("ok"):
                print(f"  ⚠️  商城登录失败: {str(lr.get('resp'))[:120]}")
                return 0, []
            print(f"  ✅ 商城登录成功")
        except Exception as e:
            print(f"  ⚠️  商城登录异常: {str(e)[:100]}")
            return 0, []

        def js(method, path, body=None):
            expr = """async (a) => {
                const opt = {credentials:'include', method:a.m};
                if (a.b) { opt.headers = {'Content-Type':'application/json;charset=utf-8'};
                           opt.body = JSON.stringify(a.b); }
                if (window.__CT_TOKEN__) {
                    opt.headers = opt.headers || {};
                    opt.headers['Authorization'] = 'Bearer ' + window.__CT_TOKEN__;
                }
                const r = await fetch(a.u, opt);
                return {s: r.status, t: await r.text()};
            }"""
            return page.evaluate(expr, {"m": method, "u": WACT + path, "b": body})

        # 1) 余额
        try:
            r = js("GET", "/gateway/golden/api/queryInfo")
            txt = str(r.get("t") or "")
            coin = None
            if r.get("s") == 200 and '"code":0' in txt:
                try:
                    coin = json.loads(txt).get("biz", {}).get("amountTotal")
                except Exception:
                    pass
            print(f"  💰 当前金豆: {coin}")
        except Exception as e:
            print(f"  ⚠️  查余额失败: {str(e)[:60]}")
            coin = None

        if coin is not None and coin < WHEEL_MIN:
            print(f"  ⏭️  金豆 {coin} 低于阈值 {WHEEL_MIN}，不抽奖")
            return 0, []

        # 2) 查转盘（该接口服务端常有 999999，失败不影响抽奖）
        act_id = os.environ.get("CT_ACTIVITY_ID", "").strip() or \
            "6ae9940d9ed8c556e095f6d6"     # 逆向自抓包的转盘活动 ID
        try:
            r = js("GET", "/gateway/golden/api/queryTurnTable")
            txt = str(r.get("t") or "")
            if r.get("s") == 200 and '"code":0' in txt:
                j = json.loads(txt)
                biz = j.get("biz") or {}
                pool = biz.get("turntableList") or []
                if biz.get("activityId"):
                    act_id = biz["activityId"]
                print(f"  🎡 转盘奖池 {len(pool)} 个奖品")
                for p in pool[:4]:
                    print(f"      {p.get('title')} (odds={p.get('odds')})")
            else:
                print(f"  ℹ️  奖池查询不可用（{txt[:60]}），继续用已知活动 ID 抽奖")
        except Exception as e:
            print(f"  ℹ️  奖池查询异常（{str(e)[:50]}），继续用已知活动 ID")

        if not act_id:
            print("  ⚠️  未取到 activityId，跳过抽奖")
            return 0, []
        print(f"  🎯 活动 ID: {act_id}")

        # 3) 抽奖
        got = []
        for i in range(1, WHEEL_MAX + 1):
            if coin is not None and coin < WHEEL_COST:
                print(f"  ⏹️  金豆不足（{coin} < {WHEEL_COST}），停止抽奖")
                break
            try:
                r = js("POST", "/gateway/golden/api/lottery",
                       {"activityId": act_id})
                txt = str(r.get("t") or "")
                if r.get("s") != 200 or '"code":0' not in txt:
                    print(f"    ⚠️  第{i}次: {txt[:100]}")
                    break
                j = json.loads(txt)
                b = j.get("biz") or {}
                rc = str(b.get("resultCode", ""))
                coin = b.get("amountTotal", coin)
                title = ((b.get("resultInfo") or {}).get("title")) or "空气"
                if rc == "0":
                    got.append(title)
                    print(f"    🎁 第{i}次: {title}（余额 {coin}）")
                elif rc == "412":
                    print(f"    ⏹️  今日 {WHEEL_MAX} 次抽奖名额已用完")
                    break
                elif rc in ("413", "420"):
                    print(f"    ⏹️  金豆不足（余额 {coin}）")
                    break
                else:
                    print(f"    ⚠️  第{i}次: resultCode={rc} {txt[:80]}")
                    break
            except Exception as e:
                print(f"    ❌ 第{i}次: {str(e)[:60]}")
                break
            time.sleep(2 + random.random() * 2)
        return len(got), got

    ok = 0
    for phone in accounts:
        tk, uid_val = get_token_for(phone)
        masked = phone[:3] + "****" + phone[-4:]
        print(f"\n===== 金豆短视频 {masked} =====")
        if not tk or not uid_val:
            print("  ⚠️  缺少 token/userId，跳过")
            continue
        try:
            t = _ticket(phone, tk, uid_val)
            if not t:
                print("  ❌ 换 ticket 失败")
                continue

            entry = ("https://xbk.189.cn/luntanSafe/external/redirect.do"
                     "?ticket=" + t +
                     "&cmpid=khd-xbktgtokhd-syjh-jt"
                     "&indexUri=videoDetailImmersion&type=7")

            # ===== 只启一个浏览器，两个功能共用 =====
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=['--disable-dev-shm-usage', '--no-sandbox',
                          '--disable-gpu'])
                ctx = browser.new_context(
                    user_agent=APP_UA,
                    viewport={"width": 375, "height": 667},
                    is_mobile=True, has_touch=True, locale="zh-CN")
                page = ctx.new_page()
                try:
                    page.goto(entry, wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
                time.sleep(8)   # 等瑞数挑战

                # ---- 1. 短视频 ----
                li = page.evaluate(
                    "async()=>{const r=await fetch('/luntanSafe/user/getLoginInfo',"
                    "{credentials:'include'});return await r.json();}")
                xuid = (li.get("data") or {}).get("id")
                if xuid:
                    print(f"  ✅ 星播客登录: {xuid}")
                    done = _watch_videos(page, xuid, uid_val, masked)
                    print(f"  📊 短视频完成 {done} 个，预计 +{done * 5} 金豆")
                else:
                    print(f"  ❌ 星播客未登录: {str(li)[:100]}")

                # ---- 2. 转盘（同一浏览器）----
                if WHEEL_ON:
                    print(f"\n  === 转盘抽奖（消耗 {WHEEL_COST} 金豆/次）===")
                    try:
                        n, prizes = _do_wheel(page, t)
                        if n:
                            print(f"  📊 抽了 {n} 次，获得: {', '.join(prizes)}")
                            print(f"     共消耗 {n * WHEEL_COST} 金豆")
                    except Exception as e:
                        print(f"  ⚠️  转盘出错: {str(e)[:100]}")
                else:
                    print("  ⏭️  跳过转盘（设 CT_WHEEL=1 开启，会消耗金豆）")

                browser.close()
            ok += 1

        except Exception as e:
            print(f"  ❌ 出错: {str(e)[:150]}")

    print(f"\n金豆短视频完成：{ok}/{len(accounts)}")

    def main():
        if _skip[0]:
            return 'skip'
        return ok > 0

    return locals()


def mod_huafei():
    """话费兑换"""

    # ---- 本模块的 import ----
    import subprocess
    import sys
    import asyncio
    import aiohttp
    import os
    import requests
    import re
    import time as time_module  # 重命名导入以避免冲突
    import json
    import random
    import datetime
    import base64
    import ssl
    import certifi
    import traceback
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Cipher import AES
    from http import cookiejar
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.ssl_ import create_urllib3_context

    # ---- def get_network_time ----
    def get_network_time():
        """从淘宝接口获取网络时间"""
        url = "https://acs.m.taobao.com/gw/mtop.common.getTimestamp/"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "t" in data["data"]:
                    timestamp = int(data["data"]["t"])
                    return datetime.datetime.fromtimestamp(timestamp / 1000)
                else:
                    raise ValueError("接口返回数据格式错误")
            else:
                raise Exception(f"获取网络时间失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"⏰{str(get_network_time())[11:22]} 🌸获取网络时间失败: {e}")
            return datetime.datetime.now()

    local_time = datetime.datetime.now()

    network_time = get_network_time()

    time_diff = network_time - local_time

    print(f"💖本地时间: {local_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

    print(f"💖网络时间: {network_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

    print(f"💖时间差: {time_diff.total_seconds():.6f} 秒")

    MEXZ = os.getenv("MEXZ")

    morning_start = datetime.time(9, 30, 3)

    morning_end = datetime.time(10, 10, 30)

    afternoon_start = datetime.time(13, 30, 3)

    afternoon_end = datetime.time(14, 10, 30)

    now = get_network_time().time()

    if (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end):
        if not MEXZ:
            MEXZ = "0.5,5,6;1,10,3"
    else:
        MEXZ = "0.5,5,6;1,10,3"

    morning_exchanges, afternoon_exchanges = MEXZ.split(';')

    morning_exchanges = [f"{x}元话费" for x in morning_exchanges.split(',')]

    afternoon_exchanges = [f"{x}元话费" for x in afternoon_exchanges.split(',')]

    DY_PROXY = os.getenv("DY_PROXY123")

    OUTER_LOOP_COUNT = int(os.getenv("OUTER_LOOP_COUNT", "20"))

    INNER_LOOP_COUNT = int(os.getenv("INNER_LOOP_COUNT", "10"))

    # ---- def get_proxy_from_pool ----
    async def get_proxy_from_pool():
        """从代理池获取代理IP"""
        if not DY_PROXY:
            raise ValueError("DY_PROXY 环境变量未设置")

        async with aiohttp.ClientSession() as session:
            async with session.get(DY_PROXY) as response:
                if response.status != 200:
                    raise Exception(f"从代理池获取代理IP失败，状态码: {response.status}")
                proxy_ip = await response.text()
                return proxy_ip.strip()

    # ---- class BlockAll ----
    class BlockAll(cookiejar.CookiePolicy):
        return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
        netscape = True
        rfc2965 = hide_cookie2 = False

    # ---- def printn ----
    def printn(m):
        print(f'\n{m}')

    # ---- def print_time_log ----
    def print_time_log(m):
        print(f'⏰{str(get_network_time())[11:22]} 🌸{m}')

    ORIGIN_CIPHERS = ('DEFAULT@SECLEVEL=1')

    # ---- class DESAdapter ----
    class DESAdapter(HTTPAdapter):
        def __init__(self, *args, **kwargs):
            CIPHERS = ORIGIN_CIPHERS.split(':')
            random.shuffle(CIPHERS)
            CIPHERS = ':'.join(CIPHERS)
            self.CIPHERS = CIPHERS + ':!aNULL:!eNULL:!MD5'
            super().__init__(*args, **kwargs)

        def init_poolmanager(self, *args, **kwargs):
            context = create_urllib3_context(ciphers=self.CIPHERS)
            context.check_hostname = False
            kwargs['ssl_context'] = context
            return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

        def proxy_manager_for(self, *args, **kwargs):
            context = create_urllib3_context(ciphers=self.CIPHERS)
            context.check_hostname = False
            kwargs['ssl_context'] = context
            return super(DESAdapter, self).proxy_manager_for(*args, **kwargs)

    requests.packages.urllib3.disable_warnings()

    ssl_context = ssl.create_default_context()

    ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")

    ss = requests.session()

    ss.verify = certifi.where()

    ss.headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36",
        "Referer": "https://wapact.189.cn:9001/JinDouMall/JinDouMall_independentDetails.html"
    }

    ss.mount('https://', DESAdapter())

    ss.cookies.set_policy(BlockAll())

    yc = 1

    wt = 0

    h = None       # 当前小时（目标场次），运行时由 get_network_time() 填充

    kswt = 0.1

    yf = get_network_time().strftime("%Y%m")

    ip_list = []

    jp = {"9": {}, "13": {}}

    dhjl = huafei_log_read()

    if yf not in dhjl:
        dhjl[yf] = {}
    else:
        # 将现有字符串记录转换为集合（仅首次加载时执行）
        for di in dhjl[yf]:
            if isinstance(dhjl[yf][di], str):
                # 拆分字符串为列表，去重后转为集合
                phone_list = dhjl[yf][di].strip('#').split('#') if dhjl[yf][di] else []
                dhjl[yf][di] = set(phone_list)

    load_token_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'chinaTelecom_cache.json')

    try:
        with open(load_token_file, 'r') as f:
            load_token = json.load(f)
    except:
        load_token = {}

    errcode = {
        "0": "兑换成功✨",
        "412": "兑换次数已达上限💔",
        "413": "商品已兑完💨",
        "420": "未知错误😥",
        "410": "该活动未开始⏳",
        "501": "服务器处理错误💻",
        "Y0001": "当前等级不足，去升级兑当前话费📈",
        "Y0002": "使用翼相连网络600分钟可兑换此奖品📶",
        "Y0003": "共享流量400M可兑换此奖品💧",
        "Y0004": "共享流量2GB可兑换此奖品💧",
        "Y0005": "当前等级不足，去升级兑当前话费📈",
        "E0001": "您的网龄不足10年，暂不能兑换⏳"
    }

    key = b'1234567`90koiuyhgtfrdews'

    iv = 8 * b'\0'

    public_key_b64 = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBkLT15ThVgz6/NOl6s8GNPofdWzWbCkWnkaAm7O2LjkM1H7dMvzkiqdxU02jamGRHLX/ZNMCXHnPcW/sDhiFCBN18qFvy8g6VYb9QtroI09e176s+ZCtiv7hbin2cCTj99iUpnEloZm19lwHyo69u5UMiPMpq0/XKBO8lYhN/gwIDAQAB
    -----END PUBLIC KEY-----'''

    public_key_data = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+ugG5A8cZ3FqUKDwM57GM4io6JGcStivT8UdGt67PEOihLZTw3P7371+N47PrmsCpnTRzbTgcupKtUv8ImZalYk65dU8rjC/ridwhw9ffW2LBwvkEnDkkKKRi2liWIItDftJVBiWOh17o6gfbPoNrWORcAdcbpk2L+udld5kZNwIDAQAB
    -----END PUBLIC KEY-----'''

    # ---- def t ----
    def t(h):
        """返回 h 点场次的开抢时刻 = h-1 点 59 分 20 秒（提前 40 秒）

        例：h=9  → 今天 08:59:20（9 点场）
            h=13 → 今天 12:59:20（13 点场）
        口径与金豆权益模块一致：场次名前 1 分钟开抢。
        """
        date = get_network_time()
        target_hour = h - 1 if h > 0 else 23
        date_zero = date.replace(hour=target_hour, minute=59,
                                 second=20, microsecond=0)
        return time_module.mktime(date_zero.timetuple())

    # ---- def encrypt ----
    def encrypt(text):
        cipher = DES3.new(key, DES3.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(text.encode(), DES3.block_size))
        return ciphertext.hex()

    # ---- def decrypt ----
    def decrypt(text):
        ciphertext = bytes.fromhex(text)
        cipher = DES3.new(key, DES3.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), DES3.block_size)
        return plaintext.decode()

    # ---- def b64 ----
    def b64(plaintext):
        public_key = RSA.import_key(public_key_b64)
        cipher = PKCS1_v1_5.new(public_key)
        ciphertext = cipher.encrypt(plaintext.encode())
        return base64.b64encode(ciphertext).decode()

    # ---- def encrypt_para ----
    def encrypt_para(plaintext):
        public_key = RSA.import_key(public_key_data)
        cipher = PKCS1_v1_5.new(public_key)
        ciphertext = cipher.encrypt(plaintext.encode())
        return ciphertext.hex()

    # ---- def encode_phone ----
    def encode_phone(text):
        encoded_chars = []
        for char in text:
            encoded_chars.append(chr(ord(char) + 2))
        return ''.join(encoded_chars)

    # ---- def ophone ----
    def ophone(t):
        key = b'34d7cb0bcdf07523'
        utf8_t = t.encode('utf-8')
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(pad(utf8_t, AES.block_size))
        return ciphertext.hex()

    # ---- def send ----
    def send(uid, content):
        appToken = os.getenv("WXPUSHER_APP_TOKEN")
        uid = os.getenv("WXPUSHER_UID")

        if not appToken or not uid:
            raise ValueError("WXPUSHER_APP_TOKEN 或 WXPUSHER_UID 未设置")

        r = requests.post('https://wxpusher.zjiecode.com/api/send/message',
                         json={"appToken": appToken, "content": content, "contentType": 1, "uids": [uid]}).json()
        return r

    # ---- def userLoginNormal ----
    def userLoginNormal(phone, password):
        # ---- Token 模式: 跳过账密, 直接用已有 token 换 ticket ----
        _tk, _uid = get_token_for(phone)
        if _tk:
            if not _uid:
                print("❌ Token 模式需要 userId，格式：手机号#token#userId")
                return False
            print("✓ 使用 Token 登录（跳过账密）")
            return get_ticket(phone, _uid, _tk)

        alphabet = 'abcdef0123456789'
        uuid = [''.join(random.sample(alphabet, 8)), ''.join(random.sample(alphabet, 4)),
                '4' + ''.join(random.sample(alphabet, 3)), ''.join(random.sample(alphabet, 4)),
                ''.join(random.sample(alphabet, 12))]
        timestamp = get_network_time().strftime("%Y%m%d%H%M%S")
        loginAuthCipherAsymmertric = 'iPhone 14 15.4.' + uuid[0] + uuid[1] + phone + timestamp + password[:6] + '0$$$0.'

        try:
            r = ss.post('https://appgologin.189.cn:9031/login/client/userLoginNormal',
                       json={"headerInfos": {"code": "userLoginNormal", "timestamp": timestamp,
                                            "broadAccount": "", "broadToken": "",
                                            "clientType": CT_CLIENT_TYPE,
                                            "shopId": "20002", "source": "110003",
                                            "sourcePassword": "Sid98s", "token": "",
                                            "userLoginName": encode_phone(phone)},
                             "content": {"attach": "test", "fieldData": {"loginType": "4",
                                                                       "accountType": "",
                                                                       "loginAuthCipherAsymmertric": b64(loginAuthCipherAsymmertric),
                                                                       "deviceUid": uuid[0] + uuid[1] + uuid[2],
                                                                       "phoneNum": encode_phone(phone),
                                                                       "isChinatelecom": "0",
                                                                       "systemVersion": "15.4.0",
                                                                       "authentication": encode_phone(password)}}}).json()
        except Exception as e:
            print(f"登录请求失败，错误信息: {e}")
            return False

        if r is None:
            print(f"登录请求失败，返回值为 None")
            return False

        if 'responseData' not in r or r['responseData'] is None:
            print(f"登录请求失败，responseData 不存在或为 None: {r}")
            return False

        if 'data' not in r['responseData'] or r['responseData']['data'] is None:
            print(f"登录请求失败，data 不存在或为 None: {r}")
            return False

        if 'loginSuccessResult' not in r['responseData']['data']:
            print(f"登录请求失败，loginSuccessResult 不存在: {r}")
            return False

        l = r['responseData']['data']['loginSuccessResult']

        if l:
            load_token[phone] = l
            _lf = load_token_file
            with open(_lf, 'w') as f:
                json.dump(load_token, f)
            ticket = get_ticket(phone, l['userId'], l['token'])
            return ticket

        return False

    # ---- def get_ticket ----
    def get_ticket(phone, userId, token):
        r = ss.post('https://appgologin.189.cn:9031/map/clientXML',
                   data='<Request><HeaderInfos><Code>getSingle</Code><Timestamp>' + get_network_time().strftime("%Y%m%d%H%M%S") +
                   '</Timestamp><BroadAccount></BroadAccount><BroadToken></BroadToken><ClientType>' + CT_CLIENT_TYPE + '</ClientType>' +
                   '<ShopId>20002</ShopId><Source>110003</Source><SourcePassword>Sid98s</SourcePassword><Token>' + token +
                   '</Token><UserLoginName>' + encode_phone(phone) + '</UserLoginName></HeaderInfos><Content><Attach>test</Attach>' +
                   '<FieldData><TargetId>' + encrypt(userId) + '</TargetId><Url>' + encrypt(CT_TARGET_URL_PLAIN) + '</Url></FieldData></Content></Request>',
                   headers={'user-agent': 'CtClient;10.4.1;Android;13;22081212C;NTQzNzgx!#!MTgwNTg1'})

        tk = re.findall('<Ticket>(.*?)</Ticket>', r.text)
        if len(tk) == 0:
            return False
        return decrypt(tk[0])

    # ---- def exchange ----
    async def exchange(phone, s, title, aid, uid, amount):
        # global h  # 闭包内不需要
        masked_phone = phone[:3] + '****' + phone[-4:]
        try:
            tt = time_module.time()
            start_time = time_module.time()
            end_time = time_module.time()
            #print_time_log(f"📱{masked_phone} 准备兑换 {title} 啦~ ⏳用时: {end_time - start_time:.3f} 秒")

            now = get_network_time()
            if h is None:
                h = now.hour

            if h == 9:
                first_target_time = now.replace(hour=h, minute=59, second=30, microsecond=0)
            elif h == 13:
                first_target_time = now.replace(hour=h, minute=59, second=30, microsecond=0)

            first_time_diff = (first_target_time - now).total_seconds()
            if 0 <= first_time_diff <= 300:
                print_time_log(f"📱{masked_phone} 等待 {first_time_diff:.2f} 秒后开始哦~")
                await asyncio.sleep(first_time_diff)

            morning_start = datetime.time(9, 30, 50)
            morning_end = datetime.time(10, 10, 5)
            afternoon_start = datetime.time(13, 30, 40)
            afternoon_end = datetime.time(14, 10, 5)
            current_time = now.time()

            proxy = None
            #if (morning_start <= current_time <= morning_end) or (afternoon_start <= current_time <= afternoon_end):
                #if DY_PROXY:
                    #try:
                        #proxy_ip = await get_proxy_from_pool()
                        #proxy = f"http://{proxy_ip}"
                        #print_time_log(f"📱{masked_phone} 拿到代理IP啦~ 🌐{proxy_ip}")
                    #except ValueError as e:
                        #print_time_log(f"📱{masked_phone} {e} 用本地网络哦~ 📶")
                #else:
                    #print_time_log(f"📱{masked_phone} 用本地网络啦~ 📶")
            #else:
                #print_time_log(f"📱{masked_phone} 用本地网络哦~ 📶")

            #if h == 9:
                #second_target_time = now.replace(hour=h, minute=59, second=56, microsecond=803600)
            #elif h == 13:
                #second_target_time = now.replace(hour=h, minute=59, second=56, microsecond=793600)

            #second_time_diff = (second_target_time - get_network_time()).total_seconds()
            #if 0 <= second_time_diff <= 300:
                #print_time_log(f"📱{masked_phone} 再等 {second_time_diff:.2f} 秒就好啦~")
                #await asyncio.sleep(second_time_diff)

            #if proxy:
                #print_time_log(f"📱{masked_phone} 正在用代理IP: {proxy} 哦~")
            #else:
                #print_time_log(f"📱{masked_phone} 正在用本地网络~")

            url = "https://wapact.189.cn:9001/gateway/standExchange/detailNew/exchange"
            request_start_time = datetime.datetime.now()

            async with s.post(url, json={"activityId": aid}, proxy=proxy) as r:
                request_end_time = datetime.datetime.now()

                print(f'\n⏰{str(get_network_time())[11:22]}')
                print(f"📱{masked_phone} 发送兑换请求时间: {request_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
                print(f"📱{masked_phone} 请求耗时: {(request_end_time - request_start_time).total_seconds():.6f} 秒")

                if r.status == 412:
                    print(f"📱{masked_phone} 遇到连续412错误，终止兑换啦~ 😢")
                    return
                print(f"📱{masked_phone} 响应码: {r.status} {await r.text()}")
                if r.status == 200:
                    r_json = await r.json()
                    if r_json["code"] == 0:
                        if r_json["biz"] != {} and r_json["biz"]["resultCode"] in errcode:
                            print(f'📱{masked_phone}  ------ {str(get_network_time())[11:22]} ------ {title} {errcode[r_json["biz"]["resultCode"]]}')

                            if r_json["biz"]["resultCode"] in ["0", "412"]:
                                if r_json["biz"]["resultCode"] == "0":
                                    msg = phone + ":" + title + "兑换成功啦~ ✨"
                                    send(uid, msg)
                                if phone not in dhjl[yf][title]:
                                    dhjl[yf][title].add(phone)
                                    try:
                                        temp_dhjl = {k: {m: list(n) for m, n in v.items()} for k, v in dhjl.items()}
                                        huafei_log_write(temp_dhjl)
                                    except Exception:
                                        pass
                    else:
                        print_time_log(f'📱{masked_phone} {r_json}')
                else:
                    print_time_log(f"📱{masked_phone} 兑换请求失败: {await r.text()}")

        except Exception as e:
            print_time_log(f"📱{masked_phone} 发生错误: {e}")

    # ---- def dh ----
    async def dh(phone, s, title, aid, wt, uid):
        # global h  # 闭包内不需要
        masked_phone = phone[:3] + '****' + phone[-4:]
        print_time_log(f"📱{masked_phone} 💕{title} 开始兑换咯~")
        cs = 0
        tasks = []
        creat_start_time = datetime.datetime.now()
        # 每个账号10次兑换循环
        while cs < INNER_LOOP_COUNT:
            amount = title.split('元')[0]
            if (h == 9 and title in morning_exchanges) or (h == 13 and title in afternoon_exchanges):
                tasks.append(exchange(phone, s, title, aid, uid, amount))
            else:
                print_time_log(f"📱{masked_phone} 💕{title} 不在兑换时间哦，跳过啦~")
            cs += 1
            await asyncio.sleep(0.3)
        creat_end_time = datetime.datetime.now()
        print_time_log(f"📱{masked_phone} 创建了【{cs}】个任务 用时：{(creat_end_time - creat_start_time).total_seconds():.6f}秒")
        while wt > get_network_time().timestamp():
            await asyncio.sleep(1)
        await asyncio.gather(*tasks)

    # ---- def fetch_goods_list ----
    async def fetch_goods_list(session, masked_phone):
        """拉金豆商城商品列表，返回 (goods_list, last_resp)。

        服务端 getGoodsList 偶发返回 code=999999 / biz=None（脚本 2302 行注释
        也记录过该现象）。单次请求失败会让 jp 为空、后面 20 轮全空转，
        所以这里做【多次重试 + 参数降级】：
          第 1 组 完整参数
          第 2 组 去掉 tabOrder（空值传参可能被服务端判为非法）
          第 3 组 只留分页
        全部失败时返回 ([], 最后一次响应)，由调用方决定中止。
        """
        base = 'https://wapact.189.cn:9001/gateway/golden/goldGoods/getGoodsList'
        variants = [
            ('floorType=0&userType=1&page=1&order=3&tabOrder=', '完整参数'),
            ('floorType=0&userType=1&page=1&order=3', '去 tabOrder'),
            ('page=1', '仅分页'),
        ]
        last_resp = None
        for attempt, (qs, desc) in enumerate(variants, 1):
            if attempt > 1:
                await asyncio.sleep(1)
            try:
                resp = await session.get(f'{base}?{qs}')
                data = await resp.json()
            except Exception as e:
                last_resp = f'{type(e).__name__}: {e}'
                print_time_log(f"📱{masked_phone} 商品列表[{desc}]请求异常: {last_resp}")
                continue

            biz = data.get('biz') if isinstance(data, dict) else None
            goods = (biz or {}).get('ExchangeGoodslist')
            if isinstance(goods, list):
                print_time_log(f"📱{masked_phone} 商品列表[{desc}]拉到 {len(goods)} 个商品"
                               + ('' if attempt == 1 else f'（第 {attempt} 组参数）'))
                return goods, data

            last_resp = data
            print_time_log(f"📱{masked_phone} 商品列表[{desc}]失败: {str(data)[:160]}")

        return [], last_resp

    # ---- def aes_ecb_encrypt ----
    def aes_ecb_encrypt(plaintext, key):
        key = key.encode('utf-8')
        if len(key) not in [16, 24, 32]:
            raise ValueError("密钥长度必须为16/24/32字节哦~")

        padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(padded_data)
        return base64.b64encode(ciphertext).decode('utf-8')

    # ---- def ks ----
    async def ks(phone, ticket, uid):
        # global h, wt  # 闭包内不需要
        masked_phone = phone[:3] + '****' + phone[-4:]
        print_time_log(f"📱{masked_phone} 准备开始兑换流程啦~")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36",
            "Referer": "https://wapact.189.cn:9001/JinDouMall/JinDouMall_independentDetails.html"
        }

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), headers=headers, timeout=timeout) as s:
            try:
                login_data = {
                    "ticket": ticket,
                    "backUrl": "https%3A%2F%2Fwapact.189.cn%3A9001",
                    "platformCode": "P201010301",
                    "loginType": 2
                }
                encrypted_data = aes_ecb_encrypt(json.dumps(login_data), 'telecom_wap_2018')
                max_retries = 3
                retries = 0
                while retries < max_retries:
                    try:
                        login_response = await s.post(
                            'https://wapact.189.cn:9001/unified/user/login',
                            data=encrypted_data,
                            headers={
                                "Content-Type": "application/json;charset=UTF-8",
                                "Accept": "application/json, text/javascript, */*; q=0.01"
                            }
                        )

                        if login_response.status == 200:
                            login = await login_response.json()
                            break
                        elif login_response.status == 412:
                            print_time_log(f"📱{masked_phone} 登录失败，重新尝试~")
                            return await ks(phone, ticket, uid)
                        else:
                            print_time_log(f"📱{masked_phone} 登录请求失败，状态码: {login_response.status}")
                            print_time_log(f"响应内容: {await login_response.text()}")

                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        retries += 1
                        print_time_log(f"📱{masked_phone} 登录失败，重试 {retries}/{max_retries}... 错误: {e}")
                        await asyncio.sleep(2 ** retries)

                        if retries == max_retries:
                            print_time_log(f"📱{masked_phone} 登录失败，重新尝试~")
                            return await ks(phone, ticket, uid)

                if 'login' in locals() and login['code'] == 0:
                    s.headers["Authorization"] = "Bearer " + login["biz"]["token"]

                    r = await s.get('https://wapact.189.cn:9001/gateway/golden/api/queryInfo')
                    r_json = await r.json()
                    amountTotal = r_json["biz"]["amountTotal"]
                    print_time_log(f'📱{masked_phone} 金豆余额：{amountTotal} 个~ ✨')

                    goods_list, last_goods_resp = await fetch_goods_list(s, masked_phone)

                    if not goods_list:
                        print_time_log(
                            f"📱{masked_phone} ❌ 商品列表三个参数组合均失败，"
                            f"无法确定可兑换商品，跳过本账号（不再空转 {OUTER_LOOP_COUNT} 轮）")
                        print_time_log(f"     最后一次响应: {str(last_goods_resp)[:200]}")
                        return

                    for i in goods_list:
                        if '话费' not in i.get("title", ""):
                            continue
                        for j in morning_exchanges:
                            if j in i["title"]:
                                jp["9"][j] = i["id"]
                        for j in afternoon_exchanges:
                            if j in i["title"]:
                                jp["13"][j] = i["id"]

                    h = get_network_time().hour
                    if 11 > h:
                        h = 9
                    else:
                        h = 13

                    if len(sys.argv) == 2 and sys.argv[1].isdigit():
                        h = int(sys.argv[1])

                    d = jp[str(h)]
                    wt = t(h) + kswt
                    # 优化后：提前过滤，仅保留未兑换的商品
                    valid_products = []
                    for di in sorted(d.keys(), key=lambda x: float(x.replace('元话费', '')), reverse=True):
                        if phone not in dhjl[yf].get(di, set()):  # 用集合快速判断
                            valid_products.append(di)

                    # ---- 商品列表拉到了，但没有本次场次的目标面额 ----
                    if not valid_products:
                        if not d:
                            print_time_log(
                                f"📱{masked_phone} ⏭️  商品列表里没有 {h} 点场次的目标面额"
                                f"（目标: {morning_exchanges if h == 9 else afternoon_exchanges}），"
                                f"跳过本账号")
                        else:
                            print_time_log(
                                f"📱{masked_phone} ⏭️  目标面额本月已全部兑换过"
                                f"（{', '.join(d.keys())}），跳过本账号")
                        return

                    # ---- 场次时间判断：非场次直接跳过，不空转 ----
                    now_ts = get_network_time().timestamp()
                    leave = wt - now_ts      # 距开抢还有多少秒
                    if leave > 120:
                        print_time_log(
                            f"⏭️  距 {h} 点开抢还有 {leave / 3600:.1f} 小时，"
                            f"非场次时间跳过（提前 2 分钟才会启动）")
                        return
                    if now_ts - wt > 30 * 60:
                        print_time_log(
                            f"⏭️  {h} 点场次已过 {int((now_ts - wt) / 60)} 分钟，跳过")
                        return
                    if leave > 0:
                        print_time_log(f"⏳ 距开抢还有 {int(leave)} 秒，等待中...")
                        await asyncio.sleep(leave + 0.5)

                    # 新增：外层循环控制
                    for loop in range(OUTER_LOOP_COUNT):
                        print_time_log(f"📱{masked_phone} 开始第 {loop + 1}/{OUTER_LOOP_COUNT} 轮兑换")
                        tasks = []
                        for di in valid_products:
                            if wt - time_module.time() > 30 * 60:
                                    print_time_log(f"等待太久啦，退出咯~")
                                    return
                            tasks.append(dh(phone, s, di, d[di], wt, uid))
                        print_time_log(f"📱{masked_phone} 第 {loop + 1} 轮共有【{len(tasks)}】个兑换任务哦~")
                        await asyncio.gather(*tasks)

                        # 轮次之间休息3秒，避免请求过于频繁
                        if loop < OUTER_LOOP_COUNT - 1:
                            await asyncio.sleep(3)
                else:
                    print_time_log(f"📱{masked_phone} 获取token失败: {login['message']}")
            except Exception as e:
                print_time_log(f"📱{masked_phone} 发生错误: {e}")
                import traceback as _tb
                print_time_log(_tb.format_exc())
                return

    # ---- def main ----
    async def main():
        # global wt, rs, h  # 闭包内不需要
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22081212C Build/TKQ1.220829.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36",
            "Referer": "https://wapact.189.cn:9001/JinDouMall/JinDouMall_independentDetails.html"
        }

        timeout = aiohttp.ClientTimeout(total=20)
        rs = 0
        accounts = []
        for key, value in os.environ.items():
         if key == 'chinaTelecomAccount':
            accounts.extend(re.split(r'@|&',value))
        # Token 模式: 手机号#token#userId → 复用已有凭据, 不需要密码
        _tok_accounts = parse_token_accounts()
        if _tok_accounts:
            for _ph, (_tk, _uid) in _tok_accounts.items():
                accounts.append(f"{_ph}#{_tk}#{_uid}")
        if not accounts:
            print("没有检测到账号哦~")
            return
        account_count = len(accounts)
        print_time_log(f"💖检测到 【{account_count}】 个账号")
        print_time_log(f"💖外层兑换循环次数: 【{OUTER_LOOP_COUNT}】 次")

        batch_size = 20
        for i in range(0, account_count, batch_size):
            batch_accounts = accounts[i:i + batch_size]
            tasks = []
            for account in batch_accounts:
                account_info = account.split('#')
                phone = account_info[0]
                password = account_info[1]
                uid = account_info[-1]
                ticket = False
                masked_phone = phone[:3] + '****' + phone[-4:]
                if phone in load_token:
                    print_time_log(f'📱{masked_phone} 用缓存登录啦~ ✨')
                    ticket = get_ticket(phone, load_token[phone]['userId'], load_token[phone]['token'])

                if not ticket:
                    # userLoginNormal 内部优先走 Token 模式，日志文案要如实反映
                    _tk_chk, _uid_chk = get_token_for(phone)
                    if _tk_chk:
                        print_time_log(f'📱{masked_phone} 用 Token 登录啦~ 🔑')
                    else:
                        print_time_log(f'📱{masked_phone} 用密码登录啦~ 🔑')
                    ticket = userLoginNormal(phone, password)

                if ticket:
                    tasks.append(ks(phone, ticket, uid))
                else:
                    print_time_log(f'📱{masked_phone} 登录失败啦~ ❌')
                    continue

            while wt > datetime.datetime.now().timestamp():
                await asyncio.sleep(1)

            await asyncio.gather(*tasks)
            print_time_log(f"✅完成第 {i // batch_size + 1} 批账号处理~")
            await asyncio.sleep(2)

    START_LOG = rf'''
    +--------------------------------------------------------------------+
    |  🌸 欢迎使用 金豆兑换话费 ✨                                                              
    +--------------------------------------------------------------------+
    '''

    try:
        dhjl = huafei_log_read()
    except FileNotFoundError:
        dhjl = {}

    current_time = get_network_time()

    start_time_1 = current_time.replace(hour=10, minute=0, second=30)

    end_time_1 = current_time.replace(hour=10, minute=10, second=0)

    start_time_2 = current_time.replace(hour=14, minute=0, second=30)

    end_time_2 = current_time.replace(hour=14, minute=10, second=0)

    if (start_time_1 <= current_time < end_time_1) or (start_time_2 <= current_time < end_time_2):
        print("任务执行完成~")
    else:
        print("当前不在推送时间哦~")

    return locals()


# ============================================================
# 任务注册
# ============================================================
MODULES = {
    'jinyu': ('金豆权益', mod_jinyu),
    'qiandao': ('金豆签到', mod_qiandao),
    'renwu': ('金豆任务', mod_renwu),
    'duanshipin': ('金豆短视频', mod_duanshipin),
    'aiyinyue': ('爱音乐', mod_aiyinyue),
    'huafei': ('话费兑换', mod_huafei),
}


# ============================================================
# 运行框架
# ============================================================
def _tb():
    """打印精简 traceback（只留本文件的帧）"""
    import traceback
    nl = chr(10)
    tb = traceback.format_exc()
    keep = [l for l in tb.split(nl)
            if '电信全任务' in l or l.strip().startswith(
                ('File ', 'ValueError', 'TypeError', 'KeyError',
                 'AttributeError', 'RuntimeError'))]
    if keep:
        print('  ' + (nl + '  ').join(keep[:8]))


def _launch_jinyu(ns, main_fn):
    """金豆权益：main(timeDiff, isTRUE, hour)，且是定时抢购型"""
    h = datetime.datetime.now().hour
    print(f'⏰ 当前 {h} 点')

    run_Time = ns.get('run_Time')
    if not run_Time:
        raise RuntimeError('缺少 run_Time')

    if 0 < h < 10:
        wt = run_Time(9, 59, 8)
        print('准备抢 10 点场次')
    elif 10 <= h <= 14:
        wt = run_Time(13, 59, 8)
        print('准备抢 14 点场次')
    else:
        wt = run_Time(23, 57, 57)
        print('准备抢凌晨场次')

    nowait = os.environ.get('UNICOM_TELECOM_NOWAIT', '') == '1'
    if wt > time.time() and not nowait:
        wait = wt - time.time()
        if wait > 3600:
            print(f'⏳ 距开抢 {wait/3600:.1f} 小时，超过1小时不等待')
            print('   建议开抢前 2 分钟启动，或设 UNICOM_TELECOM_NOWAIT=1')
            return True
        print(f'⏳ 等待 {wait:.0f} 秒...')
        time.sleep(wait)
    elif nowait:
        print('⏭️  已设 NOWAIT，跳过等待')

    asyncio.run(main_fn(0, True, h))
    return True


def _launch_async(main_fn):
    """async 入口"""
    r = main_fn()
    if hasattr(r, '__await__'):
        asyncio.run(r)
    return True


def run_task(key):
    if key not in MODULES:
        print(f'未知任务: {key}')
        return False

    label, factory = MODULES[key]
    print()
    print('=' * 60)
    print(f'▶ {label}')
    print('=' * 60)

    try:
        ns = factory()
    except ModuleNotFoundError as e:
        print(f'  ⏭️  缺少依赖: {e.name}（pip install {e.name}）')
        return 'skip'
    except Exception as e:
        print(f'  ❌ 初始化失败: {type(e).__name__}: {e}')
        _tb()
        return False

    entry = ns.get('main') or ns.get('run')
    if not entry:
        print('  ⚠️ 找不到入口（main / run）')
        return False

    try:
        if key == 'jinyu':
            return _launch_jinyu(ns, entry)
        if key == 'huafei':
            return _launch_async(entry)
        r = entry()
        if hasattr(r, '__await__'):
            asyncio.run(r)
        # main() 可以返回 'skip' 表示主动跳过（如缺可选依赖）
        if r == 'skip':
            return 'skip'
        return True
    except SystemExit:
        return True
    except ValueError as e:
        msg = str(e)
        if any(k in msg for k in ('账号', '未配置', '没有可用')):
            print(f'  ⏭️  {msg}')
            return 'skip'
        print(f'  ❌ {msg}')
        return False
    except Exception as e:
        print(f'  ❌ 执行异常: {type(e).__name__}: {e}')
        _tb()
        return False


def main():
    if '--list' in sys.argv:
        print('可用任务:')
        for k, (label, _) in MODULES.items():
            print(f'  {k:12} {label}')
        return 0

    targets = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not targets:
        targets = list(MODULES.keys())

    acct = (os.environ.get('CT_ACCOUNT', '').strip()
            or os.environ.get('chinaTelecomAccount', '').strip())
    tok = (os.environ.get('CT_TOKEN', '').strip()
           or os.environ.get('chinaTelecomToken', '').strip())

    if not acct and not tok:
        print()
        print('=' * 62)
        print('⚠️  未配置账号')
        print('=' * 62)
        print('  二选一（青龙里填在环境变量）：')
        print()
        print('  【Token 模式】推荐，不需要模拟器')
        print('    CT_TOKEN = 手机号#token#userId')
        print('    多账号用 & 分隔:')
        print('    CT_TOKEN = 手机号1#token1#userId1&手机号2#token2#userId2')
        print()
        print('  【账密模式】需要电信服务密码')
        print('    CT_ACCOUNT = 手机号#服务密码')
        print()
        print('  兼容旧名: chinaTelecomToken / chinaTelecomAccount')
        print('=' * 62)
        return 1

    if tok:
        n = len(parse_token_accounts())
        mode = 'Token'
    else:
        n = len([x for x in re.split(r'[&@]', acct) if x.strip()])
        mode = '账密'

    print()
    print('=' * 62)
    print(f'电信全任务  {len(targets)} 个子任务，{n} 个账号（{mode}模式）')
    print('=' * 62)

    ok, skip, fail = 0, [], []
    for key in targets:
        r = run_task(key)
        if r is True:
            ok += 1
        elif r == 'skip':
            skip.append(key)
        else:
            fail.append(key)

    print()
    print('=' * 62)
    parts = [f'成功 {ok}']
    if skip:
        parts.append(f'跳过 {len(skip)}')
    if fail:
        parts.append(f'失败 {len(fail)}')
    print('完成：' + ' / '.join(parts) + f'  （共 {len(targets)} 个）')
    if skip:
        print(f'  跳过: {", ".join(skip)}')
    if fail:
        print(f'  失败: {", ".join(fail)}')
    print('=' * 62)
    return 0 if not fail else 1


if __name__ == '__main__':
    sys.exit(main())
