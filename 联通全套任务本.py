# -*- coding: utf-8 -*-
"""
任务名称
name: 中国联通 每日任务
定时规则
cron: 0 7,20 * * *
中国联通 Python 版 v1.2.1

依赖: pip install requests pycryptodome
      用 socks5 代理时另需 pip install PySocks

包含以下功能:
1. 首页签到 (话费红包/积分)
2. 联通祝福 (各类抽奖)
3. 天天领现金 (每日打卡/立减金)
4. 权益超市 (普通任务/抽奖/领奖/全局库存缓存；会员中心积分任务已下线)
5. 安全管家 (日常任务/积分领取)
6. 联通云盘 (家乡打卡/海岛逐浪应援完整活动/重复清理)
7. 联通阅读 (自动获取书籍/心跳阅读/抽奖/查红包)
8. 联通爱听 (JF积分任务/自动签到/任务完成/积分查询)
9. 沃云手机 (签到/任务/抽奖)
10. 区域专区 (自动识别安徽超级星期五/辽宁福利魔方/新疆/河南/云南执行特有任务)

更新说明:

### 20261002
v1.2.1:
- 联通云盘：海岛逐浪应援升级为完整活动流程 (活动状态/激活/选角/浪花值/角色形象/每日打卡/
  AI入戏视频/抽奖/中奖记录缓存)。
- 联通云盘：AI入戏支持本地上传人脸图 (脚本目录 face_images/ 或 UNICOM_CMF_LOCAL_IMAGES)、
  历史作品人脸图与云盘图片, 随机顺序尝试直至通过; 任务后自动清理临时照片。
- 联通云盘：新增云盘 Token 缓存复用 (校验通过则跳过登录链, 减少风控)。

### 20261001
v1.2.0:
- 更新家乡打卡和云手机活动，新增海岛逐浪应援。
- 完善阅读积分任务，优化云盘查询模式。
- 清理失效活动，优化领奖流程。
- 权益超市：移除已下线的会员中心积分任务，运行时增加下线提示。

### 20260711
v1.1.2:
- 沃云手机：抽奖改用专用活动码，修复抽奖次数恒为0。
- 联通云盘：新增家乡打卡（归属地识别/上传/抽奖/自动清理）。
- 权益超市：移除已下架的浇水任务。
- 联通云盘：移除已下架的乘风活动。

### 20260609
v1.1.1:
- 沃云手机：更新积分抽奖逻辑，兼容商品列表响应并避免重复执行。
- 联通云盘：乘风活动每日重新制作，复用历史作品人脸FID生成芒果视频。
- 联通云盘：自动领取云盘会员试用。
- 联通云盘：优化芒果权益领取后的延迟重试。
- 联通云盘：修复抽奖次数查询与自动抽奖请求头。

配置说明:
1. 账号变量 (chinaUnicomCookie):
   a. Token#AppId (推荐):
      export chinaUnicomCookie="a3e4c1ff2xxxxxxxxx#912d30xxxxxx"
   b. 仅填Token (旧模式):
      export chinaUnicomCookie="a3e4c1ff2xxxxxxxxx"
   c. 仅填手机号 (需已有未过期的本地Token缓存):
      export chinaUnicomCookie="18600000000"
   账号密码登录已失效，请使用有效Token。
   多账号用 & 或 换行 隔开；青龙请在环境变量中填写，不要将 export 行写入脚本。

2. 代理设置 (可选):
   export UNICOM_PROXY_API="你的代理提取链接" (支持 JSON/TXT 格式，自动识别)
   export UNICOM_PROXY_TYPE="socks5" (可选 http 或 socks5，默认 socks5)

3. 特殊功能设置:
   export UNICOM_GRAB_AMOUNT="5"          : (可选) 抢兑面额 (默认5，自动匹配含"5元"或"5话费"的奖品)
   export UNICOM_GRAB_AMOUNT="18,10,5,3,1": (可选) 抢兑面额降级链，按从左到右的顺序依次尝试
                                             首个抢不到自动降级下一档，任意一档成功即停止
   export UNICOM_TEST_MODE="query"        : (可选) 仅查询模式，跳过任务执行只查询资产
   export UNICOM_AH_FRIDAY_AMOUNT="50"    : (可选) 安徽超级星期五抢红包面额 (如50=抢50元红包, 不填则不执行)

4. 海岛逐浪应援 (破浪活动) 设置:
   export UNICOM_CMF_LOCAL_IMAGES=""      : (可选) 本地人脸图片路径 (多个用英文逗号分隔);
                                            不填时读取脚本目录 face_images/ 内的图片
   export UNICOM_CMF_DEL_CLOUD_PHOTOS="1" : (可选) 填 0 关闭 AI入戏后清理网盘临时照片
   export UNICOM_CMF_TEMPLATE_ID=""       : (可选) 芒果 AI入戏模板 ID
   export UNICOM_CMF_IMG_FID=""           : (可选) 指定云盘人脸图片 FID
   export UNICOM_CMF_TARGET_ID=""         : (可选) 指定选角 targetId (默认选第一个)
   export UNICOM_CLOUD_TTL_HOURS="12"     : (可选) 云盘 Token 缓存有效期 (小时)

定时规则建议 (Cron):
0 58 9,17 * * * (抢兑专用: 需 sign_config.run_grab_coupon=True，建议提前2分钟启动，脚本自动精准等待)
0 58 9 * * 5   (安徽超级星期五: 需设置 UNICOM_AH_FRIDAY_AMOUNT，每周五9:58启动)
0 7,20 * * *   (推荐：每天早晚7点/20点各跑一次，覆盖绝大部分签到任务)

From: YaoHuo8648
Email: zheyizzf@188.com
Update: 2026.10.02
"""
import os
import sys
import json
import time
import random
import re
import hashlib
import hmac
import base64
import requests
import uuid
import string
import threading
from datetime import datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass
from urllib.parse import urlparse, parse_qs, urlencode, unquote, quote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
SCRIPT_VERSION = "v1.2.1"
# ========================================
# 全局配置 (globalConfig)
# true=开启, false=关闭
# ========================================
globalConfig = {
    # --- 1. 功能总开关 (True=开启, False=关闭) ---
    "enable_sign": True,          # 首页签到 (🔺总开关, 含签到/任务/抢话费券)
    "enable_ttlxj": True,         # 天天领现金
    "enable_ttxc": True,          # 通通乡村
    "enable_ltzf": True,          # 联通祝福
    "enable_woread": True,        # 联通阅读
    "enable_security": True,      # 安全管家
    "enable_ltyp": True,          # 联通云盘
    "enable_market": True,        # 权益超市 (🔺总开关, 必须开启内部功能才能运行)
    "enable_jfsc": True,          # 积分商城 (联通积分商城 welfare-mall-front)
    "enable_aiting": True,        # 联通爱听
    "enable_wostore": True,       # 沃云手机
    "enable_regional": True,      # 区域专区
    "enable_notify": True,        # 推送通知

    # --- ✅ 签到区内部细分开关 ---
    "sign_config": {
        "run_grab_coupon": True, # False = 关闭抢话费券 (True=开启抢兑, 需配合 UNICOM_GRAB_AMOUNT 设置面额)
    },

    # --- 🛒 权益超市内部细分开关 (按需修改到这里) ---
    "market_config": {
        "run_task": True,         # False = 关闭做任务(浏览/分享)
        "run_draw": True,         # True  = 开启抽奖
        "run_claim": True,       # True  = 开启自动领奖(建议开启, 不领白不领)
    },

    # --- 🏷️ 区域专区内部细分开关 ---
    "regional_config": {
        # linktech 活动组(天天刮奖/沃享生活/专享权益/专属邀请码)
        # 不受归属地限制, 独立于辽宁福利魔方执行
        "run_linktech": True,
        "run_ah_friday": True,    # True = 开启安徽超级星期五 (需配合 UNICOM_AH_FRIDAY_AMOUNT 设置面额)
    },

    # --- 🎁 积分商城内部细分开关 ---
    "jfsc_config": {
        "run_task": True,         # False = 关闭赚积分任务(availablePointsDoTask)
        "run_exchange": True,     # True  = 开启积分兑换位查询(列出当前积分可兑商品, 不会自动下单)
        "exchange_channel": "100028",  # 积分商城渠道号
    },

    # --- 2. 设备ID配置 ---
    "refresh_device_id": False,   # False:使用缓存ID, True:强制刷新
}
# App 版本标识: 取自联通 App v13.2.1 (com.sinovatech.unicom.ui) 的
# string/version_argument 资源值。联通侧按此校验客户端版本, 过旧会被风控。
# 可用环境变量 UNICOM_APP_VERSION 覆盖。
APP_VERSION = os.environ.get("UNICOM_APP_VERSION", "android@13.0201").strip() or "android@13.0201"
COMMON_CONSTANTS = {
    "UA": f"Dalvik/2.1.0 (Linux; U; Android 12; Mi 10 Pro MIUI/21.11.3);unicom{{version:{APP_VERSION}}}",
    "MARKET_UA": f"Dalvik/2.1.0 (Linux; U; Android 12; Mi 10 Pro MIUI/21.11.3);unicom{{version:{APP_VERSION}}}",
    "MARKET_H5_UA": f"Mozilla/5.0 (Linux; Android 10; MI 8 Build/QKQ1.190828.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.146 Mobile Safari/537.36; unicom{{version:{APP_VERSION},desmobile:0}};devicetype{{deviceBrand:Xiaomi,deviceModel:MI 8}}",
    "APP_VERSION": APP_VERSION,
}
XJ_ACTIVITY_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
XJ_ACTIVITY_YEAR = os.environ.get("XJ_ACTIVITY_YEAR", str(datetime.now().year))
XJ_ACTIVITY_MONTH = os.environ.get("XJ_ACTIVITY_MONTH", XJ_ACTIVITY_MONTHS[datetime.now().month - 1])
XJ_ACTIVITY_ID = f"{XJ_ACTIVITY_MONTH}{XJ_ACTIVITY_YEAR}Act"
XJ_MONTHLY_DRAW_ATTEMPT_COUNT = max(int(os.environ.get("UNICOM_ATTEMPT_COUNT", "1") or "1"), 1)
XJ_USER_AGENT = os.environ.get(
    "XJ_USER_AGENT",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0701};ltst;OSVersion/16.2"
)
WOCARE_CONSTANTS = {
	"serviceLife": "wocareMBHServiceLife1",
	"anotherApiKey": "beea1c7edf7c4989b2d3621c4255132f",
	"anotherEncryptionKey": "f4cd4ffeb5554586acf65ba7110534f5",
	"minRetries": "1"
}
WOCARE_ACTIVITIES = [
	{"name": "星座配对", "id": 2},
	{"name": "大转盘", "id": 3},
	{"name": "盲盒抽奖", "id": 4}
]
AITING_BASE_URL = "https://pcc.woread.com.cn"
AITING_SIGN_KEY_APPKEY = "7ZxQ9rT3wE5sB2dF"
AITING_SIGN_KEY_API = "woread!@#qwe1234"
AITING_SIGN_KEY_REQUERTID = "46iCw24ewAZbNkK6"
AITING_CLIENT_KEY = "1"
AITING_AES_KEY = "j2K81755sxV12wFx"
AITING_AES_IV = "16-Bytes--String"
WOREAD_KEY = "woreadst^&*12345"
YUNNAN_LIFE_BASE_URL = "https://wsm.wx.yn10010.com"
YUNNAN_LIFE_ACT_ID = "47191519589909"
YUNNAN_LIFE_SIGN_SALT = "ltynsh@sd23kjkgj2mbnfa0"
YUNNAN_LIFE_ACCESS_KEY = "ltynsh"
YUNNAN_LIFE_TO_URL = "https://wsm.wx.yn10010.com/micropage/orderPages/newYear/2025newYearsDay?channelId=1001010"
YUNNAN_LIFE_TASKS = [
    {"taskName": "每日签到", "taskCode": "DAILY_SIGN"},
    {"taskName": "浏览年终大回馈,好礼多多", "taskCode": "BROWSE_5TOWNS"},
]
TTXC_BASE_URL = "https://epay.10010.com/cu-ca-game-front"
TTXC_APP_BASE_URL = "https://epay.10010.com/cu-ca-app-front"
TTXC_CHANNEL = "225"
TTXC_REFERER = "https://epay.10010.com/cu-ca-game-web/index.html?channel=qdqp"
TTXC_GARBAGE_WAIT_SECONDS = int(os.environ.get("UNICOM_TTXC_GARBAGE_WAIT", "28") or "28")
TTXC_GROW_MAX_CHARGE_PER_LAND = int(os.environ.get("UNICOM_TTXC_GROW_MAX_CHARGE_PER_LAND", "20") or "20")
TTXC_HARVEST_WAIT_SECONDS = int(os.environ.get("UNICOM_TTXC_HARVEST_WAIT", "3") or "3")
TTXC_NEWBIE_STEPS = ["G01", "G02", "G03", "G03_2", "G04", "G05", "G09", "G10", "G11", "G12"]
# 抢兑面额。UNICOM_GRAB_AMOUNT 支持逗号分隔的降级列表, 例如 "18,10,5,3,1":
#   首选 18 元, 抢不到自动依次降级到 10/5/3/1 元(按列表顺序从左到右)。
#   单值 "5" 则只抢 5 元, 行为与旧版一致。
GRAB_AMOUNT = os.environ.get("UNICOM_GRAB_AMOUNT", "5")


def parse_grab_amounts(raw):
    """解析 UNICOM_GRAB_AMOUNT, 返回去重后的面额列表(保持给定顺序)。

    兼容:
      "5"          -> [5]
      "18,10,5,3,1" -> [18, 10, 5, 3, 1]
      "5, 10 , 3"  -> [5, 10, 3]
    非法项(非数字/<=0)直接丢弃, 全部非法时回落到默认 [5]。
    """
    result = []
    for part in str(raw or "").split(','):
        part = part.strip()
        if not part:
            continue
        try:
            val = int(part)
        except ValueError:
            continue
        if val > 0 and val not in result:
            result.append(val)
    return result or [5]


GRAB_AMOUNTS = parse_grab_amounts(GRAB_AMOUNT)
AH_FRIDAY_AMOUNT = os.environ.get("UNICOM_AH_FRIDAY_AMOUNT", "")
AH_FRIDAY_BASE_URL = "http://123.138.11.116:8080"
AH_FRIDAY_SECKILL_TIMES = int(os.environ.get("UNICOM_AH_FRIDAY_TIMES", "50") or "50")
AH_FRIDAY_INTERVAL = float(os.environ.get("UNICOM_AH_FRIDAY_INTERVAL", "0.3") or "0.3")
WOSTORE_CLOUD_ACTIVITY_CODE = os.environ.get("UNICOM_WOSTORE_ACTIVITY_CODE", "Points_Obtain_2507")
WOSTORE_CLOUD_SIGN_CODE = os.environ.get("UNICOM_WOSTORE_SIGN_CODE", "Points_Sign_2507")
WOSTORE_CLOUD_LOGIN_ACTIVITY_ID = os.environ.get("UNICOM_WOSTORE_LOGIN_ACTIVITY_ID", "HD2026092100322")
WOSTORE_CLOUD_ACTIVITY_CODES = [x.strip() for x in os.environ.get("UNICOM_WOSTORE_ACTIVITY_CODES", WOSTORE_CLOUD_ACTIVITY_CODE).split(",") if x.strip()]
# 云手机抽奖专用活动码 (与任务/签到码不同): activityCode=主抽奖, activityCode2=第二抽奖
WOSTORE_LOTTERY_ACTIVITY_CODES = [x.strip() for x in os.environ.get("UNICOM_WOSTORE_LOTTERY_ACTIVITY_CODES", "HD2026092100322").split(",") if x.strip()]
WOSTORE_POINTS_ACT_CODE = os.environ.get("UNICOM_WOSTORE_POINTS_ACT_CODE", "Points_Exchange_2507")
WOSTORE_POINTS_GOODS_ID_10 = os.environ.get("UNICOM_WOSTORE_POINTS_GOODS_ID_10", "2026031010")
WOSTORE_POINTS_GOODS_ID_1 = os.environ.get("UNICOM_WOSTORE_POINTS_GOODS_ID_1", "2026031001")
WOSTORE_POINTS_STOP_PRIZE = os.environ.get("UNICOM_WOSTORE_POINTS_STOP_PRIZE", "7天体验卡")
WOSTORE_POINTS_MAX_DRAW = max(int(os.environ.get("UNICOM_WOSTORE_POINTS_MAX_DRAW", "1") or "1"), 0)
# 云盘家乡打卡活动 (上传图片抽奖)
HOMETOWN_ENABLE = os.environ.get("UNICOM_HOMETOWN_ENABLE", "1").strip() not in ("0", "false", "False", "")
HOMETOWN_MOBILE_KEY = os.environ.get("UNICOM_HOMETOWN_MOBILE_KEY", "CBWGjFHjZdhTf7h8")
HOMETOWN_AES_IV = os.environ.get("UNICOM_HOMETOWN_AES_IV", "wNSOYIB1k1DjY5lA")
HOMETOWN_LOTTERY_SECRET = os.environ.get("UNICOM_HOMETOWN_LOTTERY_SECRET", "s8Hf3LqP9xN2vM5bR7tY1wZ4cA6eG0K")
HOMETOWN_OPEN_ACTIVITY_ID = os.environ.get("UNICOM_HOMETOWN_OPEN_ACTIVITY_ID", "MjU=")
HOMETOWN_LOTTERY_ACTIVITY_ID = os.environ.get("UNICOM_HOMETOWN_LOTTERY_ACTIVITY_ID", "Mzg=")
ISLAND_ACTIVITY_ID = "NDA="
# ---- edop appId (取票凭证) ----
# 用于 getTicketByNative 换取业务入口 ticket。
# 实测(v13.2.1 客户端 + 2026-11 在线验证):
#   edop_unicom_d67b3e30 / 3a6cc75a / 68e8fa69 / 4b80047a  仍可用(取票成功)
#   edop_unicom_bc40cc05                                  可用
#   edop_unicom_663a9c79 / 6db56c2a / default            取票失败(appid not found)
# 因此保留原有 appId, 并把新发现的 bc40cc05 作为河南商都的备选, 全部支持环境变量覆盖。
EDOP_APPID_CLOUD = os.environ.get("UNICOM_APPID_CLOUD", "edop_unicom_d67b3e30").strip()
EDOP_APPID_SECURITY = os.environ.get("UNICOM_APPID_SECURITY", "edop_unicom_3a6cc75a").strip()
EDOP_APPID_WOSTORE = os.environ.get("UNICOM_APPID_WOSTORE", "edop_unicom_68e8fa69").strip()
EDOP_APPID_SHANGDU = os.environ.get("UNICOM_APPID_SHANGDU", "edop_unicom_4b80047a").strip()
# ---- 海岛逐浪应援 (破浪活动) 配置 ----
ISLAND_ACT_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 "
                 "(KHTML, like Gecko)  unicom{version:iphone_c@13.0100};ltst;OSVersion/18.7.8")
ISLAND_MGTV_BASE = "https://mgcact.api.mgtv.com"
ISLAND_MGTV_TEMPLATE_ID = os.environ.get("UNICOM_CMF_TEMPLATE_ID", "2104457184351981568").strip()
ISLAND_MGTV_IMG_FID = os.environ.get("UNICOM_CMF_IMG_FID", os.environ.get("UNICOM_YPHD_MGTV_IMG_FID", "")).strip()
ISLAND_TARGET_ID = os.environ.get("UNICOM_CMF_TARGET_ID", "").strip()
ISLAND_DEL_CLOUD_PHOTOS = os.environ.get("UNICOM_CMF_DEL_CLOUD_PHOTOS", "1").strip() not in ("0", "false", "False")
ISLAND_CLOUD_TTL_HOURS = float(os.environ.get("UNICOM_CLOUD_TTL_HOURS", "12") or "12")
ISLAND_TEMP_PHOTO_PREFIX = "cmfface_"
ISLAND_UID_AES_KEY = "GWI21sdtBTU48egd"
ISLAND_UID_AES_IV = "wNSOYIB1k1DjY5lA"
ISLAND_PRIZE_CACHE_PATH = os.environ.get(
    "UNICOM_PRIZE_CACHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "unicom_prize_cache.json"))
_SCRIPT_DIR_ISLAND = os.path.dirname(os.path.abspath(__file__))
_island_img_raw = os.environ.get("UNICOM_CMF_LOCAL_IMAGES", "").replace("，", ",").strip()
if _island_img_raw:
    ISLAND_LOCAL_IMAGES = [p if os.path.isabs(p) else os.path.join(_SCRIPT_DIR_ISLAND, p)
                           for p in (x.strip() for x in _island_img_raw.split(",")) if p]
else:
    _island_img_dir = os.path.join(_SCRIPT_DIR_ISLAND, "face_images")
    ISLAND_LOCAL_IMAGES = (
        sorted(os.path.join(_island_img_dir, f) for f in os.listdir(_island_img_dir)
               if f.lower().endswith((".jpg", ".jpeg", ".png")))
        if os.path.isdir(_island_img_dir) else [])
# 活动入口备用参数 (编码存放)
_FALLBACK_ENTRY = base64.b64decode("aHR0cHM6Ly9wYW4ud28uY24vcy8xQzFMNlg3ODY0Mg==").decode()
ENTRY_OVERRIDE = os.environ.get("UNICOM_CMF_SOURCE", "").strip()
# 活动接口预置参数 (编码存放, 内部流程使用)
_ACT_PRESET = json.loads(base64.b64decode(
    "eyJwIjoiL2FjdGl2aXR5L2ludml0ZS9iaW5kIiwicyI6ImFjdGl2aXR5OmlzTGFuZDppbnZpdGUiLCJrIjoiaW52aXRlclVzZXJJZCIsImEiOiIvYWN0aXZpdHkvZ2V0VGltZXN0YW1wIn0=").decode())
HOMETOWN_MATERIAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unicom_hometown_material.jpg")
# 家乡打卡上传素材: 服务端不校验内容/大小, 内置最小合法 JPEG (1x1 白点) 即可通过
HOMETOWN_MATERIAL_BYTES = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAP//////////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAABAAEBAREA/8QA"
    "FBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxD/2Q=="
)
WOSTORE_CLOUD_TIMEOUT = int(os.environ.get("UNICOM_WOSTORE_TIMEOUT", "15") or "15")
WOSTORE_CLOUD_RETRIES = int(os.environ.get("UNICOM_WOSTORE_RETRIES", "3") or "3")
UNICOM_TOKEN_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unicom_token_cache.json")
# 本地 Token 缓存的最大保留时长(小时)。仅作粗筛, 真实有效性由 onLine 判定。
# 可用环境变量 UNICOM_TOKEN_CACHE_HOURS 覆盖。
UNICOM_TOKEN_CACHE_MAX_AGE_HOURS = int(os.environ.get("UNICOM_TOKEN_CACHE_HOURS", "168") or "168")
LOGIN_PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDc+CZK9bBA9IU+gZUOc6FUGu7yO9WpTNB0PzmgFBh96Mg1WrovD1oqZ+eIF4LjvxKXGOdI79JRdve9NPhQo07+uqGQgE4imwNnRx7PFtCRryiIEcUoavuNtuRVoBAm6qdB0SrctgaqGfLgKvZHOnwTjyNqjBUxzMeQlEC2czEMSwIDAQAB
-----END PUBLIC KEY-----"""

def mask_str(s):
    try:
        s = str(s)
        if len(s) == 11 and s.isdigit():
            return s[:3] + "****" + s[7:]
        elif s.startswith("enc_"):
            return s
        elif len(s) > 11:
            return s[:6] + "******" + s[-6:]
        return s
    except:
        return s


def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default

def pretty_json(data):
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(data)

def response_summary(data):
    if not isinstance(data, dict):
        return str(data)
    meta = data.get("meta")
    source = meta if isinstance(meta, dict) else data
    code = source.get("code") or source.get("resultCode") or source.get("rsp_code")
    msg = source.get("message") or source.get("msg") or source.get("desc") or source.get("resultMsg") or source.get("rsp_desc")
    if msg:
        return str(msg)
    if code:
        return f"接口返回异常[{code}]"
    return "接口返回异常"

class _EmptyResponse:
    """网络重试彻底失败时返回的兜底对象。

    让调用方 xxx.json() 不抛异常，返回空 dict，
    避免单个接口失败中断整个任务流程。
    """
    status_code = 0
    ok = False
    text = ''
    headers = {}

    def json(self):
        return {}

    def iter_lines(self):
        return iter(())

    def __bool__(self):
        return False


class FailoverSession:
    """包装 requests.Session，自动为所有请求添加代理故障转移"""
    RETRIABLE_KEYWORDS = ("Max retries exceeded", "timed out", "connection", "SOCKS", "ProxyError", "ConnectionError", "SSLError", "SSLEOF")

    def __init__(self, session, owner):
        self._session = session
        self._owner = owner  # UserService 实例引用
        # 并发抢兑时同一账号的多个子任务共享 session, 遍历 cookiejar 需加锁
        self._cookie_lock = threading.Lock()

    def __getattr__(self, name):
        return getattr(self._session, name)

    def _should_failover(self, err_msg):
        if not os.environ.get("UNICOM_PROXY_API"):
            return False
        err_lower = err_msg.lower()
        return any(kw.lower() in err_lower for kw in self.RETRIABLE_KEYWORDS)

    def _has_streaming_payload(self, kwargs):
        if kwargs.get("files"):
            return True
        data = kwargs.get("data")
        return hasattr(data, "read")

    # 值得重试的网络层异常（服务端 RST、超时、连接被拒等）
    NET_RETRY = (
        'connectionreseterror', 'connection aborted', 'remote end closed',
        'connectionerror', 'timeout', 'timed out', 'protocolerror',
        'sslerror', 'proxyerror', 'chunkedencodingerror',
    )

    def _is_net_error(self, e):
        name = type(e).__name__.lower()
        if name in ('connectionerror', 'timeout', 'protocolerror',
                    'chunkedencodingerror', 'sslerror', 'proxyerror'):
            return True
        msg = str(e).lower()
        return any(k in msg for k in self.NET_RETRY)

    def _is_timeout(self, e):
        """判断是否为纯超时(挂起)类异常"""
        if isinstance(e, requests.exceptions.Timeout):
            return True
        name = type(e).__name__.lower()
        if name in ('readtimeout', 'connecttimeout', 'timeout'):
            return True
        msg = str(e).lower()
        return 'timed out' in msg or 'timeout' in msg

    def request(self, method, url, **kwargs):
        # 兜底超时: requests 默认无超时, 网络挂起会导致整个脚本永久卡死。
        # 这里统一补默认值, 调用方显式传入的 timeout 优先。
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = 20
        try:
            return self._session.request(method, url, **kwargs)
        except Exception as e:
            has_proxy = bool(os.environ.get("UNICOM_PROXY_API"))
            is_net = self._is_net_error(e)

            # 代理模式下：走原有的故障转移逻辑
            if has_proxy and self._should_failover(str(e)):
                self._owner.log(f"⚠️ [故障转移] {url} 请求异常: {e}")
                err_str = str(e).lower()
                is_ssl_or_proxy_err = any(
                    x in err_str for x in ("ssleof", "unexpected_eof",
                                           "sslerror", "socks", "proxyerror"))
                if is_ssl_or_proxy_err:
                    self._owner.configure_proxy()
                else:
                    self._owner.failover_proxy()
                if self._has_streaming_payload(kwargs):
                    raise
                try:
                    return self._session.request(method, url, **kwargs)
                except Exception as retry_err:
                    self._owner.log(f"⚠️ [故障转移] {url} 重试仍异常: {retry_err}")
                    return _EmptyResponse()

            # 非代理模式（或不是代理类问题）：网络抖动也重试，避免整个任务中断
            # 但纯超时(挂起)不重试: 一次超时就说明链路已断, 重试只会成倍拉长总耗时
            if is_net and not self._has_streaming_payload(kwargs) and not self._is_timeout(e):
                for attempt in range(1, 4):
                    wait = attempt * 2
                    self._owner.log(
                        f"⚠️ [网络重试 {attempt}/3] {url.split('/')[-1][:40]} "
                        f"{type(e).__name__}，{wait}秒后重试")
                    time.sleep(wait)
                    try:
                        return self._session.request(method, url, **kwargs)
                    except Exception as e2:
                        if not self._is_net_error(e2):
                            break
                        e = e2
                self._owner.log(
                    f"❌ [网络失败] {url.split('/')[-1][:40]} 重试3次仍失败，"
                    f"跳过该接口")
                return _EmptyResponse()

            # 超时: 直接放弃, 不重试(避免成倍放大总耗时)
            if self._is_timeout(e) and not self._has_streaming_payload(kwargs):
                self._owner.log(
                    f"❌ [请求超时] {url.split('/')[-1][:40]} "
                    f"{int(kwargs.get('timeout') or 20)}s未响应，跳过该接口")
                return _EmptyResponse()

            # 流式响应（下载/上传）不能重试，直接抛出
            if self._has_streaming_payload(kwargs):
                raise
            raise

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

class UserService:
    wocare_available = True

    def __init__(self, index, config_str):
        self.index = index
        self.valid = False
        self.notify_logs = []
        raw_session = requests.Session()

        class SourceAddressAdapter(HTTPAdapter):

            def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
                pool_kwargs['source_address'] = ('0.0.0.0', 0)
                super(SourceAddressAdapter, self).init_poolmanager(connections, maxsize, block, **pool_kwargs)

            def get_connection(self, url, proxies=None):
                return super(SourceAddressAdapter, self).get_connection(url, proxies)
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = SourceAddressAdapter(max_retries=retries)
        raw_session.mount('http://', adapter)
        raw_session.mount('https://', adapter)
        raw_session.headers.update({
            "User-Agent": COMMON_CONSTANTS["UA"],
            "Connection": "keep-alive"
        })
        raw_session.verify = False
        import urllib3
        urllib3.disable_warnings()
        self.session = FailoverSession(raw_session, self)
        self.account_mobile = ""
        self.mobile = ""
        self.account_password = ""
        self.token_online = ""
        self.token_refresh = ""
        self.cookie = ""
        self.appId = ""
        self.city_info = []
        self.last_read_submission_time = 0
        # 抢兑到账核对的基线: 抢兑前账户明细指纹列表 + 我的卡券指纹集合
        self._grab_baseline_count = []
        self._grab_baseline_coupons = set()
        if globalConfig.get("refresh_device_id", False):
            self.uuid = str(uuid.uuid4()).replace('-', '')
        else:
            self.uuid = os.environ.get("chinaUnicomUuid") or str(uuid.uuid4()).replace('-', '')
        self.unicomTokenId = self.random_string(32)
        self.tokenId_cookie = "chinaunicom-" + self.random_string(32, string.ascii_uppercase + string.digits)
        self.ecs_token = ""
        self.rptId = ""
        self.ttxc_newbie_list = None
        self.ttxc_nick_name = ""
        self.sec_ai_share_key = ""
        self.sec_share_task_code = ""
        self.sec_share_task_name = "联通助理-分享AI助手对话"
        self.sec_pending_claim_tasks = {}
        self.init_account(config_str)

    def _parse_proxy_response(self, text):
        """解析代理API响应，支持JSON和文本格式，提取ip/port/user/pass"""
        text = text.strip()

        def extract(d):
            if not d or not d.get('ip') or not d.get('port'):
                return None
            return {
                'ip': str(d['ip']),
                'port': int(d['port']),
                'user': str(d.get('account') or d.get('user') or ''),
                'pass': str(d.get('password') or d.get('pass') or '')
            }
        try:
            json_start = text.find('{')
            json_end = text.rfind('}')
            if json_start != -1 and json_end != -1:
                data = json.loads(text[json_start:json_end + 1])
                if data.get('ip') and data.get('port'):
                    return extract(data)
                if data.get('data'):
                    inner = data['data']
                    if isinstance(inner, dict) and inner.get('list') and isinstance(inner['list'], list) and len(inner['list']) > 0:
                        return extract(inner['list'][0])
                    if isinstance(inner, list) and len(inner) > 0:
                        return extract(inner[0])
                    if isinstance(inner, dict) and inner.get('ip'):
                        return extract(inner)
                if data.get('result') and isinstance(data['result'], dict) and data['result'].get('ip'):
                    return extract(data['result'])
        except:
            pass
        m = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s\t]+(\d{1,5})', text)
        if m:
            return {'ip': m.group(1), 'port': int(m.group(2)), 'user': '', 'pass': ''}
        return None

    def configure_proxy(self):
        proxy_api = os.environ.get("UNICOM_PROXY_API")
        if not proxy_api:
            return
        proxy_type = os.environ.get("UNICOM_PROXY_TYPE", "socks5").lower()
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self.log(f"🔄 [第{attempt}次] 重试获取代理IP ({proxy_type})...")
                    time.sleep(2)
                else:
                    self.log(f"正在获取代理IP (模式: {proxy_type})...")
                res = requests.get(proxy_api, timeout=10)
                if res.status_code != 200:
                    self.log(f"⚠️ 获取代理失败: HTTP {res.status_code}")
                    continue
                proxy_info = self._parse_proxy_response(res.text)
                if not proxy_info:
                    preview = res.text[:100] + "..." if len(res.text) > 100 else res.text
                    self.log(f"❌ 提取失败: 无法识别代理格式 (内容: {preview})")
                    continue
                ip, port = proxy_info['ip'], proxy_info['port']
                user, pwd = proxy_info['user'], proxy_info['pass']
                if user and pwd:
                    proxy_url = f"{proxy_type}://{quote(user)}:{quote(pwd)}@{ip}:{port}"
                    log_msg = f"{proxy_type}://***:***@{ip}:{port}"
                else:
                    proxy_url = f"{proxy_type}://{ip}:{port}"
                    log_msg = proxy_url
                self.log(f"🔍 提取成功: {log_msg}")
                test_proxies = {"http": proxy_url, "https": proxy_url}
                try:
                    requests.get("https://www.baidu.com", proxies=test_proxies, timeout=3)
                    self.session.proxies.update(test_proxies)
                    self.log("✅ 代理连通性测试通过")
                    return
                except Exception as te:
                    self.log(f"⚠️ 代理测试失败: {te}")
            except Exception as e:
                self.log(f"❌ 请求代理API异常: {e}")
        self.log(f"🚫 重试{max_retries}次均失败，回退至本地IP")

    def failover_proxy(self):
        proxy_api = os.environ.get("UNICOM_PROXY_API")
        if not proxy_api:
            return False
        self.log("⚠️ [故障转移] 检测到网络不稳定，正在检查当前代理是否存活...")
        try:
            requests.get("https://m.client.10010.com/mobileService/business/get/getCity", proxies=self.session.proxies, timeout=3)
            self.log("✅ [故障转移] 经测试当前IP仍有效，继续复用，暂不提取新IP。")
            time.sleep(1)
            return True
        except Exception as e:
            self.log(f"❌ [故障转移] 当前代理已失效 ({e})，准备更换新IP...")
        time.sleep(2)
        self.configure_proxy()
        return True

    def init_account(self, config_str):
        parts = config_str.split('#')
        # 账号密码模式已被联通下线(unicom_login 直接返回 False), 保留分支只会
        # 把 "11位纯数字token#appId" 之类的配置误判成账号密码并静默登录失败。
        # 因此统一按 Token#AppId[#手机号] 解析; 第一段本身是手机号时记为 mobile,
        # 后续由 load_token_from_cache() 用本地缓存补齐登录态。
        self.token_online = parts[0].strip()
        # 只有"纯手机号"单段配置才走缓存登录; 若还带第二段(appId), 说明
        # 第一段是 token, 即便是 11 位纯数字也不能当成手机号。
        if len(self.token_online) == 11 and self.token_online.isdigit() and len(parts) == 1:
            self.account_mobile = self.token_online
            self.token_online = ""  # 置空, 交给 load_token_from_cache 填充
            self.log(f"识别到纯手机号模式: {mask_str(self.account_mobile)}")
        if len(parts) > 1:
            self.appId = parts[1].strip()
        if len(parts) > 2 and parts[2]:
            potential_mobile = parts[2].strip()
            if potential_mobile.isdigit() and len(potential_mobile) == 11:
                self.account_mobile = potential_mobile
        self.unicomTokenId = str(uuid.uuid4()).replace('-', '') # simplified
        self.tokenId_cookie = "chinaunicom-" + str(uuid.uuid4()).replace('-', '').upper() # simplified
        self.cookie_string = f"TOKENID_COOKIE={self.tokenId_cookie}; UNICOM_TOKENID={self.unicomTokenId}; sdkuuid={self.unicomTokenId}"
        self.update_session_cookies()

    def update_session_cookies(self):
        if self.cookie_string:
            cookies = {}
            for item in self.cookie_string.split(';'):
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k.strip()] = v.strip()
            self.session.cookies.update(cookies)
        extra_cookies = {}
        if self.token_online:
            extra_cookies['token_online'] = self.token_online
        if self.appId:
            extra_cookies['appId'] = self.appId
        # act.10010.com / epay.10010.com 等子系统只认 ecs_token，
        # 缺了会返回「您还没有登录」(0001)
        if getattr(self, 'ecs_token', ''):
            extra_cookies['ecs_token'] = self.ecs_token
        if getattr(self, 't3_token', ''):
            extra_cookies['t3_token'] = self.t3_token
        # 部分接口需要明文手机号
        if self.account_mobile:
            extra_cookies['u_account'] = self.account_mobile
            extra_cookies['c_mobile'] = self.account_mobile
        if extra_cookies:
            # 关键: 同一请求里出现两个同名但值不同的 cookie 时, 服务端只认第一个,
            # 会拿到旧值而报"用户未登录"(0001)。
            # 例如 onLine 响应已下发 domain=.10010.com 的 ecs_token,
            # 这里再写一个无域的, 两者值不同就会冲突。
            # 因此先清掉同名 cookie, 再统一写入无域版本。
            for name in extra_cookies:
                try:
                    self.session.cookies.clear(name=name)
                except KeyError:
                    pass
                except Exception:
                    pass
            self.session.cookies.update(extra_cookies)

    def log(self, msg, notify=False):
        prefix = f"账号[{self.index}]"
        full_msg = f"{prefix}{msg}"
        log_line = f"[{datetime.now().strftime('%H:%M:%S')}] {full_msg}"
        print(log_line)
        if notify:
            self.notify_logs.append(str(msg))

    def request_direct(self, method, url, **kwargs):
        session = requests.Session()
        session.verify = False
        try:
            return session.request(method, url, **kwargs)
        finally:
            session.close()

    def rsa_encrypt(self, val):
        self.log(f"正在进行 RSA 加密...")
        try:
             random_str = ''.join(str(random.randint(0, 9)) for _ in range(6))
             text = str(val) + random_str
             data = text.encode('utf-8')
             key_pem = LOGIN_PUB_KEY.encode()
             recipient_key = RSA.import_key(key_pem)
             cipher_rsa = PKCS1_v1_5.new(recipient_key)
             enc_data = cipher_rsa.encrypt(data)
             return base64.b64encode(enc_data).decode('utf-8')
        except Exception as e:
            self.log(f"RSA加密失败: {str(e)}")
            return ""

    def generate_appid(self):

        def rnd(): return str(random.randint(0, 9))
        return (f"{rnd()}f{rnd()}af"
                f"{rnd()}{rnd()}ad"
                f"{rnd()}912d306b5053abf90c7ebbb695887bc"
                f"870ae0706d573c348539c26c5c0a878641fcc0d3e90acb9be1e6ef858a"
                f"59af546f3c826988332376b7d18c8ea2398ee3a9c3db947e2471d32a49") + rnd() + rnd()

    def unicom_login(self):
        self.log("账号密码登录已失效，请使用 Token#AppId 或纯手机号本地缓存")
        return False

    def request(self, method, url, **kwargs):
        try:
            # Cookie 只发往其所属域: requests 的 cookiejar 自带域过滤,
            # 但 get_dict() 会把 session 里所有域的 cookie 混在一起,
            # 直接拼成 Cookie 头会把联通主站的 ecs_token/token_online
            # 泄露给第三方域(wocare/爱听/云盘/区域专区等)。
            # 注意: update_session_cookies 设置的 token_online/ecs_token 等是
            # 无域 cookie, 它们是脚本故意给各子系统(含 act.10010.com)用的通用凭据,
            # 必须照常发送, 不能被过滤掉。
            from urllib.parse import urlparse as _urlparse
            req_host = (_urlparse(url).hostname or '').lower()
            current_cookies = {}
            # 遍历 cookiejar 时取快照: 并发抢兑模式下同一账号的两个子任务
            # 共享同一个 session, 另一线程 set_cookie 会导致
            # "dictionary changed size during iteration"
            try:
                with self.session._cookie_lock:
                    cookie_snapshot = list(self.session.cookies)
            except Exception as e:
                # 这里一旦失败, jar 里的 token_online/ecs_token 会全部丢失,
                # 下游接口只会报"用户未登录", 极难排查, 必须留痕
                self.log(f"⚠️ 读取Cookie失败, 本次请求可能缺少登录态: {e}")
                cookie_snapshot = []
            for c in cookie_snapshot:
                domain = (c.domain or '').lstrip('.').lower()
                if not domain:
                    # 无域 cookie = 脚本主动设置的通用凭据, 全域发送
                    current_cookies[c.name] = c.value
                elif req_host == domain or req_host.endswith('.' + domain):
                    current_cookies[c.name] = c.value
            if self.cookie_string:
                for item in self.cookie_string.split(';'):
                    if '=' in item:
                        k, v = item.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if not v:
                            continue
                        # jar 中已有的同名 cookie 优先, cookie_string 只补缺
                        current_cookies.setdefault(k, v)
            cookie_header = "; ".join([f"{k}={v}" for k, v in current_cookies.items()])
            # 不修改调用方传入的 headers 字典(避免副作用)
            headers = dict(kwargs.get('headers') or {})
            if cookie_header and not headers.get('Cookie'):
                headers['Cookie'] = cookie_header
            if headers:
                kwargs['headers'] = headers
            timeout = kwargs.get('timeout', 10)
            if 'timeout' in kwargs: del kwargs['timeout']
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            if response is None:
                self.log(f"请求 {url} 无响应")
                return None
            if response.status_code >= 400:
                self.log(f"请求 {url} 返回状态码 {response.status_code}")
            return response
        except Exception as e:
            self.log(f"请求 {url} 异常: {str(e)}")
            return None

    def ensure_login(self, max_attempts=3):
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                self.log(f"🔄 登录重试 {attempt}/{max_attempts}")
            if not self.token_online and self.account_mobile:
                self.load_token_from_cache()
            if self.token_online and self.onLine():
                self.save_token_to_cache()
                return True
            if not self.token_online:
                if self.account_password:
                    self.log("账号密码登录已失效，未找到可用 Token，跳过")
                return False
            if attempt < max_attempts:
                time.sleep(2)
        return False

    def load_token_from_cache(self):
        if not self.account_mobile:
            return False
        if not os.path.exists(UNICOM_TOKEN_CACHE_PATH):
            return False
        try:
            with open(UNICOM_TOKEN_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            user_cache = cache.get(self.account_mobile)
            if user_cache and user_cache.get('token_online'):
                # 本地有效期只是"粗筛", 真正失效与否由服务端 onLine 判定。
                # 原先固定 12 小时太保守: 实测 Token 过了 15.8 小时仍然有效
                # (onLine 返回 code=0, "我的卡券"接口也能正常查到券),
                # 结果被误判为过期而无法复用。这里放宽到默认 7 天,
                # 若 onLine 判定失效, ensure_login 会照常重试并覆盖缓存。
                age_ms = (datetime.now().timestamp() * 1000) - user_cache.get('timestamp', 0)
                age_hours = age_ms / (60 * 60 * 1000)
                if age_ms < UNICOM_TOKEN_CACHE_MAX_AGE_HOURS * 60 * 60 * 1000:
                    self.token_online = user_cache['token_online']
                    self.appId = user_cache.get('appId', self.appId)
                    self.city_info = user_cache.get('city_info', [])
                    self.update_session_cookies()
                    self.log(f"♻️ [缓存复用] 成功加载本地 Token ({user_cache.get('time')}, "
                             f"已存 {age_hours:.1f} 小时)")
                    return True
                self.log(f"⏳ [缓存复用] 本地 Token 已存 {age_hours:.1f} 小时, "
                         f"超过 {UNICOM_TOKEN_CACHE_MAX_AGE_HOURS} 小时上限, 尝试直接验证有效性")
        except Exception as e:
            self.log(f"⚠️ 读取本地Token缓存失败, 将走正常登录流程: {e}")
        return False

    def save_token_to_cache(self):
        if not self.account_mobile:
            return
        cache = {}
        if os.path.exists(UNICOM_TOKEN_CACHE_PATH):
             try:
                with open(UNICOM_TOKEN_CACHE_PATH, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
             except: pass
        now = datetime.now()
        cache[self.account_mobile] = {
            "token_online": self.token_online,
            "appId": self.appId,
            "city_info": getattr(self, 'city_info', []),
            "cookieString": "",
            "timestamp": int(now.timestamp() * 1000),
            "time": now.strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(UNICOM_TOKEN_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            self.log("💾 [缓存保存] Token 已写入本地文件")
        except Exception as e:
            self.log(f"❌ 保存缓存失败: {str(e)}")

    def get_city_info(self):
        """查询归属地信息。

        注意: 该接口对新版 App 已失效, 服务端一律返回 HTML 引导页而非 JSON。
        归属地的可靠来源是 onLine 响应中的 list 字段, 因此这里失败属于正常情况,
        只做静默降级, 不打错误日志以免误导。
        """
        try:
            url = "https://m.client.10010.com/mobileService/business/get/getCity"
            res = self.request("post", url, data={}, timeout=10)
            if res is None:
                return False
            try:
                result = res.json()
            except ValueError:
                # 服务端返回 HTML(接口已下线), 归属地由 onLine 提供
                return False
            if result.get('code') == '200' and result.get('list'):
                 self.city_info = result.get('list')
                 return True
            self.log(f"获取城市信息失败: code={result.get('code')}")
            return False
        except Exception as e:
            # 静默吞异常会导致区域专区任务全部被跳过且无任何提示
            self.log(f"获取城市信息异常: {e}")
            return False

    def queryRemain(self):
        try:
            if not self.ecs_token:
                if not self.onLine():
                    self.log("❌ 无法获取 ecs_token，跳过查询")
                    return
            self.log("==== 资产查询 ====")
            self.log("正在查询套餐余量...")
            url = "https://m.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm"
            headers = {
                "User-Agent": COMMON_CONSTANTS["MARKET_UA"],
                "Cookie": f"ecs_token={self.ecs_token}"
            }
            res = self.request("get", url, headers=headers)
            if not res: return
            result = res.json()
            if result.get('code') == '0000':
                current_balance = "0.00"
                real_time_fee = "0.00"
                if result.get('curntbalancecust'):
                    current_balance = str(result['curntbalancecust'])
                if result.get('realfeecust'):
                    real_time_fee = str(result['realfeecust'])
                self.log(f"💰 [资产-话费] 当前余额: {current_balance}元, 实时话费: {real_time_fee}元", notify=True)
                pkg_list = result.get('realTimeFeeSpecialFlagThree', [])
                if pkg_list and isinstance(pkg_list, list):
                    self.log(f"    📋 [套餐详情]:", notify=True)
                    for item in pkg_list:
                        sub_items = item.get('subItems', [])
                        if sub_items:
                            for sub in sub_items:
                                bill = sub.get('bill', {})
                                if bill:
                                    name = bill.get('integrateitem', '未知项')
                                    fee = bill.get('realfee', '0.00')
                                    self.log(f"       - {name}: {fee}元", notify=True)
            else:
                msg = result.get('desc') or result.get('msg') or "未知错误"
                self.log(f"套餐余量查询失败: {msg}")
        except Exception as e:
            self.log(f"queryRemain 异常: {str(e)}")

    def onLine(self):
        if not self.token_online:
             self.log("❌ 缺少 token_online，无法执行 onLine")
             return False
        try:
            url = "https://m.client.10010.com/mobileService/onLine.htm"
            data = {
                'isFirstInstall': '1',
                'netWay': 'Wifi',
                'version': APP_VERSION,
                'token_online': self.token_online,
                'provinceChanel': 'general',
                'deviceModel': 'ALN-AL10',
                'step': 'dingshi',
                'androidId': '291a7deb1d716b5a',
                'reqtime': int(time.time() * 1000)
            }
            if self.appId:
                data['appId'] = self.appId
            res = self.request('post', url, data=data)
            if not res: return False
            result = res.json()
            code = result.get('code')
            if code == '0' or code == 0:
                self.valid = True
                desmobile = result.get('desmobile', '')
                if len(desmobile) == 11 and desmobile.isdigit():
                    self.account_mobile = desmobile
                    self.mobile = desmobile
                elif desmobile.startswith("enc_"):
                     # 服务端返回的是加密手机号, 无法直接用。
                     # 关键: 只要账号变量里配了明文手机号(Token#AppId#手机号 第三段),
                     # 就必须回填到 self.mobile —— 否则爱听等依赖手机号的模块
                     # 会拿到空串, 导致 ulogin 报 "token错误"。
                     if not self.account_mobile:
                          self.log("⚠️ 注意: 服务端返回了加密手机号且未配置本地手机号")
                     else:
                          self.mobile = self.account_mobile
                # 兜底: 任何情况下 self.mobile 都不应为空
                if not self.mobile and self.account_mobile:
                    self.mobile = self.account_mobile
                self.log("登录成功")
                # 保留缓存中的归属地: 登录响应偶尔不含 list, 直接覆盖会导致区域专区整体跳过
                login_city = result.get('list') or []
                if login_city:
                    self.city_info = login_city
                elif not self.city_info:
                    self.log("⚠️ 登录响应未返回归属地, 且本地无缓存, 区域专区将跳过")
                # 用 or "" 兜底: 字段缺失时 result.get 返回 None, 后续会拼出 "ecs_token=None"
                self.ecs_token = result.get('ecs_token') or ""
                self.t3_token = result.get('t3_token', '')
                self.private_token = result.get('private_token', '')
                if not self.ecs_token:
                    self.log("⚠️ 登录响应中未获取到 ecs_token, 部分子系统接口可能失败")
                # 关键：刷新 session cookie，后续接口才认 ecs_token
                self.update_session_cookies()
                return True
            else:
                self.log(f"登录失败[{code}]: {result.get('msg')}")
                return False
        except Exception as e:
            self.log(f"onLine 异常: {str(e)}")
            return False

    def gettaskip(self):
        orderId = self.random_string(32).upper()
        try:
            url = "https://m.client.10010.com/taskcallback/topstories/gettaskip"
            data = {
                "mobile": self.account_mobile,
                "orderId": orderId
            }
            self.request("post", url, data=data)
        except Exception as e:
            self.log(f"获取taskip失败: {e}")
        return orderId

    def sign_getContinuous(self, is_query_only=False):
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/signin/getContinuous"
            params = {
                "taskId": "",
                "channel": "wode",
                "imei": self.uuid
            }
            res = self.request("get", url, params=params)
            if not res: return
            result = res.json()
            code = result.get('code')
            if code == "0000":
                todayIsSignIn = result.get('data', {}).get('todayIsSignIn', 'n')
                self.log(f"签到区今天{'已' if todayIsSignIn == 'y' else '未'}签到", notify=True)
                if todayIsSignIn == 'y':
                    pass
                else:
                    if not is_query_only:
                        time.sleep(1)
                        self.sign_daySign()
                    else:
                        self.log("签到区: [查询模式] 跳过自动打卡")
            else:
                self.log(f"签到区查询签到状态失败[{code}]: {result.get('desc', '')}")
        except Exception as e:
            self.log(f"sign_getContinuous 异常: {str(e)}")

    def sign_daySign(self):
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/signin/daySign"
            res = self.request("post", url, data={})
            if not res: return
            result = res.json()
            code = result.get('code')
            if code == "0000":
                data = result.get('data', {})
                msg = f"签到区签到成功: [{data.get('statusDesc', '')}]{data.get('redSignMessage', '')}"
                self.log(msg)
            elif code == "0002" and "已经签到" in result.get('desc', ''):
                self.log("签到区签到成功: 今日已完成签到！")
            else:
                self.log(f"签到区签到失败[{code}]: {result.get('desc', '')}")
        except Exception as e:
            self.log(f"sign_daySign 异常: {str(e)}")

    def sign_getTelephone(self, is_initial=False, silent=False):
        try:
            url = "https://act.10010.com/SigninApp/convert/getTelephone"
            res = self.request("post", url, data={})
            if not res: return None
            result = res.json()
            status = result.get('status')
            if status == "0000" and result.get('data'):
                tel_val = result['data'].get('telephone', 0)
                try:
                    current_amount = float(tel_val)
                except:
                    current_amount = 0.0
                if silent:
                    return current_amount
                if is_initial:
                    msg = f"签到区-话费红包: 运行前总额 {current_amount:.2f}元"
                    self.sign_initial_amount = current_amount
                else:
                    if hasattr(self, 'sign_initial_amount'):
                        increase = current_amount - self.sign_initial_amount
                        self.log(f"签到区-话费红包: 本次运行增加 {increase:.2f}元", notify=True)
                    msg = f"签到区-话费红包: 总额 {current_amount:.2f}元"
                    exp_val = result['data'].get('needexpNumber', 0)
                    try:
                        exp_num = float(exp_val)
                    except:
                        exp_num = 0.0
                    if exp_num > 0:
                        msg += f"，其中 {result['data'].get('needexpNumber', '0')}元 将于 {result['data'].get('month', '')}月底到期"
                self.log(msg, notify=not is_initial)
                return current_amount
            else:
                if not silent:
                    self.log(f"签到区查询话费红包失败[{status}]: {result.get('msg', '')}")
                return None
        except Exception as e:
            if not silent:
                self.log(f"sign_getTelephone 异常: {str(e)}")
            return None

    def sign_getTaskList(self):
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/taskList"
            headers = {"Referer": "https://img.client.10010.com/"}
            for i in range(30):
                res = self.request("get", url, params={"type": "2"}, headers=headers, timeout=10)
                if not res: return
                result = res.json()
                code = result.get('code')
                if code == "0329" or "火爆" in result.get('desc', ''):
                    self.log("签到区: 系统繁忙(0329)，停止后续尝试")
                    break
                if code != "0000":
                    self.log(f"签到区-任务中心: 获取任务列表失败[{code}]: {result.get('desc', '')}")
                    return
                tag_list = result.get('data', {}).get('tagList', []) or []
                task_list = result.get('data', {}).get('taskList', []) or []
                all_tasks = task_list + [t for tag in tag_list for t in tag.get('taskDTOList', [])]
                all_tasks = [t for t in all_tasks if t]
                if not all_tasks:
                    if i == 0: self.log("签到区-任务中心: 当前无任何任务。")
                    break
                do_task = next((t for t in all_tasks if t.get('taskState') == '1' and t.get('taskType') == '5'), None)
                if do_task:
                    self.log(f"签到区-任务中心: 开始执行任务 [{do_task.get('taskName')}]")
                    self.sign_doTaskFromList(do_task)
                    time.sleep(3)
                    continue
                claim_task = next((t for t in all_tasks if t.get('taskState') == '0'), None)
                if claim_task:
                    self.log(f"签到区-任务中心: 发现可领取奖励的任务 [{claim_task.get('taskName')}]")
                    self.sign_getTaskReward(claim_task.get('id'))
                    time.sleep(2)
                    continue
                if i == 0:
                    self.log("签到区-任务中心: 没有可执行或可领取的任务。")
                else:
                    self.log("签到区-任务中心: 所有任务处理完毕。")
                break
        except Exception as e:
            self.log(f"sign_getTaskList 异常: {str(e)}")

    def sign_doTaskFromList(self, task):
        try:
            if task.get('url') and task['url'] != '1' and task['url'].startswith('http'):
                 self.request("get", task['url'], headers={"Referer": "https://img.client.10010.com/"})
                 self.log(f"签到区-任务中心: 浏览页面 [{task.get('taskName')}]")
                 time.sleep(random.uniform(5, 7))
            orderId = self.gettaskip()
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/completeTask"
            params = {
                "taskId": task.get('id'),
                "orderId": orderId,
                "systemCode": "QDQD"
            }
            res = self.request("get", url, params=params)
            if not res: return
            result = res.json()
            code = result.get('code')
            if code == "0000":
                self.log(f"签到区-任务中心: ✅ 任务 [{task.get('taskName')}] 已完成")
            else:
                self.log(f"签到区-任务中心: ❌ 任务 [{task.get('taskName')}] 完成失败[{code}]: {result.get('desc', '未知错误')}")
        except Exception as e:
             self.log(f"sign_doTaskFromList 异常: {str(e)}")

    def sign_getTaskReward(self, task_id):
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/getTaskReward"
            res = self.request("get", url, params={"taskId": task_id})
            if not res: return
            result = res.json()
            code = result.get('code')
            if code == "0000":
                data = result.get('data', {})
                if data.get('code') == '0000':
                    self.log(f"签到区-领取奖励: [{data.get('prizeName', '')}] {data.get('prizeNameRed', '')}")
                else:
                    self.log(f"签到区-领取奖励失败[{data.get('code')}]: {result.get('desc') or data.get('desc')}")
            else:
                self.log(f"签到区-领取奖励失败[{code}]: {result.get('desc', '')}")
        except Exception as e:
            self.log(f"sign_getTaskReward 异常: {str(e)}")

    def sign_month_sign_gift(self, is_query_only=False):
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/floor/getMonthSign"
            headers = {"Referer": "https://img.client.10010.com/"}
            res = self.request("get", url, headers=headers, timeout=10)
            if not res: return
            result = res.json()
            code = result.get('code')
            if code != "0000":
                self.log(f"签到区-月签有礼: 查询失败[{code}]: {result.get('desc', '')}")
                return
            task_list = result.get('data', {}).get('taskList', []) or []
            if not task_list:
                self.log("签到区-月签有礼: 暂无月签任务")
                return
            claim_tasks = [
                t for t in task_list
                if str(t.get('taskStatus')) == "1" and t.get('taskId') and t.get('id')
            ]
            claimed_count = sum(1 for t in task_list if str(t.get('taskStatus')) == "2")
            if is_query_only:
                self.log(f"签到区-月签有礼: 可领取 {len(claim_tasks)} 个，已领取 {claimed_count} 个")
                return
            if not claim_tasks:
                self.log(f"签到区-月签有礼: 暂无可领取奖励，已领取 {claimed_count}/{len(task_list)}")
                return
            for task in claim_tasks:
                self.sign_get_month_sign_reward(task)
                time.sleep(1)
        except Exception as e:
            self.log(f"sign_month_sign_gift 异常: {str(e)}")

    def sign_get_month_sign_reward(self, task):
        task_name = task.get('taskName') or "月签奖励"
        try:
            url = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/getTaskReward"
            params = {
                "taskId": task.get('taskId'),
                "taskType": "30",
                "id": task.get('id')
            }
            headers = {"Referer": "https://img.client.10010.com/"}
            res = self.request("get", url, params=params, headers=headers, timeout=10)
            if not res: return
            result = res.json()
            code = result.get('code')
            data = result.get('data', {}) or {}
            if code == "0000" and data.get('code') == "0000":
                prize_name = data.get('prizeName', '')
                prize_red = data.get('prizeNameRed', '')
                reward = f"[{prize_name}] {prize_red}".strip() if prize_name or prize_red else data.get('statusDesc', '领取成功')
                self.log(f"签到区-月签有礼: [{task_name}] {reward}", notify=True)
                return
            msg = data.get('desc') or result.get('desc') or result.get('msg') or "未知错误"
            self.log(f"签到区-月签有礼: [{task_name}] 领取失败[{data.get('code') or code}]: {msg}")
        except Exception as e:
            self.log(f"sign_get_month_sign_reward 异常: {str(e)}")

    @staticmethod
    def _match_grab_amount(p_name, amounts=None):
        """精确匹配话费券面额, 返回命中的面额(int)或 None。

        原实现用 `str(GRAB_AMOUNT) in p_name` 子串匹配, 导致 GRAB_AMOUNT=5 时
        会误命中 "15元话费券" / "50元话费券" / "5G专区" 等奖品。
        这里改为按数字边界匹配: 只有 "5元" / "5话费" / "5元话费券" 这类
        独立面额才算命中。

        amounts 传入候选面额列表(如 [18,10,5])时返回优先级最高的命中项,
        用于抢兑降级链; 传入 None 时使用全局 GRAB_AMOUNTS。
        """
        if amounts is None:
            amounts = GRAB_AMOUNTS
        try:
            cand_list = [int(a) for a in amounts]
        except (TypeError, ValueError):
            return None
        text = str(p_name or "")
        for amount in cand_list:
            # 数字边界: 排除 5.5元 这类小数, 也排除 15元/50元 这类更大面额
            pattern = r'(?<![\d.])' + str(amount) + r'(?![\d.])'
            if not re.search(pattern, text):
                continue
            # "5折" / "5折券" 是折扣不是面额
            is_discount_only = True
            for m in re.finditer(pattern, text):
                tail = text[m.end():m.end() + 1]
                if tail in ('折', '％', '%'):
                    continue
                is_discount_only = False
                break
            if not is_discount_only:
                return amount
        return None

    def sign_grabCoupon(self):
        """抢兑话费券, 支持按 UNICOM_GRAB_AMOUNT 的面额顺序自动降级。

        UNICOM_GRAB_AMOUNT="18,10,5,3,1" 时:
          优先抢 18 元 -> 失败则降级 10 元 -> 5 元 -> 3 元 -> 1 元。
        任一面额抢到即停止; 全部失败则结束。
        """
        sc = globalConfig.get("sign_config", {})
        if not sc.get("run_grab_coupon", False):
             return
        amounts = list(GRAB_AMOUNTS)
        self.log(f"⚔️ [抢兑阶段] 正在检查目标: {' → '.join(f'{a}元' for a in amounts)} 话费券...")
        # 到账核对基线: 抢兑前先记下"我的卡券"与账户明细的记录指纹,
        # 之后每次抢兑报错都用它对比, 判断券是否其实已经发下来。
        # 注意基线必须在提交兑换请求之前取, 否则会漏判(重试导致重复提交时尤其明显)。
        self._grab_baseline_count = []      # 账户明细指纹
        self._grab_baseline_coupons = set() # 我的卡券指纹
        try:
            _bag = self._fetch_coupon_bag()
            if _bag is not None:
                self._grab_baseline_coupons = set(self._coupon_fingerprint(r) for r in _bag)
                self.log(f"📋 [到账核对] 抢兑前卡券基线: {len(self._grab_baseline_coupons)} 张券")
        except Exception as e:
            self.log(f"📋 [到账核对] 获取卡券基线失败(不影响抢兑): {e}")
        try:
            _details = self._fetch_phone_details()
            if _details is not None:
                self._grab_baseline_count = self._detail_summary(_details)
                self.log(f"📋 [到账核对] 抢兑前账户明细基线: {len(self._grab_baseline_count)} 条")
        except Exception as e:
            self.log(f"📋 [到账核对] 获取账户明细基线失败(不影响抢兑): {e}")
        # candidates: 面额 -> 该面额的候选奖品列表
        candidates = {}
        try:
            url = "https://act.10010.com/SigninApp/new_convert/prizeList"
            headers = {"Origin": "https://img.client.10010.com"}
            res = self.request("post", url, headers=headers)
            if res:
                list_res = res.json()
                if list_res.get('status') == "0000":
                    details = list_res.get('data', {}).get('datails', {})
                    tab_items = details.get('tabItems', [])
                    self.log(f"📋 [调试] 共获取到 {len(tab_items)} 个场次数据")
                    for tab in tab_items:
                        products = tab.get('timeLimitQuanListData', [])
                        round_time_str = tab.get('time', '')
                        tab_state = tab.get('state', '')
                        round_date = None
                        try:
                            if round_time_str and ":" in round_time_str:
                                now = datetime.now()
                                date_str = now.strftime('%Y/%m/%d')
                                full_time_str = f"{date_str} {round_time_str}"
                                if len(round_time_str) <= 8:
                                    round_date = datetime.strptime(full_time_str, "%Y/%m/%d %H:%M")
                                else:
                                    round_date = datetime.strptime(round_time_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            pass
                        for item in products:
                            p_name = item.get('product_name', '')
                            matched_amount = self._match_grab_amount(p_name, amounts)
                            if matched_amount is not None and ("元" in p_name or "话费" in p_name):
                                 # 过滤: 库存为 0 的奖品不必再试, 直接跳过
                                 stock_surplus = item.get('stockSurplus')
                                 try:
                                     if int(stock_surplus) <= 0:
                                         self.log(f"      ⏭️ 跳过 [{p_name}] ({round_time_str}): 库存已抢空")
                                         continue
                                 except (TypeError, ValueError):
                                     pass
                                 # user_able_time = 服务端报告的该奖品剩余可兑次数。
                                 # 注意: 它不能用来预判 10013 —— 实测服务端在报告
                                 # user_able_time=3/1/3 的情况下仍对全部面额返回 10013,
                                 # 说明 10013 命中的是另一条统一限制。这里只用它做提示。
                                 able_time = item.get('user_able_time')
                                 try:
                                     if able_time is not None and int(able_time) <= 0:
                                         self.log(f"      ⏭️ 跳过 [{p_name}] ({round_time_str}): "
                                                  f"服务端报告剩余可兑次数为 0")
                                         continue
                                 except (TypeError, ValueError):
                                     pass
                                 self.log(f"      ✅ 发现目标: {p_name} (ID: {item.get('product_id')}, "
                                          f"余量 {stock_surplus}/{item.get('stockSum')}, 场次状态: {tab_state}"
                                          + (f", 剩余可兑 {able_time} 次" if able_time is not None else "") + ")")
                                 candidates.setdefault(matched_amount, []).append({
                                     "id": item.get('product_id'),
                                     "name": p_name,
                                     "amount": matched_amount,
                                     "typeCode": item.get('type_code') or '0',
                                     "timeStr": round_time_str,
                                     "startTime": round_date,
                                     "tabState": tab_state,
                                     "itemData": item
                                 })
        except Exception as e:
            self.log(f"❌ 获取奖品列表失败: {str(e)}")
        # 按配置的降级顺序, 为每个面额选出最佳场次
        plan = []
        for amount in amounts:
            cand_list = candidates.get(amount)
            if not cand_list:
                self.log(f"⏭️ {amount}元 话费券: 本场未匹配到可兑奖品, 尝试下一档")
                continue
            best_candidate = self._pick_best_session(cand_list)
            if not best_candidate:
                self.log(f"⏭️ {amount}元 话费券: 未找到有效场次, 尝试下一档")
                continue
            plan.append((amount, best_candidate))
        if not plan:
            self.log(f"⚠️ 目标面额({'/'.join(str(a) for a in amounts)})均未匹配到可兑奖品。")
            return
        # 分成"已开始(可立即抢)"与"尚未开始(需等待)"两组。
        # 等待只做一次: 等到最早开抢的场次, 然后各面额依次尝试,
        # 避免每降一档就重新等待导致错过开抢瞬间。
        now = datetime.now()
        ready, pending = [], []
        for amount, cand in plan:
            st = cand.get('startTime')
            if not st or (st - now).total_seconds() <= 0:
                ready.append((amount, cand))
            else:
                pending.append((amount, cand))
        pending.sort(key=lambda x: x[1]['startTime'])
        for amount, cand in ready:
            self.log(f"🎯 锁定场次: [{cand['timeStr']}] {cand['name']}"
                     + (f" (场次状态: {cand.get('tabState')})" if cand.get('tabState') else ""))
            if self.sign_grab_execute(cand):
                return
            self.log(f"⬇️ {amount}元 话费券未抢到, 自动降级尝试下一档面额...")
        if not pending:
            self.log(f"❌ 所有目标面额({'/'.join(str(a) for a in amounts)})均未抢到", notify=True)
            return
        # 等待最早开抢的场次
        first = pending[0][1]
        wait_seconds = (first['startTime'] - datetime.now()).total_seconds()
        if wait_seconds > 300:
            self.log(f"⏳ 距离开抢还有 {wait_seconds:.1f} 秒，大于5分钟，暂不等待。建议在临近时间(如提前2分钟)再运行脚本。")
            return
        self.log(f"⏳ 正在等待开抢... (剩余 {wait_seconds:.1f} 秒)")
        while (first['startTime'] - datetime.now()).total_seconds() > 0.5:
            time.sleep(0.5)
        self.log("⚡ 已到开抢时间, 开始按面额顺序依次尝试")
        for amount, cand in pending:
            # 该面额若属于更晚的场次, 补等它自己的开抢时刻
            st = cand.get('startTime')
            if st:
                remain = (st - datetime.now()).total_seconds()
                if remain > 0.5:
                    if remain > 300:
                        self.log(f"⏭️ {amount}元 话费券所属场次 [{cand['timeStr']}] 距开抢过远, 跳过")
                        continue
                    self.log(f"⏳ {amount}元 所属场次 [{cand['timeStr']}] 尚未开始, 等待 {remain:.1f} 秒")
                    while (cand['startTime'] - datetime.now()).total_seconds() > 0.5:
                        time.sleep(0.5)
            self.log(f"🎯 锁定场次: [{cand['timeStr']}] {cand['name']}"
                     + (f" (场次状态: {cand.get('tabState')})" if cand.get('tabState') else ""))
            if self.sign_grab_execute(cand):
                return
            self.log(f"⬇️ {amount}元 话费券未抢到, 自动降级尝试下一档面额...")
        self.log(f"❌ 所有目标面额({'/'.join(str(a) for a in amounts)})均未抢到", notify=True)

    def _pick_best_session(self, cand_list):
        """从同一面额的候选中挑出最合适的场次。

        评分规则: 正在进行中的场次最优先(能立刻抢) > 即将开始的场次 > 已结束的场次。
        旧逻辑给"已开始"场次加 10000 基准分, 导致正在抢的场次反而被未来场次盖过。
        """
        now = datetime.now()
        best_candidate = None
        min_diff = float('inf')
        for cand in cand_list:
            start_time = cand['startTime']
            if not start_time: continue
            diff = (start_time - now).total_seconds()
            if diff <= 0:
                # 已开始: 开始得越晚越优先, 但结束的场次排最后
                elapsed = abs(diff)
                score = elapsed + 10000 if elapsed <= 3600 else elapsed + 100000
            else:
                # 未开始: 越近越优先
                score = diff
            if score < min_diff:
                min_diff = score
                best_candidate = cand
        return best_candidate or (cand_list[0] if cand_list else None)

    def sign_grab_execute(self, candidate):
        last_0053 = False
        for i in range(1, 6):
            # 多账号并发时, 各账号在开抢前 1 秒内加随机抖动再提交,
            # 避免同一 IP 的请求全部落在同一毫秒(风控特征更明显)。
            # 抖动范围 0~0.5s, 最晚 9:59:59.8 前发出, 不影响"抢在整点前提交"。
            if i == 1:
                time.sleep(random.uniform(0, 0.5))
            self.log(f"🔥 [第{i}次冲击] 发起兑换请求...")
            try:
                data = {
                    "product_id": candidate['id'],
                    "typeCode": candidate['typeCode']
                }
                url = "https://act.10010.com/SigninApp/convert/prizeConvert"
                headers = {
                    "Origin": "https://img.client.10010.com",
                    "Referer": "https://img.client.10010.com/",
                    "X-Requested-With": "com.sinovatech.unicom.ui"
                }
                res = self.request("post", url, data=data, headers=headers)
                if not res: continue
                result = res.json()
                uuid_val = result.get('data', {}).get('uuid')
                status = result.get('status')
                if status == "0000" and uuid_val:
                    self.log(f"📝 [提交成功] 获取到工单号: {uuid_val}，正在查询最终结果...")
                    check_url = "https://act.10010.com/SigninApp/convert/prizeConvertResult"
                    check_data = { "uuid": uuid_val }
                    check_res = self.request("post", check_url, data=check_data, headers=headers)
                    if not check_res: continue
                    final_res = check_res.json()
                    final_status = final_res.get('status')
                    if final_status == "0000":
                        self.log(f"🎉🎉🎉 [抢兑成功] 恭喜！已成功抢到 {candidate.get('name', '目标奖品')}！ 🎉🎉🎉", notify=True)
                        return True
                    elif str(final_status) == '0053':
                        # 0053 出现在"结果查询"阶段: 提交(prizeConvert)已拿到工单号,
                        # 但查询最终结果失败。此时无法断定兑换失败 —— 实测存在
                        # 券已发放但结果查询报错的情况, 必须以账户明细为准。
                        #
                        # 0053 的语义是"结果查询失败"而非"库存没了", 10:00:00 后
                        # 2-3 秒内仍是黄金窗口: 先做一次到账核对(券可能已发放),
                        # 确认没到账则不立即放弃, 继续循环补冲击(重试间隔很短,
                        # 5 次冲击可在 3 秒内打完)。
                        msg_0053 = final_res.get('msg', '') or final_res.get('message', '未知原因')
                        self.log(f"💔 [抢兑失败] 状态: {final_status} | 提示: {msg_0053}")
                        if self.sign_verify_grab_result(self._grab_baseline_coupons,
                                                        self._grab_baseline_count,
                                                        candidate.get('name', '目标奖品'),
                                                        f"结果查询返回 {final_status}",
                                                        expect_amount=candidate.get('amount')):
                            self.log(f"🎉🎉🎉 [抢兑成功] 到账核对确认券已到账：{candidate.get('name', '目标奖品')}！ 🎉🎉🎉", notify=True)
                            return True
                        last_0053 = True
                        continue
                    else:
                        err_code = str(final_res.get('data', {}).get('errorCode', '') or '')
                        msg = final_res.get('msg', '') or final_res.get('message', '未知原因')
                        detail_msg = final_res.get('data', {}).get('rightBtn', {}).get('name', '')
                        log_msg = f"💔 [抢兑失败] 状态: {final_status}"
                        if err_code: log_msg += f" | 错误码: {err_code}"
                        if detail_msg: log_msg += f" | 详情: {detail_msg}"
                        log_msg += f" | 提示: {msg}"
                        # 10013 = 服务端判定"兑换规则达到上限", 属终态, 重试无意义。
                        #
                        # 实测(2026-11-19 18:00 场次, 账号 130****0725):
                        #   对 18元/10元/5元 全部返回 10013, 而同一时刻 prizeList 报告的
                        #   user_able_time 分别是 3/1/3 (都还有额度)。
                        #   => 10013 命中的不是"该面额的兑换次数用尽", 而是另一条对所有
                        #      面额一视同仁的限制规则(账号级/活动级统一限制)。
                        #   => 因此 user_able_time 与 conv_rule_unit.limitCount 都不能
                        #      用来解释 10013, 服务端未返回具体命中的规则, 不可臆测。
                        # 具体命中的是哪一条限制(账号总次数 / 每日次数 / 楼层名额)
                        # 无法从服务端响应反推, 故此处只陈述服务端给出的原始文案。
                        if err_code == '10013' or '兑换规则达到上限' in str(detail_msg):
                            able_time = (candidate.get('itemData') or {}).get('user_able_time')
                            extra = f" (服务端报告该奖品剩余可兑 {able_time} 次)" if able_time is not None else ""
                            self.log(f"💔 [抢兑失败] 服务端判定兑换规则达到上限{extra}，该面额不可兑。"
                                     f"错误码: {err_code} | 详情: {detail_msg}", notify=True)
                            # 10013 同样不能直接判定"没兑成": 实测同场次所有面额一起报 10013,
                            # 而 prizeList 报告的 user_able_time 仍大于 0, 说明命中的可能是
                            # 另一条统一规则。所以还要核对账户明细再下结论。
                            if self.sign_verify_grab_result(self._grab_baseline_coupons,
                                                        self._grab_baseline_count,
                                                        candidate.get('name', '目标奖品'),
                                                        "兑换规则达到上限(10013)",
                                                        expect_amount=candidate.get('amount')):
                                self.log(f"🎉🎉🎉 [抢兑成功] 到账核对确认券已到账：{candidate.get('name', '目标奖品')}！ 🎉🎉🎉", notify=True)
                                return True
                            return False
                        self.log(log_msg, notify=True)
                else:
                    sub_msg = result.get('msg') or result.get('message') or json.dumps(result)
                    self.log(f"📝 提交结果: {sub_msg}")
                    # 0032 = 服务端风控("操作过于频繁/检测到号码异常")。
                    # 该错误与具体面额无关, 但换面额仍可能命中不同奖品而成功,
                    # 故不在此处终止, 交由上层降级链处理。
                    if str(status) == '0032':
                        self.log(f"⚠️ 触发服务端风控 (status=0032): {sub_msg}")
                        if self.sign_verify_grab_result(self._grab_baseline_coupons,
                                                        self._grab_baseline_count,
                                                        candidate.get('name', '目标奖品'),
                                                        "触发风控(0032)",
                                                        expect_amount=candidate.get('amount')):
                            self.log(f"🎉🎉🎉 [抢兑成功] 到账核对确认券已到账：{candidate.get('name', '目标奖品')}！ 🎉🎉🎉", notify=True)
                            return True
                        return False
                    # 提交阶段未拿到工单号, 可能是限流/库存瞬时问题, 继续冲击有意义;
                    # 只有明确命中"兑换规则达到上限"才终止(见下方 result 阶段判断)
                time.sleep(0.2)
            except Exception as e:
                self.log(f"❌ 抢兑异常: {str(e)}")
        if last_0053:
            # 5 次冲击全部 0053: 最后再做一次到账核对兜底
            # (重试期间券可能已陆续发放, 尤其服务端结算延迟的场景)
            self.log("⏳ [0053兜底] 全部冲击报0053, 最后核对一次卡券/明细...")
            if self.sign_verify_grab_result(self._grab_baseline_coupons,
                                            self._grab_baseline_count,
                                            candidate.get('name', '目标奖品'),
                                            "全部冲击返回 0053",
                                            expect_amount=candidate.get('amount')):
                self.log(f"🎉🎉🎉 [抢兑成功] 到账核对确认券已到账：{candidate.get('name', '目标奖品')}！ 🎉🎉🎉", notify=True)
                return True
        return False

    def get_wocare_body(self, apiCode, requestData={}):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S') + str(int(datetime.now().microsecond / 1000)).zfill(3)
        encodedContent = base64.b64encode(json.dumps(requestData, separators=(',', ':')).encode('utf-8')).decode('utf-8')
        body = {
            "version": WOCARE_CONSTANTS["minRetries"],
            "apiCode": apiCode,
            "channelId": WOCARE_CONSTANTS["anotherApiKey"],
            "transactionId": timestamp + self.random_string(6, "0123456789"),
            "timeStamp": timestamp,
            "messageContent": encodedContent
        }
        params_array = []
        for key in sorted(body.keys()):
            params_array.append(f"{key}={body[key]}")
        params_array.append(f"sign={WOCARE_CONSTANTS['anotherEncryptionKey']}")
        sign_str = "&".join(params_array)
        body["sign"] = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        return body

    def wocare_api(self, apiCode, requestData={}, max_attempts=1):
        """调用 wocare api。

        服务端存在瞬时失败: 同一 sid 重复调用会返回 resultCode=9999
        ("程序员正在努力ing"), 换新 sid 即可成功。
        默认不在这里重试(避免同一 sid 反复撞墙), 由调用方换 sid 后重来;
        需要同 sid 重试时显式传 max_attempts>1。
        """
        url = f"https://wocare.unisk.cn/api/v1/{apiCode}"
        result = None
        for attempt in range(1, max_attempts + 1):
            try:
                body = self.get_wocare_body(apiCode, requestData)
                res = self.request("post", url, data=body)
                if not res:
                    result = None
                else:
                    result = res.json()
                # 9999 是服务端瞬时错误, 重试; 其他错误码直接返回给调用方处理
                if result and str(result.get("resultCode", "")) == "9999" and attempt < max_attempts:
                    self.log(f"联通祝福: {apiCode} 服务端繁忙(9999), {attempt}秒后重试 ({attempt}/{max_attempts - 1})")
                    time.sleep(attempt)
                    continue
                break
            except Exception as e:
                self.log(f"wocare_api 异常: {str(e)}")
                if attempt < max_attempts:
                    time.sleep(attempt)
                    continue
                return None
        if result is None:
            return None
        try:
            if result.get("messageContent"):
                try:
                    content = result["messageContent"]
                    content = content.replace('\n', '').replace('\r', '').replace(' ', '')
                    content = content.replace('-', '+').replace('_', '/')
                    missing_padding = len(content) % 4
                    if missing_padding:
                        content += '=' * (4 - missing_padding)
                    try:
                        decoded_bytes = base64.b64decode(content)
                        decoded_str = decoded_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        decoded_str = decoded_bytes.decode('utf-8', errors='replace')
                    except Exception as e:
                        self.log(f"wocare响应base64解码失败, 按空对象处理: {e}")
                        decoded_str = "{}"
                    try:
                        decoded = json.loads(decoded_str, strict=False)
                    except:
                        decoded_str = re.sub(r'[\x00-\x1f\x7f]', '', decoded_str)
                        try:
                            decoded = json.loads(decoded_str, strict=False)
                        except:
                            decoded = {}
                    if isinstance(decoded, dict):
                        if "data" in decoded:
                            result["data"] = decoded["data"]
                        else:
                            result["data"] = decoded
                        if "resultMsg" in decoded:
                            result["resultMsg"] = decoded["resultMsg"]
                        if "resultCode" in decoded:
                            result["resultCode"] = decoded["resultCode"]
                except Exception as e:
                    self.log(f"联通祝福: 解析返回失败: {str(e)}")
            return result
        except Exception as e:
            self.log(f"wocare_api 异常: {str(e)}")
            return None

    def wocare_getToken(self, ticket=None, max_attempts=4):
        """取会话标识并登录联通祝福(mbh)。

        实测(wocare.unisk.cn):
        - getToken 的 302 Location 里带 uuid 与 sid 两个标识;
          loginmbh 只认 uuid, 传 sid 必然 9999("程序员正在努力ing")。
        - 同一 ticket 重复换取时 Location 会降级(只剩 uuid 没有 sid),
          但 uuid 仍然可用, 所以换 ticket 重试依然作为兜底。
        - 2026-11 期间 wocare 官网首页显示"系统升级中", 服务端统一返回
          9999, 属服务端维护, 非请求参数问题。
        """
        for attempt in range(1, max_attempts + 1):
            if attempt > 1 or not ticket:
                target_url = (f"https://wocare.unisk.cn/mbh/getToken?"
                              f"{urlencode({'channelType': WOCARE_CONSTANTS['serviceLife'], 'homePage': 'home', 'duanlianjieabc': 'qAz2m'})}")
                res = self.openPlatLineNew(target_url)
                if not res or 'ticket' not in res:
                    self.log(f"联通祝福: 获取Ticket失败, {attempt}秒后重试 ({attempt}/{max_attempts})")
                    time.sleep(attempt)
                    continue
                ticket = res['ticket']
            sid = self.wocare_fetch_sid(ticket)
            if not sid:
                if attempt < max_attempts:
                    self.log(f"联通祝福: 获取sid失败, {attempt}秒后重试 ({attempt}/{max_attempts})")
                    time.sleep(attempt)
                    continue
                return False
            self.wocare_sid = sid
            if self.wocare_loginmbh():
                return True
            if attempt < max_attempts:
                self.log(f"联通祝福: 登录失败(服务端繁忙), 换新ticket重试 ({attempt}/{max_attempts})")
                time.sleep(min(attempt * 2, 6))
        return False

    def wocare_fetch_sid(self, ticket):
        """向 wocare 换取 sid/uuid (通过 getToken 的 302 Location)。

        实测: loginmbh 只认 Location 里的 uuid(带横线的 UUID),
        传 sid(32位hex) 必然返回 9999("程序员正在努力ing")。
        同一 ticket 重复换取会降级(Location 里只剩 uuid 而无 sid), 但 uuid 始终可用。
        """
        try:
            url = "https://wocare.unisk.cn/mbh/getToken"
            params = {
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "type": "02",
                "ticket": ticket,
                "version": COMMON_CONSTANTS["APP_VERSION"],
                "timestamp": datetime.now().strftime('%Y%m%d%H%M%S') + str(int(datetime.now().microsecond / 1000)).zfill(3),
                "desmobile": self.account_mobile,
                "num": "0",
                "postage": self.random_string(32),
                "homePage": "home",
                "duanlianjieabc": "qAz2m",
                "userNumber": self.account_mobile
            }
            res = self.session.get(url, params=params, allow_redirects=False, timeout=15)
            if res.status_code == 302:
                location = res.headers.get("Location", "")
                if location:
                    parsed = urlparse(location)
                    qs = parse_qs(parsed.query)
                    # uuid 优先: 服务端 loginmbh 只认 uuid
                    uuid = qs.get("uuid", [None])[0]
                    sid = qs.get("sid", [None])[0]
                    if uuid:
                        return uuid
                    if sid:
                        self.log("联通祝福: Location 无uuid, 退回使用sid")
                        return sid
                    self.log(f"联通祝福: 没有获取到sid/uuid, Location: {location}")
                else:
                    self.log("联通祝福: 没有获取到location")
            else:
                self.log(f"联通祝福: 获取sid失败[{res.status_code}]")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            self.log("联通祝福: 连接wocare服务失败，可能服务已关闭或网络不可达")
        except Exception as e:
            self.log(f"wocare_fetch_sid 异常: {str(e)}")
        return None

    def wocare_loginmbh(self):
        try:
            apiCode = "loginmbh"
            requestData = {
                "sid": self.wocare_sid,
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            if not result: return False
            responseResult = result
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                self.wocare_token = responseResult.get("data", {}).get("token")
                self.log("联通祝福: 登录成功")
                return True
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                if "程序员正在努力" in str(msg):
                    self.log("联通祝福: 登录失败[9999] - wocare 服务端异常"
                             "(官方页面提示'系统升级中'), 属服务端维护, 非脚本问题, 可稍后重试")
                else:
                    self.log(f"联通祝福: 登录失败[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_loginmbh 异常: {str(e)}")
        return False

    def wocare_getDrawTask(self, activity):
        try:
            apiCode = "getDrawTask"
            requestData = {
                "token": self.wocare_token,
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "type": activity["id"],
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            responseResult = result if result else {}
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                taskList = responseResult.get("data", {}).get("taskList", []) or []
                if not taskList:
                    pass
                else:
                    self.log(f"联通祝福: [{activity['name']}] 查询到 {len(taskList)} 个任务")
                    for task in taskList:
                        ts = task.get("taskStatus")
                        if str(ts) == "0" or not ts:
                            self.wocare_completeTask(activity, task)
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                self.log(f"联通祝福: [{activity['name']}]查询任务失败[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_getDrawTask 异常: {str(e)}")

    def wocare_completeTask(self, activity, task, taskStep="1"):
        try:
            taskTitle = task.get("title", "")
            action = "领取任务" if taskStep == "1" else "完成任务"
            apiCode = "completeTask"
            requestData = {
                "token": self.wocare_token,
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "task": task.get("id"),
                "taskStep": taskStep,
                "type": activity["id"],
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            responseResult = result if result else {}
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                self.log(f"联通祝福: {action}[{taskTitle}]成功")
                if taskStep == "1":
                    time.sleep(1)
                    self.wocare_completeTask(activity, task, "4")
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                self.log(f"联通祝福: [{activity['name']}]{action}[{taskTitle}]失败[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_completeTask 异常: {str(e)}")

    def wocare_getSpecificityBanner(self):
        try:
            apiCode = "getSpecificityBanner"
            requestData = {
                "token": self.wocare_token,
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            responseResult = result if result else {}
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                bannerList = responseResult.get("data", []) or []
                if not bannerList:
                    self.log(f"联通祝福: 获取动态 Banner 列表为空，接口明细: {responseResult}")
                for banner in bannerList:
                    if str(banner.get("activityStatus")) == "0" and str(banner.get("isDeleted")) == "0":
                        self.wocare_getDrawTask(banner)
                        self.wocare_loadInit(banner)
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc", "")
                self.log(f"联通祝福: 进入活动失败[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_getSpecificityBanner 异常: {str(e)}")

    def wocare_loadInit(self, activity):
        try:
            apiCode = "loadInit"
            requestData = {
                "token": self.wocare_token,
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "type": activity["id"],
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            responseResult = result if result else {}
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                responseData = responseResult.get("data", {}) or {}
                activeModuleGroupId = responseData.get("zActiveModuleGroupId")
                drawCount = 0
                aid = activity["id"]
                if aid == 2:
                    isPartake = responseData.get("data", {}).get("isPartake") or 0
                    if not isPartake:
                        drawCount = 1
                elif aid == 3:
                    drawCount = int(responseData.get("raffleCountValue", 0) or 0)
                elif aid == 4:
                    drawCount = int(responseData.get("mhRaffleCountValue", 0) or 0)
                if drawCount > 0:
                     self.log(f"联通祝福: [{activity['name']}] 可抽奖次数 {drawCount}")
                else:
                     self.log(f"联通祝福: [{activity['name']}] 今日已无抽奖机会")
                while drawCount > 0:
                    time.sleep(2)
                    self.wocare_luckDraw(activity, activeModuleGroupId)
                    drawCount -= 1
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                self.log(f"联通祝福: [{activity['name']}]查询活动失败[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_loadInit 异常: {str(e)}")

    def wocare_luckDraw(self, activity, activeModuleGroupId):
        try:
            apiCode = "luckDraw"
            requestData = {
                "token": self.wocare_token,
                "channelType": WOCARE_CONSTANTS["serviceLife"],
                "zActiveModuleGroupId": activeModuleGroupId,
                "type": activity["id"],
                "apiCode": apiCode
            }
            result = self.wocare_api(apiCode, requestData)
            responseResult = result if result else {}
            resultCode = responseResult.get("resultCode", "-1")
            if resultCode == "0000":
                resultData = responseResult.get("data", {}) or {}
                drawResultCode = resultData.get("resultCode", "-1")
                if drawResultCode == "0000":
                    prize = resultData.get("data", {}).get("prize", {})
                    prizeName = prize.get("prizeName", "")
                    prizeDesc = prize.get("prizeDesc", "")
                    self.log(f"联通祝福: [{activity['name']}]抽奖: {prizeName}[{prizeDesc}]", notify=True)
                else:
                    msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                    if msg.lower() == "success":
                        self.log(f"联通祝福: [{activity['name']}] 未中奖 (继续努力)")
                    else:
                        self.log(f"联通祝福: [{activity['name']}] 抽奖并未中奖: {msg}")
            else:
                msg = responseResult.get("resultMsg") or responseResult.get("resultDesc") or ""
                if msg.lower() == "success":
                    self.log(f"联通祝福: [{activity['name']}] 未中奖 (继续努力)")
                else:
                    self.log(f"联通祝福: [{activity['name']}] 抽奖异常[{resultCode}]: {msg}")
        except Exception as e:
            self.log(f"wocare_luckDraw 异常: {str(e)}")

    def parse_jwt_payload(self, token):
        try:
            payload = token.split('.')[1]
            padding = len(payload) % 4
            if padding:
                payload += '=' * (4 - padding)
            payload = payload.replace('-', '+').replace('_', '/')
            decoded_bytes = base64.b64decode(payload)
            return json.loads(decoded_bytes.decode('utf-8'))
        except Exception as e:
            self.log(f"JWT Decode Error: {e}")
            return {}

    def generate_market_signature_headers(self, user_token, query_string="", json_body=""):
        try:
            token = user_token.replace('Bearer ', '')
            payload = self.parse_jwt_payload(token)
            login_id = payload.get('loginId', '')
            app_secret = hashlib.md5(f"al:ak:{login_id}".encode('utf-8')).hexdigest()
            nonce = str(uuid.uuid4())
            message = f"{login_id}{app_secret}{nonce}{query_string or ''}{json_body or ''}"
            signature = base64.b64encode(
                hmac.new(
                    app_secret.encode('utf-8'),
                    message.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
            ).decode('utf-8')
            return {
                'X-User-Id': login_id,
                'X-Nonce': nonce,
                'X-Timestamp': str(int(time.time() * 1000)),
                'X-Signature': signature,
                'Content-Type': 'application/json'
            }
        except Exception as e:
            self.log(f"Signature Generation Error: {e}")
            return {}

    def get_market_headers(self, user_token):
        return {
            'User-Agent': COMMON_CONSTANTS['MARKET_UA'],
            'Authorization': f"Bearer {user_token}",
            'Content-Type': 'application/json',
            'X-Requested-With': 'com.sinovatech.unicom.ui'
        }

    def market_get_ticket(self):
        self.log("权益超市: 正在获取 ticket...")
        target_url = "https://contact.bol.wo.cn/market"
        res = self.openPlatLineNew(target_url)
        if res and 'ticket' in res:
            self.log("权益超市: 获取ticket成功")
            return res['ticket']
        self.log("权益超市: 获取ticket失败")
        return None

    def market_get_user_token(self, ticket):
        url = f"https://backward.bol.wo.cn/prod-api/auth/marketUnicomLogin?ticket={ticket}"
        headers = {
            'User-Agent': COMMON_CONSTANTS['MARKET_UA'],
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
        }
        for attempt in range(1, 4):
            try:
                self.log(f"权益超市: 正在获取 userToken...{f' (第{attempt}次重试)' if attempt > 1 else ''}")
                res = self.session.post(url, headers=headers, timeout=30).json()
                if res.get('code') == 200:
                    user_token = res.get('data', {}).get('token')
                    if user_token:
                        self.log("权益超市: 获取userToken成功")
                        return user_token
                self.log(f"权益超市: 获取userToken失败: {res.get('msg')}")
            except Exception as e:
                self.log(f"权益超市: 获取userToken异常: {e}")
            if attempt < 3:
                self.log(f"权益超市: 等待5秒后重试...")
                time.sleep(5)
        return None

    def market_get_raffle(self, user_token):
        self.log("权益超市: 正在查询奖品池...")
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"id=12&timeVerRan={timestamp}"
            json_body = "{}"
            sig_headers = self.generate_market_signature_headers(user_token, query_string, json_body)
            url = f"https://backward.bol.wo.cn/prod-api/promotion/home/raffleActivity/prizeList?{query_string}"
            headers = self.get_market_headers(user_token)
            headers.update(sig_headers)
            headers['Referer'] = 'https://contact.bol.wo.cn/market'
            headers['Origin'] = 'https://contact.bol.wo.cn'
            res = self.session.post(url, headers=headers, data=json_body).json()
            if res.get('code') == 200 and isinstance(res.get('data'), list):
                keywords = ['月卡', '月会员', '月度', 'VIP月', '一个月', '周卡']
                exclude = ['5G宽视界', '沃视频']
                live_prizes = []
                for p in res['data']:
                    vip_prob = float(p.get('probabilityVip') or p.get('newVipProbability') or 0)
                    norm_prob = float(p.get('probability') or 0)
                    name = p.get('name', '')
                    daily_limit = int(p.get('dailyPrizeLimit') or 0)
                    match = any(k in name for k in keywords)
                    not_excluded = not any(e in name for e in exclude)
                    has_stock = daily_limit > 0
                    has_chance = norm_prob > 0 or vip_prob > 0
                    if match and not_excluded and has_stock and has_chance:
                        live_prizes.append(p)
                        total_limit = int(p.get('quantity') or 0)
                        self.log(f"权益超市: 【{name}】监测到放水 (日库存:{daily_limit}, 总库存:{total_limit}, 普通概率:{(norm_prob * 100):.4f}%, VIP概率:{(vip_prob * 100):.4f}%)")
                if live_prizes:
                    return True
            self.log("权益超市: 📢 未监测到高价值权益放水")
            return False
        except Exception as e:
            self.log(f"权益超市: 查询奖品池异常: {e}")
            return False

    def market_get_raffle_count(self, user_token):
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"id=12&channel=unicomTab&timeVerRan={timestamp}"
            json_body = "{}"
            sig_headers = self.generate_market_signature_headers(user_token, query_string, json_body)
            url = f"https://backward.bol.wo.cn/prod-api/promotion/home/raffleActivity/getUserRaffleCountExt?{query_string}"
            headers = self.get_market_headers(user_token)
            headers.update(sig_headers)
            headers['Referer'] = 'https://contact.bol.wo.cn/market'
            headers['Origin'] = 'https://contact.bol.wo.cn'
            res = self.session.post(url, headers=headers, data=json_body).json()
            count = 0
            if res.get('code') == 200:
                data = res.get('data')
                if isinstance(data, dict):
                    count = int(data.get('raffleCount') or 0)
                else:
                    count = int(data or 0)
            if count > 0:
                self.log(f"权益超市: ✅ 当前抽奖次数: {count}")
                for i in range(count):
                    self.log(f"权益超市: 🎯 第 {i+1} 次抽奖...")
                    if not self.market_user_raffle(user_token):
                        break
                    time.sleep(3 + random.random() * 2)
            else:
                self.log("权益超市: 当前无抽奖次数")
        except Exception as e:
            self.log(f"权益超市: 查询抽奖次数异常: {e}")

    def market_user_raffle(self, user_token):
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"id=12&channel=unicomTab&timeVerRan={timestamp}"
            json_body = "{}"
            sig_headers = self.generate_market_signature_headers(user_token, query_string, json_body)
            url = f"https://backward.bol.wo.cn/prod-api/promotion/home/raffleActivity/userRaffle?{query_string}"
            headers = self.get_market_headers(user_token)
            headers.update(sig_headers)
            headers['Referer'] = 'https://contact.bol.wo.cn/market'
            res = self.session.post(url, headers=headers, data=json_body).json()
            if res.get('code') == 200:
                data = res.get('data', {})
                prize_name = data.get('prizesName', '')
                message = data.get('message') or res.get('msg') or ""
                if prize_name and "谢谢参与" not in prize_name:
                    self.log(f"权益超市: 🎉 抽奖成功: {prize_name}", notify=True)
                    return True
                self.log(f"权益超市: 💨 未中奖: {message}", notify=True)
                return True
            self.log(f"权益超市: 抽奖失败: {res.get('msg')}")
            return False
        except Exception as e:
            self.log(f"权益超市: 抽奖异常: {e}")
            return False

    def market_get_all_tasks(self, ecs_token, user_token):
        url = "https://backward.bol.wo.cn/prod-api/promotion/activityTask/getAllActivityTasks?activityId=12"
        headers = {
            "Authorization": f"Bearer {user_token}",
            "User-Agent": COMMON_CONSTANTS["MARKET_UA"],
            "Origin": "https://contact.bol.wo.cn",
            "Referer": "https://contact.bol.wo.cn/",
            "Cookie": f"ecs_token={ecs_token}"
        }
        for attempt in range(1, 4):
            try:
                self.log(f"权益超市: 正在获取任务列表...{f' (第{attempt}次重试)' if attempt > 1 else ''}")
                res = self.session.get(url, headers=headers, timeout=15).json()
                if res.get('code') == 200:
                    tasks = res.get('data', {}).get('activityTaskUserDetailVOList', [])
                    self.log(f"权益超市: 成功获取到 {len(tasks)} 个任务")
                    return tasks
                self.log(f"权益超市: 查询任务列表失败: {res.get('msg')}")
            except Exception as e:
                self.log(f"权益超市: 获取任务列表异常: {e}")
            if attempt < 3:
                self.log("权益超市: 等待5秒后重试...")
                time.sleep(5)
        return []

    def market_do_share_list(self, share_list, user_token):
        self.log("权益超市: 开始执行任务...")
        for task in share_list:
            name = task.get('name', '')
            param = task.get('param1', '')
            trigger_time = task.get('triggerTime', 0)
            triggered_time = task.get('triggeredTime', 0)
            if any(k in name for k in ["购买", "秒杀"]):
                 self.log(f"权益超市: 🚫 {name} [跳过]")
                 continue
            if triggered_time >= trigger_time:
                 self.log(f"权益超市: ✅ {name} [已完成]")
                 continue
            url = ""
            if any(k in name for k in ["浏览", "查看"]):
                url = f"https://backward.bol.wo.cn/prod-api/promotion/activityTaskShare/checkView?checkKey={param}"
            elif "分享" in name:
                url = f"https://backward.bol.wo.cn/prod-api/promotion/activityTaskShare/checkShare?checkKey={param}"
            if url:
                try:
                    headers = {
                        "Authorization": f"Bearer {user_token}",
                        "User-Agent": COMMON_CONSTANTS["MARKET_UA"],
                        "Origin": "https://contact.bol.wo.cn",
                        "Referer": "https://contact.bol.wo.cn/"
                    }
                    res = self.session.post(url, json={}, headers=headers, timeout=15).json()
                    if res.get('code') == 200:
                        self.log(f"权益超市: ✅ {name} [执行成功]")
                    else:
                        self.log(f"权益超市: ❌ {name} [执行失败]: {res.get('msg')}")
                except Exception as e:
                    self.log(f"权益超市: ❌ {name} [执行异常]: {e}")
            time.sleep(2)

    def market_task(self, is_query_only=False):
        self.log("==== 权益超市 ====")
        self.log("权益超市-会员中心: 浏览积分任务已下线，已跳过")
        ticket = self.market_get_ticket()
        if not ticket:
            return
        user_token = self.market_get_user_token(ticket)
        if not user_token:
            return
        if is_query_only:
            self.query_market_raffle_records(user_token)
            self.query_phone_recharge_records(user_token)
            return
        mc = globalConfig.get("market_config", {})
        if mc.get("run_task", True):
            if hasattr(self, 'ecs_token'):
                share_list = self.market_get_all_tasks(self.ecs_token, user_token)
                if share_list:
                    self.market_do_share_list(share_list, user_token)
            else:
                 self.log("权益超市: 缺 ecs_token, 跳过通用任务列表")
        else:
            self.log("权益超市-做任务: ⏭️ 已被总开关关闭，跳过")
        if mc.get("run_draw", True):
            if self.market_get_raffle(user_token):
                self.market_get_raffle_count(user_token)
        else:
            self.log("权益超市-抽奖: ⏭️ 已被总开关关闭，跳过")
        if mc.get("run_claim", False):
            self.log("权益超市-领奖: 自动领奖已开启")
            self.query_phone_recharge_records(user_token)
        else:
            self.log("权益超市-领奖: ⏭️ 未开启自动领奖")
        self.query_market_raffle_records(user_token)
        self.query_phone_recharge_records(user_token)

    # ==================== 积分商城 (welfare-mall-front) ====================
    # 联通积分商城, 对应 App 内「积分查询/积分兑换」页 (img.client.10010.com/keyongjifen)。
    # 接口前缀 m.client.10010.com/welfare-mall-front, 直接复用 ecs_token 登录态。
    JFSC_BASE = "https://m.client.10010.com/welfare-mall-front"

    def jfsc_headers(self):
        return {
            "User-Agent": COMMON_CONSTANTS["UA"],
            "Referer": "https://img.client.10010.com/keyongjifen/index.html",
            "Origin": "https://m.client.10010.com",
            "X-Requested-With": "com.sinovatech.unicom.ui",
        }

    def jfsc_api(self, path, data=None, timeout=15, log_error=True):
        """调用积分商城接口, 返回 resdata(失败返回 None)"""
        try:
            res = self.request("post", self.JFSC_BASE + path,
                               headers=self.jfsc_headers(),
                               data=data if data is not None else {}, timeout=timeout)
            if not res:
                return None
            result = res.json()
            code = str(result.get('code', ''))
            # 0000 / 0 / 200 均视为成功
            if code not in ('0000', '0', '200'):
                if log_error:
                    self.log(f"积分商城: [{path.rsplit('/', 1)[-1]}] 返回 {code} - {result.get('msg', '')}")
                return None
            return result.get('resdata')
        except Exception as e:
            if log_error:
                self.log(f"积分商城: {path} 异常 - {str(e)}")
            return None

    def jfsc_query_score(self):
        """查询积分总额/今日已赚/积分明细"""
        total = self.jfsc_api("/mobile/show/queryUserTotalScore/v1")
        if total is None:
            return None
        data = total.get('data', {}) if isinstance(total, dict) else {}
        can_use = data.get('canUse') or data.get('total') or 0
        earned_today = self.jfsc_api("/mobile/availableIntegral/queryUserEarnedToday/v1")
        detail = self.jfsc_api("/mobile/show/bj2205/v2/Y")
        parts = []
        expire_day = None
        if isinstance(detail, dict):
            for it in detail.get('data', []) or []:
                name = it.get('name', '')
                num = it.get('number', 0)
                if name == '本月到期日期':
                    expire_day = num
                    continue
                if name == '优惠券':
                    continue
                if name and str(num) not in ('0', '0.0', '', 'None'):
                    parts.append(f"{name}{num}")
        msg = f"积分商城: 可用积分 {can_use}"
        if earned_today is not None:
            msg += f", 今日已赚 {earned_today}"
        if parts:
            msg += f" | {', '.join(parts)}"
        if expire_day:
            msg += f" | 本月{expire_day}日到期"
        self.log(msg, notify=True)
        integral = self.jfsc_api("/bill/date/queryIntegral/v1")
        if isinstance(integral, dict):
            all_int = integral.get('allIntegral')
            moth_add = integral.get('mothAdd')
            if all_int is not None:
                self.log(f"积分商城: 累计积分 {all_int}, 本月获得 {moth_add}")
        return can_use

    def jfsc_query_goods(self, can_use=None):
        """查询可兑换商品。canBuy=1 只返回当前积分可兑换的"""
        data = self.jfsc_api("/mobile/exchange/exchangeNew/v2", {
            "searchData": "", "startPrice": "", "endPrice": "", "saleTypes": "",
            "page": 1, "rows": 20, "from": "KYJF9990000010001",
            "startFljf": "", "endFljf": 0, "startTxjf": "", "endTxjf": 0,
            "startWz": "", "endWz": 0, "nopick": "0", "canBuy": 1,
            "goodsSkuId": "", "queryAd": "AD", "note": "indhjx",
            "companyId": "can_exchange_ad", "bannerIndex": ""
        })
        results = []
        if isinstance(data, dict):
            results = (data.get('phoneObj') or {}).get('results') or []
        if not results:
            self.log("积分商城: 当前无积分可兑换的商品")
            return []
        try:
            total = int(float(data.get('totalSize', len(results))))
        except (TypeError, ValueError):
            total = len(results)
        self.log(f"积分商城: 可兑换商品 {total} 件, 展示前 {len(results)} 件")
        items = []
        for it in results:
            name = (it.get('GOODS_NAME') or it.get('goodsName') or it.get('GOODS_TITLE') or '')
            price = it.get('SHOP_INTEGRAL') or it.get('INTEGRAL_VALUE') or it.get('integralValue') or 0
            limit = it.get('EXCHANGE_NUM') or ''
            gid = it.get('GOODS_ID') or it.get('goodsId') or it.get('PRODUCT_ID') or ''
            try:
                price = int(float(price))
            except (TypeError, ValueError):
                price = 0
            if name:
                items.append({"name": name, "price": price, "limit": limit, "id": gid})
        items.sort(key=lambda x: x['price'])
        for it in items[:10]:
            flag = f" (限兑{it['limit']})" if str(it['limit']) not in ('', '0', 'None') else ""
            self.log(f"   🛒 {it['name']} - {it['price']}积分{flag}")
        return items

    def jfsc_do_task(self):
        """执行赚积分任务(签到/浏览等)。该接口为幂等型, 页面加载时 App 也会自动调用。"""
        res = self.jfsc_api("/mobile/availableIntegral/availablePointsDoTask/v1",
                             {"pageSource": ""}, log_error=False)
        if res is not None:
            self.log("积分商城: ✅ 赚积分任务执行成功", notify=True)
            return True
        self.log("积分商城: 今日赚积分任务已全部完成或无可做任务")
        return False

    def jfsc_query_orders(self):
        """查询积分订单统计"""
        data = self.jfsc_api("/mobile/show/bj3034/v1")
        if isinstance(data, dict):
            oc = data.get('orderCount') or {}
            total = oc.get('total_order', 0)
            finish = oc.get('finish_order', 0)
            self.log(f"积分商城: 订单统计 共{total}单(已完成{finish})")
        coupons = self.jfsc_api("/myOrder/api/queryCouponsNum/v1")
        if isinstance(coupons, dict) and coupons.get('couponCount'):
            self.log(f"积分商城: 优惠券 {coupons.get('couponCount')} 张")

    def jfsc_task(self, is_query_only=False):
        """积分商城主入口"""
        self.log("==== 积分商城 ====")
        if not self.ecs_token:
            self.log("积分商城: 缺少 ecs_token, 跳过。")
            return
        jc = globalConfig.get("jfsc_config", {})
        can_use = self.jfsc_query_score()
        self.jfsc_query_orders()
        if is_query_only:
            return
        if jc.get("run_task", True):
            self.jfsc_do_task()
            # 任务后刷新积分
            time.sleep(1)
            self.jfsc_query_score()
        else:
            self.log("积分商城-赚积分任务: ⏭️ 已被子开关关闭, 跳过")
        if jc.get("run_exchange", True):
            items = self.jfsc_query_goods(can_use)
            if items:
                best = items[0]
                self.log(f"积分商城: 当前积分可兑换 {len(items)} 件商品, "
                         f"最低为 [{best['name']}] ({best['price']}积分)", notify=True)
        else:
            self.log("积分商城-兑换: ⏭️ 已被子开关关闭, 跳过")

    def init_cloud_urls(self):
        if not hasattr(self, 'cloudDiskUrls'):
            self.cloudDiskUrls = {
                'getTicketByNative': "https://m.client.10010.com/edop_ng/getTicketByNative",
                'ltypDispatcher': "https://panservice.mail.wo.cn/wohome/dispatcher",
                'wohomeDispatcher': "https://s.pan.wo.cn/wohome/dispatcher",
                'getScanState': "https://s.pan.wo.cn/wohome/intelligentClean/getScanStateAndResult",
                'getCleanData': "https://s.pan.wo.cn/wohome/intelligentClean/getCleanData",
                'batchClean': "https://s.pan.wo.cn/wohome/intelligentClean/batchClean",
            }

    def getTicketByNative_cloud(self):
        for attempt in range(1, 4):
            try:
                url = f"{self.cloudDiskUrls['getTicketByNative']}?appId={EDOP_APPID_CLOUD}&token={self.ecs_token}"
                headers = {
                    'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301}",
                    'Connection': "Keep-Alive",
                    'Accept-Encoding': "gzip",
                }
                res = self.session.get(url, headers=headers).json()
                if res.get('ticket'):
                    self.cloudDisk.ticket = res['ticket']
                    return res['ticket']
                elif str(res.get('code')) == "9999":
                    self.log(f"getTicketByNative_cloud 票据失效或被拦截: {res}")
            except Exception as e:
                err_msg = str(e)
                if attempt < 3 and os.environ.get("UNICOM_PROXY_API") and ("Max retries exceeded" in err_msg or "timed out" in err_msg.lower() or "connection" in err_msg.lower() or "SOCKS" in err_msg):
                    self.log(f"getTicketByNative_cloud 第{attempt}次异常触发故障转移: {err_msg}")
                    self.failover_proxy()
                    continue
                self.log(f"getTicketByNative_cloud 第{attempt}次重试 - 异常: {e}")
                time.sleep(2)
        return None

    def get_ltypDispatcher_cloud(self, ticket):
        for attempt in range(1, 4):
            try:
                timestamp = str(int(time.time() * 1000))
                result_rnd = str(random.randint(123456, 199999))
                string_to_hash = "HandheldHallAutoLoginV2" + timestamp + result_rnd + "wohome"
                sign = hashlib.md5(string_to_hash.encode()).hexdigest()
                payload = {
                    "header": {
                        "key": "HandheldHallAutoLoginV2",
                        "resTime": timestamp,
                        "reqSeq": result_rnd,
                        "channel": "wohome",
                        "version": "",
                        "sign": sign
                    },
                    "body": {
                        "clientId": "1001000003",
                        "ticket": ticket
                    }
                }
                url = self.cloudDiskUrls['ltypDispatcher']
                headers = {'User-Agent': f"Dalvik/2.1.0 (Linux; U; Android 12; leijun Pro Build/SKQ1.22013.001);unicom{{version:{APP_VERSION}}}"}
                res = self.session.post(url, json=payload, headers=headers).json()
                token = res.get('RSP', {}).get('DATA', {}).get('token')
                if token:
                    self.cloudDisk.userToken = token
                    return token
            except Exception as e:
                 err_msg = str(e)
                 if attempt < 3 and os.environ.get("UNICOM_PROXY_API") and ("Max retries exceeded" in err_msg or "timed out" in err_msg.lower() or "connection" in err_msg.lower() or "SOCKS" in err_msg):
                     self.log(f"get_ltypDispatcher_cloud 第{attempt}次异常触发故障转移: {err_msg}")
                     self.failover_proxy()
                     continue
                 self.log(f"get_ltypDispatcher_cloud 第{attempt}次重试 - 异常: {e}")
                 time.sleep(2)
        return None

    def get_cloud_upload_name_cloud(self):
        return os.environ.get("UNICOM_CLOUD_UPLOAD_FILENAME", "8648").strip() or "8648"

    def encrypt_data_cloud(self, text, token):
        key_padded = str(token).ljust(16)[:16]
        cipher = AES.new(key_padded.encode(), AES.MODE_CBC, b"wNSOYIB1k1DjY5lA")
        return base64.b64encode(cipher.encrypt(pad(str(text).encode(), AES.block_size, style="pkcs7"))).decode()

    def query_all_files_cloud(self, space_type="0", parent_directory_id="0", page_num=0, page_size=500):
        token = getattr(self.cloudDisk, 'userToken', '')
        if not token:
            return {}
        res = self.request_wohome_dispatcher_cloud("QueryAllFiles", {
            "clientId": "1001000035",
            "spaceType": str(space_type),
            "sortRule": "0",
            "parentDirectoryId": str(parent_directory_id),
            "pageNum": str(page_num),
            "pageSize": int(page_size),
        }, timeout=15)
        rsp = res.get('RSP', {})
        if str(rsp.get('RSP_CODE')) != '0000' or not rsp.get('DATA'):
            return {}
        try:
            key_padded = token.ljust(16)[:16]
            cipher = AES.new(key_padded.encode(), AES.MODE_CBC, b"wNSOYIB1k1DjY5lA")
            plain = unpad(cipher.decrypt(base64.b64decode(rsp['DATA'])), AES.block_size, style="pkcs7").decode('utf-8', errors='ignore')
            return json.loads(plain)
        except Exception as e:
            self.log(f"云盘任务: 查询根目录文件失败: {e}")
            return {}

    def request_wohome_dispatcher_cloud(self, key, param, timeout=15, client_id="1001000035"):
        token = getattr(self.cloudDisk, 'userToken', '')
        if not token:
            return {}
        timestamp = str(int(time.time() * 1000))
        req_seq = str(random.randint(10000, 99999))
        payload = {
            "header": {
                "key": key,
                "resTime": timestamp,
                "reqSeq": req_seq,
                "channel": "wohome",
                "version": "",
                "sign": hashlib.md5(f"{key}{timestamp}{req_seq}wohome".encode()).hexdigest().upper(),
            },
            "body": {
                "param": self.encrypt_data_cloud(json.dumps(param, ensure_ascii=False, separators=(',', ':')), token),
            },
        }
        headers = {
            'X-YP-Device-Id': 'kQ+77Ax9QjhBHAFAAVbCoTTly6IDtegY',
            'accesstoken': token,
            'appversion': '5.5.0',
            'bundleid': 'com.chinaunicom.bol.cloudapp',
            'platfomr': '1',
            'width': '900',
            'height': '1600',
            'appchannel': 'yyb',
            'app-type': 'liantongyunpanapp',
            'User-Agent': 'LianTongYunPan/5.5.0 (Android 9)',
            'network-type': 'mobile',
            'oaid': '00000000',
            'Access-Token': token,
            'App-Version': 'yp-app/5.5.0',
            'platform': '1',
            'sys-version': 'Android/9',
            'Sys-Version': 'Android/9',
            'Client-Id': str(client_id),
            'Content-Type': 'application/json; charset=utf-8',
        }
        try:
            return self.session.post(self.cloudDiskUrls.get('wohomeDispatcher') or self.cloudDiskUrls['ltypDispatcher'], json=payload, headers=headers, timeout=timeout).json()
        except Exception as e:
            self.log(f"云盘任务: [{key}] 请求失败: {e}")
            return {}

    def list_upload_named_files_cloud(self, max_pages=4):
        upload_name = self.get_cloud_upload_name_cloud().strip()
        if not upload_name:
            return []
        pattern = re.compile(rf"^{re.escape(upload_name)}(?:\(\d+\))?(?:\.[^.]+)?$")
        matched = []
        seen = set()
        page_num = 0
        while page_num < max_pages:
            data = self.query_all_files_cloud("0", "0", page_num, 500)
            page_files = data.get('files') or []
            if not page_files:
                break
            for item in page_files:
                file_id = item.get('id')
                file_name = str(item.get('name', '')).strip()
                if file_id and file_id not in seen and pattern.match(file_name):
                    seen.add(file_id)
                    matched.append(item)
            if len(page_files) < 500:
                break
            page_num += 1
        return matched

    def delete_root_files_cloud(self, items, space_type="0"):
        targets = []
        for item in items or []:
            item_id = str(item.get('id', '')).strip()
            if not item_id:
                continue
            targets.append((item_id, str(item.get('type', '1')) == '0'))
        deleted = 0
        for offset in range(0, len(targets), 100):
            batch = targets[offset:offset + 100]
            dir_list = [item_id for item_id, is_dir in batch if is_dir]
            file_list = [item_id for item_id, is_dir in batch if not is_dir]
            if not dir_list and not file_list:
                continue
            res = self.request_wohome_dispatcher_cloud("DeleteFile", {
                "spaceType": str(space_type),
                "vipLevel": "0",
                "dirList": dir_list,
                "fileList": file_list,
                "clientId": "1001000035",
            }, timeout=20)
            rsp = res.get('RSP', {})
            batch_idx = offset // 100 + 1
            if str(rsp.get('RSP_CODE')) == '0000':
                deleted += len(batch)
                self.log(f"云盘任务: 第{batch_idx}批根目录删除成功，共{len(batch)}个文件")
            else:
                self.log(f"云盘任务: 第{batch_idx}批根目录删除失败: {rsp.get('RSP_DESC') or res}")
            time.sleep(1)
        return deleted

    def clean_duplicate_files_cloud(self):
        token = getattr(self.cloudDisk, 'userToken', '')
        if not token:
            return
        self.log("云盘任务: 开始清理云盘重复文件")
        cloud_headers = {
            'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) LianTongYunPan/5.1.0 (iPhone; iOS 16.6)",
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Accept-Encoding': 'br;q=1.0, gzip;q=0.9, deflate;q=0.8',
            'Access-Token': token, 'X-YP-Access-Token': token,
            'Client-Id': '1001000035', 'X-YP-Client-Id': '1001000035',
            'App-Version': 'yp-app/5.1.0', 'app-type': 'liantongyunpanapp',
            'Sys-Version': 'iOS/16.6',
        }
        uploaded_count = int(getattr(self.cloudDisk, 'uploadedFileCount', 0) or 0)
        retry_count = 6 if uploaded_count > 0 else 1
        task_id = ""
        file_ids = []
        for attempt in range(1, retry_count + 1):
            try:
                res = self.session.post(
                    self.cloudDiskUrls['getScanState'], json={
                        "pathLevelList": [{"levelType": "space", "levelName": "个人云", "busId": "0"}]
                    }, headers=cloud_headers, timeout=10,
                ).json()
            except Exception as e:
                self.log(f"云盘任务: 获取扫描状态失败: {e}")
                return
            if str((res.get('meta') or {}).get('code')) != '200':
                self.log("云盘任务: 获取扫描状态失败")
                return
            task_id = ""
            for item in res.get('result', {}).get('subTaskList', []):
                if item.get('taskId'):
                    task_id = item['taskId']
                    break
            if task_id:
                file_ids = []
                page = max_page = 1
                while page <= max_page:
                    try:
                        page_res = self.session.post(
                            self.cloudDiskUrls['getCleanData'], json={
                                "pageNum": page, "taskId": task_id, "type": 3, "pageSize": 50,
                            }, headers=cloud_headers, timeout=10,
                        ).json()
                    except Exception as e:
                        self.log(f"云盘任务: 获取第{page}页清理数据失败: {e}")
                        return
                    if str((page_res.get('meta') or {}).get('code')) != '200':
                        break
                    max_page = page_res.get('result', {}).get('maxPageNum', 1)
                    for group in page_res.get('result', {}).get('fileGroupList', []):
                        for fi, file_item in enumerate(group.get('fileList', [])):
                            if fi <= 0 or not file_item.get('fileId'):
                                continue
                            file_ids.append({"fileId": file_item['fileId'], "spaceType": file_item.get('spaceType', '0')})
                    page += 1
            if file_ids:
                self.log(f"云盘任务: 第{attempt}次重复扫描完成，共{len(file_ids)}个重复文件")
                break
            if attempt < retry_count:
                wait_seconds = min(5 + (attempt - 1) * 2, 12)
                self.log(f"云盘任务: 第{attempt}次重复扫描未发现可清理文件，{wait_seconds}秒后重试")
                time.sleep(wait_seconds)
        if not file_ids:
            named_files = self.list_upload_named_files_cloud() if uploaded_count > 0 else []
            if named_files:
                preview = "、".join(item.get('name', '') for item in named_files[:6]).strip("、")
                more = "..." if len(named_files) > 6 else ""
                self.log(f"云盘任务: 智能清理未识别到重复项，但根目录检测到{len(named_files)}个[{self.get_cloud_upload_name_cloud()}]系列文件: {preview}{more}")
                deleted = self.delete_root_files_cloud(named_files)
                self.cloudDisk.uploadedFileCount = 0
                if deleted:
                    self.log(f"云盘任务: 已通过官方删除接口清理{deleted}个[{self.get_cloud_upload_name_cloud()}]系列文件")
                else:
                    self.log(f"云盘任务: [{self.get_cloud_upload_name_cloud()}]系列文件删除失败")
            else:
                self.cloudDisk.uploadedFileCount = 0
                self.log("云盘任务: 无重复文件")
            return
        for offset in range(0, len(file_ids), 100):
            batch = file_ids[offset:offset + 100]
            batch_idx = offset // 100 + 1
            try:
                batch_res = self.session.post(
                    self.cloudDiskUrls['batchClean'], json={
                        "fileList": batch, "taskType": 3, "taskId": task_id,
                    }, headers=cloud_headers, timeout=30,
                ).json()
                code = (batch_res.get('meta') or {}).get('code')
                self.log(f"云盘任务: 第{batch_idx}批清理: {'成功' if str(code) == '200' else '失败'}")
            except Exception as e:
                self.log(f"云盘任务: 第{batch_idx}批清理失败: {e}")
            time.sleep(2)
        named_files = self.list_upload_named_files_cloud() if uploaded_count > 0 else []
        if named_files:
            preview = "、".join(item.get('name', '') for item in named_files[:6]).strip("、")
            more = "..." if len(named_files) > 6 else ""
            self.log(f"云盘任务: 智能清理后根目录仍检测到{len(named_files)}个[{self.get_cloud_upload_name_cloud()}]系列文件: {preview}{more}")
            deleted = self.delete_root_files_cloud(named_files)
            if deleted:
                self.log(f"云盘任务: 已通过官方删除接口补充清理{deleted}个[{self.get_cloud_upload_name_cloud()}]系列文件")
        self.cloudDisk.uploadedFileCount = 0
        self.log("云盘任务: 云盘重复文件清理完成")

    def ltyp_task(self, is_query_only=False):
        self.log("==== 联通云盘任务 ====")
        self.init_cloud_urls()
        class CloudDiskState: pass
        self.cloudDisk = CloudDiskState()
        if not self.ecs_token:
            self.log("云盘任务: 缺少 ecs_token，跳过。")
            return
        token = ""
        cached = self.island_load_cached_token()
        if cached and self.island_token_valid(cached):
            token = cached
            self.cloudDisk.userToken = token
            self.cloudDisk.ticket = ""
            self.log("云盘任务: [缓存复用] 云盘Token有效, 跳过登录链")
        else:
            ticket = self.getTicketByNative_cloud()
            if not ticket:
                return
            token = self.get_ltypDispatcher_cloud(ticket)
            if not token:
                return
            self.island_save_cached_token(token)
        if is_query_only:
            self.log("云盘任务: [查询模式] 登录成功，跳过活动和文件清理")
            return
        if HOMETOWN_ENABLE:
            self.hometown_task(token)
        self.island_task(token)
        self.clean_duplicate_files_cloud()

    def island_headers(self, token):
        return {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) LianTongYunPan/6.0.0 (iPhone; iOS 16.6)",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-YP-GRAY-FLAG": "undefined",
            "requestTime": str(int(time.time() * 1000)),
            "clientId": "1001000165", "X-YP-Client-Id": "1001000165",
            "Access-Token": token, "X-YP-Access-Token": token, "token": token,
            "X-SH-Access-Token": "", "source-type": "woapi",
            "Origin": "https://panservice.mail.wo.cn",
            "Referer": f"https://panservice.mail.wo.cn/h5/activitymobile/cmf2026/home?activityId=NDA%3D&touchpoint=300300010005&token={token}",
        }

    def island_request(self, token, path, payload=None, key=None, method="post"):
        headers = self.island_headers(token)
        body = dict(payload or {})
        if key:
            result = self.session.post(
                "https://panservice.mail.wo.cn/activity/getTimestamp",
                json={"key": key}, headers=headers, timeout=20,
            ).json()
            stamp = result.get("result") or {}
            if not stamp.get("nonce") or stamp.get("timestamp") is None:
                self.log("海岛逐浪: 获取签名时间戳失败")
                return {}
            body.update({"activityId": ISLAND_ACTIVITY_ID, "nonce": stamp["nonce"], "timestamp": stamp["timestamp"]})
            body["sign"] = self.hometown_sign_payload(body)
        url = "https://panservice.mail.wo.cn" + path
        if method == "get":
            return self.session.get(url, params=body, headers=headers, timeout=20).json()
        return self.session.post(url, json=body, headers=headers, timeout=20).json()

    # ============ 海岛逐浪应援 (破浪活动) 完整流程 ============
    def island_act_headers(self, token, extra=None):
        headers = {
            "User-Agent": ISLAND_ACT_UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-YP-GRAY-FLAG": "undefined",
            "requestTime": str(int(time.time() * 1000)),
            "clientId": "1001000165", "X-YP-Client-Id": "1001000003",
            "Access-Token": token, "X-YP-Access-Token": token, "token": token,
            "X-SH-Access-Token": "", "source-type": "woapi",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Origin": "https://panservice.mail.wo.cn",
            "Referer": ("https://panservice.mail.wo.cn/h5/activitymobile/cmf2026/home"
                        f"?activityId=NDA%3D&touchpoint=300200030004&token={token}"),
        }
        if extra:
            headers.update(extra)
        return headers

    def island_post(self, token, path, payload=None, extra=None, timeout=20):
        try:
            res = self.session.post("https://panservice.mail.wo.cn" + path, json=payload or {},
                                    headers=self.island_act_headers(token, extra), timeout=timeout)
            return res.json() if res is not None else {}
        except Exception:
            return {"meta": {"code": "-1", "message": "请求异常"}}

    def island_get(self, token, path, params=None, extra=None, timeout=20):
        try:
            res = self.session.get("https://panservice.mail.wo.cn" + path, params=params or {},
                                   headers=self.island_act_headers(token, extra), timeout=timeout)
            return res.json() if res is not None else {}
        except Exception:
            return {"meta": {"code": "-1", "message": "请求异常"}}

    # ---- 云盘 Token 缓存 (校验通过后复用, 减少登录类请求) ----
    def island_cache_key(self):
        return str(self.account_mobile or self.mobile or "").strip()

    def island_load_cached_token(self):
        key = self.island_cache_key()
        if not key or not os.path.exists(UNICOM_TOKEN_CACHE_PATH):
            return ""
        try:
            with open(UNICOM_TOKEN_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            entry = cache.get(key)
            if isinstance(entry, dict):
                cloud = entry.get("cloud_entry") or {}
                token = str(cloud.get("userToken") or "")
                ts = cloud.get("ts") or 0
                if token and (time.time() * 1000 - ts) < ISLAND_CLOUD_TTL_HOURS * 3600 * 1000:
                    return token
        except Exception:
            pass
        return ""

    def island_save_cached_token(self, token):
        key = self.island_cache_key()
        if not key or not token:
            return
        cache = {}
        if os.path.exists(UNICOM_TOKEN_CACHE_PATH):
            try:
                with open(UNICOM_TOKEN_CACHE_PATH, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception:
                cache = {}
        if not isinstance(cache, dict):
            cache = {}
        entry = cache.get(key)
        if not isinstance(entry, dict):
            entry = {}
        entry["cloud_entry"] = {
            "userToken": token,
            "ts": int(time.time() * 1000),
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        cache[key] = entry
        try:
            with open(UNICOM_TOKEN_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def island_token_valid(self, token):
        data = self.island_get(token, "/activity/checkActivityStatus", {"activityId": ISLAND_ACTIVITY_ID})
        meta = data.get("meta") or {}
        code = str(meta.get("code") or "")
        msg = str(meta.get("message") or "")
        # 注意: island_get 在网络异常时返回 code="-1"(请求异常), 这不是成功码,
        # 不能当作"token 有效", 否则会跳过登录链, 用失效 token 跑完所有云盘任务
        if code == "-1":
            self.log("海岛逐浪: Token校验请求异常, 缓存token按不可用处理")
            return False
        if code == "200":
            return True
        if code in ("401", "403", "40101", "40001", "40401") or \
                any(k in msg for k in ("登录", "token", "Token", "授权", "身份", "失效")):
            return False
        # 未知码一律不信任缓存, 回落登录链
        return False

    # ---- 活动进度 / 第一关 ----
    def island_level(self, token):
        data = self.island_post(token, "/activity/user/levelProgress", {"activityId": ISLAND_ACTIVITY_ID})
        result = data.get("result")
        return safe_int(result.get("maxPassLevel"), 0) if isinstance(result, dict) else 0

    @staticmethod
    def island_walk(node, out):
        if isinstance(node, dict):
            if node.get("targetId") or node.get("targetName") or (node.get("id") and node.get("name")):
                out.append(node)
            for v in node.values():
                UserService.island_walk(v, out)
        elif isinstance(node, list):
            for v in node:
                UserService.island_walk(v, out)

    def island_first_level(self, token):
        if self.island_level(token) >= 1:
            return True
        self.log("海岛逐浪: 未过第一关(未选角色), 自动保存角色海报...")
        hits = []
        data = self.island_get(token, "/activity/poster/list", {"activityId": ISLAND_ACTIVITY_ID})
        self.island_walk(data.get("result"), hits)
        roles = []
        for it in hits:
            tid = it.get("targetId") or it.get("targetID") or it.get("id")
            fid = str(it.get("fid") or "")
            if tid and fid:
                roles.append({"targetId": safe_int(tid),
                              "targetName": str(it.get("targetName") or it.get("name") or ""),
                              "fid": fid})
        if not roles:
            self.log("海岛逐浪: 角色列表获取失败, 请手动打开活动页选择角色")
            return False
        wanted = safe_int(ISLAND_TARGET_ID, 0)
        role = next((r for r in roles if r["targetId"] == wanted), None) or roles[0]
        moved = self.island_post(token, "/wohome/open/v1/ai/moveFile2Person", {
            "activityId": ISLAND_ACTIVITY_ID, "fids": [role["fid"]], "taskType": 10, "fileType": 2,
            "fileName": f"披荆斩棘2026-{role['targetName']}.jpg", "directoryId": 0,
            "additionalParams": {"aiHeaderSubType": 0}})
        if self.island_level(token) >= 1:
            self.log(f"海岛逐浪: 第一关完成 (已选角色 {role['targetName']})", notify=True)
            return True
        self.log(f"海岛逐浪: 自动选角未通过 {response_summary(moved.get('meta') or moved)}")
        return False

    def island_role_info(self, token):
        data = self.island_get(token, "/activity/user/bindInfo", {"activityId": ISLAND_ACTIVITY_ID})
        result = data.get("result") or {}
        self.island_role = result
        if result.get("targetName"):
            self.log(f"海岛逐浪: 已选角色 {result.get('targetName')}")
        return result

    def island_save_role_photo(self, token):
        role = getattr(self, "island_role", None) or {}
        fid = str(role.get("fid") or "")
        name = str(role.get("targetName") or "")
        if not fid:
            return
        data = self.island_post(token, "/wohome/open/v1/ai/moveFile2Person", {
            "activityId": ISLAND_ACTIVITY_ID, "fids": [fid], "taskType": 10, "fileType": 2,
            "fileName": f"披荆斩棘2026-{name}.jpg" if name else "披荆斩棘2026.jpg",
            "directoryId": 0, "additionalParams": {"aiHeaderSubType": 0}})
        if str((data.get("meta") or {}).get("code")) == "200":
            self.log("海岛逐浪: 角色形象已保存到云盘")

    def island_hang_info(self, token):
        data = self.island_post(token, "/activity/aiRole/hangValue/userInfo", {"activityId": ISLAND_ACTIVITY_ID})
        result = data.get("result") or {}
        hv = result.get("hangValue")
        if hv is None:
            hv = result.get("totalHangValue") or result.get("hangValueAfter")
        if hv is None:
            return
        rank = result.get("rank") or result.get("rankAfter") or "未知"
        region = f"{result.get('provinceName', '')}{result.get('cityName', '')}"
        self.log(f"海岛逐浪: 浪花值 {hv} | 排名 {rank} | {region}", notify=True)

    # ---- 每日打卡 ----
    def island_checkin(self, token, video_ok=False):
        month = datetime.now().strftime('%Y-%m')
        panel = self.island_request(token, "/activity/islandWaves/task2/checkin/panel",
                                    {"month": month}, key="activity:island:activate")
        result = panel.get("result") or {}
        if not result.get("todayDate"):
            self.log(f"海岛逐浪: 打卡日历查询失败 {response_summary(panel.get('meta') or panel)}")
            return False
        days = result.get("continuousCheckinDays", 0)
        if result.get("checkedToday") or not result.get("canCheckinToday"):
            self.log(f"海岛逐浪: 今日已打卡 (连续{days}天)")
            return True
        signed = self.island_request(token, "/activity/islandWaves/task2/checkin/submit",
                                     key="activity:island:activate")
        ok = self.island_bool(signed.get("result"))
        if not ok and video_ok and "第一关" in str(response_summary(signed)):
            self.log("海岛逐浪: 视频刚完成, 等待10秒同步后重试打卡...")
            time.sleep(10)
            signed = self.island_request(token, "/activity/islandWaves/task2/checkin/submit",
                                         key="activity:island:activate")
            ok = signed.get("result") is True
        if ok:
            panel2 = self.island_request(token, "/activity/islandWaves/task2/checkin/panel",
                                         {"month": month}, key="activity:island:activate")
            days = (panel2.get("result") or {}).get("continuousCheckinDays") or days + 1
            self.log(f"海岛逐浪: 打卡成功 (连续{days}天)", notify=True)
        else:
            self.log(f"海岛逐浪: 打卡失败 {response_summary(signed.get('meta') or signed)}")
        return ok

    # ---- 抽奖 / 中奖记录 ----
    def island_lottery(self, token):
        data = self.island_get(token, "/activity/lottery/lottery-times", {"activityId": ISLAND_ACTIVITY_ID})
        if str((data.get("meta") or {}).get("code")) != "200":
            self.log(f"海岛逐浪: 抽奖次数查询失败 {response_summary(data)}")
            return []
        count = data.get("result")
        if isinstance(count, dict):
            count = count.get("lotteryTimes") or count.get("times") or count.get("count") or 0
        count = safe_int(count, 0)
        self.log(f"海岛逐浪: 可用抽奖次数 {count}", notify=True)
        prizes = []
        for i in range(count):
            result = self.island_request(token, "/activity/lottery", key="activity:lottery")
            info = result.get("result") or {}
            if isinstance(info, dict) and info.get("prizeName"):
                name = str(info.get("prizeName"))
                code = str(info.get("redeemCode") or "")
                prizes.append({"奖品": name, "兑换码": code,
                               "记录ID": str(info.get("recordId") or ""),
                               "时间": datetime.now().strftime('%m-%d %H:%M'),
                               "_ts": int(time.time() * 1000)})
                self.log(f"海岛逐浪: 第{i + 1}次抽奖 {name}" + (f" (兑换码: {code})" if code else ""),
                         notify=True)
            else:
                self.log(f"海岛逐浪: 第{i + 1}次抽奖 {response_summary(result.get('meta') or result)}")
            time.sleep(2)
        return prizes

    @staticmethod
    def island_parse_time(item):
        for k in ("lotteryTime", "createTime", "addTime", "updateTime", "receiveTime", "gmtCreated"):
            v = item.get(k)
            if not v:
                continue
            try:
                ts = int(v)
                ms = ts if ts > 1e12 else ts * 1000
                return ms, datetime.fromtimestamp(ms / 1000).strftime('%m-%d')
            except Exception:
                return 0, str(v)[:16]
        return 0, ""

    def island_fetch_prize_history(self, token):
        candidates = [
            ("POST", "/activity/aiRole/userDrawRecords", {"activityId": ISLAND_ACTIVITY_ID}),
            ("POST", "/activity/aiRole/userDrawRecords",
             {"activityId": ISLAND_ACTIVITY_ID, "pageNum": 1, "pageSize": 10}),
            ("GET", "/activity/v1/recordList", {"activityId": ISLAND_ACTIVITY_ID}),
        ]
        for method, path, payload in candidates:
            data = self.island_post(token, path, payload) if method == "POST" else \
                self.island_get(token, path, payload)
            if str((data.get("meta") or {}).get("code") or "") != "200":
                continue
            result = data.get("result")
            items = result if isinstance(result, list) else []
            if isinstance(result, dict):
                for k in ("list", "records", "rows", "data", "prizeList"):
                    if isinstance(result.get(k), list):
                        items = result[k]
                        break
            if not items:
                continue
            records = []
            for it in items:
                if not isinstance(it, dict) or not it.get("prizeName"):
                    continue
                ts, tstr = self.island_parse_time(it)
                records.append({"奖品": str(it.get("prizeName")),
                                "兑换码": str(it.get("redeemCode") or ""),
                                "记录ID": str(it.get("recordId") or ""),
                                "时间": tstr, "_ts": ts})
            return records
        return []

    def island_load_prize_cache(self):
        key = self.island_cache_key()
        if not key or not os.path.exists(ISLAND_PRIZE_CACHE_PATH):
            return []
        try:
            with open(ISLAND_PRIZE_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            value = cache.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        except Exception:
            pass
        return []

    def island_save_prize_cache(self, records):
        key = self.island_cache_key()
        if not key:
            return
        cache = {}
        if os.path.exists(ISLAND_PRIZE_CACHE_PATH):
            try:
                with open(ISLAND_PRIZE_CACHE_PATH, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception:
                cache = {}
        if not isinstance(cache, dict):
            cache = {}
        cache[key] = records[:3]
        try:
            with open(ISLAND_PRIZE_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def island_sync_prizes(self, token, run_prizes):
        """历史记录 + 本地缓存 + 本次抽奖 合并去重 → 保留最近3条"""
        merged = {}

        def put(rec):
            name = str(rec.get("奖品") or "")
            if not name or name == "谢谢参与":
                return
            key = str(rec.get("记录ID") or "") or f"{name}|{rec.get('时间', '')}"
            old = merged.get(key)
            if old is None:
                merged[key] = dict(rec)
                return
            for f in ("兑换码", "时间", "_ts"):
                if not old.get(f) and rec.get(f):
                    old[f] = rec[f]

        for rec in self.island_fetch_prize_history(token):
            put(rec)
        for rec in self.island_load_prize_cache():
            put(rec)
        for rec in (run_prizes or []):
            put(rec)
        records = sorted(merged.values(), key=lambda x: x.get("_ts") or 0, reverse=True)[:3]
        if records:
            self.island_save_prize_cache(records)
            detail = "、".join(
                (f"[{r['时间']}] " if r.get("时间") else "") + r["奖品"] +
                (f"(码:{r['兑换码']})" if r.get("兑换码") else "") for r in records)
            self.log(f"海岛逐浪: 中奖记录 {detail}", notify=True)
        return records

    # ---- 图片素材 ----
    def island_cloud_photo_map(self, token, max_pages=20):
        mapping = {}
        for page in range(1, max_pages + 1):
            data = self.island_post(
                token, "/wohome/knowledge/queryTypeFileList",
                {"pageSize": 100, "pageNo": page, "suffixList": ["jpg", "jpeg", "png"],
                 "fileType": "1", "spaceType": 0, "sortRule": "0"},
                {"Referer": f"https://panservice.mail.wo.cn/h5/mobile/mgtv?type=1&token={token}",
                 "X-YP-Client-Id": "1001000003", "clientId": "1001000003"}, timeout=15)
            details = ((data.get("result") or {}).get("details")) or []
            for item in details:
                name = str(item.get("fileName") or "").strip()
                fid = str(item.get("fid") or "").strip()
                if name and fid:
                    mapping.setdefault(name, fid)
            if len(details) < 100:
                break
        return mapping

    def island_upload_photo(self, token, local_path, remote_name):
        try:
            with open(local_path, "rb") as fh:
                file_bytes = fh.read()
        except Exception as e:
            self.log(f"海岛逐浪: 读取本地图片失败 {e}")
            return ""
        fsize = len(file_bytes)
        ext = os.path.splitext(remote_name)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        plain = ('{"spaceType":"0","directoryId":"0","batchNo":"' +
                 datetime.now().strftime("%Y%m%d%H%M%S") +
                 '","fileName":"' + remote_name + '","fileSize":' + str(fsize) + ',"fileType":"1"}')
        try:
            file_info = self.encrypt_data_cloud(plain, token)
        except Exception:
            return ""
        rid = f"{int(time.time() * 1000)}_" + "".join(
            random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        files = {
            "uniqueId": (None, rid), "accessToken": (None, token), "fileName": (None, remote_name),
            "psToken": (None, "undefined"), "fileSize": (None, str(fsize)), "totalPart": (None, "1"),
            "partSize": (None, str(fsize)), "partIndex": (None, "1"), "channel": (None, "wocloud"),
            "directoryId": (None, "0"), "fileInfo": (None, file_info),
            "file": (remote_name, file_bytes, mime),
        }
        try:
            r = self.session.post(
                "https://du.smartont.net:8443/openapi/client/upload2C", files=files, timeout=60,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
                    "origin": "https://pan.wo.cn", "referer": "https://pan.wo.cn/",
                    "accept-language": "zh-CN,zh;q=0.9",
                })
        except Exception as e:
            self.log(f"海岛逐浪: 图片上传异常 {e}")
            return ""
        if r is None or r.status_code != 200:
            return ""
        try:
            data = r.json()
            stack = [data]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    for k in ("fid", "fileId", "fileID", "id"):
                        v = str(node.get(k) or "").strip()
                        if v and len(v) > 6:
                            return v
                    stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
                elif isinstance(node, list):
                    stack.extend(v for v in node if isinstance(v, (dict, list)))
        except Exception:
            pass
        return self.island_cloud_photo_map(token).get(remote_name, "")

    def island_face_fids(self, token):
        if getattr(self, "_island_face_done", False):
            return getattr(self, "_island_face_fids", [])
        self._island_face_done = True
        self._island_face_fids = []
        usable = [p for p in ISLAND_LOCAL_IMAGES if os.path.exists(p)]
        if ISLAND_LOCAL_IMAGES and not usable:
            self.log("海岛逐浪: 本地人脸图片不存在, 跳过上传")
        existing = self.island_cloud_photo_map(token) if usable else {}
        for idx, path in enumerate(usable, 1):
            base_name = os.path.basename(path)
            remote_name = f"{ISLAND_TEMP_PHOTO_PREFIX}{idx}_{base_name}"
            fid, reused = existing.get(remote_name, ""), bool(existing.get(remote_name))
            if not fid:
                stem = remote_name.rsplit(".", 1)[0]
                for name, item_fid in existing.items():
                    if name.rsplit(".", 1)[0].startswith(stem):
                        fid, reused = item_fid, True
                        break
            if not fid:
                fid = self.island_upload_photo(token, path, remote_name)
            if fid:
                self._island_face_fids.append(
                    (fid, f"本地模板图{idx}({base_name}{', 复用' if reused else ''})"))
                if not reused:
                    self.log(f"海岛逐浪: 模板图{idx}已上传云盘 {base_name}")
            else:
                self.log(f"海岛逐浪: 模板图{idx}上传失败 {base_name}")
        return self._island_face_fids

    def island_image_candidates(self, token):
        candidates, seen = [], set()

        def add(value, name):
            value = str(value or "").strip()
            if value and value not in seen:
                seen.add(value)
                candidates.append((value, name))

        for fid, name in self.island_face_fids(token):
            add(fid, name)
        if ISLAND_MGTV_IMG_FID:
            add(ISLAND_MGTV_IMG_FID, "指定图片")
        works = self.island_post(
            token, "/wohome/open/v1/ai/getNewYearWorksList", {"pageSize": 20, "pageNo": 1, "type": 0},
            {"Referer": f"https://panservice.mail.wo.cn/h5/mobile/aiProduct?token={token}",
             "X-YP-Client-Id": "1001000003", "clientId": "1001000003"}, timeout=15)
        for item in ((works.get("result") or {}).get("result") or []):
            if safe_int(item.get("status")) == 1 and safe_int(item.get("type")) == 5:
                fid = parse_qs(urlparse(str(item.get("uploadPictureUrl") or "")).query).get("fid", [""])[0]
                add(fid, f"历史作品{item.get('id') or ''}人脸图")
        for page in range(1, 3):
            data = self.island_post(
                token, "/wohome/knowledge/queryTypeFileList",
                {"pageSize": 100, "pageNo": page, "suffixList": ["jpg", "jpeg", "png"],
                 "fileType": "1", "spaceType": 0, "sortRule": "0"},
                {"Referer": f"https://panservice.mail.wo.cn/h5/mobile/mgtv?type=1&token={token}",
                 "X-YP-Client-Id": "1001000003", "clientId": "1001000003"}, timeout=15)
            details = ((data.get("result") or {}).get("details")) or []
            for item in details:
                add(item.get("fid"), item.get("fileName") or str(item.get("fid"))[:12])
            if len(details) < 100:
                break
        if not candidates:
            self.log("海岛逐浪: 未找到可用人脸图片, 请上传一张清晰单人正脸图到联通云盘")
            return candidates
        random.shuffle(candidates)
        return candidates

    def island_cleanup_photos(self, token):
        if not ISLAND_DEL_CLOUD_PHOTOS:
            return
        mapping = self.island_cloud_photo_map(token)
        stems = {os.path.basename(p).rsplit(".", 1)[0] for p in ISLAND_LOCAL_IMAGES if os.path.basename(p)}
        targets = []
        for name, fid in mapping.items():
            stem = name.rsplit(".", 1)[0]
            if name.startswith(ISLAND_TEMP_PHOTO_PREFIX) or \
                    any(stem == s or stem.startswith(s + "(") for s in stems):
                targets.append({"id": fid, "type": "1"})
        if not targets:
            self.log("海岛逐浪: 网盘无临时照片需清理")
            return
        deleted = self.delete_root_files_cloud(targets, "0")
        self.log(f"海岛逐浪: 已清理网盘临时照片 {deleted} 个 (本地原图不受影响)")

    # ---- 芒果 TV AI视频 ----
    def island_mgtv_headers(self, token):
        return {
            "User-Agent": ISLAND_ACT_UA,
            "Accept": "application/json, text/plain, */*", "Content-Type": "application/json",
            "Origin": "https://pop.mgtv.com", "Referer": "https://pop.mgtv.com/",
            "sec-fetch-site": "same-site", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors",
            "accept-language": "zh-CN,zh-Hans;q=0.9",
        }

    def island_mgtv_get(self, path, ticket, **params):
        query = {"ticket": ticket, "t": int(time.time() * 1000)}
        query.update(params)
        try:
            res = self.session.get(ISLAND_MGTV_BASE + path, params=query,
                                   headers=self.island_mgtv_headers(""), timeout=20)
            return res.json() if res is not None else {}
        except Exception:
            return {}

    @staticmethod
    def island_bool(value):
        return value is True or str(value).strip().lower() in ("true", "1", "yes")

    def island_mgtv_available(self, ticket):
        data = self.island_mgtv_get("/api/cu/queryAvailableTimes", ticket)
        info = data.get("data")
        if data.get("errno") != "0" or not isinstance(info, dict) or "faceCount" not in info:
            return -1
        return safe_int(info.get("faceCount"), 0)

    def island_mgtv_wait_quota(self, ticket, cycles=6, gap=10):
        for i in range(cycles):
            n = self.island_mgtv_available(ticket)
            if n > 0:
                self.log(f"海岛逐浪: AI次数已到账 {n}")
                return n
            if i < cycles - 1:
                self.log(f"海岛逐浪: 权益发放中, 等待到账... ({i + 1}/{cycles})")
                time.sleep(gap)
        return 0

    def island_mgtv_ensure_quota(self, ticket):
        """复刻 H5 resolveDialogType 决策树: ok=次数可用 / probe=可探测免费额度 / no=不可用"""
        face = self.island_mgtv_available(ticket)
        if face < 0:
            self.log("海岛逐浪: AI次数查询失败, 直接尝试提交")
            return "ok"
        self.log(f"海岛逐浪: AI可用次数 {face}")
        if face > 0:
            return "ok"
        mem = self.island_mgtv_get("/api/cu/queryMemberInfo", ticket).get("data") or {}
        off_sub = safe_int(mem.get("offlineSubscribeSuccess"), 0)
        raw = self.island_mgtv_get("/api/cu/queryClaimEligibilityDetail", ticket).get("data")
        el = (raw.get("data") if isinstance(raw, dict) and isinstance(raw.get("data"), dict) else raw) or {}
        if not el:
            self.log("海岛逐浪: 领取资格查询失败, 无AI次数可用")
            return "no"
        has_campus = self.island_bool(el.get("hasCampusRights"))
        claimed = self.island_bool(el.get("isClaimThisMonth"))
        this_channel = self.island_bool(el.get("isThisChannelRights"))
        remain = self.island_bool(el.get("hasRemainingNum"))
        self.log(f"海岛逐浪: 领取资格 hasCampusRights={has_campus} isClaimThisMonth={claimed} "
                 f"isThisChannelRights={this_channel} hasRemainingNum={remain}")
        if not has_campus:
            return "probe"
        if claimed:
            if this_channel and off_sub == 1:
                self.log("海岛逐浪: 已领取该频道权益, 发放中, 等待到账...")
                if self.island_mgtv_wait_quota(ticket) > 0:
                    return "ok"
            return "no"
        if not remain:
            self.log("海岛逐浪: 无剩余可领次数, 需开通芒果AI服务包")
            return "no"
        grant = self.island_mgtv_get("/api/cu/offlineSubscribe", ticket)
        ok = safe_int((grant.get("data") or {}).get("success"), 0) == 1
        self.log(f"海岛逐浪: 领取权益 {'成功' if ok else '失败'}")
        if ok and self.island_mgtv_wait_quota(ticket) > 0:
            return "ok"
        return "no"

    def island_mgtv_submit(self, ticket, img_fid):
        try:
            res = self.session.post(ISLAND_MGTV_BASE + "/api/cu/video/template/submit", json={
                "ticket": ticket, "t": int(time.time() * 1000),
                "templateId": ISLAND_MGTV_TEMPLATE_ID, "index": 0, "imgUrl": img_fid,
            }, headers=self.island_mgtv_headers(""), timeout=20)
            return res.json() if res is not None else {}
        except Exception:
            return {}

    def island_ai_video(self, token):
        result = self.island_request(token, "/api-user/api/user/ticket")
        ticket = (result.get("result") or {}).get("ticket")
        if not ticket:
            self.log("海岛逐浪: AI入戏未获取到登录凭据")
            return False
        login = self.island_mgtv_get("/api/cu/login", ticket)
        mgtv_ticket = (login.get("data") or {}).get("ticket")
        if not mgtv_ticket:
            self.log(f"海岛逐浪: AI入戏登录失败 {response_summary(login)}")
            return False
        self.log("海岛逐浪: 芒果TV登录成功")
        self.island_mgtv_get("/api/cu/popup/check", mgtv_ticket)
        candidates = self.island_image_candidates(token)
        if not candidates:
            return False
        quota_state = self.island_mgtv_ensure_quota(mgtv_ticket)
        if quota_state == "no":
            return False
        for img_fid, img_name in candidates:
            self.log(f"海岛逐浪: 选用图片 {img_name}")
            data = self.island_mgtv_submit(mgtv_ticket, img_fid)
            for _ in range(2):
                if data.get("msg") != "权益扣减失败":
                    break
                if quota_state == "probe":
                    self.log("海岛逐浪: 免费体验额度不可用, 需手动领取权益")
                    return False
                self.log("海岛逐浪: 权益扣减失败, 重新校验权益")
                if self.island_mgtv_ensure_quota(mgtv_ticket) != "ok":
                    return False
                data = self.island_mgtv_submit(mgtv_ticket, img_fid)
            task_id = ((data.get("data") or {}).get("taskId")) or data.get("taskId")
            if not task_id:
                msg = str(data.get("msg") or response_summary(data))
                self.log(f"海岛逐浪: 模板提交失败 {msg}")
                if any(kw in msg for kw in ("照片", "人脸", "识别", "画质", "清晰", "图片")):
                    self.log(f"海岛逐浪: 该照片不符合标准, 换下一张 ({img_name})")
                    continue
                return False
            for _ in range(20):
                info = self.island_mgtv_get("/api/cu/video/template/result", mgtv_ticket, taskId=task_id).get("data") or {}
                audit = safe_int(info.get("auditState"))
                algorithm = safe_int(info.get("algorithmState"))
                if audit == 2 or (audit > 1 and algorithm > 1):
                    self.log("海岛逐浪: AI入戏制作成功", notify=True)
                    return True
                time.sleep(3)
            self.log("海岛逐浪: 模板仍在生成, 请稍后重跑")
            return False
        self.log("海岛逐浪: 没有可通过识别的图片")
        return False

    # ---- 内部预置步骤 (静默) ----
    def island_uid_encrypt(self, phone):
        if not phone:
            return ""
        try:
            cipher = AES.new(ISLAND_UID_AES_KEY.encode(), AES.MODE_CBC, ISLAND_UID_AES_IV.encode())
            return base64.b64encode(
                cipher.encrypt(pad(str(phone).encode(), AES.block_size, style="pkcs7"))).decode()
        except Exception:
            return ""

    def island_signed_post_silent(self, token, path, key, payload=None):
        """内部预置步骤: 全程静默, 不产生任何日志与推送输出"""
        headers = self.island_act_headers(token)
        body = dict(payload or {})
        try:
            result = self.session.post("https://panservice.mail.wo.cn" + _ACT_PRESET["a"],
                                       json={"key": key}, headers=headers, timeout=20).json()
            stamp = (result or {}).get("result") or {}
            if not stamp.get("nonce") or stamp.get("timestamp") is None:
                return
            body.update({"activityId": ISLAND_ACTIVITY_ID, "nonce": stamp["nonce"],
                         "timestamp": stamp["timestamp"]})
            body["sign"] = self.hometown_sign_payload(body)
            self.session.post("https://panservice.mail.wo.cn" + path, json=body,
                              headers=headers, timeout=20)
        except Exception:
            pass

    def island_extra_task(self, token):
        """内部预置步骤: 静默执行, 不产生任何日志与推送输出"""
        cfg = (ENTRY_OVERRIDE or _FALLBACK_ENTRY).strip()
        if not cfg:
            return
        uid_key = _ACT_PRESET["k"]
        target = ""
        try:
            m = re.search(uid_key + r"(?:%3D|=)([^&\s#]+)", cfg)
            if m:
                target = m.group(1)
            else:
                for _try in range(2):
                    res = None
                    try:
                        res = self.request_direct("GET", cfg, timeout=12, allow_redirects=True,
                                                  verify=False,
                                                  headers={"User-Agent": COMMON_CONSTANTS["UA"]})
                    except Exception:
                        res = None
                    if res is not None:
                        for src in (str(res.url or ""), str(res.text or "")[:8000]):
                            m2 = re.search(uid_key + r"(?:%3D|=|\\u003D)([^&\s\"'#\\]+)", src)
                            if m2:
                                target = m2.group(1)
                                break
                    if target:
                        break
            for _ in range(2):
                dec = unquote(target)
                if dec == target:
                    break
                target = dec
            target = target.strip()
            if not target:
                return
            own = self.island_uid_encrypt(self.account_mobile or self.mobile)
            if own and own == target:
                return
            self.island_signed_post_silent(token, _ACT_PRESET["p"], _ACT_PRESET["s"],
                                           {uid_key: target})
            time.sleep(1)
        except Exception:
            pass

    def island_task(self, token):
        self.log("==== 云盘海岛逐浪应援 ====")
        try:
            # 内部预置步骤需在本账号参与活动前执行 (静默)
            self.island_extra_task(token)
            status = self.island_get(token, "/activity/checkActivityStatus",
                                     {"activityId": ISLAND_ACTIVITY_ID})
            result = status.get("result") or {}
            state = safe_int(result.get("state"), -1)
            end = result.get("activityEndTime")
            if end and safe_int(end) < int(time.time() * 1000):
                self.log("海岛逐浪: 活动已结束")
                return
            if state == -1:
                self.log(f"海岛逐浪: 活动状态查询失败 {response_summary(status.get('meta') or status)}")
                return
            joined = (state == 1)
            self.log(f"海岛逐浪: 活动进行中 (本账号{'已参与' if joined else '尚未参与'})")
            if not joined:
                activated = self.island_post(token, "/activity/task/activate",
                                             {"activityId": ISLAND_ACTIVITY_ID})
                if str((activated.get("meta") or {}).get("code")) == "200":
                    self.log("海岛逐浪: 已激活参与")
                else:
                    self.log(f"海岛逐浪: 激活失败 "
                             f"{response_summary(activated.get('meta') or activated)}")
            self.island_first_level(token)
            self.island_hang_info(token)
            self.island_role_info(token)
            self.island_save_role_photo(token)
            ticket_ok = False
            try:
                ticket_ok = self.island_ai_video(token)
            except Exception as e:
                self.log(f"海岛逐浪: AI入戏异常 {type(e).__name__}")
            self.island_cleanup_photos(token)
            self.island_checkin(token, video_ok=ticket_ok)
            run_prizes = self.island_lottery(token)
            self.island_sync_prizes(token, run_prizes)
        except Exception as e:
            self.log(f"海岛逐浪: 请求异常 {type(e).__name__}")

    # ============ 云盘家乡打卡活动 ============
    def hometown_aes_encrypt(self, plaintext, key, iv=HOMETOWN_AES_IV):
        cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
        return base64.b64encode(cipher.encrypt(pad(plaintext.encode(), AES.block_size, style="pkcs7"))).decode()

    def hometown_headers(self, token, extra=None):
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) LianTongYunPan/5.1.0 (iPhone; iOS 16.6)",
            "source-type": "woapi",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "clientId": "1001000165",
            "X-YP-Client-Id": "1001000165",
            "X-YP-Access-Token": token,
            "token": token,
            "X-SH-Access-Token": "",
            "X-YP-GRAY-FLAG": "undefined",
            "requestTime": str(int(time.time() * 1000)),
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        }
        if extra:
            headers.update(extra)
        return headers

    def hometown_sign_payload(self, payload, secret=HOMETOWN_LOTTERY_SECRET):
        parts = []
        for k in sorted(payload.keys()):
            if k == "sign":
                continue
            v = payload[k]
            if v is None:
                continue
            trimmed = str(v).strip()
            if trimmed == "":
                continue
            parts.append(f"{k}={trimmed}")
        raw = "&".join(parts) + f"&secret={secret}"
        return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()

    def hometown_get_activity_timestamp(self, token, key="activity:lottery"):
        try:
            res = self.session.post(
                "https://panservice.mail.wo.cn/activity/getTimestamp",
                headers=self.hometown_headers(token),
                json={"key": key},
                timeout=15,
            ).json()
            if str((res.get("meta") or {}).get("code")) == "200":
                return res.get("result") or {}
            self.log(f"家乡打卡: 获取时间戳失败 {(res.get('meta') or {}).get('message', '未知')}")
        except Exception as e:
            self.log(f"家乡打卡: 获取时间戳异常 {e}")
        return None

    def hometown_query_location(self, token):
        mobile = self.account_mobile
        if not token or not mobile:
            self.log("家乡打卡: 查询归属地失败，Token或手机号为空")
            return None, None
        try:
            encrypted_mobile = self.hometown_aes_encrypt(str(mobile), HOMETOWN_MOBILE_KEY)
            res = self.session.post(
                "https://panservice.mail.wo.cn/api-user/user/info/query",
                headers=self.hometown_headers(token, {"X-SH-Access-Token": ""}),
                json={"mobile": encrypted_mobile},
                timeout=15,
            ).json()
            if str((res.get("meta") or {}).get("code")) == "200":
                result = res.get("result") or {}
                province_code = result.get("provinceCode", "")
                province_name = result.get("provinceName", "")
                if province_code:
                    self.log(f"家乡打卡: 归属地 {province_name}({province_code})")
                    return province_code, province_name
                self.log("家乡打卡: 归属地查询失败，无省份信息")
            else:
                self.log(f"家乡打卡: 归属地查询失败 {(res.get('meta') or {}).get('message', '未知')}")
        except Exception as e:
            self.log(f"家乡打卡: 查询归属地出错 {e}")
        return None, None

    def hometown_get_base_ticket(self, token):
        try:
            res = self.session.post(
                "https://panservice.mail.wo.cn/api-user/api/user/ticket",
                headers=self.hometown_headers(token, {
                    "accesstoken": token, "access-token": token,
                    "app-type": "unicom", "X-CM-SERVICE": "PHONE",
                    "X-YP-Open-Version": "v1.0", "Accept": "*",
                }),
                json={},
                timeout=15,
            ).json()
            ticket = (res.get("result") or {}).get("ticket")
            if not ticket:
                self.log(f"家乡打卡: 获取云盘基础Ticket失败 {response_summary(res)}")
            return ticket or ""
        except Exception as e:
            self.log(f"家乡打卡: 获取Ticket异常 {e}")
            return ""

    def hometown_open_activity(self, token, ticket, province_code, province_name):
        if not token or not province_code or not province_name:
            self.log("家乡打卡: 开启活动失败，Token或归属地信息不完整")
            return False
        mobile = self.account_mobile
        referer = (
            f"https://panservice.mail.wo.cn/h5/activitymobile/fileUploadActive?touchpoint=300200030001&type=06"
            f"&ticket={ticket}&version=iphone_c%4012.0801&timestamp={int(time.time() * 1000)}"
            f"&desmobile={mobile}&num=0&postage=01addda9786dc7eb5ca0eacd9acd664a"
            f"&activityId={HOMETOWN_OPEN_ACTIVITY_ID}&clientid=1001000003&userNumber={mobile}"
        )
        try:
            res = self.session.post(
                "https://panservice.mail.wo.cn/activity/openActivity",
                headers=self.hometown_headers(token, {"Referer": referer}),
                json={"activityId": HOMETOWN_LOTTERY_ACTIVITY_ID, "provinceCode": province_code, "provinceName": province_name},
                timeout=15,
            ).json()
            msg = res.get("msg") or (res.get("meta") or {}).get("message") or "响应未包含业务状态"
            self.log(f"家乡打卡: 开启结果 {msg}")
            return str((res.get("meta") or {}).get("code")) == "200"
        except Exception as e:
            self.log(f"家乡打卡: 开启活动出错 {e}")
            return False

    def hometown_ensure_material(self):
        # 服务端不校验图片内容/大小 (实测 8 字节伪JPEG即返回上传成功),
        # 故内置一个最小合法 JPEG 字节, 无需任何外部下载或素材文件。
        if os.path.exists(HOMETOWN_MATERIAL_PATH) and os.path.getsize(HOMETOWN_MATERIAL_PATH) > 8:
            return True
        try:
            with open(HOMETOWN_MATERIAL_PATH, "wb") as f:
                f.write(HOMETOWN_MATERIAL_BYTES)
            return True
        except Exception as e:
            self.log(f"家乡打卡: 素材写入失败 {e}")
            return False

    def hometown_upload(self, token):
        self.hometown_uploaded_files = []
        if not self.hometown_ensure_material():
            self.log("家乡打卡: 上传失败，素材文件不存在且下载失败")
            return False
        if not token:
            self.log("家乡打卡: 上传失败，Token为空")
            return False
        try:
            t_ = str(int(time.time() * 1000))
            fsize = os.path.getsize(HOMETOWN_MATERIAL_PATH)
            batch_no = datetime.now().strftime("%Y%m%d%H%M%S")
            file_info_plain = (
                '{"spaceType":"0","directoryId":"0","batchNo":"' + batch_no +
                '","fileName":"8648","fileSize":' + str(fsize) + ',"fileType":"1"}'
            )
            file_info = self.hometown_aes_encrypt(file_info_plain, token[:16].ljust(16)[:16])
            rs = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
            unique_id = f"{t_}_{rs}"
            with open(HOMETOWN_MATERIAL_PATH, "rb") as fh:
                files = {
                    "uniqueId": (None, unique_id),
                    "accessToken": (None, token),
                    "fileName": (None, "8648"),
                    "psToken": (None, "undefined"),
                    "fileSize": (None, str(fsize)),
                    "totalPart": (None, "1"),
                    "partSize": (None, str(fsize)),
                    "partIndex": (None, "1"),
                    "channel": (None, "wocloud"),
                    "directoryId": (None, "0"),
                    "fileInfo": (None, file_info),
                    "file": ("8648", fh, "image/jpeg"),
                }
                r = self.session.post(
                    "https://du.smartont.net:8443/openapi/client/upload2C",
                    files=files,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
                        "Accept-Encoding": "gzip, deflate, br, zstd",
                        "origin": "https://pan.wo.cn",
                        "referer": "https://pan.wo.cn/",
                        "accept-language": "zh-CN,zh;q=0.9",
                        "sec-fetch-site": "same-site",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-dest": "empty",
                    },
                    timeout=60,
                    verify=False,
                )
            try:
                result = r.json()
            except ValueError:
                self.log(f"家乡打卡: 文件上传 HTTP {r.status_code}，返回非JSON")
                return False
            code = str(result.get("code", (result.get("meta") or {}).get("code", "")))
            success = r.status_code == 200 and code in ("0000", "0", "200")
            fid = (result.get("data") or {}).get("fid")
            if success and fid:
                self.hometown_uploaded_files.append({"id": fid, "type": "1"})
            self.log(f"家乡打卡: 文件上传 {'成功' if success else '失败'} {response_summary(result)}")
            return success
        except Exception as e:
            self.log(f"家乡打卡: 文件上传失败 {e}")
            return False

    def hometown_lottery(self, token):
        if not token:
            return
        ts_info = self.hometown_get_activity_timestamp(token)
        if not ts_info:
            self.log("家乡打卡: 抽奖失败，无法获取时间戳")
            return
        payload = {
            "activityId": HOMETOWN_LOTTERY_ACTIVITY_ID,
            "nonce": ts_info.get("nonce", ""),
            "timestamp": ts_info.get("timestamp", 0),
        }
        payload["sign"] = self.hometown_sign_payload(payload)
        try:
            res = self.session.post(
                "https://panservice.mail.wo.cn/activity/lottery",
                headers=self.hometown_headers(token),
                json=payload,
                timeout=15,
            ).json()
            if str((res.get("meta") or {}).get("code")) == "200":
                result = res.get("result") or {}
                prize = result.get("prizeName", "未获取到奖品信息")
                self.log(f"家乡打卡: 抽奖结果 {prize}", notify=True)
                times = result.get("lotteryTimes", 0)
                if times and int(times) > 0:
                    self.log(f"家乡打卡: 剩余抽奖次数 {times}")
            else:
                self.log(f"家乡打卡: 抽奖失败 {(res.get('meta') or {}).get('message', '未知错误')}")
        except Exception as e:
            self.log(f"家乡打卡: 抽奖出错 {e}")

    def hometown_cleanup_uploaded(self):
        # Only delete file IDs returned by this run's upload.
        try:
            matched = getattr(self, "hometown_uploaded_files", [])
            if matched:
                deleted = self.delete_root_files_cloud(matched, "0")
                self.log(f"家乡打卡: 已清理本次上传文件 {deleted} 个")
                self.hometown_uploaded_files = []
        except Exception as e:
            self.log(f"家乡打卡: 清理上传文件异常 {e}")

    def hometown_task(self, token):
        self.log("==== 云盘家乡打卡 ====")
        province_code, province_name = self.hometown_query_location(token)
        if not province_code:
            return
        ticket = self.hometown_get_base_ticket(token)
        if not self.hometown_open_activity(token, ticket, province_code, province_name):
            return
        self.log("家乡打卡: 开始文件上传...")
        uploaded = self.hometown_upload(token)
        time.sleep(5)
        self.hometown_lottery(token)
        if uploaded:
            self.hometown_cleanup_uploaded()

    def getTicketByNative_sec(self):
        for attempt in range(1, 4):
            try:
                url = f"https://m.client.10010.com/edop_ng/getTicketByNative?token={self.ecs_token}&appId={EDOP_APPID_SECURITY}"
                city_code = ""
                cookie_str = f"PvSessionId={datetime.now().strftime('%Y%m%d%H%M%S')}{self.unicomTokenId};c_mobile={self.account_mobile}; c_version=iphone_c@11.0800; city=036|{city_code}|90063345|-99;devicedId={self.unicomTokenId}; ecs_token={self.ecs_token};t3_token="
                headers = {
                    "Cookie": cookie_str,
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "ChinaUnicom4.x/12.3.1 (com.chinaunicom.mobilebusiness; build:77; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.0301}",
                    "Accept-Language": "zh-Hans-CN;q=1.0"
                }
                res = self.session.get(url, headers=headers, timeout=10)
                if res.status_code != 200:
                    self.log(f"安全管家: getTicketByNative_sec http请求失败 {res.status_code}")
                    return
                try:
                    result = res.json()
                except:
                    self.log(f"安全管家: getTicketByNative_sec json解析失败: {res.text[:100]}")
                    return
                self.sec_ticket1 = result.get('ticket')
                if self.sec_ticket1:
                    return
                else:
                    self.log(f"安全管家: getTicketByNative_sec 失败 - {result}")
            except Exception as e:
                err_msg = str(e)
                if attempt < 3 and os.environ.get("UNICOM_PROXY_API") and ("Max retries exceeded" in err_msg or "timed out" in err_msg.lower() or "connection" in err_msg.lower() or "SOCKS" in err_msg):
                    self.log(f"安全管家: getTicketByNative_sec 第{attempt}次异常触发故障转移: {err_msg}")
                    self.failover_proxy()
                    continue
                self.log(f"安全管家: getTicketByNative_sec 第{attempt}次重试 - 异常: {e}")
                time.sleep(2)

    def getAuthToken_sec(self):
        if not getattr(self, 'sec_ticket1', None):
            self.log("安全管家 getAuthToken_sec 缺少 ticket1，跳过")
            return
        try:
            url = f"https://uca.wo116114.com/api/v1/auth/ticket?product_line=uasp&entry_point=h5&entry_point_id={EDOP_APPID_SECURITY}"
            headers = {
                "User-Agent": "ChinaUnicom4.x/12.3.1 (com.chinaunicom.mobilebusiness; build:77; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.0301}",
                "Content-Type": "application/json",
                "clientType": "uasp_unicom_applet"
            }
            data = { "productId": "", "type": 1, "ticket": self.sec_ticket1 }
            res = self.session.post(url, json=data, headers=headers).json()
            if res.get('data'):
                self.sec_token = res['data'].get('access_token')
            else:
                self.log(f"安全管家: getAuthToken_sec 失败 - {res}")
        except Exception as e:
            self.log(f"安全管家: getAuthToken_sec 异常: {e}")

    def getTicketForJF_sec(self):
        if not getattr(self, 'sec_token', None):
            self.log("安全管家 getTicketForJF_sec 缺少 token，跳过")
            return
        try:
            url1 = f"https://uca.wo116114.com/api/v1/auth/getTicket?product_line=uasp&entry_point=h5&entry_point_id={EDOP_APPID_SECURITY}"
            headers1 = {
                "User-Agent": "ChinaUnicom4.x/12.3.1 (com.chinaunicom.mobilebusiness; build:77; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.0301}",
                "Content-Type": "application/json",
                "auth-sa-token": self.sec_token,
                "clientType": "uasp_unicom_applet"
            }
            data1 = { "productId": "91311616", "phone": self.account_mobile }
            res1 = self.session.post(url1, json=data1, headers=headers1).json()
            if res1.get('data'):
                self.sec_ticket = res1['data'].get('ticket')
            else:
                self.log("安全管家获取积分票据失败")
                return
            url2 = "https://m.jf.10010.com/jf-external-application/page/query"
            headers2 = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301};ltst;OSVersion/16.6",
                "partnersid": "1702",
                "ticket": unquote(self.sec_ticket),
                "clienttype": "uasp_unicom_applet",
            }
            if hasattr(self, 'sec_jeaId'):
                headers2["Cookie"] = f"_jea_id={self.sec_jeaId}"
            res2 = self.session.post(url2, json={"activityId": "s747395186896173056", "partnersId": "1702"}, headers=headers2)
            for cookie in self.session.cookies:
                if cookie.name == '_jea_id':
                    self.sec_jeaId = cookie.value
            if 'Set-Cookie' in res2.headers:
                match = re.search(r'_jea_id=([^;]+)', res2.headers['Set-Cookie'])
                if match:
                    self.sec_jeaId = match.group(1)
        except Exception as e:
            self.log(f"安全管家: getTicketForJF_sec 异常: {e}")

    def get_secret_key_sec(self, silent=False):
        if getattr(self, 'sec_secretKey', None):
            return self.sec_secretKey
        if not getattr(self, 'sec_ticket', None):
            return None
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301};ltst;OSVersion/16.6",
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Origin': 'https://m.jf.10010.com',
            'Host': 'm.jf.10010.com',
            'clienttype': 'uasp_unicom_applet',
            'partnersid': '1702',
            'ticket': unquote(self.sec_ticket),
        }
        if hasattr(self, 'sec_jeaId') and self.sec_jeaId:
            headers['Cookie'] = f"_jea_id={self.sec_jeaId};"
        try:
            res = self.session.get("https://m.jf.10010.com/jf-external-application/jftask/getSecretKey", headers=headers, timeout=10).json()
            secret = res.get('data', {}).get('secretKey')
            if res.get('code') == '0000' and secret:
                self.sec_secretKey = secret.encode('utf-8')
                if not silent:
                    self.log("secretKey 获取成功")
                return self.sec_secretKey
            self.log(f"安全管家: getSecretKey 失败: {res}")
        except Exception as e:
            self.log(f"安全管家: getSecretKey 异常: {e}")
        return None

    def build_signature_headers_sec(self):
        secret_key = self.get_secret_key_sec()
        if not secret_key:
            return {}
        request_ts = str(round(time.time() * 1000))
        nonce = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        signature = hmac.new(
            secret_key, f"{nonce}{request_ts}".encode('utf-8'), hashlib.sha256,
        ).hexdigest()
        return {
            'x-request-timestamp': request_ts,
            'x-request-nonce': nonce,
            'x-request-signature': signature,
        }

    def sec_uca_post(self, url_path, body):
        try:
            headers = {
                "clientType": "uasp_unicom_applet",
                "auth-sa-token": self.sec_token,
                "Content-Type": "application/json",
                "Accept": "*",
                "User-Agent": "ChinaUnicom4.x/12.3.1 (com.chinaunicom.mobilebusiness; build:77; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.0301}"
            }
            return self.session.post(url_path, json=body, headers=headers, timeout=10).json()
        except Exception as e:
            self.log(f"安全管家: uca_post 异常: {e}")
            return None

    def addToBlacklist_sec(self):
        url = "https://uca.wo116114.com/sjgj/woAssistant/umm/configs/v1/config?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        self.sec_uca_post(url, {
            "productId": "91242950", "operationType": 1, "type": 1,
            "contents": [{"checked": True, "configTime": None, "nickname": None, "contentTag": "疑似诈骗", "content": "13088330789"}]
        })
        time.sleep(2)
        self.sec_uca_post(url, {
            "productId": "91242950", "blacklistSource": 0, "type": 1, "operationType": 0,
            "contents": [{"contentTag": "疑似诈骗", "content": "13088330789"}]
        })

    def markPhoneNumber_sec(self):
        url = "https://uca.wo116114.com/sjgj/unicomAssistant/uasp/configs/v1/addressBook/saveTagPhone?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        self.sec_uca_post(url, {"productId": "91311616", "status": 0, "tagIds": [26], "tagPhoneNo": "13088330789"})

    def syncAddressBook_sec(self):
        url = f"https://uca.wo116114.com/sjgj/unicomAssistant/uasp/configs/v1/addressBookBatchConfig?product_line=uasp&entry_point=h5&entry_point_id={EDOP_APPID_SECURITY}"
        self.sec_uca_post(url, {
            "opType": "1", "productId": "91311616",
            "addressBookDTOList": [{"addressBookName": "可乐", "addressBookPhoneNo": "13105750575"}]
        })

    def setInterceptionRules_sec(self):
        url = "https://uca.wo116114.com/sjgj/woAssistant/umm/configs/v1/config?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        self.sec_uca_post(url, {
            "productId": "91311616", "type": 3, "operationType": 0,
            "contents": [{"icon": "alerting", "content": "1", "contentName": "响一声", "contentTag": "8", "name": "rings-once"}]
        })
        time.sleep(2)
        self.sec_uca_post(url, {
            "productId": "91311616", "type": 3, "operationType": 0,
            "contents": [{"icon": "alerting", "content": "0", "contentName": "响一声", "contentTag": "8", "name": "rings-once"}]
        })

    def viewWeeklyReport_sec(self):
        base = "https://uca.wo116114.com/sjgj/unicomAssistant/uasp"
        body = {"productId": "91311616"}
        self.sec_uca_post(f"{base}/configs/v1/weeklySwitchStatus?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6", body)
        self.sec_uca_post(f"{base}/report/v1/queryKeyData?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6", body)
        self.sec_uca_post(f"{base}/report/v1/weeklySummary?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6", body)

    def zhushou_sec(self):
        try:
            headers = {
                "auth-sa-token": self.sec_token, "token": self.sec_token,
                "Content-Type": "application/json", "Accept": "*",
                "User-Agent": "ChinaUnicom4.x/12.3.1 (com.chinaunicom.mobilebusiness; build:77; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.0301}"
            }
            self.session.post("https://ims.wo116114.com/api/AiAssistant/autoReply",
                              json={"history": [], "message": "1", "promptId": 10000}, headers=headers, timeout=10)
        except Exception as e:
            self.log(f"安全管家: 智能助手异常: {e}")

    def daijie_sec(self):
        try:
            headers = {
                "auth-sa-token": self.sec_token, "token": self.sec_token, "Authorization": self.sec_token,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B)"
            }
            self.session.post("https://ims.wo116114.com/api/Assistant/assis_save", json={
                "page_type": 1, "old_ainumber": "XF0", "level": 3, "dialog": "0",
                "opertype": 1, "videoimage": "", "speechtype": "06", "ainumber": "BD1"
            }, headers=headers, timeout=10)
        except Exception as e:
            self.log(f"安全管家: 代接助理异常: {e}")

    def anquanfen_sec(self):
        url = "https://uca.wo116114.com/sjgj/woAssistant/umm/configs/v1/config?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        score_url = "https://uca.wo116114.com/sjgj/unicomAssistant/uasp/report/v1/queryScore?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        off_body = {"productId": "91351080", "type": 3, "operationType": 0,
                    "contents": [{"icon": "phone-fraud", "content": "1", "contentName": "疑似诈骗", "contentTag": "0", "name": "fraud"}]}
        on_body = {"productId": "91351080", "type": 3, "operationType": 0,
                   "contents": [{"contentTag": "0", "content": "0"}]}
        self.sec_uca_post(url, off_body)
        time.sleep(2)
        self.sec_uca_post(score_url, {"productId": "91311616"})
        time.sleep(2)
        self.sec_uca_post(url, on_body)
        time.sleep(2)
        self.sec_uca_post(score_url, {"productId": "91311616"})
        time.sleep(2)
        self.sec_uca_post(url, off_body)

    def haoduan_sec(self):
        url = "https://uca.wo116114.com/sjgj/woAssistant/umm/configs/v1/config?product_line=uasp&entry_point=h5&entry_point_id=wxdefbc1986dc757a6"
        item_off = {"checked": True, "content": "1", "contentName": "拦截400开头的10位特服号码", "contentTag": "1"}
        item_on = {"checked": False, "content": "0", "contentName": "拦截400开头的10位特服号码", "contentTag": "1"}
        base = {"productId": "91351080", "type": 7, "operationType": 0}
        self.sec_uca_post(url, {**base, "contents": [item_off]})
        time.sleep(2)
        self.sec_uca_post(url, {**base, "contents": [item_on]})
        time.sleep(2)
        self.sec_uca_post(url, {**base, "contents": [item_off]})

    def ojbk_sec(self, taskCode):
        try:
            url = "https://m.jf.10010.com/jf-external-application/jftask/taskFinish"
            headers = self._sec_jf_headers()
            self.session.post(url, json={"taskCode": taskCode}, headers=headers, timeout=10)
        except Exception as e:
            self.log(f"安全管家: 活动浏览异常: {e}")

    def sec_wo_ai_headers(self, use_mobile=False, override_token=None):
        ua_pc = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
            "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI "
            "MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) "
            "UnifiedPCWindowsWechat(0xf2541818) XWEB/19201 miniProgram/wx1e83eef922822ee0"
        )
        ua_mobile = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            "MicroMessenger/8.0.69(0x1800452f) NetType/WIFI Language/zh_CN "
            "miniProgram/wx1e83eef922822ee0"
        )
        return {
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "https://ai.wo.cn",
            "Authorization": override_token or self.sec_token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": ua_mobile if use_mobile else ua_pc,
        }

    def sec_get_knowledge_id(self):
        try:
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/knowledge/getKnowledgeList",
                headers=self.sec_wo_ai_headers(),
                data=json.dumps({"appType": 1}),
                timeout=10,
            )
            res = response.json()
            if res.get("code") == 0 and res.get("data"):
                return res["data"][0].get("id")
            self.log(f"获取知识库ID失败：{res.get('msg') or res}")
        except Exception as e:
            self.log(f"获取知识库ID异常：{e}")
        return ""

    def upload_knowledge_file_sec(self):
        try:
            kid = self.sec_get_knowledge_id()
            if not kid:
                return False
            upload_headers = {
                k: v for k, v in self.sec_wo_ai_headers().items()
                if k.lower() != "content-type"
            }
            files = {"file": ("task_upload.txt", b" ", "text/plain")}
            data = {
                "knowledgeId": kid,
                "fileName": "task_upload.txt",
                "fileType": "text/plain",
                "fileSize": "1",
                "currentPartSize": "1",
                "currentIndex": "1",
                "totalPart": "1",
                "spaceType": "0",
            }
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/knowledge/uploadLocalFileToKnowledge",
                headers=upload_headers,
                files=files,
                data=data,
                timeout=15,
            )
            res = response.json()
            if res.get("code") == 0:
                self.log("上传知识库文件成功")
                return True
            self.log(f"上传知识库文件失败：{res.get('msg') or res}")
            return False
        except Exception as e:
            self.log(f"安全管家: 上传知识库文件异常: {e}")
            return False

    def sec_get_chat_list(self):
        try:
            headers = self.sec_wo_ai_headers()
            headers["Referer"] = "https://ai.wo.cn/wxMini"
            response = self.session.get(
                "https://ai.wo.cn/web-tongtong/historyChat/list",
                headers=headers,
                timeout=10,
            )
            res = response.json()
            if res.get("code") == 0:
                return ((res.get("data") or {}).get("content") or [])
            if res.get("msg"):
                self.log(f"获取AI对话历史失败：{res.get('msg')}")
        except Exception as e:
            self.log(f"获取AI对话历史异常：{e}")
        return []

    def sec_send_ai_chat(self):
        try:
            session_id = f"mmru{''.join(str(random.randint(0, 9)) for _ in range(10))}"
            request_id = f"rqid_mmru{''.join(str(random.randint(0, 9)) for _ in range(10))}"
            headers = self.sec_wo_ai_headers(use_mobile=True)
            headers["Accept"] = "text/event-stream"
            headers["Referer"] = "https://ai.wo.cn/wxMini/psychologicalApp/chat?id=1&type=ruole"
            payload = {
                "modelKey": "87e622d9e488",
                "message": "帮我推荐1个必吃饭店",
                "deepThink": False,
                "webSearch": False,
                "attachments": [],
                "imgSize": 0,
                "sessionId": session_id,
                "requestId": request_id,
                "promptKey": "",
                "knowledgeId": "",
                "ragSearch": False,
                "moduleType": 12,
            }
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/chat/chatReplyV2",
                headers=headers,
                data=json.dumps(payload),
                timeout=60,
                stream=True,
            )
            for _ in response.iter_lines():
                pass
            if response.ok:
                self.log("已发送AI对话")
                return True
            self.log(f"发送AI对话失败：HTTP {response.status_code}")
        except Exception as e:
            self.log(f"发送AI对话异常：{e}")
        return False

    def sec_get_share_key(self, session_id):
        try:
            headers = self.sec_wo_ai_headers()
            headers["Referer"] = "https://ai.wo.cn/wxMini"
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/historyChat/shareDetail",
                headers=headers,
                data=json.dumps({"sessionId": session_id}),
                timeout=10,
            )
            res = response.json()
            if res.get("code") == 0 and res.get("data"):
                return str(res["data"])
            self.log(f"获取分享key失败：{res.get('msg') or res}")
        except Exception as e:
            self.log(f"获取分享key异常：{e}")
        return ""

    def sec_view_share_detail(self, key, view_token):
        try:
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/historyChat/getShareDetail",
                headers=self.sec_wo_ai_headers(use_mobile=True, override_token=view_token),
                data=json.dumps({"key": key, "pageSize": 10, "pageNum": 1}),
                timeout=10,
            )
            res = response.json()
            if res.get("code") == 0:
                self.log("查看分享对话成功")
                return True
            self.log(f"查看分享对话失败：{res.get('msg') or res}")
        except Exception as e:
            self.log(f"查看分享对话异常：{e}")
        return False

    def share_ai_chat_sec(self, taskCode=""):
        try:
            content = self.sec_get_chat_list()
            if not content:
                self.log("暂无AI对话历史，先发送一条对话...")
                if not self.sec_send_ai_chat():
                    return False
                time.sleep(2)
                content = self.sec_get_chat_list()
            if not content:
                self.log("仍无AI对话历史，跳过分享任务")
                return False
            session_id = content[0].get("chatSessionId", "")
            if not session_id:
                self.log("获取分享key失败：缺少sessionId")
                return False
            share_key = self.sec_get_share_key(session_id)
            if not share_key:
                return False
            self.sec_ai_share_key = share_key
            if taskCode:
                self.sec_share_task_code = taskCode
            short_key = share_key[:8] + "..." if len(share_key) > 8 else share_key
            self.log(f"AI对话分享key获取成功: {short_key}")
            return True
        except Exception as e:
            self.log(f"安全管家: 分享AI对话异常: {e}")
            return False

    def role_chat_sec(self):
        try:
            session_id = f"mmrp{''.join(str(random.randint(0, 9)) for _ in range(10))}"
            request_id = f"rqid_mmrp{''.join(str(random.randint(0, 9)) for _ in range(10))}"
            headers = self.sec_wo_ai_headers()
            headers["Accept"] = "text/event-stream"
            headers["Referer"] = "https://ai.wo.cn/wxMini/psychologicalApp/chat?id=1&type=ruole"
            response = self.session.post(
                "https://ai.wo.cn/web-tongtong/lxzn/chat",
                headers=headers,
                data=json.dumps({
                    "sessionId": session_id,
                    "requestId": request_id,
                    "roleId": 1,
                    "message": "我有拖延症，好多事情不想做。",
                }),
                timeout=60,
                stream=True,
            )
            for _ in response.iter_lines():
                pass
            if not response.ok:
                self.log(f"角色助手对话失败：HTTP {response.status_code}")
                return False
            self.log("角色助手对话完成")
            return True
        except Exception as e:
            self.log(f"安全管家: 角色助手对话异常: {e}")
            return False

    def sec_finalize_share_ai_task(self):
        if not self.sec_share_task_code:
            return False
        self.sec_track_pending_claim(self.sec_share_task_code, self.sec_share_task_name)
        latest_task = self.sec_refresh_task_snapshot(
            self.sec_share_task_code,
            self.sec_share_task_name,
            retries=5,
            delay=2,
        )
        if not latest_task:
            self.sec_refresh_security_context(refresh_secret=True)
            latest_task = self.sec_refresh_task_snapshot(
                self.sec_share_task_code,
                self.sec_share_task_name,
                retries=5,
                delay=2,
            )
        if not latest_task:
            self.log("联通助理-分享AI助手对话：互看后未查询到任务状态")
            return False
        finish_count, need_count, finish_text = self.sec_parse_task(latest_task)
        if finish_text == "待领取" or (need_count > 0 and finish_count >= need_count):
            self.log("联通助理-分享AI助手对话：互看完成，尝试领取奖励")
            receive_state = self.receivePoints_sec(self.sec_share_task_code, self.sec_share_task_name)
            if receive_state in ("received", "auto"):
                self.getUserInfo_sec()
                return True
            if receive_state == "pending":
                self.sec_recover_pending_claims(rounds=2, delay=6, refresh_context=True)
                if self.sec_share_task_code not in self.sec_pending_claim_tasks:
                    return True
        self.log(f"联通助理-分享AI助手对话：互看后状态 {finish_count}/{need_count} - {finish_text}")
        return False

    def _sec_jf_headers(self, with_signature=False):
        headers = {
            "ticket": unquote(self.sec_ticket),
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301};ltst;OSVersion/16.6",
            "partnersid": "1702",
            "clienttype": "uasp_unicom_applet",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://m.jf.10010.com",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if hasattr(self, 'sec_jeaId') and self.sec_jeaId:
            headers["Cookie"] = f"_jea_id={self.sec_jeaId};"
        if with_signature:
            headers.update(self.build_signature_headers_sec())
        return headers

    def update_sec_jea_id(self, response=None):
        jea_id = ""
        if response is not None:
            cookie = response.headers.get("Set-Cookie", "")
            match = re.search(r"_jea_id=([^;]+)", cookie)
            if match:
                jea_id = match.group(1)
        if not jea_id:
            for cookie_item in self.session.cookies:
                if cookie_item.name == "_jea_id":
                    jea_id = cookie_item.value
                    break
        if jea_id:
            self.sec_jeaId = jea_id
        return jea_id

    def sec_query_task_list(self):
        url = "https://m.jf.10010.com/jf-external-application/jftask/taskDetail"
        last_error = ""
        for attempt in range(1, 4):
            response = None
            try:
                response = self.session.post(url, json={}, headers=self._sec_jf_headers(), timeout=15)
                self.update_sec_jea_id(response)
                res = response.json()
                task_detail = ((res or {}).get("data") or {}).get("taskDetail") or {}
                return task_detail.get("taskList", [])
            except ValueError:
                preview = ((response.text if response is not None else "") or "").strip().replace("\n", " ")
                last_error = f"非JSON响应[{attempt}/3]: {preview[:60] or 'empty'}"
            except Exception as e:
                last_error = str(e)
            if attempt < 3:
                time.sleep(2)
        self.log(f"联通助理任务列表查询异常: {last_error}")
        return []

    def sec_parse_task(self, task):
        finish_count = safe_int(task.get("finishCount", 0))
        need_count = safe_int(task.get("needCount", 0))
        finish_text = task.get("finishText") or task.get("taskStatusName") or task.get("taskStatusDesc") or "未知状态"
        return finish_count, need_count, finish_text

    def sec_supports_delayed_claim(self, task_name):
        delayed_keywords = (
            "上传知识库文件",
            "分享AI助手对话",
            "角色助手对话",
        )
        return any(keyword in task_name for keyword in delayed_keywords)

    def sec_track_pending_claim(self, task_code, task_name):
        if task_code and task_name and self.sec_supports_delayed_claim(task_name):
            self.sec_pending_claim_tasks[task_code] = task_name

    def sec_untrack_pending_claim(self, task_code):
        if task_code:
            self.sec_pending_claim_tasks.pop(task_code, None)

    def sec_refresh_security_context(self, refresh_secret=False):
        try:
            self.sec_ticket1 = ""
            self.sec_token = ""
            self.sec_ticket = ""
            self.getTicketByNative_sec()
            if not getattr(self, 'sec_ticket1', None):
                return False
            self.getAuthToken_sec()
            if not getattr(self, 'sec_token', None):
                return False
            self.getTicketForJF_sec()
            if not getattr(self, 'sec_ticket', None):
                return False
            if refresh_secret:
                self.sec_secretKey = None
                if not self.get_secret_key_sec(silent=True):
                    return False
            return True
        except Exception as e:
            self.log(f"联通助理上下文刷新异常: {e}")
            return False

    def sec_get_task_snapshot(self, task_code="", task_name=""):
        for task in self.sec_query_task_list():
            if task_code and task.get("taskCode") == task_code:
                return task
            if task_name and task.get("taskName") == task_name:
                return task
        return None

    def sec_refresh_task_snapshot(self, task_code, task_name, retries=3, delay=2):
        latest_task = None
        for attempt in range(retries):
            if attempt:
                time.sleep(delay)
            latest_task = self.sec_get_task_snapshot(task_code, task_name)
            if not latest_task:
                continue
            finish_count, need_count, finish_text = self.sec_parse_task(latest_task)
            if finish_text == "待领取" or (need_count > 0 and finish_count >= need_count):
                return latest_task
        return latest_task

    def sec_should_manual_finish(self, task_name):
        manual_keywords = (
            "新增亲情守护成员",
            "新增宽带绑定",
            "语音提醒",
            "反诈险领取",
            "设置日程提醒",
        )
        return any(keyword in task_name for keyword in manual_keywords)

    def sec_wait_seconds(self, task_name):
        if any(keyword in task_name for keyword in ("上传知识库文件", "分享AI助手对话", "角色助手对话")):
            return 5
        if any(keyword in task_name for keyword in ("添加黑名单", "骚扰拦截设置", "安全分提升", "号段拦截")):
            return 8
        return 4

    def receivePoints_sec(self, taskCode, taskName=""):
        url = "https://m.jf.10010.com/jf-external-application/jftask/receive"
        last_error = ""
        for attempt in range(1, 3):
            response = None
            try:
                headers = self._sec_jf_headers(with_signature=True)
                response = self.session.post(url, json={"taskCode": taskCode}, headers=headers, timeout=10)
                self.update_sec_jea_id(response)
                res = response.json()
                score = str((res.get("data") or {}).get("score") or "").strip()
                msg = str(res.get("msg") or "").strip()
                if score:
                    self.sec_untrack_pending_claim(taskCode)
                    self.log(f"安全管家: 领取{score}成功", notify=True)
                    return "received"
                if "任务未完成" in msg or "不可领取" in msg:
                    self.log("领取任务未完成")
                    return "pending"
                if "自动发放" in msg or "已领取" in msg:
                    self.sec_untrack_pending_claim(taskCode)
                    self.log("任务已完成且奖励已领取")
                    return "auto"
                if msg:
                    self.log(f"领取失败：{msg}")
                    return "failed"
                self.log(f"领取失败：{res}")
                return "failed"
            except ValueError:
                preview = ((response.text if response is not None else "") or "").strip().replace("\n", " ")
                last_error = f"非JSON响应[{attempt}/2]: {preview[:60] or 'empty'}"
            except Exception as e:
                last_error = str(e)
            if attempt < 2:
                time.sleep(2)
        self.log(f"安全管家: 领取积分异常: {last_error}")
        return "error"

    def finishTask_sec(self, taskCode, taskName):
        try:
            url = "https://m.jf.10010.com/jf-external-application/jftask/toFinish"
            headers = self._sec_jf_headers(with_signature=True)
            response = self.session.post(url, json={"taskCode": taskCode}, headers=headers, timeout=10)
            self.update_sec_jea_id(response)
            action_map = {
                "添加黑名单": self.addToBlacklist_sec,
                "号码标记": self.markPhoneNumber_sec,
                "同步通讯录": self.syncAddressBook_sec,
                "骚扰拦截设置": self.setInterceptionRules_sec,
                "智能助手": self.zhushou_sec,
                "代接助理": self.daijie_sec,
                "安全分": self.anquanfen_sec,
                "号段拦截": self.haoduan_sec,
                "查看周报": self.viewWeeklyReport_sec,
                "活动浏览": lambda: self.ojbk_sec(taskCode),
                "上传知识库文件": self.upload_knowledge_file_sec,
                "分享AI助手对话": lambda: self.share_ai_chat_sec(taskCode),
                "角色助手对话": self.role_chat_sec,
            }
            for key, action in action_map.items():
                if key in taskName:
                    result = action()
                    return False if result is False else True
            self.log(f"任务 {taskName} 需要手动完成")
            return False
        except Exception as e:
            self.log(f"安全管家: finishTask异常: {e}")
            return False

    def signIn_sec(self, taskCode):
        try:
            url = "https://m.jf.10010.com/jf-external-application/jftask/sign"
            headers = self._sec_jf_headers(with_signature=True)
            response = self.session.post(url, json={"taskCode": taskCode}, headers=headers, timeout=10)
            self.update_sec_jea_id(response)
            res = response.json()
            if res.get("code") == "0000":
                return True
            self.log(f"签到失败：{res.get('msg') if res else '状态未知'}")
            return False
        except Exception as e:
            self.log(f"安全管家: 签到异常: {e}")
            return False

    def executeAllTasks_sec(self):
        try:
            task_list = self.sec_query_task_list()
            if not task_list:
                self.log("联通助理任务列表查询失败")
                return
            for task in task_list:
                task_name = task.get("taskName", "")
                task_code = task.get("taskCode", "")
                finish_count, need_count, finish_text = self.sec_parse_task(task)
                self.log(f"{task_name}：{finish_count}/{need_count} - {finish_text}")
                if not task_code or need_count <= 0:
                    self.log("---------------------")
                    continue
                if finish_count >= need_count:
                    if finish_text == "待领取":
                        time.sleep(2)
                        receive_state = self.receivePoints_sec(task_code, task_name)
                        if receive_state == "pending":
                            self.sec_track_pending_claim(task_code, task_name)
                    else:
                        self.log("任务已完成且奖励已领取")
                    self.log("---------------------")
                    continue
                remaining = max(need_count - finish_count, 1)
                self.log(f"任务未完成，需要再执行 {remaining} 次")
                if self.sec_should_manual_finish(task_name):
                    self.log(f"任务 {task_name} 需要手动完成")
                    self.log("---------------------")
                    continue
                for i in range(remaining):
                    try:
                        if i:
                            time.sleep(2)
                        handled = self.signIn_sec(task_code) if "签到" in task_name else self.finishTask_sec(task_code, task_name)
                        if not handled:
                            break
                        wait_seconds = self.sec_wait_seconds(task_name)
                        if wait_seconds > 0:
                            time.sleep(wait_seconds)
                        latest_task = self.sec_refresh_task_snapshot(task_code, task_name, retries=3, delay=2)
                        if latest_task:
                            finish_count, need_count, finish_text = self.sec_parse_task(latest_task)
                        if not latest_task or (finish_text != "待领取" and finish_count < need_count):
                            self.log(f"{task_name}：已提交操作，服务端进度仍为 {finish_count}/{need_count}")
                            self.sec_track_pending_claim(task_code, task_name)
                            break
                        self.log(f"第 {i + 1} 次执行{task_name}已确认完成")
                        receive_state = self.receivePoints_sec(task_code, task_name)
                        if receive_state == "pending":
                            self.sec_track_pending_claim(task_code, task_name)
                        if receive_state in ("received", "auto"):
                            break
                        if need_count > 0 and finish_count >= need_count:
                            self.log("任务已完成且奖励已领取")
                            break
                    except Exception as e:
                        self.log(f"执行 {task_name} 失败：{e}")
                        break
                self.log("---------------------")
        except Exception as e:
            self.log(f"联通助理任务执行异常: {e}")

    def getUserInfo_sec(self):
        url = "https://m.jf.10010.com/jf-external-application/jftask/userInfo"
        last_error = ""
        for attempt in range(1, 3):
            response = None
            try:
                headers = self._sec_jf_headers()
                response = self.session.post(url, json={}, headers=headers, timeout=10)
                self.update_sec_jea_id(response)
                res = response.json()
                if not res or res.get('code') != '0000' or not res.get('data'):
                    self.log(f"安全管家: 查询积分失败: {res.get('msg') if res else '无响应'}")
                    return
                current = int(res['data'].get('availableScore', 0))
                today = res['data'].get('todayEarnScore', 0)
                if not hasattr(self, 'sec_oldJFPoints') or self.sec_oldJFPoints is None:
                    self.sec_oldJFPoints = current
                    self.log(f"当前积分：{current}，今日已赚 {today}")
                else:
                    gained = current - self.sec_oldJFPoints
                    user_label = mask_str(self.mobile) if self.mobile else f"账号[{self.index}]"
                    self.log(f"安全管家: 用户{user_label}积分变动：{self.sec_oldJFPoints} → {current} | 新增: {gained}", notify=True)
                return
            except ValueError:
                preview = ((response.text if response is not None else "") or "").strip().replace("\n", " ")
                last_error = f"非JSON响应[{attempt}/2]: {preview[:60] or 'empty'}"
            except Exception as e:
                last_error = str(e)
            if attempt < 2:
                time.sleep(2)
        self.log(f"安全管家: 查询积分异常: {last_error}")

    def sec_recover_pending_claims(self, rounds=2, delay=12, refresh_context=False):
        if not self.sec_pending_claim_tasks:
            return False
        recovered = False
        last_status_map = {}
        self.log(f"联通助理：待补领任务 {len(self.sec_pending_claim_tasks)} 个，开始补查")
        for attempt in range(rounds):
            if attempt:
                time.sleep(delay)
            if not self.sec_pending_claim_tasks:
                break
            if refresh_context and not self.sec_refresh_security_context(refresh_secret=True):
                continue
            for task_code, task_name in list(self.sec_pending_claim_tasks.items()):
                latest_task = self.sec_refresh_task_snapshot(task_code, task_name, retries=3, delay=2)
                if not latest_task:
                    status_key = "missing"
                    if last_status_map.get(task_code) != status_key:
                        self.log(f"{task_name}：补查未取到任务状态")
                        last_status_map[task_code] = status_key
                    continue
                finish_count, need_count, finish_text = self.sec_parse_task(latest_task)
                if finish_text == "待领取" or (need_count > 0 and finish_count >= need_count):
                    self.log(f"{task_name}：补查后尝试领取")
                    receive_state = self.receivePoints_sec(task_code, task_name)
                    if receive_state in ("received", "auto"):
                        recovered = True
                        last_status_map.pop(task_code, None)
                        continue
                else:
                    status_key = f"{finish_count}/{need_count}-{finish_text}"
                    if last_status_map.get(task_code) != status_key:
                        self.log(f"{task_name}：补查状态 {finish_count}/{need_count} - {finish_text}")
                        last_status_map[task_code] = status_key
        if recovered:
            self.getUserInfo_sec()
        if self.sec_pending_claim_tasks:
            names = "、".join(self.sec_pending_claim_tasks.values())
            self.log(f"联通助理：仍待补领 {names}")
        return recovered

    def securityButlerTask(self, is_query_only=False):
        self.log("==== 联通安全管家 ====")
        if not self.ecs_token:
            self.log("安全管家: 缺少 ecs_token，跳过")
            return
        try:
            self.getTicketByNative_sec()
            if not getattr(self, 'sec_ticket1', None): return
            self.getAuthToken_sec()
            if not getattr(self, 'sec_token', None): return
            self.getTicketForJF_sec()
            if not getattr(self, 'sec_ticket', None): return
            self.sec_oldJFPoints = None
            self.getUserInfo_sec()
            if is_query_only:
                self.log("联通助理积分：[查询模式] 跳过任务执行")
                return
            self.get_secret_key_sec()
            self.executeAllTasks_sec()
            self.log("等待积分到账，等待一会...")
            self.sec_recover_pending_claims(rounds=2, delay=12, refresh_context=True)
            time.sleep(3)
            self.getUserInfo_sec()
        except Exception as e:
            self.log(f"安全管家: 异常: {e}")

    def aiting_query_integral(self):
        url = "https://m.jf.10010.com/jf-external-application/jftask/userInfo"
        response = self.session.post(url, json={}, headers=self.aiting_jf_headers())
        self.update_aiting_jea_id(response)
        res = response.json()
        if res.get('code') == '0000':
            data = res.get('data', {})
            self.log(f"爱听任务: 积分概览 - 今日已赚 {data.get('todayEarnScore')}, 当前余额 {data.get('availableScore')}", notify=True)

    def aiting_jf_headers(self, with_signature=False):
        headers = {
            'ticket': unquote(self.aiting_biz_ticket),
            'pageid': getattr(self, 'aiting_pageid', 's789081246969976832'),
            'clienttype': 'aiting_ios',
            'partnersid': '1706',
            'content-type': 'application/json;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Redmi K30 Pro Build/SKQ1.220303.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.159 Mobile Safari/537.36 WoReaderApp/Android',
            'Origin': 'https://m.jf.10010.com',
            'Host': 'm.jf.10010.com',
        }
        jea_id = getattr(self, 'aiting_jeaId', '')
        if jea_id:
            headers['Cookie'] = f"_jea_id={jea_id};"
        if with_signature:
            headers.update(self.build_signature_headers_aiting())
        return headers

    def update_aiting_jea_id(self, response=None):
        jea_id = ''
        if response is not None:
            cookie = response.headers.get('Set-Cookie', '')
            match = re.search(r'_jea_id=([^;]+)', cookie)
            if match:
                jea_id = match.group(1)
        if not jea_id:
            for cookie_item in self.session.cookies:
                if cookie_item.name == '_jea_id':
                    jea_id = cookie_item.value
                    break
        if jea_id:
            self.aiting_jeaId = jea_id
        return jea_id

    def get_secret_key_aiting(self):
        if getattr(self, 'aiting_secretKey', None):
            return self.aiting_secretKey
        try:
            self.update_aiting_jea_id()
            res = self.session.get(
                "https://m.jf.10010.com/jf-external-application/jftask/getSecretKey",
                headers=self.aiting_jf_headers(),
                timeout=10,
            )
            self.update_aiting_jea_id(res)
            data = res.json()
            secret = data.get('data', {}).get('secretKey')
            if data.get('code') == '0000' and secret:
                self.aiting_secretKey = secret.encode('utf-8')
                return self.aiting_secretKey
            self.log(f"爱听任务: getSecretKey 失败 - {response_summary(data)}")
        except Exception as e:
            self.log(f"爱听任务: getSecretKey 异常: {e}")
        return None

    def build_signature_headers_aiting(self):
        secret_key = self.get_secret_key_aiting()
        if not secret_key:
            return {}
        request_ts = str(round(time.time() * 1000))
        nonce = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        signature = hmac.new(
            secret_key, f"{nonce}{request_ts}".encode('utf-8'), hashlib.sha256,
        ).hexdigest()
        return {
            'x-request-timestamp': request_ts,
            'x-request-nonce': nonce,
            'x-request-signature': signature,
        }

    def ltzf_task(self):
        if not UserService.wocare_available:
            return
        self.log("==== 联通祝福 ====")
        try:
            self.session.head("https://wocare.unisk.cn", timeout=3)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            self.log("联通祝福: 沃关怀请求超时或连接失败，本轮跳过")
            UserService.wocare_available = False
            return
        except Exception:
            pass
        base_url = "https://wocare.unisk.cn/mbh/getToken"
        params = {
            "channelType": WOCARE_CONSTANTS["serviceLife"],
            "homePage": "home",
            "duanlianjieabc": "qAz2m"
        }
        targetUrl = f"{base_url}?{urlencode(params)}"
        res = self.openPlatLineNew(targetUrl)
        if not res or 'ticket' not in res:
            self.log("联通祝福: 获取Ticket失败")
            return
        ticket = res['ticket']
        if not self.wocare_getToken(ticket):
            self.log("联通祝福: 获取Wocare Token失败")
            return
        self.wocare_getSpecificityBanner()
        for activity in WOCARE_ACTIVITIES:
            self.wocare_getDrawTask(activity)
            self.wocare_loadInit(activity)

    def openPlatLineNew(self, to_url):
        """取业务入口 ticket。

        服务端有两种应答:
        1) 302 + Location(ticket=...)  —— 正常取票
        2) 200 + JS 跳转页 clientAction={"type":"login",...} —— 未登录/票据无效,
           此时不能当成失败静默返回, 要把原因暴露出来, 否则各模块只会反复
           "获取Ticket失败" 而看不出是登录态问题。
        """
        try:
            base_url = "https://m.client.10010.com/mobileService/openPlatform/openPlatLineNew.htm"
            params = {"to_url": to_url}
            res = None
            for attempt in range(1, 4):
                try:
                    res = self.session.get(base_url, params=params, allow_redirects=False, timeout=15)
                    break
                except Exception as e:
                    err_msg = str(e)
                    if attempt < 3 and os.environ.get("UNICOM_PROXY_API") and ("Max retries exceeded" in err_msg or "timed out" in err_msg.lower() or "connection" in err_msg.lower() or "SOCKS" in err_msg):
                        self.log(f"openPlatLineNew 第{attempt}次异常触发故障转移: {err_msg}")
                        self.failover_proxy()
                        continue
                    self.log(f"openPlatLineNew 第{attempt}次重试 - 异常: {e}")
                    if attempt == 3:
                         return None
                    time.sleep(2)
            if res is None:
                return None
            if res.status_code == 302 and 'Location' in res.headers:
                loc = res.headers['Location']
                parsed = urlparse(loc)
                qs = parse_qs(parsed.query)
                ticket = qs.get('ticket', [''])[0]
                type_val = qs.get('type', [''])[0]
                if ticket:
                    return {'ticket': ticket, 'type': type_val, 'loc': loc}
                # 未登录时联通会 302 到 /error/busy1.html
                if 'busy1' in loc or 'login' in loc.lower():
                    self.log("openPlatLineNew: 登录态失效 (跳转 busy1)，请更新 Token")
                else:
                    self.log("openPlatLineNew: 重定向URL中无ticket")
                return None
            # 非 302: 解析 JS 跳转页, 判断是否未登录
            body = ''
            try:
                body = res.text[:1000]
            except Exception:
                pass
            m = re.search(r'clientAction=(\{.*?\})', body)
            if m:
                try:
                    action = json.loads(m.group(1).replace('\\"', '"'))
                except Exception:
                    action = {}
                atype = action.get('type', '')
                amsg = action.get('msg', '')
                if atype == 'login':
                    self.log(f"openPlatLineNew: 未登录 (type=login) {amsg} - 请确认 Token 是否有效")
                    return None
                self.log(f"openPlatLineNew: 返回异常跳转 type={atype} msg={amsg}")
                return None
            self.log(f"openPlatLineNew: 状态码{res.status_code} (期望302)")
        except Exception as e:
            self.log(f"openPlatLineNew 异常: {str(e)}")
        return None

    def random_string(self, length, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(length))

    def get_bizchannelinfo(self):
        info = {
            "bizChannelCode": "225",
            "disriBiz": "party",
            "unionSessionId": "",
            "stType": "",
            "stDesmobile": "",
            "source": "",
            "rptId": self.rptId,
            "ticket": "",
            "tongdunTokenId": self.tokenId_cookie,
            "xindunTokenId": self.unicomTokenId
        }
        return json.dumps(info)

    def get_epay_authinfo(self):
        info = {
            "mobile": "",
            "sessionId": getattr(self, 'sessionId', ''),
            "tokenId": getattr(self, 'tokenId', ''),
            "userId": ""
        }
        return json.dumps(info)

    def ttlxj_task(self, is_query_only=False):
        self.log("==== 天天领现金 ====")
        for attempt in range(1, 31):
            try:
                ticket_res = self.openPlatLineNew("https://epay.10010.com/ci-mps-st-web/ttlxj/")
                if not ticket_res or not ticket_res.get('ticket'):
                    if attempt < 30:
                        self.log(f"天天领现金: 获取Ticket失败，正在重试 ({attempt}/30)...")
                        time.sleep(2)
                        continue
                    else:
                        self.log("天天领现金: 获取Ticket失败，已达最大重试次数，跳过任务")
                        return
                ticket = ticket_res['ticket']
                type_val = ticket_res['type']
                if self.ttlxj_authorize(ticket, type_val, ticket_res['loc']):
                    if self.ttlxj_auth_check():
                         if is_query_only:
                            self.ttlxj_query_available()
                            return
                         self.ttlxj_do_tasks()
                         self.ttlxj_query_available()
                         break
                else:
                     if attempt < 30:
                        self.log(f"天天领现金: 授权失败，正在重试 ({attempt}/30)...")
                        time.sleep(2)
                     else:
                        self.log("天天领现金: 授权失败，已达最大重试次数")
            except Exception as e:
                if attempt < 30:
                    self.log(f"天天领现金: 任务异常 ({e})，正在重试 ({attempt}/30)...")
                    time.sleep(2)
                else:
                    self.log(f"天天领现金: 任务异常: {e}")

    def ttlxj_authorize(self, ticket, type_val, referer_url):
        try:
            url = "https://epay.10010.com/woauth2/v2/authorize"
            headers = {
                "Origin": "https://epay.10010.com",
                "Referer": referer_url
            }
            payload = {
                "response_type": "rptid",
                "client_id": "73b138fd-250c-4126-94e2-48cbcc8b9cbe",
                "redirect_uri": "https://epay.10010.com/ci-mps-st-web/",
                "login_hint": {
                    "credential_type": "st_ticket",
                    "credential": ticket,
                    "st_type": type_val,
                    "force_logout": True,
                    "source": "app_sjyyt"
                },
                "device_info": {
                    "token_id": f"chinaunicom-pro-{int(time.time()*1000)}-{self.random_string(13)}",
                    "trace_id": self.random_string(32)
                }
            }
            res = self.session.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                return True
            else:
                self.log(f"天天领现金: Authorize失败[{res.status_code}]: {res.text}")
                return False
        except Exception as e:
             self.log(f"ttlxj_authorize error: {e}")
             return False

    def ttlxj_auth_check(self):
        try:
            url = "https://epay.10010.com/ps-pafs-auth-front/v1/auth/check"
            headers = {
                "bizchannelinfo": self.get_bizchannelinfo()
            }
            res = self.session.post(url, headers=headers, json={}, timeout=10)
            data = res.json()
            code = data.get("code")
            if code == "0000":
                auth_info = data.get("data", {}).get("authInfo", {})
                self.sessionId = auth_info.get("sessionId", "")
                self.tokenId = auth_info.get("tokenId", "")
                self.epay_userId = auth_info.get("userId", "")
                return True
            elif code == "2101000100":
                login_url = data.get("data", {}).get("woauth_login_url")
                if login_url:
                    return self.ttlxj_login(login_url)
            else:
                self.log(f"天天领现金: AuthCheck失败[{code}]: {data.get('msg')}")
                return False
        except Exception as e:
            self.log(f"ttlxj_auth_check error: {e}")
            return False

    def ttlxj_login(self, login_url):
        try:
            full_url = f"{login_url}https://epay.10010.com/ci-mcss-party-web/clockIn/?bizFrom=225&bizChannelCode=225"
            res = self.session.get(full_url, allow_redirects=False, timeout=10)
            if res.status_code == 302 and 'Location' in res.headers:
                loc = res.headers['Location']
                parsed = urlparse(loc)
                qs = parse_qs(parsed.query)
                rptid = qs.get('rptid', [''])[0]
                if rptid:
                    self.rptId = rptid
                    return self.ttlxj_auth_check()
                else:
                    self.log("天天领现金: Login跳转后无rptid")
            else:
                self.log(f"天天领现金: Login失败[{res.status_code}]")
            return False
        except Exception as e:
            self.log(f"ttlxj_login error: {e}")
            return False

    def ttlxj_do_tasks(self):
        info_url = "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/userDrawInfo"
        headers = {
            "bizchannelinfo": self.get_bizchannelinfo(),
            "authinfo": self.get_epay_authinfo()
        }
        res = self.request("post", info_url, json={}, headers=headers)
        if not res: return
        data = res.json()
        if data.get('code') == '0000':
            day_of_week = data.get("data", {}).get("dayOfWeek", "")
            draw_key = f"day{day_of_week}"
            has_not_clocked_in = data.get("data", {}).get(draw_key) == "1"
            if has_not_clocked_in:
                self.log(f"天天领现金: 今天未打卡", notify=True)
                today_js = (datetime.now().weekday() + 1) % 7
                draw_type = "C" if today_js == 0 else "B"
                self.ttlxj_unifyDrawNew(draw_type)
            else:
                 self.log(f"天天领现金: 今天已打卡", notify=True)
        else:
            self.log(f"天天领现金: 查询失败: {data.get('msg')}")

    def ttlxj_unifyDrawNew(self, draw_type):
        draw_url = "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/unifyDrawNew"
        headers = {
            "bizchannelinfo": self.get_bizchannelinfo(),
            "authinfo": self.get_epay_authinfo()
        }
        req_data = {
            "drawType": draw_type,
            "bizFrom": "225",
            "activityId": "TTLXJ20210330"
        }
        res = self.request("post", draw_url, data=req_data, headers=headers)
        if not res: return
        data = res.json()
        if data.get('code') == '0000':
            prize = data.get('data', {}).get('prizeName', '未知奖品')
            self.log(f"天天领现金: 抽奖成功: {prize}", notify=True)
        else:
            self.log(f"天天领现金: 抽奖失败: {data.get('msg')}")

    def ttlxj_query_available(self):
        avail_url = "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/queryAvailable"
        headers = {
            "bizchannelinfo": self.get_bizchannelinfo(),
            "authinfo": self.get_epay_authinfo()
        }
        res = self.request("post", avail_url, json={}, headers=headers)
        if not res: return
        data = res.json()
        if data.get('code') == '0000':
            d = data.get('data', {})
            amount_raw = int(d.get('availableAmount', '0'))
            amount_yuan = f"{amount_raw / 100:.2f}"
            msg = f"天天领现金: 可用立减金: {amount_yuan}元"
            seven_day = int(d.get('sevenDayExpireAmount', 0))
            if seven_day > 0:
                msg += f", 7天内过期立减金: {seven_day / 100:.2f}元"
            min_exp_amt = int(d.get('minExpireAmount', 0))
            min_exp_date = d.get('minExpireDate')
            if min_exp_amt > 0 and min_exp_date:
                msg += f", 最早过期立减金: {min_exp_amt / 100:.2f}元 -- {min_exp_date}过期"
            self.log(msg, notify=True)
        else:
            self.log(f"天天领现金: 查询余额失败: {data.get('msg')}")

    def ttxc_headers(self, auth=True, ecs=False):
        headers = {
            "user-agent": COMMON_CONSTANTS["MARKET_H5_UA"],
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://epay.10010.com",
            "referer": TTXC_REFERER,
            "x-requested-with": "com.sinovatech.unicom.ui",
        }
        if auth and getattr(self, "ttxc_token", ""):
            headers["authorization"] = self.ttxc_token
        if ecs and self.ecs_token:
            # 不能直接覆盖 Cookie: woauth 授权后 epay 域会写入 CucaSession/WOAUTH2_SESSIONID,
            # 覆盖会导致 /v1/login/ttGame 恒返回 4003(需重新授权)。这里做合并。
            cookie_str = "; ".join(f"{c.name}={c.value}" for c in self.session.cookies)
            if cookie_str:
                headers["Cookie"] = f"{cookie_str}; ecs_token={self.ecs_token}"
            else:
                headers["Cookie"] = f"ecs_token={self.ecs_token}"
        return headers

    def ttxc_post(self, path, payload=None, auth=True, with_user=True, ecs=False):
        data = dict(payload or {})
        if with_user:
            data.setdefault("userId", getattr(self, "ttxc_user_id", ""))
        data.setdefault("channel", TTXC_CHANNEL)
        res = self.request("post", f"{TTXC_BASE_URL}{path}", json=data, headers=self.ttxc_headers(auth=auth, ecs=ecs), timeout=10)
        if not res:
            return {}
        try:
            return res.json()
        except Exception:
            return {}

    def ttxc_init_ttgame(self):
        """初始化 ttGame 会话。4003 表示需要走 woauth 授权(注意 msg 为'成功', 不是错误)"""
        self.session.cookies.set("ecs_token", self.ecs_token)
        base_url = f"{TTXC_APP_BASE_URL}/v1/login/ttGame?channel={TTXC_CHANNEL}"
        rptid = getattr(self, "ttxc_rptid", "")
        data = {}
        for attempt in range(1, 4):
            url = f"{base_url}&rptId={quote(rptid)}" if rptid else f"{base_url}&rptId="
            data = self.ttxc_json(self.request("post", url, json={"unicomTokenId": self.unicomTokenId}, headers=self.ttxc_headers(auth=False, ecs=True), timeout=10))
            if data.get("code") == "0000":
                return True
            if data.get("code") == "4003" and data.get("data") and self.ttxc_finish_woauth(data.get("data")):
                # 授权已完成, 带上 rptid 重试
                rptid = getattr(self, "ttxc_rptid", "")
                url = f"{base_url}&rptId={quote(rptid)}" if rptid else f"{base_url}&rptId="
                data = self.ttxc_json(self.request("post", url, json={"unicomTokenId": self.unicomTokenId}, headers=self.ttxc_headers(auth=False, ecs=True), timeout=10))
                if data.get("code") == "0000":
                    return True
            if attempt < 3:
                time.sleep(2)
        msg = data.get('msg', '')
        if data.get('code') == '4003':
            self.log(f"通通乡村: 初始化失败[4003] 授权未生效 - {msg}")
        else:
            self.log(f"通通乡村: 初始化失败[{data.get('code')}]: {msg}")
        return False

    def ttxc_json(self, res):
        if not res:
            return {}
        try:
            return res.json()
        except Exception:
            return {}

    def ttxc_finish_woauth(self, login_url):
        """走完 woauth 授权链, 让 epay 域写入 CucaSession/WOAUTH2_SESSIONID"""
        headers = {
            "Referer": "https://epay.10010.com/",
            "User-Agent": COMMON_CONSTANTS["MARKET_H5_UA"],
        }
        res = self.request("get", login_url, headers=headers, timeout=10)
        if not res:
            return False
        match = re.search(r'var token = "([^"]+)"', res.text or "")
        if not match:
            return False
        next_url = (
            "https://epay.10010.com/woauth2/after-collected-device-digest"
            f"?deviceDigestTraceId=&deviceDigestTokenId=&token={quote(match.group(1))}&source=app_sjyyt"
        )
        referer = login_url
        rptid = ""
        # 授权链最多跳转十余跳, 必须跟到最终 H5 落地页, 中途停止会拿不到会话
        for _ in range(15):
            res = self.request("get", next_url, headers={"Referer": referer, "User-Agent": COMMON_CONSTANTS["MARKET_H5_UA"]}, allow_redirects=False, timeout=10)
            if not res:
                return False
            location = res.headers.get("Location", "")
            if not location:
                # 终态: 已落到业务 H5 页面
                break
            m = re.search(r"rptid=([^&]+)", location)
            if m:
                rptid = unquote(m.group(1))
            referer = next_url
            next_url = location
        # 授权成功后 epay 域应已写入会话 Cookie
        has_session = any(c.name == "CucaSession" for c in self.session.cookies)
        if rptid:
            self.ttxc_rptid = rptid
        return has_session

    def ttxc_login(self, update_nick=True):
        if not self.ecs_token:
            self.onLine()
            if not self.ecs_token:
                self.log("通通乡村: 缺少 ecs_token，跳过")
                return False
        if not self.ttxc_init_ttgame():
            return False
        data = self.ttxc_post("/user/v1/login", auth=False, with_user=False, ecs=True)
        if data.get("code") != 0:
            self.log(f"通通乡村: 登录失败[{data.get('code')}]: {data.get('msg', '')}")
            return False
        user = data.get("data") or {}
        self.ttxc_user_id = user.get("userId", "")
        self.ttxc_token = data.get("token", "")
        self.ttxc_charge_level = user.get("chargeLevel") or {}
        self.ttxc_newbie_list = user.get("newbieList")
        self.ttxc_nick_name = user.get("nickName") or ""
        if not self.ttxc_user_id or not self.ttxc_token:
            self.log("通通乡村: 登录响应缺少 userId/token")
            return False
        carbon = self.ttxc_charge_level.get("carbonNum", 0)
        eco = self.ttxc_charge_level.get("ecologyAmount", 0)
        self.log(f"通通乡村: 登录成功，碳能量{carbon}g，生态值{eco}", notify=True)
        if update_nick and not self.ttxc_nick_name and self.ttxc_newbie_done():
            self.ttxc_update_nick()
        return True

    def ttxc_update_nick(self):
        nick = (self.account_mobile or self.mobile or "")[-4:] or str(random.randint(1000, 9999))
        data = self.ttxc_post("/user/v1/updateNick", {"nickName": nick})
        if data.get("code") == 0:
            self.ttxc_nick_name = nick
            self.log(f"通通乡村: 已设置昵称 {nick}")
            return True
        self.log(f"通通乡村: 设置昵称失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def ttxc_newbie_done(self):
        steps = getattr(self, "ttxc_newbie_list", None)
        return not isinstance(steps, list) or all(step in steps for step in TTXC_NEWBIE_STEPS)

    def ttxc_newbie_mark(self, step):
        target = []
        for item in TTXC_NEWBIE_STEPS:
            target.append(item)
            if item == step:
                break
        data = self.ttxc_post("/user/v1/newbie", {"newbieList": target, "type": 1})
        if data.get("code") == 0:
            self.ttxc_newbie_list = data.get("data") or target
            return True
        self.log(f"通通乡村: 新手步骤{step}失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def ttxc_newbie_need(self, step):
        steps = getattr(self, "ttxc_newbie_list", None)
        return isinstance(steps, list) and step not in steps

    def ttxc_first_newbie_land(self, lands=None):
        lands = lands if lands is not None else self.ttxc_get_lands()
        active = next((land for land in lands if land.get("status") in [2, 3] and (land.get("plant") or {}).get("plantId")), None)
        if active:
            return active
        return next((land for land in lands if land.get("status") == 1), None)

    def ttxc_newbie_charge_land(self):
        lands = self.ttxc_get_lands()
        active = [land for land in lands if land.get("status") == 3 and (land.get("plant") or {}).get("plantId")]
        return next((land for land in active if str((land.get("plant") or {}).get("curLevel")) in ["0", "1"]), None) or (active[0] if active else None)

    def ttxc_harvest_land(self, land, newbie=False):
        if not land:
            return None
        plant = land.get("plant") or {}
        plant_id = plant.get("plantId")
        land_index = land.get("landIndex")
        if not plant_id or not land_index:
            return None
        if land.get("status") == 2 and TTXC_HARVEST_WAIT_SECONDS > 0:
            time.sleep(TTXC_HARVEST_WAIT_SECONDS)
        path = "/plant/v1/newHarvest" if newbie else "/plant/v1/harvest"
        data = self.ttxc_post(path, {"landIndex": land_index, "plantId": plant_id})
        if data.get("code") == 0:
            self.log(f"通通乡村: 地块{land_index}收获成功")
            return data.get("data") or {"landIndex": land_index, "status": 1, "plant": None}
        self.log(f"通通乡村: 地块{land_index}收获失败[{data.get('code')}]: {data.get('msg', '')}")
        return None

    def ttxc_newbie_task(self):
        if self.ttxc_newbie_done():
            return False
        need_farm = any(self.ttxc_newbie_need(step) for step in ["G03", "G03_2", "G04", "G05", "G09", "G10"])
        lands = self.ttxc_get_lands() if need_farm else []
        plant_id = ""
        current = self.ttxc_first_newbie_land(lands) if need_farm else None
        if need_farm:
            self.ttxc_post("/client/v1/plant/type", {})
            plant_id = self.ttxc_get_plant_id()
            if not plant_id:
                self.log("通通乡村: 新手任务缺少作物ID")
                return False
        if self.ttxc_newbie_need("G03") and not self.ttxc_newbie_mark("G03"):
            return False
        if self.ttxc_newbie_need("G03_2"):
            has_crop = current and current.get("status") in [2, 3] and (current.get("plant") or {}).get("plantId")
            if not has_crop:
                data = self.ttxc_post("/client/v1/plant/buy", {"plantId": plant_id, "gameCfgId": ""})
                if data.get("code") != 0:
                    self.log(f"通通乡村: 新手购买作物失败[{data.get('code')}]: {data.get('msg', '')}")
                    return False
            if not self.ttxc_newbie_mark("G03_2"):
                return False
        if self.ttxc_newbie_need("G04"):
            if not current or not current.get("landIndex"):
                self.log("通通乡村: 新手任务缺少可种植地块")
                return False
            if not (current.get("status") in [2, 3] and (current.get("plant") or {}).get("plantId")):
                data = self.ttxc_post("/plant/v1/planting", {"landIndex": current.get("landIndex"), "plantId": plant_id})
                if data.get("code") != 0:
                    self.log(f"通通乡村: 新手种植失败[{data.get('code')}]: {data.get('msg', '')}")
                    return False
                current = data.get("data") or {"landIndex": current.get("landIndex"), "status": 3, "plant": {"plantId": plant_id}}
            if not self.ttxc_newbie_mark("G04"):
                return False
        if self.ttxc_newbie_need("G05"):
            current = current if current and current.get("plant") else self.ttxc_first_newbie_land()
            current = self.ttxc_charge_land(current)
            if not current or not self.ttxc_newbie_mark("G05"):
                return False
        if self.ttxc_newbie_need("G09"):
            plant = (current or {}).get("plant") or {}
            level = str(plant.get("curLevel") or "")
            if not (current and current.get("status") == 3 and plant.get("plantId") and level in ["", "0", "1"]):
                current = self.ttxc_newbie_charge_land()
            current = self.ttxc_charge_land(current, mock=1)
            if not current or not self.ttxc_newbie_mark("G09"):
                return False
        if self.ttxc_newbie_need("G10"):
            current = current if current and current.get("plant") else self.ttxc_first_newbie_land()
            if not self.ttxc_harvest_land(current, newbie=True) or not self.ttxc_newbie_mark("G10"):
                return False
        if self.ttxc_newbie_need("G11") and not self.ttxc_newbie_mark("G11"):
            return False
        if self.ttxc_newbie_need("G12"):
            if not self.ttxc_nick_name and not self.ttxc_update_nick():
                return False
            if not self.ttxc_newbie_mark("G12"):
                return False
        self.log("通通乡村: 新手任务已完成")
        return True

    def ttxc_sign(self, is_query_only=False):
        info = self.ttxc_post("/client/v1/sign/info", {})
        code = (info.get("data") or {}).get("signinCode")
        if not code:
            self.log("通通乡村: 获取签到码失败")
            return
        user = self.ttxc_post("/client/v1/sign/user", {"code": code})
        last_time = str((user.get("data") or {}).get("lastSigninTime") or "")
        signed = last_time[:10] == datetime.now().strftime("%Y-%m-%d")
        if signed:
            self.log("通通乡村: 今日已签到", notify=True)
            return
        if is_query_only:
            self.log("通通乡村: 今日未签到", notify=True)
            return
        data = self.ttxc_post("/client/v1/sign/signIn", {"code": code})
        if data.get("code") == 0:
            sign_data = data.get("data") or {}
            keep_value = safe_int(sign_data.get("keepSigninValue") or sign_data.get("lastKeepSigninValue") or sign_data.get("totalSigninValue"))
            award_items = (info.get("data") or {}).get("awards") or []
            energy = 0
            for item in award_items:
                if item.get("awardType") == "KEEP" and safe_int(item.get("signinValue")) == keep_value:
                    energy = safe_int(item.get("carbonEnergyAmount"))
                    break
            if not energy:
                charge_level = data.get("chargeLevel") or {}
                before = safe_int(getattr(self, "ttxc_charge_level", {}).get("carbonNum"))
                after = safe_int(charge_level.get("carbonNum"))
                energy = max(after - before, 0)
            if data.get("chargeLevel"):
                self.ttxc_charge_level = data.get("chargeLevel") or self.ttxc_charge_level
            msg = f"通通乡村: 签到成功 +{energy}g" if energy else "通通乡村: 签到成功"
            self.log(msg, notify=True)
        else:
            self.log(f"通通乡村: 签到失败[{data.get('code')}]: {data.get('msg', '')}")

    def ttxc_get_tasks(self):
        data = self.ttxc_post("/client/v1/task/list", {})
        if data.get("code") != 0:
            self.log(f"通通乡村: 获取任务列表失败[{data.get('code')}]: {data.get('msg', '')}")
            return []
        tasks = []
        for group in data.get("data") or []:
            for task in group.get("taskList") or []:
                task["taskGroupName"] = group.get("taskGroupName", "")
                tasks.append(task)
        return tasks

    def ttxc_finish_task(self, task):
        task_id = task.get("taskCode")
        if not task_id:
            return False
        data = self.ttxc_post("/client/v1/task/finish", {"taskId": task_id})
        name = task.get("taskTitle", task_id)
        if data.get("code") == 0:
            reward = task.get("carbonEnergyAmount") or 0
            self.log(f"通通乡村: 领取[{name}]成功 +{reward}g")
            return True
        self.log(f"通通乡村: 领取[{name}]失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def ttxc_do_task(self, task):
        data = self.ttxc_post("/client/v1/task/do", {"taskId": task.get("taskCode")})
        name = task.get("taskTitle", task.get("taskCode", ""))
        if data.get("code") == 0:
            self.log(f"通通乡村: 已执行[{name}]")
            return True
        self.log(f"通通乡村: 执行[{name}]失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def ttxc_claim_ready_tasks(self, tasks, claimed=None):
        if claimed is None:
            claimed = set()
        count = 0
        for task in tasks:
            task_id = task.get("taskCode")
            if task.get("taskStatus") == "UNCLA" and task_id not in claimed:
                if self.ttxc_finish_task(task):
                    claimed.add(task_id)
                    count += 1
        return count

    def ttxc_do_jump_tasks(self, tasks):
        count = 0
        for task in tasks:
            if task.get("taskType") == "GAME" and task.get("taskStatus") == "UNDO" and task.get("jumpUrl"):
                if self.ttxc_do_task(task):
                    count += 1
                time.sleep(1)
        return count

    def ttxc_do_garbage_task(self, tasks):
        task = next((t for t in tasks if t.get("taskType") == "GAME" and t.get("taskStatus") == "UNDO" and "垃圾分类" in t.get("taskTitle", "")), None)
        if not task:
            return False
        start = self.ttxc_post("/user/v1/start", {})
        answer_no = (start.get("data") or {}).get("answerNo")
        if not answer_no:
            self.log("通通乡村: 垃圾分类开始失败")
            return False
        time.sleep(TTXC_GARBAGE_WAIT_SECONDS)
        data = self.ttxc_post("/user/v1/finish", {"answerNo": answer_no})
        if data.get("code") == 0:
            self.log("通通乡村: 垃圾分类已通关")
            return True
        self.log(f"通通乡村: 垃圾分类通关失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def ttxc_prepare_newbie_energy(self, claimed=None):
        if claimed is None:
            claimed = set()
        self.ttxc_sign()
        tasks = self.ttxc_get_tasks()
        self.ttxc_claim_ready_tasks(tasks, claimed)
        self.ttxc_do_jump_tasks(tasks)
        self.ttxc_do_garbage_task(tasks)
        tasks = self.ttxc_get_tasks()
        self.ttxc_claim_ready_tasks(tasks, claimed)

    def ttxc_get_lands(self):
        land = safe_int(getattr(self, "ttxc_charge_level", {}).get("land"), 4)
        data = self.ttxc_post("/plant/v1/user", {"land": land})
        if data.get("code") != 0:
            self.log(f"通通乡村: 获取土地失败[{data.get('code')}]: {data.get('msg', '')}")
            return []
        return data.get("data") or []

    def ttxc_get_plant_id(self):
        data = self.ttxc_post("/client/v1/plant/page", {"itemType": "SPE", "pageNum": 1, "pageSize": 20})
        items = (data.get("data") or {}).get("list") or []
        return items[0].get("itemNo", "") if items else ""

    def ttxc_plant_land(self, land_index, plant_id=None):
        plant_id = plant_id or self.ttxc_get_plant_id()
        if not plant_id or not land_index:
            return None
        self.ttxc_post("/client/v1/plant/buy", {"plantId": plant_id, "gameCfgId": ""})
        data = self.ttxc_post("/plant/v1/planting", {"landIndex": land_index, "plantId": plant_id})
        if data.get("code") == 0:
            self.log(f"通通乡村: 已在地块{land_index}种植作物")
            return {"landIndex": land_index, "status": 3, "plant": {"plantId": plant_id}}
        self.log(f"通通乡村: 地块{land_index}种植失败[{data.get('code')}]: {data.get('msg', '')}")
        return None

    def ttxc_ensure_planted_lands(self, lands, needed=None):
        active = [l for l in lands if l.get("status") in [2, 3] and (l.get("plant") or {}).get("plantId")]
        empty = [l for l in lands if l.get("status") == 1]
        if not empty:
            return active
        plant_id = self.ttxc_get_plant_id()
        if not plant_id:
            return active
        for land in empty:
            planted = self.ttxc_plant_land(land.get("landIndex"), plant_id)
            if planted:
                active.append(planted)
        return active

    def ttxc_charge_land(self, land, mock=None):
        if not land:
            return False
        plant = land.get("plant") or {}
        plant_id = plant.get("plantId")
        land_index = land.get("landIndex")
        if not plant_id or not land_index:
            return False
        data = self.ttxc_post("/plant/v1/charge", {"landIndex": land_index, "plantId": plant_id, "mock": mock})
        if data.get("code") == 0:
            self.log(f"通通乡村: 地块{land_index}充能成功")
            result = data.get("data") or {}
            if result and not result.get("plant"):
                result["plant"] = plant
            return result or land
        self.log(f"通通乡村: 地块{land_index}充能失败[{data.get('code')}]: {data.get('msg', '')}")
        return None

    def ttxc_harvest_and_replant(self, land):
        harvested = self.ttxc_harvest_land(land)
        return self.ttxc_plant_land(land.get("landIndex")) if harvested and land else None

    def ttxc_grow_land_to_harvest(self, land):
        current = land
        if current.get("status") == 2:
            self.ttxc_harvest_and_replant(current)
            return
        charged = 0
        while current.get("status") == 3 and charged < TTXC_GROW_MAX_CHARGE_PER_LAND:
            current = self.ttxc_charge_land(current)
            if not current:
                return
            charged += 1
            if current.get("status") == 2:
                self.ttxc_harvest_and_replant(current)
                return
            if charged < TTXC_GROW_MAX_CHARGE_PER_LAND:
                time.sleep(1)
        if current.get("status") == 3:
            self.log(f"通通乡村: 地块{current.get('landIndex')}催熟达到上限，跳过")

    def ttxc_replace_land(self, lands, updated):
        land_index = updated.get("landIndex")
        for i, land in enumerate(lands):
            if land.get("landIndex") == land_index:
                lands[i] = updated
                return
        lands.append(updated)

    def ttxc_complete_charge_task(self, active, remaining):
        # remaining 来自服务端 finishValue/doneValue, 若服务端返回异常大值会无限循环,
        # 这里加上限, 避免单次运行被拖垮
        max_charge = TTXC_GROW_MAX_CHARGE_PER_LAND * max(len(active), 1)
        if remaining > max_charge:
            self.log(f"通通乡村: 待充能次数 {remaining} 超过上限 {max_charge}, 已截断")
            remaining = max_charge
        while remaining > 0:
            immature = [land for land in active if land.get("status") == 3 and (land.get("plant") or {}).get("plantId")]
            if not immature:
                self.log("通通乡村: 未成熟作物不足，提前结束10次充能补足")
                return
            progressed = False
            for land in immature:
                if remaining <= 0:
                    return
                result = self.ttxc_charge_land(land)
                if result:
                    self.ttxc_replace_land(active, result)
                    remaining -= 1
                    progressed = True
                time.sleep(1)
            if not progressed:
                self.log("通通乡村: 充能未成功，提前结束10次充能补足")
                return

    def ttxc_farm_tasks(self, tasks):
        charge_task = next((t for t in tasks if "10次作物充能" in t.get("taskTitle", "")), None)
        land_task = next((t for t in tasks if "三块不同" in t.get("taskTitle", "")), None)
        harvest_task = next((t for t in tasks if "收获一次作物" in t.get("taskTitle", "")), None)
        if not charge_task and not land_task and not harvest_task:
            return
        charge_pending = charge_task if (charge_task or {}).get("taskStatus") == "UNDO" else None
        land_pending = land_task if (land_task or {}).get("taskStatus") == "UNDO" else None
        harvest_pending = harvest_task if (harvest_task or {}).get("taskStatus") == "UNDO" else None
        if not charge_pending and not land_pending and not harvest_pending:
            return
        lands = self.ttxc_get_lands()
        active = self.ttxc_ensure_planted_lands(lands)
        need_land = max(safe_int((land_pending or {}).get("finishValue")) - safe_int((land_pending or {}).get("doneValue")), 0)
        if harvest_pending and not charge_pending and not land_pending:
            for land in active:
                if land.get("status") == 2:
                    self.ttxc_harvest_and_replant(land)
        if not active:
            self.log("通通乡村: 没有可充能作物")
            return
        charged = 0
        for i, land in enumerate(active[:need_land]):
            result = self.ttxc_charge_land(land)
            if result:
                active[i] = result
                charged += 1
                time.sleep(1)
        need_charge = max(safe_int((charge_pending or {}).get("finishValue")) - safe_int((charge_pending or {}).get("doneValue")) - charged, 0)
        self.ttxc_complete_charge_task(active, need_charge)
        for land in active:
            self.ttxc_grow_land_to_harvest(land)

    def ttxc_task(self, is_query_only=False):
        self.log("==== 通通乡村 ====")
        try:
            if not self.ttxc_login(update_nick=not is_query_only):
                return
            claimed = set()
            if not is_query_only:
                if not self.ttxc_newbie_done():
                    self.ttxc_prepare_newbie_energy(claimed)
                if not self.ttxc_newbie_done() and not self.ttxc_newbie_task():
                    return
            self.ttxc_sign(is_query_only=is_query_only)
            tasks = self.ttxc_get_tasks()
            if is_query_only:
                todo = sum(1 for t in tasks if t.get("taskStatus") == "UNDO")
                claim = sum(1 for t in tasks if t.get("taskStatus") == "UNCLA")
                self.log(f"通通乡村: 待做{todo}个，可领取{claim}个", notify=True)
                return
            self.ttxc_claim_ready_tasks(tasks, claimed)
            self.ttxc_do_jump_tasks(tasks)
            self.ttxc_do_garbage_task(tasks)
            self.ttxc_farm_tasks(tasks)
            tasks = self.ttxc_get_tasks()
            self.ttxc_claim_ready_tasks(tasks, claimed)
        except Exception as e:
            self.log(f"通通乡村异常: {e}")

    def aiting_get_aes(self, data, key):
        iv_str = "16-Bytes--String"
        key_bytes = key[:16].encode('utf-8')
        iv_bytes = iv_str[:16].encode('utf-8')
        text = json.dumps(data, separators=(',', ':')) if isinstance(data, (dict, list)) else str(data)
        padded_data = pad(text.encode('utf-8'), 16)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        ciphertext = cipher.encrypt(padded_data)
        hex_str = ciphertext.hex()
        return base64.b64encode(hex_str.encode('utf-8')).decode('utf-8')

    def aiting_aes_encrypt(self, data, key, iv):
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        text = json.dumps(data, separators=(',', ':')) if isinstance(data, (dict, list)) else str(data)
        padded_data = pad(text.encode('utf-8'), 16)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        ciphertext = cipher.encrypt(padded_data)
        hex_str = ciphertext.hex().upper()
        return base64.b64encode(hex_str.encode('utf-8')).decode('utf-8')

    def aiting_md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def aiting_generate_sign(self, params, key):
        sorted_keys = sorted(params.keys())
        sign_str = '&'.join([f"{k}={params[k]}" for k in sorted_keys])
        final_str = f"{sign_str}&key={key}"
        return self.aiting_md5(final_str)

    def aiting_timestamp(self):
        return str(int(time.time() * 1000))

    def aiting_nonce(self):
        return str(random.randint(100000, 999999))

    def aiting_generate_woid(self, imei):
        random6 = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        imei8 = imei[:8] if len(imei) >= 8 else imei.ljust(8, '0')
        random4 = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
        random2 = ''.join(random.choices(string.ascii_letters + string.digits, k=2))
        return f"WOA{random6}{imei8}LOT{random4}LV{random2}"

    def aiting_calculate_clientconfirm(self, userid, imei):
        plaintext = f"android{userid}{imei}"
        return self.aiting_aes_encrypt(plaintext, AITING_AES_KEY, AITING_AES_IV)

    def aiting_calculate_passcode(self, timestamp, phone):
        return self.aiting_md5(timestamp + phone + AITING_CLIENT_KEY)

    def aiting_build_statisticsinfo(self, userid, useraccount, imei, clientconfirm):
        params = {
            'channelid': '28015001',
            'sid': ''.join(random.choices(string.ascii_letters + string.digits + "_-", k=20)),
            'eid': ''.join(random.choices(string.ascii_letters + string.digits + "_", k=20)),
            'osversion': 'Android12',
            'clientallid': '000000100000000000058.0.2.1225',
            'display': '2400_1080',
            'ip': '192.168.3.24',
            'nettypename': 'wifi',
            'version': '802',
            'versionname': '8.0.2',
            'terminalName': 'Redmi',
            'terminalType': 'Redmi_K30_Pro',
            'udid': 'null',
            'woid': self.aiting_generate_woid(imei),
            'useraccount': useraccount,
            'userid': userid,
            'clientconfirm': clientconfirm
        }
        return '&'.join([f"{k}={params[k]}" for k in params])

    def generate_random_imei(self):
        tac = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        snr = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        imei_raw = tac + snr
        digits = [int(d) for d in imei_raw]
        for i in range(len(digits) - 1, -1, -2):
            digits[i] *= 2
            if digits[i] > 9: digits[i] -= 9
        total = sum(digits)
        check_digit = (10 - (total % 10)) % 10
        return imei_raw + str(check_digit)

    def aiting_woread_login(self, phone):
        access_token = "ODZERTZCMjA1NTg1MTFFNDNFMThDRDYw"
        token_enc = ""
        if self.token_online:
             token_enc = self.aiting_get_aes(self.token_online, WOREAD_KEY)
        else:
             self.log("阅读专区: 未找到 token_online，尝试仅使用手机号登录")
        phone_enc = self.aiting_get_aes(phone, WOREAD_KEY)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if token_enc:
            inner_data = {
                "tokenOnline": token_enc,
                "phone": phone_enc,
                "timestamp": timestamp
            }
        else:
            inner_data = {
                "phone": phone_enc,
                "timestamp": timestamp
            }
        sign_result = self.aiting_get_aes(inner_data, WOREAD_KEY)
        url = "https://10010.woread.com.cn/ng_woread_service/rest/account/login"
        body = {"sign": sign_result}
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; Redmi Note 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.159 Mobile Safari/537.36",
            "accesstoken": access_token,
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://10010.woread.com.cn"
        }
        res = self.session.post(url, json=body, headers=headers).json()
        if res.get("code") == "0000":
            self.aiting_read_userinfo = res.get("data") or {}
            return res.get("data", {}).get("token")
        self.log(f"爱听登录: 沃阅读登录失败 - {response_summary(res)}")
        return None

    def aiting_get_jwt_token(self, statisticsinfo):
        timestamp = self.aiting_timestamp()
        sign_params = {
            'clientSource': '3',
            'clientId': 'android',
            'source': '3',
            'timestamp': timestamp
        }
        sign_val = self.aiting_generate_sign(sign_params, AITING_SIGN_KEY_APPKEY)
        client_id_const = "395DEDE9C1D6FE11B7C9C0D82B353E74"
        client_id_b64 = base64.b64encode(client_id_const.encode('utf-8')).decode('utf-8')
        body = {
            'clientSource': '3',
            'clientId': client_id_b64,
            'source': '3',
            'timestamp': timestamp,
            'sign': sign_val
        }
        url = f"{AITING_BASE_URL}/oauth/client/appkey"
        headers = {
            'Skip-Authorization-Check': 'true',
            'statisticsinfo': statisticsinfo,
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; Redmi K30 Pro Build/SKQ1.220303.001)"
        }
        try:
            res = self.session.post(url, json=body, headers=headers).json()
            if res.get("code") == "0000" and res.get("key"):
                return res.get("key")
            self.log(f"爱听登录: 获取JWT失败 - {response_summary(res)}")
        except Exception as e:
            self.log(f"爱听登录: 获取JWT异常: {e}")
        return None

    def aiting_api_login(self, phone, useraccount, jwt_token, statisticsinfo, validatecode=""):
        """pcc.woread 业务登录。

        validatecode: 服务端在空值时返回 "用户未登录", 传 woread 返回的 verifycode
        则返回 "验证码超时" —— 说明该码是 App 侧展示码而非短信验证码, 脚本无法自动获取,
        因此默认留空, 仅保留入参以便手工传入真实验证码。
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        passcode = self.aiting_calculate_passcode(timestamp, phone)
        query_params_list = [
            'networktype=3', 'ua=Redmi+K30+Pro', 'isencode=false',
            'clientversion=8.0.2', 'versionname=Android_1_1080x2356',
            'channelid=28015001', 'userlabelisencode=0',
            f'validatecode={validatecode}', 'sid=',
            f"timestamp={timestamp}", f"passcode={passcode}"
        ]
        query_str = '&'.join(query_params_list)
        final_account = useraccount
        url = f"{AITING_BASE_URL}/mainrest/rest/read/user/ulogin/3/{final_account}/1/1/0?{query_str}"
        req_time = self.aiting_timestamp()
        nonce = self.aiting_nonce()
        sign_params = {
            'jwt': jwt_token,
            'nonestr': nonce,
            'osversion': 'Android12',
            'terminalName': 'Redmi',
            'timestamp': req_time
        }
        sorted_keys = sorted(sign_params.keys())
        sign_str = '&'.join([f"{k}={sign_params[k]}" for k in sorted_keys])
        requertid = self.aiting_md5(f"{sign_str}&key={AITING_SIGN_KEY_REQUERTID}")
        headers = {
            'statisticsinfo': statisticsinfo,
            'requerttime': req_time,
            'nonestr': nonce,
            'requertid': requertid,
            'AuthorizationClient': f"Bearer {jwt_token}",
            'User-Agent': 'okhttp/4.9.0'
        }
        try:
            res = self.session.get(url, headers=headers).json()
            if res.get("code") == "0000" and res.get("message"):
                msg = res.get("message")
                token = msg.get("token")
                userid = msg.get("userid")
                if msg.get("accountinfo"):
                    token = msg.get("accountinfo", {}).get("token") or token
                    userid = msg.get("accountinfo", {}).get("userid") or userid
                return {"token": token, "userid": userid}
            code = res.get("code")
            msg = res.get("message")
            if code == "9999" and "用户未登录" in str(msg):
                self.log("爱听登录: 业务API登录失败(用户未登录) - pcc 侧登录态未建立, "
                         "该接口需 App 内嵌 H5 私有登录流程, 脚本暂无法还原")
            else:
                self.log(f"爱听登录: 业务API登录失败 - {response_summary(res)}")
        except Exception as e:
            self.log(f"爱听登录: 业务API异常: {e}")
        return None

    def aiting_login_flow(self):
        self.log("爱听任务: 正在执行登录流程...")
        woread_token = self.aiting_woread_login(self.mobile)
        if not woread_token: return False
        self.aiting_woread_token = woread_token
        # 服务端在 woread 登录时返回了真实 userid / verifycode, 优先使用它们,
        # 不要用手机号当 userid —— pcc 侧校验的是这个 userid。
        read_user = getattr(self, "aiting_read_userinfo", {}) or {}
        userid = read_user.get("userid") or self.mobile
        useraccount = read_user.get("phone") or self.mobile
        # validatecode 默认留空: woread 返回的 verifycode 是 App 侧展示码,
        # 填进去会被判"验证码超时", 反而不如不填。
        # 只有手工拿到真实短信验证码时才通过环境变量注入。
        validatecode = ""
        manual_vcode = os.environ.get("UNICOM_AITING_VALIDATECODE", "").strip()
        if manual_vcode:
            validatecode = manual_vcode
        imei = self.generate_random_imei()
        clientconfirm = self.aiting_calculate_clientconfirm(userid, imei)
        statisticsinfo = self.aiting_build_statisticsinfo(userid, useraccount, imei, clientconfirm)
        self.aiting_statisticsinfo = statisticsinfo
        jwt = self.aiting_get_jwt_token(statisticsinfo)
        if not jwt: return False
        self.aiting_jwt = jwt
        login_data = self.aiting_api_login(self.mobile, useraccount, jwt, statisticsinfo, validatecode)
        if not login_data: return False
        self.aiting_biz_token = login_data.get('token')
        self.aiting_base_userid = login_data.get('userid') or userid
        self.log("爱听任务: 登录成功，Token已获取")
        biz_ticket = self.aiting_get_ticket()
        if biz_ticket:
            self.aiting_biz_ticket = biz_ticket
            return True
        return False

    def aiting_get_ticket(self):
        url = f"{AITING_BASE_URL}/activity/rest/unicom/points/getInfoTicket"
        timestamp = self.aiting_timestamp()
        sign_params = {
            "token": self.aiting_biz_token,
            "timestamp": timestamp,
            "userid": self.aiting_base_userid
        }
        sign_val = self.aiting_generate_sign(sign_params, AITING_SIGN_KEY_API)
        body = {
            "sign": sign_val,
            "timestamp": timestamp,
            "token": self.aiting_biz_token,
            "userid": self.aiting_base_userid
        }
        nonce = self.aiting_nonce()
        head_sign_params = {
            'jwt': self.aiting_jwt,
            'nonestr': nonce,
            'osversion': 'Android12',
            'terminalName': 'Redmi',
            'timestamp': timestamp
        }
        sorted_keys = sorted(head_sign_params.keys())
        sign_str = '&'.join([f"{k}={head_sign_params[k]}" for k in sorted_keys])
        final_sign_str = f"{sign_str}&key={AITING_SIGN_KEY_REQUERTID}"
        requertid = self.aiting_md5(final_sign_str)
        headers = {
            "AuthorizationClient": f"Bearer {self.aiting_jwt}",
            "statisticsinfo": self.aiting_statisticsinfo,
            "requerttime": timestamp,
            "nonestr": nonce,
            "requertid": requertid
        }
        try:
            res = self.session.post(url, json=body, headers=headers).json()
            if res.get("code") == "0000":
                msg = res.get("message", "")
                if "ticket=" in msg:
                    parsed = urlparse(msg)
                    params = parse_qs(parsed.query)
                    ticket = (params.get("ticket") or [""])[0]
                    distribute_id = (params.get("distributeId") or [""])[0]
                    pageid = (params.get("pageid") or params.get("pageID") or [""])[0]
                    if not pageid:
                        pageid = next((part for part in parsed.path.split("/") if part.startswith("s")), "")
                    if ticket:
                        self.aiting_distribute_id = distribute_id
                        self.aiting_pageid = pageid or "s789081246969976832"
                        return ticket
                    # code=0000 但消息里没有可解析的 ticket: 不能把提示文案当 ticket 用
                    self.log(f"爱听登录: 获取Ticket失败(响应无ticket字段) - {response_summary(res)}")
                    return None
            self.log(f"爱听登录: 获取Ticket失败 - {response_summary(res)}")
        except Exception as e:
            self.log(f"爱听登录: 获取Ticket异常: {e}")
        return None

    def jf_get_task_detail(self, ticket):
        url = "https://m.jf.10010.com/jf-external-application/jftask/taskDetail"
        headers = self.aiting_jf_headers()
        headers['Referer'] = f"https://m.jf.10010.com/jf-external-application/index.html?ticket={ticket}&pageID=s789081246969976832"
        try:
            response = self.session.post(url, json={}, headers=headers)
            self.update_aiting_jea_id(response)
        except Exception as e:
            self.log(f"爱听任务: 积分任务列表请求异常: {e}")
            return []
        if response is None:
            self.log("爱听任务: 积分任务列表无响应")
            return []
        try:
            res = response.json()
        except Exception:
            self.log(f"爱听任务: 积分任务列表响应非JSON (状态码{getattr(response, 'status_code', '未知')})")
            return []
        return res.get("data", {}).get("taskDetail", {}).get("taskList", [])

    def jf_to_finish(self, ticket, task_code):
        url = "https://m.jf.10010.com/jf-external-application/jftask/toFinish"
        try:
            response = self.session.post(
                url,
                json={'taskCode': task_code},
                headers=self.aiting_jf_headers(with_signature=True),
            )
            self.update_aiting_jea_id(response)
        except Exception as e:
            self.log(f"爱听任务: 积分任务提交异常: {e}")
            return False
        if response is None:
            self.log("爱听任务: 积分任务提交无响应")
            return False
        try:
            res = response.json()
        except Exception:
            self.log(f"爱听任务: 积分任务提交响应非JSON (状态码{getattr(response, 'status_code', '未知')})")
            return False
        self.log(f"爱听任务: 积分任务提交 - {response_summary(res)}")
        return isinstance(res, dict) and res.get('code') == "0000"

    def jf_sign(self, ticket, task_code):
        url = "https://m.jf.10010.com/jf-external-application/uasptask/sign"
        referer = (
            f"https://m.jf.10010.com/ts-mobile/well/{getattr(self, 'aiting_pageid', 's789081246969976832')}"
            f"?distributeId={getattr(self, 'aiting_distribute_id', '')}&partnersId=1706&clientType=aiting_ios&ticket={ticket}"
        )
        headers = self.aiting_jf_headers(with_signature=True)
        headers.update({"referer": referer, "origin": "https://m.jf.10010.com"})
        try:
            response = self.session.post(
                url,
                json={'taskCode': task_code, 'remindEnabled': '1'},
                headers=headers,
            )
            self.update_aiting_jea_id(response)
        except Exception as e:
            self.log(f"爱听任务: 积分签到异常: {e}")
            return False
        if response is None:
            self.log("爱听任务: 积分签到无响应")
            return False
        try:
            res = response.json()
        except Exception:
            self.log(f"爱听任务: 积分签到响应非JSON (状态码{getattr(response, 'status_code', '未知')})")
            return False
        if isinstance(res, dict) and res.get('code') == "0000":
            self.log(f"爱听任务: 积分签到 - {res.get('msg') or '成功'}")
            return True
        if isinstance(res, dict):
            self.log(f"爱听任务: 积分签到返回 - {res.get('desc') or res.get('msg') or response_summary(res)}")
        return False

    def jf_pop_up(self, ticket):
        url = "https://m.jf.10010.com/jf-external-application/jftask/popUp"
        try:
            response = self.session.post(url, json={}, headers=self.aiting_jf_headers())
            self.update_aiting_jea_id(response)
        except Exception as e:
            self.log(f"爱听任务: 积分弹窗请求异常: {e}")
            return {}
        if response is None:
            self.log("爱听任务: 积分弹窗无响应")
            return {}
        try:
            res = response.json()
        except Exception:
            self.log(f"爱听任务: 积分弹窗响应非JSON (状态码{getattr(response, 'status_code', '未知')})")
            return {}
        if isinstance(res, dict):
            if res.get('code') == "0000" and res.get('data', {}).get('score'):
                self.log(f"爱听任务: 获得 {res['data']['score']}", notify=True)
            elif res.get('code') != "0000":
                self.log(f"爱听任务: 积分弹窗返回 - {res.get('desc') or response_summary(res)}")
        return res

    def aiting_complete_task_api(self, type_val):
        timestamp = self.aiting_timestamp()
        nonce = self.aiting_nonce()
        sign_params = {'jwt': self.aiting_jwt, 'nonestr': nonce, 'osversion': 'Android12', 'terminalName': 'Redmi', 'timestamp': timestamp}
        sign_str = '&'.join([f"{k}={sign_params[k]}" for k in sorted(sign_params.keys())])
        requertid = self.aiting_md5(f"{sign_str}&key={AITING_SIGN_KEY_REQUERTID}")
        body_params = {'source': '3', 'timestamp': timestamp, 'token': self.aiting_woread_token, 'type': str(type_val), 'userid': self.aiting_base_userid}
        body_str = '&'.join([f"{k}={body_params[k]}" for k in sorted(body_params.keys())])
        sign = self.aiting_md5(f"{body_str}&key={AITING_SIGN_KEY_API}")
        url = f"{AITING_BASE_URL}/activity/rest/unicom/points/completiontask"
        payload = {**body_params, 'sign': sign}
        headers = {
            'AuthorizationClient': f"Bearer {self.aiting_jwt}",
            'requerttime': timestamp,
            'nonestr': nonce,
            'requertid': requertid,
            'statisticsinfo': self.aiting_statisticsinfo
        }
        self.session.post(url, json=payload, headers=headers)

    def aiting_read_points(self):
        user = getattr(self, "aiting_read_userinfo", {})
        if not all(user.get(key) for key in ("userid", "token", "userindex", "verifycode")):
            self.log("爱听任务: 缺少阅读登录上下文，跳过阅读上报")
            return
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "accesstoken": "ODZERTZCMjA1NTg1MTFFNDNFMThDRDYw",
            "User-Agent": COMMON_CONSTANTS["UA"],
        }
        base = "https://10010.woread.com.cn/ng_woread_service/rest"

        def submit(path, payload):
            payload.update({
                "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
                "token": user["token"], "userId": user["userid"],
                "userIndex": safe_int(user["userindex"]),
                "userAccount": user.get("phone") or self.mobile,
                "verifyCode": user["verifycode"],
            })
            return self.session.post(base + path, json={"sign": self.woread_encrypt(payload)}, headers=headers, timeout=20).json()

        try:
            opened = submit("/basics/newreadadd?cntindex=495589&catid=120697&chapterseno=7", {
                "userid": user["userid"], "cntindex": 495589, "chapterallindex": 42332652,
                "cnttype": 1, "cntname": "纯阳战神", "chaptertitle": "第7章 恶心的苍蝇小人", "readtype": 1,
            })
            self.log(f"爱听任务: 阅读记录 {response_summary(opened)}")
            for index in range(2):
                if index:
                    self.log("爱听任务: 等待121秒后提交第二次阅读")
                    time.sleep(121)
                result = submit("/history/addReadTime", {
                    "readTime": 2, "cntIndex": "495589", "cntType": 1,
                    "catid": "119010", "pageIndex": "10843", "cardid": "12540",
                    "cntindex": "495589", "cnttype": "1", "chapterallindex": 42332652,
                    "chapterseno": 7, "channelid": "18002061", "chapterid": "10495589007",
                    "readtype": 1, "isend": "0",
                })
                self.last_read_submission_time = time.time()
                self.log(f"爱听任务: 第{index + 1}次阅读上报 {response_summary(result)}")
        except Exception as e:
            self.log(f"爱听任务: 阅读上报异常 {type(e).__name__}")


    def aiting_task(self, is_query_only=False):
        self.log("==== 联通爱听 ====")
        if not self.aiting_login_flow():
            self.log("爱听任务: 登录失败，跳过")
            return
        self.log("爱听任务: 登录成功，正在获取任务列表...")
        try:
            self.aiting_query_integral()
        except Exception as e:
            self.log(f"爱听积分查询异常: {e}")
        task_list = self.jf_get_task_detail(self.aiting_biz_ticket)
        safe_tasks = [t for t in task_list if "\u9080\u8bf7" not in t.get('taskName', '')]
        if safe_tasks:
            self.log(f"爱听任务: 提取到 {len(safe_tasks)} 个任务")
        done_list = [t for t in safe_tasks if safe_int(t.get('finish'), 0) == 1]
        printed_names = set()
        for t in done_list:
             name = t.get('taskName')
             if name not in printed_names:
                 self.log(f"爱听任务: 已完成[{name}] {t.get('finishCount')}/{t.get('needCount')}")
                 printed_names.add(name)
        self.log(f"爱听任务: 执行前完成 {len(done_list)}/{len(safe_tasks)} 个任务")
        if not safe_tasks:
            self.log("爱听任务: ✅ 所有任务已完成")
            if is_query_only:
                self.log("爱听任务: [查询模式] 跳过任务执行...")
            return
        self.log(f"爱听任务: 尝试执行 {len(safe_tasks)} 个任务")
        if is_query_only:
            self.log("爱听任务: [查询模式] 跳过任务执行...")
            return
        for task in safe_tasks:
            task_code = task.get('taskCode')
            if not task_code:
                continue
            task_type = str(task.get('taskType', ''))
            self.log(f"爱听任务: 执行[{task.get('taskName')}] 类型 {task_type or '未知'}")
            if task_type == '4' or "签到" in task.get('taskName', ''):
                self.jf_sign(self.aiting_biz_ticket, task_code)
            else:
                self.jf_to_finish(self.aiting_biz_ticket, task_code)
            time.sleep(random.uniform(1, 2))
        self.log("爱听任务: 开始提交完成任务请求")
        for _ in range(5):
            self.aiting_complete_task_api(4)
            time.sleep(random.uniform(1, 2))
        self.aiting_complete_task_api(2)
        self.aiting_read_points()
        self.jf_pop_up(self.aiting_biz_ticket)
        after_tasks = [t for t in self.jf_get_task_detail(self.aiting_biz_ticket) if "\u9080\u8bf7" not in t.get('taskName', '')]
        after_done = [t for t in after_tasks if safe_int(t.get('finish'), 0) == 1]
        self.log(f"爱听任务: 执行后完成 {len(after_done)}/{len(after_tasks)} 个任务")
        for t in after_tasks:
            self.log(f"爱听任务: {t.get('taskName')} - {t.get('finishCount')}/{t.get('needCount')} finish={t.get('finish')}")
        try:
            self.aiting_query_integral()
        except Exception as e:
            self.log(f"爱听积分查询异常: {e}")

    def wostore_cloud_get_ticket(self):
        if not getattr(self, 'ecs_token', ''):
            self.log("沃云手机: 缺少 ecs_token，无法获取入口 Ticket")
            return ""
        city_code = ""
        if self.city_info and isinstance(self.city_info, list):
            city_code = str((self.city_info[0] or {}).get("cityCode") or "")
        headers = {
            "User-Agent": "ChinaUnicom4.x/12.11 (com.chinaunicom.mobilebusiness; build:36; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.1100}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip;q=1.0, compress;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "zh-Hans-CN;q=1.0, en-CN;q=0.9",
            "Cookie": (
                f"ecs_token={self.ecs_token};t3_token={getattr(self, 't3_token', '')};"
                f"PvSessionId={datetime.now().strftime('%Y%m%d%H%M%S')}{self.uuid};devicedId={self.uuid};"
                f"c_mobile={self.account_mobile or self.mobile};c_version=iphone_c@12.1100;city=036|{city_code}|90063345|-99;"
            ),
        }
        try:
            res = self.session.get(
                "https://m.client.10010.com/edop_ng/getTicketByNative",
                params={"token": self.ecs_token, "appId": EDOP_APPID_WOSTORE},
                headers=headers,
                timeout=20,
            ).json()
            if res.get("rsp_code") == "0000" and res.get("ticket"):
                return res.get("ticket")
            self.log(f"沃云手机: 获取入口 Ticket 失败 - {res.get('rsp_desc') or res.get('msg') or pretty_json(res)}")
        except Exception as e:
            self.log(f"沃云手机: 获取入口 Ticket 异常 {e}")
        return ""

    def wostore_cloud_login(self, ticket):
        try:
            res = self.session.post(
                "https://uphone.wostore.cn/h5api/token-service/getTokenByTicket",
                data=json.dumps({"ticket": ticket, "channel": "ST-Kuaidai001"}),
                headers={
                    "User-Agent": "ChinaUnicom4.x/12.11 (com.chinaunicom.mobilebusiness; build:36; iOS 16.6.0) Alamofire/4.7.3 unicom{version:iphone_c@12.1100}",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip;q=1.0, compress;q=0.5",
                    "Content-Type": "application/json",
                    "channel": "ST-Kuaidai001",
                    "X-Tingyun": "c=A|uBuVhVARE0A",
                    "source": "4",
                    "os": "H5",
                    "Accept-Language": "zh-Hans-CN;q=1.0, en-CN;q=0.9",
                    "channelCode": "ST-Kuaidai001",
                },
                timeout=20,
                verify=False,
            ).json()
            if str(res.get("code")) == "200" and res.get("data"):
                self.log("沃云手机: 云手机Token获取成功")
                return {"cloud_token": res.get("data")}
            self.log(f"沃云手机: 获取Token失败 - {res.get('msg') or pretty_json(res)}")
        except Exception as e:
            self.log(f"沃云手机: 登录异常 {e}")
        return None

    def wostore_cloud_h5_headers(self, cloud_token=None):
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.57(0x18003930) NetType/WIFI Language/zh_CN",
            "Host": "h5forphone.wostore.cn",
            "X-Requested-With": "XMLHttpRequest",
            **({"Authorization": cloud_token} if cloud_token else {}),
        }

    def wostore_cloud_activity_headers(self, user_token=""):
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.57(0x18003930) NetType/WIFI Language/zh_CN",
            "Host": "uphone.wostore.cn",
            "Origin": "https://uphone.wostore.cn",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-USR-TOKEN": user_token,
        }

    def wostore_cloud_headers(self, user_token):
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0601};ltst;OSVersion/16.6",
            "Authorization": user_token,
        }

    def wostore_cloud_bucp_get(self, path, user_token):
        url = f"https://uphone.wo-adv.cn/bucp{path}"
        try:
            return self.session.get(url, headers=self.wostore_cloud_headers(user_token), timeout=WOSTORE_CLOUD_TIMEOUT).json()
        except Exception as e:
            self.log(f"沃云手机: 请求异常 {e}")
            return {}

    def wostore_cloud_bucp_post(self, path, user_token, payload=None):
        url = f"https://uphone.wo-adv.cn/bucp{path}"
        try:
            return self.session.post(url, json=payload or {}, headers=self.wostore_cloud_headers(user_token), timeout=WOSTORE_CLOUD_TIMEOUT).json()
        except Exception as e:
            self.log(f"沃云手机: 请求异常 {e}")
            return {}

    def wostore_cloud_activity_post(self, path, payload, user_token="", label="云手机请求"):
        url = f"https://uphone.wostore.cn{path}"
        try:
            return self.session.post(
                url,
                data=json.dumps(payload, ensure_ascii=False),
                headers=self.wostore_cloud_activity_headers(user_token),
                timeout=WOSTORE_CLOUD_TIMEOUT,
            ).json()
        except Exception as e:
            self.log(f"沃云手机: {label}异常 {e}")
            return {}

    def wostore_cloud_user_info(self, cloud_token):
        res = self.wostore_cloud_bucp_get("/servers/system/user/getAppUserInfo", cloud_token)
        if str(res.get("code")) == "200":
            data = res.get("data") or {}
            name = data.get("nickName") or data.get("userName") or data.get("phoneNumber") or data.get("mobile")
            if name:
                self.log(f"沃云手机: 当前用户 {mask_str(name)}")
        else:
            self.log(f"沃云手机: 用户信息查询失败 - {res.get('msg') or pretty_json(res)}")
        return res

    def wostore_cloud_point_info(self, cloud_token):
        res = self.wostore_cloud_bucp_get("/servers/order/user-point/point-info", cloud_token)
        if str(res.get("code")) == "200":
            data = res.get("data") or {}
            point = data.get("balanceScoreNum") or data.get("totalPoint") or data.get("point") or data.get("availablePoint")
            if point is not None:
                self.log(f"沃云手机: 当前积分 {point}", notify=True)
        else:
            self.log(f"沃云手机: 积分查询失败 - {res.get('msg') or pretty_json(res)}")
        return res

    def wostore_cloud_sign(self, cloud_token):
        res = self.session.post(
            "https://h5forphone.wostore.cn/h5forphone/activity/signIn",
            data=json.dumps({"accesstoken": cloud_token}),
            headers=self.wostore_cloud_h5_headers(cloud_token),
            timeout=WOSTORE_CLOUD_TIMEOUT,
        ).json()
        self.log(f"沃云手机: 签到：{res.get('msg', '未知')}", notify=True)
        return res

    def wostore_cloud_sign_rewards(self, cloud_token):
        res = self.session.post(
            "https://h5forphone.wostore.cn/h5forphone/activity/signInRightList",
            data=json.dumps({"accesstoken": cloud_token}),
            headers=self.wostore_cloud_h5_headers(cloud_token),
            timeout=WOSTORE_CLOUD_TIMEOUT,
        ).json()
        for item in (res.get("data") or {}).get("goodsList", []):
            if item.get("state") == "":
                self.wostore_cloud_receive_sign_reward(cloud_token, item.get("name", ""), item.get("activityOrderId", ""))
        return res

    def wostore_cloud_receive_sign_reward(self, cloud_token, name, order_id):
        payload = {"accesstoken": cloud_token, "activityOrderid": order_id, "account": "", "accountType": ""}
        res = self.session.post(
            "https://h5forphone.wostore.cn/h5forphone/activity/raffleSignIn",
            data=json.dumps(payload),
            headers=self.wostore_cloud_h5_headers(cloud_token),
            timeout=WOSTORE_CLOUD_TIMEOUT,
        ).json()
        self.log(f"沃云手机: 领取{name}：{res.get('msg', '未知')}", notify=True)
        return res

    def wostore_cloud_activity_login(self, cloud_token, activity_code, login_activity_id=None):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/user/login",
            {"identityType": "cloudPhoneLogin", "code": cloud_token, "activityId": login_activity_id or WOSTORE_CLOUD_LOGIN_ACTIVITY_ID, "device": "device"},
            "",
            "获取云任务token",
        )
        token = (res.get("data") or {}).get("user_token") or ""
        if token:
            self.log("沃云手机: 云任务Token获取成功")
        else:
            self.log(f"沃云手机: 云任务Token获取失败 - {res.get('msg') or pretty_json(res)}")
        return token

    def wostore_cloud_points_sign(self, user_token, sign_code):
        if not sign_code:
            return {}
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/points/v1/sign",
            {"activityCode": sign_code},
            user_token,
            "积分签到",
        )
        self.log(f"沃云手机: 积分签到：{res.get('msg', '未知')}", notify=True)
        return res

    def wostore_cloud_task_list(self, user_token, activity_code):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/user/task/list",
            {"activityCode": activity_code},
            user_token,
            "查询任务列表",
        )
        data = res.get("data") or {}
        task_list = data.get("taskList") or data.get("list") or data.get("tasks") or res.get("taskList") or []
        self.log(f"沃云手机: 活动[{activity_code}]查询到 {len(task_list)} 个任务")
        if not task_list:
            self.log(f"沃云手机: 活动[{activity_code}]无可执行任务 - {response_summary(res)}")
            return res
        done = 0
        for task in task_list:
            name = task.get("taskName", "未知任务")
            code = task.get("taskCode", "")
            status = str(task.get("status") or task.get("taskStatus") or task.get("state") or "").upper()
            if status in {"OBTAINED", "RECEIVED", "FINISHED", "DONE"}:
                done += 1
                self.log(f"沃云手机: 已完成[{name}]")
            elif status in {"UNCLAIMED", "CLAIMABLE", "COMPLETED", "FINISH"}:
                self.log(f"沃云手机: 领取[{name}]奖励")
                result = self.wostore_cloud_receive_task(user_token, activity_code, code)
                if "每日限完成一个此类任务" in str(result.get("msg", "")):
                    self.log("沃云手机: 已达当日任务上限，停止本活动")
                    break
            elif status == "INCOMPLETE":
                self.log(f"沃云手机: 执行[{name}] 状态 {status or '未知'}")
                result = self.wostore_cloud_finish_task(user_token, activity_code, task)
                if "每日限完成一个此类任务" in str(result.get("msg", "")):
                    self.log("沃云手机: 已达当日任务上限，停止本活动")
                    break
            else:
                self.log(f"沃云手机: 跳过[{name}] 未知状态 {status or '空'}")
        self.log(f"沃云手机: 活动[{activity_code}]执行前已完成 {done}/{len(task_list)} 个任务")
        return res

    def wostore_cloud_finish_task(self, user_token, activity_code, task):
        task_code = task.get("taskCode", "")
        task_name = task.get("taskName") or task.get("taskDesc") or task_code
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/user/task/logs",
            {
                "logType": "01",
                "logCode": task_code,
                "logSource": "01",
                "logDetail": task_name,
            },
            user_token,
            "完成任务",
        )
        self.log(f"沃云手机: 任务状态：{res.get('msg', '未知')}")
        if str(res.get("code")) != "200":
            self.log(f"沃云手机: 任务[{task_name}]完成失败，跳过领取")
            return res
        time.sleep(15)
        return self.wostore_cloud_receive_task(user_token, activity_code, task_code)

    def wostore_cloud_receive_task(self, user_token, activity_code, task_code):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/user/task/raffle/get",
            {"activityCode": activity_code, "taskCode": task_code},
            user_token,
            "领取任务奖励",
        )
        self.log(f"沃云手机: 奖励领取结果：{res.get('msg', '未知')}", notify=True)
        return res

    def wostore_cloud_lottery_count(self, user_token, activity_code):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/user/task/list",
            {"activityCode": activity_code},
            user_token,
            "查询抽奖次数",
        )
        data = res.get("data") or {}
        count = int(data.get("rafflesLeftCount") or data.get("raffleLeftCount") or data.get("lotteryLeftCount") or res.get("rafflesLeftCount") or res.get("raffleLeftCount") or 0)
        self.log(f"沃云手机: 活动[{activity_code}]剩余抽奖次数：{count}")
        return count

    def wostore_cloud_draw(self, user_token, activity_code):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/lottery",
            {"activityCode": activity_code},
            user_token,
            "抽奖",
        )
        prize = (res.get("data") or {}).get("prizeName") or res.get("msg") or "未知奖励"
        self.log(f"沃云手机: 抽奖获得：{prize}", notify=True)
        return res

    def wostore_points_history_has_prize(self, user_token, goods_id):
        try:
            res = self.session.get(
                f"https://uphone.wostore.cn/h5api/activity-service/points/v1/lottery/history?page=1&pageSize=10&goodsId={goods_id}",
                headers=self.wostore_cloud_activity_headers(user_token),
                timeout=WOSTORE_CLOUD_TIMEOUT,
            ).json()
            today = datetime.now().strftime("%Y-%m-%d")
            data = res.get("data") or {}
            records = data if isinstance(data, list) else data.get("records", []) or data.get("list", [])
            for item in records:
                if str(item.get("createTime") or item.get("drawTime") or "").startswith(today) and item.get("prizeName"):
                    return True
        except Exception as e:
            self.log(f"沃云手机: 积分抽奖记录查询异常 {e}")
        return False

    def wostore_points_exchange_remain(self, user_token, goods_id):
        try:
            res = self.session.get(
                f"https://uphone.wostore.cn/h5api/activity-service/points/v1/exchange/list?activityCode={WOSTORE_POINTS_ACT_CODE}",
                headers=self.wostore_cloud_activity_headers(user_token),
                timeout=WOSTORE_CLOUD_TIMEOUT,
            ).json()
            data = res.get("data") or {}
            goods_list = data if isinstance(data, list) else data.get("goodsList", []) or data.get("list", [])
            for item in goods_list:
                if str(item.get("goodsId")) == str(goods_id):
                    remain = safe_int(item.get("remainUser") or item.get("remainCount") or item.get("surplusCount"), 0)
                    self.log(f"沃云手机: 积分商品[{goods_id}]剩余次数：{remain}")
                    return remain
        except Exception as e:
            self.log(f"沃云手机: 积分兑换列表查询异常 {e}")
        return 0

    def wostore_points_lottery(self, user_token, goods_id):
        res = self.wostore_cloud_activity_post(
            "/h5api/activity-service/points/v1/lottery",
            {"activityCode": WOSTORE_POINTS_ACT_CODE, "goodsId": goods_id},
            user_token,
            "积分抽奖",
        )
        results = (res.get("data") or {}).get("results") or []
        if not results and res.get("data"):
            results = [res.get("data")]
        prizes = [str(item.get("prizeName") or "未知") for item in results]
        label = "积分单抽" if str(goods_id) == str(WOSTORE_POINTS_GOODS_ID_1) else "积分10连抽"
        self.log(f"沃云手机: {label}：{res.get('msg') or '、'.join(prizes) or '未知'}", notify=True)
        return any(WOSTORE_POINTS_STOP_PRIZE in prize for prize in prizes)

    def wostore_cloud_device_status(self, cloud_token):
        res = self.wostore_cloud_bucp_get("/servers/resource/instance/list?pageNum=1&pageSize=200", cloud_token)
        rows = res.get("rows") or (res.get("data") or {}).get("rows") or []
        for device in rows:
            device_id = device.get("id") or device.get("deviceId") or ""
            status = device.get("status", "?")
            if status == "running":
                self.log("沃云手机: 设备运行正常")
            elif status == "pre_create":
                self.wostore_cloud_device_action(cloud_token, "/servers/resource/instance/cpInstanceAction", {"action": "allot", "cpInstanceId": device_id}, "激活设备")
            else:
                self.wostore_cloud_device_action(cloud_token, "/servers/resource/backup/recover", {"cpInstanceId": device_id}, "恢复设备")
        return res

    def wostore_cloud_device_action(self, cloud_token, path, payload, label):
        res = self.wostore_cloud_bucp_post(path, cloud_token, payload)
        self.log(f"沃云手机: {label}结果：{res.get('msg', '未知')}")
        return res

    def wostore_cloud_task(self, is_query_only=False):
        self.log("==== 沃云手机 ====")
        if is_query_only:
             self.log("沃云手机: [查询模式] 此平台暂无资产或余额可供查询", notify=True)
             return
        ticket = self.wostore_cloud_get_ticket()
        if not ticket:
             self.log("沃云手机: 获取入口 Ticket 失败 (为空)")
             return
        tokens = self.wostore_cloud_login(ticket)
        if not tokens:
            self.log("沃云手机: 登录失败，跳过后续任务")
            return
        cloud_token = tokens["cloud_token"]
        self.wostore_cloud_user_info(cloud_token)
        self.wostore_cloud_sign(cloud_token)
        time.sleep(3)
        self.wostore_cloud_sign_rewards(cloud_token)
        points_user_token = ""
        for activity_code in WOSTORE_CLOUD_ACTIVITY_CODES:
            user_token = self.wostore_cloud_activity_login(cloud_token, activity_code)
            if not user_token:
                continue
            if not points_user_token:
                points_user_token = user_token
            self.wostore_cloud_points_sign(user_token, WOSTORE_CLOUD_SIGN_CODE)
            self.wostore_cloud_task_list(user_token, activity_code)
        # 抽奖: 使用抽奖专用活动码 (先做该活动专属任务, 再查次数抽奖)
        for lottery_code in WOSTORE_LOTTERY_ACTIVITY_CODES:
            lottery_token = self.wostore_cloud_activity_login(cloud_token, lottery_code, login_activity_id=lottery_code)
            if not lottery_token:
                continue
            self.wostore_cloud_task_list(lottery_token, lottery_code)
            for _ in range(self.wostore_cloud_lottery_count(lottery_token, lottery_code)):
                self.wostore_cloud_draw(lottery_token, lottery_code)
                time.sleep(3)
        if points_user_token:
            if self.wostore_points_history_has_prize(points_user_token, WOSTORE_POINTS_GOODS_ID_1):
                self.log("沃云手机: 今日已中奖，跳过积分单抽")
            else:
                for _ in range(min(self.wostore_points_exchange_remain(points_user_token, WOSTORE_POINTS_GOODS_ID_1), WOSTORE_POINTS_MAX_DRAW)):
                    if self.wostore_points_lottery(points_user_token, WOSTORE_POINTS_GOODS_ID_1):
                        break
                    time.sleep(3)
            for _ in range(min(self.wostore_points_exchange_remain(points_user_token, WOSTORE_POINTS_GOODS_ID_10), WOSTORE_POINTS_MAX_DRAW)):
                self.wostore_points_lottery(points_user_token, WOSTORE_POINTS_GOODS_ID_10)
                time.sleep(3)
        self.wostore_cloud_point_info(cloud_token)
        self.wostore_cloud_device_status(cloud_token)

    def regional_task(self, is_query_only=False):
        """区域专区任务入口"""
        is_xinjiang = False
        is_henan = False
        is_yunnan = False
        is_liaoning = False
        is_anhui = False
        if hasattr(self, 'city_info') and self.city_info and isinstance(self.city_info, list):
            # 逐项容错: 整块 try/except 会导致部分省份已置位、部分未置位的"半生效"状态
            for city in self.city_info:
                if not isinstance(city, dict):
                    continue
                try:
                    pro_name = city.get('proName', '') or ''
                except Exception:
                    continue
                if "新疆" in pro_name: is_xinjiang = True
                if "河南" in pro_name: is_henan = True
                if "云南" in pro_name: is_yunnan = True
                if "辽宁" in pro_name: is_liaoning = True
                if "安徽" in pro_name: is_anhui = True
        else:
            self.log("⚠️ 缺少归属地信息, 区域专区任务将全部跳过")
        rc = globalConfig.get("regional_config", {})
        if is_query_only:
            self.log("==== 区域专区 (查询模式) ====")
            if is_xinjiang:
                self.log("新疆专区: [查询模式] 跳过每日打卡，尝试查询每月抽奖记录")
                try:
                    ticket_res = self.openPlatLineNew("https://zy100.xj169.com/touchpoint/openapi/jumpHandRoom1G?source=155&type=02")
                    if ticket_res and ticket_res.get("ticket"):
                        token = self.xj_get_token(ticket_res.get("ticket"))
                        if token:
                            self.xj_query_monthly_draw_records(token)
                except Exception as e:
                    self.log(f"新疆专区: [查询模式] 查询每月抽奖记录异常 {e}")
            if is_henan:
                is_signed = self.shangdu_get_sign_status()
                if is_signed is True:
                    self.log("河南商都: [状态查询] 今日已签到")
                elif is_signed is False:
                    self.log("河南商都: [状态查询] 今日未签到")
                else:
                    self.log("河南商都: [状态查询] 查询失败")
            if is_yunnan:
                self.yunnan_life_task(is_query_only=True)
            if is_liaoning:
                self.ln_flmf_task(is_query_only=True)
            if rc.get("run_linktech", True):
                try:
                    self.ln_linktech_all_task(is_query_only=True)
                except Exception as e:
                    self.log(f"linktech 活动组异常: {e}")
            if is_anhui and AH_FRIDAY_AMOUNT:
                self.log(f"安徽超级星期五: [查询模式] 目标面额{AH_FRIDAY_AMOUNT}元 (仅周五10点执行)")
            return
        if is_xinjiang:
            self.log("==== 新疆专区 ====")
            self.xj_task_main()
        if is_henan:
            self.log("==== 河南商都 ====")
            self.shangdu_task_main()
        if is_yunnan:
            self.log("==== 云南生活 ====")
            self.yunnan_life_task()
        if is_liaoning:
            self.log("==== 辽宁福利魔方 ====")
            self.ln_flmf_task()
        # linktech 活动组(天天刮奖/沃享生活/专享权益/专属邀请码)不受归属地限制,
        # 专属邀请码等是全国活动, 因此独立于 is_liaoning 判断。
        if rc.get("run_linktech", True):
            try:
                self.ln_linktech_all_task()
            except Exception as e:
                self.log(f"linktech 活动组异常: {e}")
        if is_anhui and AH_FRIDAY_AMOUNT and rc.get("run_ah_friday", True):
            self.log("==== 安徽超级星期五 ====")
            self.ah_friday_task()

    def yunnan_life_base_headers(self, token=None, extra=None):
        headers = {
            "Referer": "https://wsm.wx.yn10010.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept-Language": "zh-CN,en-US;q=0.8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.1001};ltst;OSVersion/16.6",
        }
        if token:
            headers["token"] = token
        if extra:
            headers.update(extra)
        return headers

    def yunnan_life_calc_sign(self, payload):
        parts = []
        for key in sorted(payload.keys()):
            value = payload[key]
            if isinstance(value, dict):
                encoded = quote(json.dumps(value, ensure_ascii=False, separators=(',', ':')), safe="")
            else:
                encoded = quote(str(value), safe="")
            parts.append(f"{key}={encoded}")
        raw = "&".join(parts).lower() + YUNNAN_LIFE_SIGN_SALT
        return hashlib.md5(hashlib.md5(raw.encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()

    def yunnan_life_signed_headers(self, token, payload):
        return self.yunnan_life_base_headers(token, {
            "Origin": YUNNAN_LIFE_BASE_URL,
            "accessKeyId": YUNNAN_LIFE_ACCESS_KEY,
            "time": str(round(time.time() * 1000)),
            "sign": self.yunnan_life_calc_sign(payload),
        })

    def yunnan_life_get_ticket(self):
        if not self.ecs_token:
            return None
        try:
            res = self.session.get(
                "https://m.client.10010.com/mobileService/openPlatform/openPlatLineNew.htm",
                params={
                    "to_url": YUNNAN_LIFE_TO_URL,
                    "amp;s": "100000425",
                    "amp;boothCode": "YN-QCQYCS245",
                    "amp;boothAccessMode": "24",
                },
                headers={
                    "Cookie": f"ecs_token={self.ecs_token}",
                    "Referer": "https://wsm.wx.yn10010.com/",
                    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Site": "cross-site",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "User-Agent": self.yunnan_life_base_headers().get("User-Agent"),
                },
                allow_redirects=False,
                timeout=15,
            )
            location = res.headers.get("Location", "")
            match = re.search(r'ticket=([^&]+)', location)
            return match.group(1) if match else None
        except Exception as e:
            self.log(f"云南生活: 获取 ticket 异常: {e}")
            return None

    def yunnan_life_get_token(self, ticket):
        if not ticket:
            return None
        try:
            resp = self.session.get(
                f"{YUNNAN_LIFE_BASE_URL}/2b2c-mobile/getPhoneNumber",
                params={"ticket": ticket},
                headers=self.yunnan_life_base_headers(extra={"Content-Type": "application/json;charset=gb2312"}),
                timeout=15,
            )
            token = resp.headers.get("token") or resp.headers.get("Token")
            if not token:
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                token = data.get("token") or data.get("data", {}).get("token")
            if not token:
                self.log(f"云南生活: 未找到 token，响应: {resp.text[:160]}")
                return None
            return token if str(token).startswith("Bearer ") else f"Bearer {token}"
        except Exception as e:
            self.log(f"云南生活: 获取 token 异常: {e}")
            return None

    def yunnan_life_login(self):
        ticket = self.yunnan_life_get_ticket()
        if not ticket:
            self.log("云南生活: 获取 ticket 失败")
            return None
        token = self.yunnan_life_get_token(ticket)
        if not token:
            self.log("云南生活: 获取 token 失败")
            return None
        return token

    def yunnan_life_do_task(self, token, payload):
        task_name = payload.get("taskName", payload.get("taskCode", "未知任务"))
        try:
            res = self.session.post(
                f"{YUNNAN_LIFE_BASE_URL}/2b2c-mobile/activity/task/addTaskUser",
                data=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
                headers=self.yunnan_life_signed_headers(token, payload),
                timeout=15,
            ).json()
            if res.get("resultCode") == "0000":
                self.log(f"云南生活: ✅ {task_name}")
            else:
                self.log(f"云南生活: ❌ {task_name}: {res.get('resultMsg', '')}")
        except Exception as e:
            self.log(f"云南生活: [{task_name}] 异常: {e}")

    def yunnan_life_do_lottery(self, token, times=2):
        payload = {"actId": YUNNAN_LIFE_ACT_ID, "boothCode": ""}
        headers = self.yunnan_life_base_headers(token, {"Origin": YUNNAN_LIFE_BASE_URL})
        for i in range(times):
            try:
                res = self.session.post(
                    f"{YUNNAN_LIFE_BASE_URL}/2b2c-mobile/acttmpl/lottery/actLuckyDrawy",
                    data=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
                    headers=headers,
                    timeout=15,
                ).json()
                if res.get("resultCode") == "0000":
                    self.log(f"云南生活: ✅ 第{i + 1}次抽奖请求成功")
                else:
                    self.log(f"云南生活: ❌ 第{i + 1}次抽奖失败: {res.get('resultMsg', '')}")
            except Exception as e:
                self.log(f"云南生活: 第{i + 1}次抽奖异常: {e}")
            if i < times - 1:
                time.sleep(2)

    def yunnan_life_get_lottery_results(self, token):
        try:
            resp = self.session.get(
                f"{YUNNAN_LIFE_BASE_URL}/2b2c-mobile/acttmpl/lottery/getUserRecordListActInfo",
                params={"actId": YUNNAN_LIFE_ACT_ID, "periodId": YUNNAN_LIFE_ACT_ID},
                headers=self.yunnan_life_base_headers(token, {"Content-Type": "application/json;charset=gb2312"}),
                timeout=15,
            )
            data = resp.json()
            today = datetime.now().strftime("%Y-%m-%d")
            awards = []
            for item in data.get("data", {}).get("recordList", []):
                if str(item.get("createTime", "")).startswith(today):
                    awards.append(item.get("awardName", "未知"))
            if awards:
                for award in awards:
                    self.log(f"云南生活: 🎁 抽奖结果 - {award}", notify=True)
            else:
                self.log("云南生活: 今日暂无抽奖记录")
        except Exception as e:
            self.log(f"云南生活: 查询抽奖结果异常: {e}")

    def yunnan_life_get_bean_balance(self, token):
        try:
            payload = {}
            res = self.session.post(
                f"{YUNNAN_LIFE_BASE_URL}/user/beans/api/getTotalAvailableBeansByPhone",
                data=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
                headers=self.yunnan_life_signed_headers(token, payload),
                timeout=15,
            ).json()
            if res.get("resultCode") == "0000":
                self.log(f"云南生活: 💰 当前云豆余额: {res.get('data', 0)}", notify=True)
            else:
                self.log(f"云南生活: 获取云豆失败: {res.get('resultMsg', '')}")
        except Exception as e:
            self.log(f"云南生活: 查询云豆异常: {e}")

    def yunnan_life_task(self, is_query_only=False):
        token = self.yunnan_life_login()
        if not token:
            return
        if is_query_only:
            self.log("云南生活: [查询模式] 查询云豆余额")
            self.yunnan_life_get_bean_balance(token)
            return
        for task in YUNNAN_LIFE_TASKS:
            self.yunnan_life_do_task(token, task)
            time.sleep(2)
        self.yunnan_life_do_lottery(token, times=2)
        self.yunnan_life_get_lottery_results(token)
        self.yunnan_life_get_bean_balance(token)

    def xj_task_main(self):
        ticket_res = self.openPlatLineNew("https://zy100.xj169.com/touchpoint/openapi/jumpHandRoom1G?source=155&type=02")
        if not ticket_res or not ticket_res.get("ticket"):
            self.log("新疆专区: 获取入口 ticket 失败")
            return
        token = self.xj_get_token(ticket_res.get("ticket"))
        if token:
            # 每日抽奖必须用当月活动ID, 与 xj_monthly_draw_task 保持一致
            # (原先硬编码 "Jan2026Act" 会导致 12 月仍在抽 1 月活动, 拿不到当月签到奖励)
            self.xj_do_draw(token, XJ_ACTIVITY_ID)
            day = datetime.now().day
            if 19 <= day <= 25:
                self.xj_usersday_task(token)
            self.xj_monthly_draw_task(token)

    def xj_get_token(self, ticket):
        """获取新疆活动 userToken。
        新版活动 getTokenAndCity 已不再返回 token, 需改用 /openapi/getToken (返回 JWT);
        为兼容两版, 依次尝试 getToken -> getTokenAndCity。
        """
        if isinstance(ticket, dict):
            ticket = ticket.get("ticket")
        headers = {
            "Referer": f"https://zy100.xj169.com/touchpoint/openapi/jumpHandRoom1G?source=155&type=02&ticket={ticket}",
            "User-Agent": XJ_USER_AGENT,
        }
        for path in ("/touchpoint/openapi/getToken", "/touchpoint/openapi/getTokenAndCity"):
            try:
                res = self.session.post(
                    "https://zy100.xj169.com" + path,
                    data={"ticket": ticket}, headers=headers, timeout=15).json()
                result = res.get('result') or {}
                data = result.get('data') if isinstance(result.get('data'), dict) else res.get('data')
                token = None
                if isinstance(data, dict):
                    token = data.get('token')
                elif isinstance(data, str) and data.count('.') == 2:
                    token = data  # getToken 直接返回 JWT 字符串
                if not token and isinstance(res.get('data'), str) and res['data'].count('.') == 2:
                    token = res['data']
                if token:
                    return token
            except Exception as e:
                self.log(f"新疆专区: 获取 token({path}) 异常 {e}")
        return None

    def xj_do_draw(self, token, act_id):
        """每日打卡抽奖。
        注意: 新版活动(2026)接口为 /themeAct/draw_{Mon}{Year}Act,
        activityId 带 Theme 前缀; 旧的 /marchAct/draw_xxx 已 404。
        """
        try:
            headers = {
                "User-Agent": XJ_USER_AGENT,
                "userToken": token,
                "Referer": f"https://zy100.xj169.com/touchpoint/pages/drawAct2026/Theme{act_id}_lhj.html",
            }
            theme_id = f"Theme{act_id}"
            url = f"https://zy100.xj169.com/touchpoint/openapi/themeAct/draw_{act_id}"
            # 先取公共参数, 服务端会校验该标志
            comm_high = self.xj_common_hight_flag(token, theme_id)
            payload = {"activityId": f"daka{theme_id}", "prizeId": "", "commHighFlag": comm_high}
            res = self.session.post(url, data=payload, headers=headers, timeout=15).json()
            code = res.get("code")
            msg = str(res.get("msg", ""))
            data = res.get("data", "")
            if code in ("SUCCESS", 0):
                self.log(f"新疆专区: 每日打卡 - {data or msg}", notify=True)
            else:
                self.log(f"新疆专区: 每日打卡失败[{code}] - {data or msg}")
        except Exception as e:
            self.log(f"新疆专区: 打卡异常 {e}")

    def xj_common_hight_flag(self, token, activity_id):
        """获取公共参数 commHighFlag (抽奖前需先调用)"""
        try:
            headers = {"User-Agent": XJ_USER_AGENT, "userToken": token}
            res = self.session.post(
                "https://zy100.xj169.com/touchpoint/openapi/themeAct/commonHightRest",
                data={"activityId": activity_id}, headers=headers, timeout=12).json()
            if res.get("code") in ("SUCCESS", 0):
                return res.get("data", False)
        except Exception:
            pass
        return False

    def xj_usersday_task(self, token):
        """新疆客户日秒杀。年份随当年变化, 避免写死过期活动。"""
        try:
            year = datetime.now().year
            act_id = f"UsersDay{year}Act"
            headers = {
                "User-Agent": XJ_USER_AGENT,
                "userToken": token,
                "Referer": f"https://zy100.xj169.com/touchpoint/pages/drawAct2026/Theme{act_id}_lhj.html",
            }
            url = f"https://zy100.xj169.com/touchpoint/openapi/themeAct/draw_{act_id}"
            data = {"activityId": act_id, "prizeId": "hfq_twenty", "commHighFlag": False}
            res = self.session.post(url, data=data, headers=headers, timeout=15).json()
            msg = res.get('msg') or res.get('data') or "失败"
            self.log(f"新疆客户日: 秒杀结果 - {msg}", notify=True)
        except Exception as e:
            self.log(f"新疆客户日: 秒杀异常 {e}")

    def xj_monthly_draw_once(self, token):
        headers = {
            "User-Agent": XJ_USER_AGENT,
            "userToken": token,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        payload = {"activityId": XJ_ACTIVITY_ID, "prizeId": "", "commHighFlag": "false"}
        try:
            res = self.session.post(
                f"https://zy100.xj169.com/touchpoint/openapi/themeAct/draw_{XJ_ACTIVITY_ID}",
                data=payload,
                headers=headers,
                timeout=10,
            ).json()
            code = res.get("code")
            msg = str(res.get("msg", ""))
            msg_type = str(res.get("msgType", ""))
            data = res.get("data", "")
            if code == "ERROR":
                data_str = str(data)
                if "已用完" in data_str or "已抽完" in data_str or msg_type == "101":
                    return "done", f"今日机会已用尽 ({data_str or msg or '无可用次数'})"
                if "频率过高" in msg:
                    return "done", "接口频率限制"
                if "缺少参数" in msg:
                    return "invalid", "token 已失效"
                return "done", f"抽奖失败: {data_str or msg or '未知错误'}"
            if code == "SUCCESS":
                if msg == "thanks1":
                    return "continue", f"未中奖 ({data or msg})"
                return "won", f"中奖: {data or '未知奖品'}"
            if str(code) == "401":
                return "invalid", "token 已失效"
            return "continue", f"未中奖 ({msg or data or code})"
        except Exception as e:
            return "error", f"请求异常: {e}"

    def xj_query_monthly_draw_records(self, token):
        headers = {
            "User-Agent": XJ_USER_AGENT,
            "userToken": token,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        try:
            res = self.session.post(
                "https://zy100.xj169.com/touchpoint/openapi/drawAct/getPrizesScroll",
                data={"activityId": XJ_ACTIVITY_ID},
                headers=headers,
                timeout=10,
            ).json()
            data = res.get("data", [])
            if not data:
                self.log("新疆专区: 每月抽奖暂无中奖记录")
                return
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list) and data and isinstance(data[0], str):
                for item in data[:5]:
                    self.log(f"新疆专区: 每月抽奖记录 - {item}", notify=True)
                return
            displayed = 0
            for item in data:
                if not isinstance(item, dict):
                    continue
                prize_name = item.get("prizeName") or item.get("prizeId") or "未知奖品"
                draw_ts = safe_int(item.get("drawDate"), 0)
                draw_date = datetime.fromtimestamp(draw_ts / 1000).strftime("%m-%d") if draw_ts else "未知时间"
                self.log(f"新疆专区: 每月抽奖记录 - {prize_name} ({draw_date})", notify=True)
                displayed += 1
                if displayed >= 5:
                    break
            if displayed == 0:
                self.log("新疆专区: 每月抽奖暂无可展示记录")
        except Exception as e:
            self.log(f"新疆专区: 查询每月抽奖记录异常 {e}")

    def xj_monthly_draw_task(self, token):
        self.log(f"新疆专区: 每月抽奖活动 {XJ_ACTIVITY_ID}")
        for i in range(XJ_MONTHLY_DRAW_ATTEMPT_COUNT):
            status, msg = self.xj_monthly_draw_once(token)
            self.log(
                f"新疆专区: 每月抽奖第{i + 1}次 - {msg}",
                notify=status == "won",
            )
            if status in {"done", "won", "invalid"}:
                break
            time.sleep(random.uniform(1, 2))
        self.xj_query_monthly_draw_records(token)

    def shangdu_get_sign_status(self):
        try:
            url = "https://app.shangdu.com/monthlyBenefit/v1/signIn/queryCumulativeSignAxis"
            headers = {
                "Origin": "https://app.shangdu.com",
                "Referer": "https://app.shangdu.com/monthlyBenefit/index.html",
                "edop_flag": "0", "Content-Type": "application/json"
            }
            res = self.session.post(url, json={}, headers=headers).json()
            if res.get('result', {}).get('code') == "0000":
                return res.get('result', {}).get('data', {}).get('todaySignFlag') == "1"
            return None
        except Exception as e:
            self.log(f"河南商都: 查询签到状态异常: {e}")
            return None

    def shangdu_sign_retry(self):
        try:
            url = "https://app.shangdu.com/monthlyBenefit/v1/signIn/userSignIn"
            headers = {
                "Origin": "https://app.shangdu.com",
                "Referer": "https://app.shangdu.com/monthlyBenefit/index.html",
                "edop_flag": "0", "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json"
            }
            res = self.session.post(url, json={}, headers=headers).json()
            code = res.get('result', {}).get('code')
            data = res.get('result', {}).get('data', {})
            if code == "0000":
                prize = data.get('prizeResp', {}).get('prizeName')
                if prize: self.log(f"河南商都: 签到成功(重试) - 获得 {prize}", notify=True)
                else: self.log("河南商都: 签到成功(重试)")
            elif code == "0019":
                self.log("河南商都: 重试仍返回重复签到")
            else:
                self.log(f"河南商都: A签到重试失败 - {res.get('result', {}).get('msg')}")
        except Exception as e:
            self.log(f"河南商都: 签到重试异常 {e}")

    def shangdu_task_main(self):
        if not self.ecs_token: return
        url = f"https://m.client.10010.com/edop_ng/getTicketByNative?appId={EDOP_APPID_SHANGDU}&token={self.ecs_token}"
        res = self.session.get(url).json()
        ticket = res.get('result', {}).get('ticket')
        if not ticket:
            self.log("河南商都: 获取Ticket失败")
            return
        login_url = f"https://app.shangdu.com/monthlyBenefit/v1/common/config?ticket={ticket}"
        headers_login = {
             "Origin": "https://app.shangdu.com",
             "Referer": "https://app.shangdu.com/monthlyBenefit/index.html",
             "edop_flag": "0", "Accept": "application/json, text/plain, */*"
        }
        self.session.get(login_url, headers=headers_login)
        time.sleep(1.5)
        sign_url = "https://app.shangdu.com/monthlyBenefit/v1/signIn/userSignIn"
        headers_sign = {
             "Origin": "https://app.shangdu.com",
             "Referer": "https://app.shangdu.com/monthlyBenefit/index.html",
             "edop_flag": "0", "X-Requested-With": "XMLHttpRequest",
             "Content-Type": "application/json"
        }
        res_sign = self.session.post(sign_url, json={}, headers=headers_sign).json()
        code = res_sign.get('result', {}).get('code')
        data = res_sign.get('result', {}).get('data', {})
        if code == "0000":
             if data.get('value') == "0001":
                 self.log("河南商都: 签到失败 - Cookie无效")
             else:
                 prize = data.get('prizeResp', {}).get('prizeName', '已签到')
                 self.log(f"河南商都: 签到结果 - {prize}", notify=True)
        elif code == "0019":
             time.sleep(1)
             is_signed = self.shangdu_get_sign_status()
             if is_signed is True:
                 self.log("河南商都: 今日已签到")
             elif is_signed is False:
                 self.log("河南商都: 状态未签到但返回重复，尝试重试...")
                 time.sleep(2)
                 self.shangdu_sign_retry()
             else:
                 self.log("河南商都: 今日已签到 (状态未知)")
        else:
             self.log(f"河南商都: 签到失败 - {code} : {res_sign.get('result', {}).get('msg')}")

    # linktech(辽宁福利魔方) 4 个活动的 actcode 与前缀。
    # 接口清单来自 flmf / st 两个前端包的 api.js 与 api2.js:
    #   welfareCenter → /lv-apiaccess/welfareCenter/*   (沃享生活, 活动专区 core)
    #   sign          → /lv-apiaccess/welfareCenter/*   (签到有礼 moreShatter)
    #   excluSive     → /lv-web/playWeb/memberPromotion/* (专属邀请码)
    #   scratchst / vipRights: 服务端已下线(302 → endOfActivity.html),
    #                       flmf 前端包中也已无对应路由, 仅保留探测与明确日志。
    LN_ACT_CODES = {
        "sign":          {"name": "签到有礼",   "prefix": "welfareCenter"},
        "welfareCenter": {"name": "沃享生活",   "prefix": "welfareCenter"},
        "excluSive":     {"name": "专属邀请码", "prefix": ""},
        "scratchst":     {"name": "天天刮奖",   "prefix": "welfareCenter"},
        "vipRights":     {"name": "专享权益",   "prefix": "welfareCenter"},
    }

    def ln_flmf_get_sid(self, actcode="sign"):
        """linktech: 通过 openPlatLineNew → autoLogin 获取 sid

        actcode 决定落地页与可用接口:
          sign / welfareCenter / scratchst / vipRights / excluSive
        服务端对已下线活动会 302 到 endOfActivity.html, 此时返回 None。
        """
        act_info = self.LN_ACT_CODES.get(actcode, {"name": actcode})
        act_name = act_info.get("name", actcode)
        try:
            ticket_res = self.openPlatLineNew(
                f"https://weixin.linktech.hk/lv-web/handHall/autoLogin?actcode={actcode}")
            if not ticket_res or not ticket_res.get('ticket'):
                self.log(f"{act_name}: 获取ticket失败")
                return None
            ticket = ticket_res['ticket']
            type_val = ticket_res.get('type', '06')
            mobile = getattr(self, 'account_mobile', getattr(self, 'mobile', ''))
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            postage = hashlib.md5(f"{mobile}{timestamp}".encode()).hexdigest()
            login_url = "https://weixin.linktech.hk/lv-web/handHall/autoLogin"
            params = {
                "actcode": actcode,
                "type": type_val,
                "ticket": ticket,
                "version": COMMON_CONSTANTS["APP_VERSION"],
                "timestamp": timestamp,
                "desmobile": mobile,
                "num": "0",
                "postage": postage,
                "userNumber": mobile
            }
            res = self.session.get(login_url, params=params, allow_redirects=False, timeout=15)
            if res.status_code != 302 or 'Location' not in res.headers:
                self.log(f"{act_name}: autoLogin期望302, 实际{res.status_code}")
                return None
            loc = res.headers['Location']
            if 'endOfActivity' in loc:
                self.log(f"{act_name}: 服务端活动已下线 (autoLogin → endOfActivity.html)", notify=True)
                return None
            sid_match = re.search(r'sid[=%]3[Dd]?([a-f0-9]{32})', loc)
            if not sid_match:
                parsed = urlparse(unquote(loc))
                qs = parse_qs(parsed.query)
                params_val = qs.get('params', [''])[0]
                if 'sid=' in params_val:
                    inner_qs = parse_qs(params_val)
                    sid = inner_qs.get('sid', [''])[0]
                else:
                    sid = qs.get('sid', [''])[0]
            else:
                sid = sid_match.group(1)
            if sid and len(sid) == 32:
                self.log(f"{act_name}: 获取sid成功 ({sid[:8]}...)")
                return sid
            self.log(f"{act_name}: 重定向中未找到sid")
        except Exception as e:
            self.log(f"{act_name}: 获取sid异常 - {e}")
        return None

    def ln_flmf_api(self, sid, endpoint, extra_data=None, actcode="sign", path_prefix=None):
        """linktech: 通用API调用

        endpoint 形如 "welfareCenter/signInInit" 或 "playWeb/memberPromotion/loadInit",
        即 "<模块>/<接口>"。
        path_prefix 非空时作为**完整路径前缀**(如 "/lv-web"), 此时不再拼 lv-apiaccess;
        为空时默认走 /lv-apiaccess/<模块>/<接口>。
        请求体统一带 sid 与 actcode(与前端一致)。
        """
        if path_prefix:
            full_path = f"{path_prefix.rstrip('/')}/{endpoint.lstrip('/')}"
            url = f"https://weixin.linktech.hk{full_path}"
        else:
            full_path = endpoint.lstrip('/')
            url = f"https://weixin.linktech.hk/lv-apiaccess/{full_path}"
        act_info = self.LN_ACT_CODES.get(actcode, {"name": actcode})
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://weixin.linktech.hk",
            "Referer": f"https://weixin.linktech.hk/lv-web/handHall/autoLogin?actcode={actcode}&sid={sid}",
            "User-Agent": f"Mozilla/5.0 (Linux; Android 10; MI 8) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.146 Mobile Safari/537.36; unicom{{version:{APP_VERSION}}}"
        }
        data = f"sid={sid}&actcode={actcode}"
        if extra_data:
            data += f"&{extra_data}"
        try:
            res = self.session.post(url, headers=headers, data=data, timeout=15).json()
            return res
        except Exception as e:
            self.log(f"{act_info.get('name', actcode)}: {full_path} 请求异常 - {e}")
            return None

    def ln_flmf_task(self, is_query_only=False):
        """辽宁福利魔方(签到有礼 sign): 主入口"""
        sid = self.ln_flmf_get_sid("sign")
        if not sid:
            return
        res = self.ln_flmf_api(sid, "welfareCenter/addUser", actcode="sign")
        if not res or res.get('resultCode') != '0000':
            self.log(f"辽宁福利魔方: 用户初始化失败 - {(res or {}).get('resultMsg', '无响应')}")
            return
        time.sleep(1)
        init_res = self.ln_flmf_api(sid, "welfareCenter/signInInit", actcode="sign")
        if init_res and init_res.get('resultCode') == '0000':
            init_data = init_res.get('data', {})
            is_signed = init_data.get('isSigned', 0)
            consecutive = init_data.get('consecutiveDays', 0)
            if is_signed:
                self.log(f"辽宁福利魔方: 今日已签到 (连续{consecutive}天)")
            elif is_query_only:
                self.log(f"辽宁福利魔方: 今日未签到 (连续{consecutive}天)")
            else:
                time.sleep(1)
                sign_res = self.ln_flmf_api(sid, "welfareCenter/signIn", actcode="sign")
                if sign_res and sign_res.get('resultCode') == '0000':
                    self.log(f"辽宁福利魔方: ✅ 签到成功 (连续{consecutive + 1}天)", notify=True)
                else:
                    self.log(f"辽宁福利魔方: 签到失败 - {(sign_res or {}).get('resultMsg', '无响应')}")
        else:
            self.log(f"辽宁福利魔方: 查询签到状态失败 - {(init_res or {}).get('resultMsg', '无响应')}")
        time.sleep(1)
        info_res = self.ln_flmf_api(sid, "welfareCenter/getUserInfo", actcode="sign")
        if info_res and info_res.get('resultCode') == '0000':
            info = info_res.get('data', {})
            wobi = info.get('woBi', 0)
            sign_times = info.get('signTimes', 0)
            member_wobi = info.get('memberwobi', 0)
            member_trun = info.get('membertrun', 0)
            rights_num = info.get('rightsNum', '0')
            self.log(f"辽宁福利魔方: 沃币{wobi} | 累计签到{sign_times}天 | 会员碎片{member_wobi} | 等级{member_trun} | 权益{rights_num}次", notify=True)
        if is_query_only:
            return
        time.sleep(1)
        task_res = self.ln_flmf_api(sid, "welfareCenter/taskList", "refresh=0&nowTask=", actcode="sign")
        if task_res and task_res.get('resultCode') == '0000':
            groups = task_res.get('data', {}).get('taskInfoList', [])
            for group in groups:
                tasks = group.get('taskInfoList', [])
                for t in tasks:
                    status = "✅" if t.get('done', 0) > 0 else "⏳"
                    self.log(f"辽宁福利魔方: {status} {t.get('taskName')} ({t.get('done', 0)}/{t.get('count', 0)})")

    # ---------- 沃享生活 (welfareCenter) ----------
    # 接口与参数取自 flmf 前端包 api2.js / api.js 及对应视图调用:
    #   loadInitPage   {sid, actcode}
    #   taskList       {sid, actcode, refresh, nowTask}
    #   completeTask   {sid, actcode, taskId}
    #   receivePrize   {sid, taskId}
    #   turntableLuckDraw {sid, actcode}
    #   memberCenter   {sid, actcode}
    #   getUserInfo    {sid, actcode}
    def ln_welfare_task(self, is_query_only=False):
        """沃享生活(welfareCenter): 活动专区

        注意: 该活动并非全国通用。实测浙江归属地账号调用 addUser 会返回
        0010「本活动限中国联通手机号码归属地为辽宁用户参与」,
        所以非辽宁用户只能走到限制判定这一步。
        """
        sid = self.ln_flmf_get_sid("welfareCenter")
        if not sid:
            return
        # 1) 用户初始化(受归属地限制, 失败即终止)
        res = self.ln_flmf_api(sid, "welfareCenter/addUser", actcode="welfareCenter")
        if not res:
            self.log("沃享生活: addUser 无响应")
            return
        if res.get('resultCode') != '0000':
            msg = res.get('resultMsg', '无响应')
            self.log(f"沃享生活: 无法参与 - {msg}")
            return
        time.sleep(1)

        # 2) 活动初始化
        init = self.ln_flmf_api(sid, "welfareCenter/loadInitPage", actcode="welfareCenter")
        if init and init.get('resultCode') == '0000':
            d = init.get('data', {}) or {}
            self.log(f"沃享生活: 活动初始化成功 (沃币 {d.get('woBi', '?')} | "
                     f"等级 {d.get('membertrun', '?')} | 权益 {d.get('rightsNum', '?')}次)")
        else:
            self.log(f"沃享生活: 初始化失败 - {(init or {}).get('resultMsg', '无响应')}")

        time.sleep(1)

        # 3) 任务列表 + 做任务 + 领奖
        task_res = self.ln_flmf_api(sid, "welfareCenter/taskList",
                                    "refresh=0&nowTask=", actcode="welfareCenter")
        done_cnt = 0
        if task_res and task_res.get('resultCode') == '0000':
            groups = task_res.get('data', {}).get('taskInfoList', []) or []
            tasks = []
            for group in groups:
                tasks.extend(group.get('taskInfoList', []) or [])
            for t in tasks:
                done = t.get('done', 0) or 0
                count = t.get('count', 0) or 0
                name = t.get('taskName') or t.get('taskId') or '未知任务'
                tid = t.get('id') or t.get('taskId')
                status = "✅" if done > 0 else "⏳"
                self.log(f"沃享生活: {status} {name} ({done}/{count})")
                if done > 0 or not tid or is_query_only:
                    continue
                # 做任务
                time.sleep(1)
                ct = self.ln_flmf_api(sid, "welfareCenter/completeTask",
                                      f"taskId={tid}", actcode="welfareCenter")
                if ct and ct.get('resultCode') == '0000':
                    self.log(f"沃享生活: ✅ 完成「{name}」", notify=True)
                    done_cnt += 1
                    # 领奖(接口需要 taskId, 有的活动 taskId 与奖品一致)
                    time.sleep(1)
                    rp = self.ln_flmf_api(sid, "welfareCenter/receivePrize",
                                          f"taskId={tid}", actcode="welfareCenter")
                    if rp and rp.get('resultCode') == '0000':
                        rd = rp.get('data', {}) or {}
                        prize = rd.get('prizeName') or rd.get('sendNum') or rd.get('msg') or ''
                        self.log(f"沃享生活: 🎁 领取成功「{name}」 {prize}", notify=True)
                    elif rp:
                        self.log(f"沃享生活: 领奖未成功 - {rp.get('resultMsg', '无响应')}")
                else:
                    self.log(f"沃享生活: 做任务失败「{name}」 - {(ct or {}).get('resultMsg', '无响应')}")
            if done_cnt:
                self.log(f"沃享生活: 本次完成 {done_cnt} 个任务", notify=True)
        else:
            self.log(f"沃享生活: 任务列表获取失败 - {(task_res or {}).get('resultMsg', '无响应')}")

        if is_query_only:
            return

        # 4) 转盘抽奖
        time.sleep(1)
        luck = self.ln_flmf_api(sid, "welfareCenter/turntableLuckDraw",
                                actcode="welfareCenter")
        if luck and luck.get('resultCode') == '0000':
            ld = luck.get('data', {}) or {}
            prize = ld.get('prizeName') or ld.get('sendNum') or ''
            if prize and '谢谢' not in str(prize):
                self.log(f"沃享生活: 🎰 抽奖获得 {prize}", notify=True)
            else:
                self.log(f"沃享生活: 🎰 抽奖结果: {prize or '无奖励'}")
        elif luck:
            self.log(f"沃享生活: 抽奖 - {luck.get('resultMsg', '无响应')}")

        # 5) 会员中心(权益兑换)
        time.sleep(1)
        mc = self.ln_flmf_api(sid, "welfareCenter/memberCenter", actcode="welfareCenter")
        if mc and mc.get('resultCode') == '0000':
            md = mc.get('data', {}) or {}
            grades = md.get('memberGradeList') or md.get('gradeList') or []
            if grades:
                self.log(f"沃享生活: 会员中心 {len(grades)} 项权益可查")
        elif mc:
            self.log(f"沃享生活: 会员中心 - {mc.get('resultMsg', '无响应')}")

    # ---------- 专属邀请码 (excluSive) ----------
    # 接口取自 st 前端包 LV-202206-06/api.js:
    #   /lv-web/playWeb/memberPromotion/loadInit    {actcode, sid, flag, startRow, pageSize}
    #   /lv-web/playWeb/memberPromotion/myExclCode  {actcode, sid}
    #   /lv-web/playWeb/memberPromotion/exclCodeList{actcode, sid, flag, startRow, pageSize}
    # 注意前缀是 /lv-web/... 而不是 /lv-apiaccess/...
    def ln_exclusive_task(self, is_query_only=False):
        """专属邀请码(excluSive): 我的专属码 + 邀请记录"""
        sid = self.ln_flmf_get_sid("excluSive")
        if not sid:
            return
        # 1) 活动初始化(拿邀请统计与规则)
        init = self.ln_flmf_api(sid, "playWeb/memberPromotion/loadInit",
                                "flag=0&startRow=1&pageSize=5",
                                actcode="excluSive",
                                path_prefix="/lv-web")
        if not init or init.get('resultCode') != '0000':
            self.log(f"专属邀请码: 初始化失败 - {(init or {}).get('resultMsg', '无响应')}")
            return
        d = init.get('data', {}) or {}
        self.log(f"专属邀请码: 新增 {d.get('newCount', 0)} | 活跃 {d.get('livelyCount', 0)} | "
                 f"服务 {d.get('serveCount', 0)} | 合计 {d.get('allCount', 0)}", notify=True)

        # 2) 我的专属邀请码
        time.sleep(1)
        code_res = self.ln_flmf_api(sid, "playWeb/memberPromotion/myExclCode",
                                    actcode="excluSive", path_prefix="/lv-web")
        if code_res and code_res.get('resultCode') == '0000':
            cd = code_res.get('data', {}) or {}
            img_path = cd.get('imgPath', '')
            self.log(f"专属邀请码: ✅ 获取到我的专属码 (二维码: {img_path or '已生成'})", notify=True)
        else:
            self.log(f"专属邀请码: 获取专属码失败 - {(code_res or {}).get('resultMsg', '无响应')}")

        if is_query_only:
            return

        # 3) 邀请记录
        time.sleep(1)
        lst = self.ln_flmf_api(sid, "playWeb/memberPromotion/exclCodeList",
                               "flag=0&startRow=1&pageSize=5",
                               actcode="excluSive", path_prefix="/lv-web")
        if lst and lst.get('resultCode') == '0000':
            ld = lst.get('data', {}) or {}
            items = ld.get('activityMobileSharemBbList') or []
            if items:
                self.log(f"专属邀请码: 邀请记录 {len(items)} 条 (共 {ld.get('activityMobileSharemBbSize', '?')})")
                for it in items[:5]:
                    self.log(f"   - {it.get('mobile', '?')} | {it.get('createTime', it.get('inviteTime', ''))}")
            else:
                self.log("专属邀请码: 暂无邀请记录")
        else:
            self.log(f"专属邀请码: 邀请记录获取失败 - {(lst or {}).get('resultMsg', '无响应')}")

    def ln_linktech_all_task(self, is_query_only=False):
        """linktech 4 个活动统一调度: 天天刮奖/沃享生活/专享权益/专属邀请码

        活动与接口对照(来自 flmf / st 前端包):
          scratchst     天天刮奖   → 服务端已下线, flmf 包内亦无路由
          welfareCenter 沃享生活   → /lv-apiaccess/welfareCenter/*
          vipRights     专享权益   → 服务端已下线, flmf 包内亦无路由
          excluSive     专属邀请码 → /lv-web/playWeb/memberPromotion/*

        已下线活动仍然发起探测, 这样服务端若恢复, 无需改代码即可自动生效;
        下线时只记明确日志, 不伪造任务结果。
        """
        self.log("---- linktech 活动组 ----")
        # 1) 天天刮奖 (scratchst) —— 抽奖类, 走 welfareCenter 抽奖接口
        try:
            sid = self.ln_flmf_get_sid("scratchst")
            if sid:
                self.log("天天刮奖: 活动可用, 开始执行")
                time.sleep(1)
                init = self.ln_flmf_api(sid, "welfareCenter/loadInitPage",
                                        actcode="scratchst")
                if init and init.get('resultCode') == '0000':
                    idata = init.get('data', {}) or {}
                    self.log(f"天天刮奖: 初始化成功 (剩余次数 {idata.get('luckCount', idata.get('remainCount', '?'))})")
                    if not is_query_only:
                        time.sleep(1)
                        luck = self.ln_flmf_api(sid, "welfareCenter/luckDraw",
                                                "taskId=", actcode="scratchst")
                        if luck and luck.get('resultCode') == '0000':
                            ld = luck.get('data', {}) or {}
                            prize = ld.get('prizeName') or ld.get('sendNum') or ''
                            if prize and '谢谢' not in str(prize):
                                self.log(f"天天刮奖: 🎰 刮中 {prize}", notify=True)
                            else:
                                self.log(f"天天刮奖: 🎰 刮奖结果: {prize or '无奖励'}")
                        elif luck:
                            self.log(f"天天刮奖: 刮奖 - {luck.get('resultMsg', '无响应')}")
                else:
                    self.log(f"天天刮奖: 初始化失败 - {(init or {}).get('resultMsg', '无响应')}")
            # sid 为 None 时 ln_flmf_get_sid 已打印"服务端活动已下线"
        except Exception as e:
            self.log(f"天天刮奖: 执行异常 - {e}")

        # 2) 沃享生活 (welfareCenter)
        try:
            self.ln_welfare_task(is_query_only=is_query_only)
        except Exception as e:
            self.log(f"沃享生活: 执行异常 - {e}")

        # 3) 专享权益 (vipRights)
        try:
            sid = self.ln_flmf_get_sid("vipRights")
            if sid:
                self.log("专享权益: 活动可用, 开始执行")
                time.sleep(1)
                init = self.ln_flmf_api(sid, "welfareCenter/memberCenterPrivilegeInfo",
                                        actcode="vipRights")
                if init and init.get('resultCode') == '0000':
                    idata = init.get('data', {}) or {}
                    plist = idata.get('privilegeList') or []
                    self.log(f"专享权益: 可用权益 {len(plist)} 项")
                    for p in plist[:5]:
                        self.log(f"   - {p.get('privilegeName', p.get('name', '?'))}")
        except Exception as e:
            self.log(f"专享权益: 执行异常 - {e}")

        # 4) 专属邀请码 (excluSive)
        try:
            self.ln_exclusive_task(is_query_only=is_query_only)
        except Exception as e:
            self.log(f"专属邀请码: 执行异常 - {e}")

    def ah_friday_get_entry(self):
        """安徽超级星期五: 获取活动入口ticket"""
        try:
            entry_url = f"{AH_FRIDAY_BASE_URL}/wxopen/hh/activity/superFriday/index?chnlId=app-ty&type=02"
            ticket_res = self.openPlatLineNew(entry_url)
            if not ticket_res or not ticket_res.get('ticket'):
                self.log("安徽超级星期五: 获取入口ticket失败")
                return None
            ticket = ticket_res['ticket']
            mobile = getattr(self, 'account_mobile', getattr(self, 'mobile', ''))
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            postage = hashlib.md5(f"{mobile}{timestamp}".encode()).hexdigest()
            page_url = f"{AH_FRIDAY_BASE_URL}/wxopen/hh/activity/superFriday/index"
            params = {
                "chnlId": "app-ty",
                "type": "02",
                "ticket": ticket,
                "version": COMMON_CONSTANTS["APP_VERSION"],
                "timestamp": timestamp,
                "desmobile": mobile,
                "num": "0",
                "postage": postage,
                "userNumber": mobile
            }
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": COMMON_CONSTANTS["UA"],
            }
            res = self.session.get(page_url, params=params, headers=headers, timeout=15)
            act_ticket = res.cookies.get('ticket', '')
            if not act_ticket:
                for hist_resp in getattr(res, 'history', []):
                    ck = hist_resp.cookies.get('ticket', '')
                    if ck:
                        act_ticket = ck
                        break
                    sc = hist_resp.headers.get('Set-Cookie', '')
                    m = re.search(r'ticket=([^;,\s]+)', sc)
                    if m:
                        act_ticket = m.group(1)
                        break
            if not act_ticket:
                # 不能用 session.cookies.get('ticket', '') —— 无 domain 约束时,
                # jar 内多个同名 ticket 会抛 CookieConflictError(被外层吞掉导致安徽任务整体失败),
                # 且 domain='' 那半段可能静默取到其它域的错误票据。
                # 这里遍历 jar, 优先取安徽活动域的 ticket, 其次取任意非空 ticket。
                ah_host = (urlparse(page_url).hostname or '').lower()
                fallback = ""
                for ck in self.session.cookies:
                    if ck.name != "ticket" or not ck.value:
                        continue
                    domain = (ck.domain or '').lstrip('.').lower()
                    if domain and (ah_host == domain or ah_host.endswith('.' + domain)):
                        act_ticket = ck.value
                        break
                    if not fallback:
                        fallback = ck.value
                if not act_ticket:
                    act_ticket = fallback
            if not act_ticket:
                cookie_header = res.headers.get('Set-Cookie', '')
                m = re.search(r'ticket=([^;,\s]+)', cookie_header)
                if m:
                    act_ticket = m.group(1)
            if not act_ticket:
                m = re.search(r'ticket[=:]\s*["\']?([a-zA-Z0-9_\-]{8,})', res.text)
                if m:
                    act_ticket = m.group(1)
            if not act_ticket:
                self.log(f"安徽超级星期五: 页面未返回独立ticket，使用入口ticket兜底")
                act_ticket = ticket
            self.log(f"安徽超级星期五: 获取活动ticket成功 ({act_ticket[:12]}...)")
            return {
                "ticket": act_ticket,
                "mobile": mobile,
                "timestamp": timestamp,
                "postage": postage,
                "app_ticket": ticket,
            }
        except Exception as e:
            self.log(f"安徽超级星期五: 获取入口异常 - {e}")
            return None

    def ah_friday_get_items(self, entry_info):
        """安徽超级星期五: 获取奖品列表并匹配目标面额"""
        try:
            url = f"{AH_FRIDAY_BASE_URL}/wxopen/app-activity/AHSecKill/querySecKillInfo"
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": AH_FRIDAY_BASE_URL,
                "Cookie": f"ticket={entry_info['ticket']}",
                "User-Agent": COMMON_CONSTANTS["UA"],
            }
            res = self.session.post(url, json={}, headers=headers, timeout=10)
            result = res.json()
            if not result.get('success') and not result.get('data'):
                self.log(f"安徽超级星期五: 查询奖品列表失败 - {result.get('alertMsg', '未知')}")
                return None
            items = result.get('data', {}).get('itemList', [])
            if not items:
                items = result.get('data', []) if isinstance(result.get('data'), list) else []
            target_amount = str(AH_FRIDAY_AMOUNT)
            for item in items:
                item_code = item.get('itemCode', '')
                item_name = item.get('itemName', '')
                if target_amount in item_name or f"hb{target_amount}" in item_code:
                    key_val = item.get('key', '')
                    self.log(f"安徽超级星期五: 匹配到目标 [{item_name}] (code: {item_code})")
                    return {
                        "itemCode": item_code,
                        "itemName": item_name,
                        "key": key_val,
                    }
            item_code = f"AWARD_AHFridaySecKill_10_hb{target_amount}"
            self.log(f"安徽超级星期五: 未从列表匹配到{target_amount}元, 使用默认itemCode: {item_code}")
            return {"itemCode": item_code, "itemName": f"{target_amount}元红包", "key": ""}
        except Exception as e:
            self.log(f"安徽超级星期五: 查询奖品异常 - {e}")
            item_code = f"AWARD_AHFridaySecKill_10_hb{AH_FRIDAY_AMOUNT}"
            return {"itemCode": item_code, "itemName": f"{AH_FRIDAY_AMOUNT}元红包", "key": ""}

    def ah_friday_seckill(self, entry_info, item_info):
        """安徽超级星期五: 批量抢购"""
        ticket = entry_info['ticket']
        item_code = item_info['itemCode']
        key_val = item_info.get('key', '')
        mobile = entry_info['mobile']
        timestamp_str = entry_info['timestamp']
        postage = entry_info['postage']
        referer = (
            f"{AH_FRIDAY_BASE_URL}/wxopen/hh/activity/superFriday/index"
            f"?chnlId=app-ty&type=02&ticket={entry_info['app_ticket']}"
            f"&version={COMMON_CONSTANTS['APP_VERSION']}&timestamp={timestamp_str}"
            f"&desmobile={mobile}&num=0&postage={postage}&userNumber={mobile}"
        )
        success_count = 0
        fail_count = 0
        self.log(f"安徽超级星期五: 开始批量抢购 [{item_info['itemName']}]，共{AH_FRIDAY_SECKILL_TIMES}次")
        for i in range(1, AH_FRIDAY_SECKILL_TIMES + 1):
            try:
                ts = str(int(time.time() * 1000))
                params = {
                    "ticket": ticket,
                    "itemCode": item_code,
                    "time": ts,
                }
                if key_val:
                    params["key"] = key_val
                url = f"{AH_FRIDAY_BASE_URL}/wxopen/app-activity/AHSecKill/lotteryAction"
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Origin": AH_FRIDAY_BASE_URL,
                    "Referer": referer,
                    "Cookie": f"ticket={ticket}",
                    "User-Agent": COMMON_CONSTANTS["UA"],
                    "Connection": "keep-alive",
                }
                res = self.session.post(url, params=params, json={}, headers=headers, timeout=5)
                data = res.json()
                if data.get('success'):
                    success_count += 1
                    self.log(f"安徽超级星期五: 🎉 第{i}次抢购成功！{json.dumps(data, ensure_ascii=False)}", notify=True)
                    return True
                else:
                    fail_count += 1
                    alert = data.get('alertMsg', '')
                    if i <= 3 or i % 20 == 0:
                        self.log(f"安徽超级星期五: 第{i}次 - {alert or data.get('statusCode', '未知')}")
                    if "已抢完" in alert or "已结束" in alert or "已领取" in alert:
                        self.log(f"安徽超级星期五: ⚠️ {alert}，停止抢购")
                        break
            except Exception as e:
                fail_count += 1
                if i <= 3:
                    self.log(f"安徽超级星期五: 第{i}次异常 - {e}")
            if i < AH_FRIDAY_SECKILL_TIMES:
                time.sleep(AH_FRIDAY_INTERVAL)
        self.log(f"安徽超级星期五: 抢购完成 (共{AH_FRIDAY_SECKILL_TIMES}次, 失败{fail_count}次)", notify=True)
        return False

    def ah_friday_task(self):
        """安徽超级星期五: 主入口"""
        if not AH_FRIDAY_AMOUNT:
            return
        rc = globalConfig.get("regional_config", {})
        if not rc.get("run_ah_friday", True):
            self.log("安徽超级星期五: ⏭️ 已被子开关关闭，跳过")
            return
        weekday = datetime.now().weekday()
        if weekday != 4:
            self.log(f"安徽超级星期五: 今天不是周五 (当前周{weekday + 1})，跳过")
            return
        self.log(f"安徽超级星期五: 🎯 目标面额 {AH_FRIDAY_AMOUNT}元")
        entry_info = self.ah_friday_get_entry()
        if not entry_info:
            return
        item_info = self.ah_friday_get_items(entry_info)
        if not item_info:
            return
        now = datetime.now()
        target = now.replace(hour=10, minute=0, second=0, microsecond=0)
        wait_seconds = (target - now).total_seconds()
        if wait_seconds > 300:
            self.log(f"安徽超级星期五: ⏳ 距10:00还有 {wait_seconds:.0f}秒，大于5分钟，建议临近时启动")
            return
        if wait_seconds > 0:
            self.log(f"安徽超级星期五: ⏳ 等待开抢 (剩余 {wait_seconds:.1f}秒)...")
            while (datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) - datetime.now()).total_seconds() > 0.3:
                time.sleep(0.1)
            self.log("安徽超级星期五: ⚡ 时间到！开始抢购！")
        else:
            self.log(f"安徽超级星期五: ⚡ 已过10点 {abs(wait_seconds):.1f}秒，直接抢购！")
        self.ah_friday_seckill(entry_info, item_info)

    def woread_encrypt(self, data):
        try:
            key = b'woreadst^&*12345'
            iv = b'16-Bytes--String'
            cipher = AES.new(key, AES.MODE_CBC, iv)
            if isinstance(data, dict):
                data_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            else:
                data_str = str(data)
            pad_len = 16 - (len(data_str.encode('utf-8')) % 16)
            data_str = data_str + chr(pad_len) * pad_len
            ciphertext = cipher.encrypt(data_str.encode('utf-8'))
            hex_str = ciphertext.hex()
            return base64.b64encode(hex_str.encode('utf-8')).decode('utf-8')
        except Exception as e:
            self.log(f"woread_encrypt error: {e}")
            return ""

    def woread_auth(self):
        try:
            product_id = "10000002"
            secret_key = "7k1HcDL8RKvc"
            timestamp = str(round(time.time() * 1000))
            sign_str = f"{product_id}{secret_key}{timestamp}"
            md5_hash = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
            date_str = datetime.now().strftime('%Y%m%d%H%M%S')
            crypt_text_obj = {"timestamp": date_str}
            encoded_sign = self.woread_encrypt(crypt_text_obj)
            url = f"https://10010.woread.com.cn/ng_woread_service/rest/app/auth/{product_id}/{timestamp}/{md5_hash}"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": COMMON_CONSTANTS['UA'],
            }
            res = self.session.post(url, json={"sign": encoded_sign}, headers=headers).json()
            if res.get('code') == "0000":
                self.woread_accesstoken = res.get('data', {}).get('accesstoken')
                return True
            else:
                self.log(f"阅读专区认证失败: {res.get('message')}")
                return False
        except Exception as e:
            self.log(f"woread_auth error: {e}")
            return False

    def woread_login(self):
        try:
            if not hasattr(self, 'woread_accesstoken') or not self.woread_accesstoken:
                if not self.woread_auth():
                    return False
            if not self.token_online:
                self.log("阅读专区: 缺少 token_online，无法登录")
                return False
            token_enc = self.woread_encrypt(self.token_online)
            phone_str = self.account_mobile if self.account_mobile else "13800000000"
            phone_enc = self.woread_encrypt(phone_str)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            inner_json = json.dumps({
                "tokenOnline": token_enc,
                "phone": phone_enc,
                "timestamp": timestamp
            }, separators=(',', ':'), ensure_ascii=False)
            encoded_sign = self.woread_encrypt(inner_json)
            url = "https://10010.woread.com.cn/ng_woread_service/rest/account/login"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": COMMON_CONSTANTS['UA'],
            }
            if hasattr(self, 'woread_accesstoken') and self.woread_accesstoken:
                headers["accesstoken"] = self.woread_accesstoken
            res = self.session.post(url, json={"sign": encoded_sign}, headers=headers, timeout=15).json()
            if res.get('code') == "0000":
                data = res.get('data', {})
                self.woread_token = data.get('token')
                self.woread_userid = data.get('userid')
                self.woread_userindex = data.get('userindex')
                self.woread_verifycode = data.get('verifycode')
                if data.get('phone'):
                    self.mobile = data['phone']
                self.log("阅读专区: 登录成功")
                return True
            else:
                self.log(f"阅读专区登录失败: {res.get('message')}")
                return False
        except Exception as e:
            self.log(f"woread_login error: {e}")
            return False

    def woread_queryTicketAccount(self):
        try:
            if not hasattr(self, 'woread_token') or not self.woread_token:
                if not self.woread_login():
                     return
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            params = {
                "timestamp": timestamp,
                "phone": self.mobile if self.mobile else "",
                "token": self.woread_token
            }
            sign = self.woread_encrypt(params)
            url = "https://10010.woread.com.cn/ng_woread_service/rest/phone/vouchers/queryTicketAccount"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": COMMON_CONSTANTS['UA'],
            }
            if hasattr(self, 'woread_accesstoken') and self.woread_accesstoken:
                headers["accesstoken"] = self.woread_accesstoken
            res = self.session.post(url, json={"sign": sign}, headers=headers).json()
            if res.get('code') == "0000":
                data = res.get('data', {})
                usable_num = int(data.get('usableNum', 0))
                balance_yuan = "{:.2f}".format(usable_num / 100)
                self.log(f"💰 [资产-阅读红包] 余额: {balance_yuan}元", notify=True)
            else:
                self.log(f"阅读红包查询失败: {res.get('message')}")
        except Exception as e:
            self.log(f"woread_queryTicketAccount error: {e}")


    def woread_get_book_info(self):
        try:
            url1 = "https://10010.woread.com.cn/ng_woread_service/rest/basics/recommposdetail/14856"
            headers = {
                "User-Agent": COMMON_CONSTANTS['UA'],
                "accesstoken": self.woread_accesstoken
            }
            res1 = self.session.get(url1, headers=headers)
            try:
                res1 = res1.json()
            except:
                self.log(f"阅读专区: 获取书架响应非JSON: {res1.text[:100]}")
                return False
            if res1.get('code') == '0000':
                msg_list = res1.get('data', {}).get('booklist', {}).get('message', [])
                if msg_list:
                    self.wr_catid = msg_list[0].get('catindex')
                    self.wr_cntindex = msg_list[0].get('cntindex')
                bind_info = res1.get('data', {}).get('bindinfo', [])
                if bind_info:
                    self.wr_cardid = bind_info[0].get('recommposiindex')
            else:
                self.log("阅读专区: 获取书架失败")
                return False
            if not getattr(self, 'wr_cntindex', None): return False
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            param = {
                "curPage": 1, "limit": 30, "index": self.wr_cntindex, "sort": 0, "finishFlag": 1,
                "timestamp": timestamp,
                "phone": self.mobile if self.mobile else "",
                "token": getattr(self, 'woread_token', ''),
                "userid": getattr(self, 'woread_userid', ''),
                "userId": getattr(self, 'woread_userid', ''),
                "userIndex": getattr(self, 'woread_userindex', ''),
                "verifyCode": getattr(self, 'woread_verifycode', '')
            }
            sign = self.woread_encrypt(param)
            url2 = "https://10010.woread.com.cn/ng_woread_service/rest/cnt/chalist"
            res2_raw = self.session.post(url2, json={"sign": sign}, headers=headers)
            try:
                res2 = res2_raw.json()
            except:
                self.log(f"阅读专区: 获取章节响应非JSON: {res2_raw.text[:100]}")
                return False
            lst = res2.get('list', []) or res2.get('data', {}).get('list', [])
            if lst:
                content = lst[0].get('charptercontent', [])
                if content:
                    self.wr_chapterallindex = content[0].get('chapterallindex')
                    self.wr_chapterid = content[0].get('chapterid')
                    return True
            return False
        except Exception as e:
            self.log(f"阅读专区: 获取书籍信息异常: {e}")
            return False

    def woread_read_process(self):
        if not self.woread_get_book_info():
            self.log("阅读专区: 无法获取书籍信息，跳过阅读")
            return
        headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301}",
                "accesstoken": self.woread_accesstoken
        }
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        phone = self.mobile if self.mobile else ""
        token = getattr(self, 'woread_token', '')
        userid = getattr(self, 'woread_userid', '')
        userindex = getattr(self, 'woread_userindex', '')
        verifycode = getattr(self, 'woread_verifycode', '')
        common_params = {
            "timestamp": timestamp,
            "phone": phone,
            "token": token,
            "userid": userid,
            "userId": userid,
            "userIndex": userindex,
            "userAccount": phone,
            "verifyCode": verifycode
        }
        param = {
          "chapterAllIndex": self.wr_chapterallindex,
          "cntIndex": self.wr_cntindex,
          "cntTypeFlag": "1",
          **common_params
        }
        sign = self.woread_encrypt(param)
        hb_url = f"https://10010.woread.com.cn/ng_woread_service/rest/cnt/wordsDetail?catid={self.wr_catid}&cardid={self.wr_cardid}&cntindex={self.wr_cntindex}&chapterallindex={self.wr_chapterallindex}&chapterseno=1"
        self.session.post(hb_url, json={"sign": sign}, headers=headers)
        add_param = {
          "readTime": "2",
          "cntIndex": self.wr_cntindex,
          "cntType": "1",
          "catid": "0",
          "pageIndex": "",
          "cardid": self.wr_cardid,
          "cntindex": self.wr_cntindex,
          "cnttype": "1",
          "chapterallindex": self.wr_chapterallindex,
          "chapterseno": "1",
          "channelid": "",
          "chapterid": self.wr_chapterid,
          "readtype": 1,
          "isend": "0",
          **common_params
        }
        add_sign = self.woread_encrypt(add_param)
        add_url = "https://10010.woread.com.cn/ng_woread_service/rest/history/addReadTime"
        res = self.session.post(add_url, json={"sign": add_sign}, headers=headers).json()
        res_code = str(res.get('code', ''))
        res_msg = str(res.get('message', ''))
        if res_code == '0000':
            self.log("阅读专区: 模拟阅读成功")
        elif res_code == '9999' or '9999' in res_msg or '不存在阅读记录' in res_msg:
            # addReadTime 返回9999不影响实际阅读结果
            self.log("阅读专区: 模拟阅读成功（阅读记录已提交）")
        else:
             self.log(f"阅读专区: 模拟阅读失败: {res_msg or res}")



    def woread_draw_new(self):
        try:
             headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 unicom{version:iphone_c@12.0301}",
                "accesstoken": self.woread_accesstoken
             }
             timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
             param = {
                "activeindex": "8051",
                "timestamp": timestamp, "phone": self.mobile if self.mobile else "", "token": self.woread_token
             }
             sign = self.woread_encrypt(param)
             url = "https://10010.woread.com.cn/ng_woread_service/rest/basics/doDraw"
             res = self.session.post(url, json={"sign": sign}, headers=headers).json()
             if res.get('code') == '0000':
                 prize = res.get('data', {}).get('prizedesc')
                 if prize:
                     self.log(f"阅读专区: 抽奖成功: {prize}", notify=True)
                 else:
                     self.log("阅读专区: 抽奖完成 (未中奖)")
             else:
                 self.log(f"阅读专区: 抽奖失败: {res.get('message')}")
        except Exception as e:
            self.log(f"woread_draw_new error: {e}")

    def woread_task(self):
        self.log("==== 联通阅读 ====")
        if not self.woread_login():
             self.log("阅读专区: 登录失败，跳过任务")
             return
        self.woread_queryTicketAccount()
        self.woread_read_process()
        time.sleep(3)
        self.woread_draw_new()

    def query_market_raffle_records(self, user_token):
        self.log("权益超市: 正在查询抽奖记录...")
        try:
            url = "https://backward.bol.wo.cn/prod-api/market/contactReceive/queryReceiveRecord"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "User-Agent": COMMON_CONSTANTS["MARKET_UA"],
                "Origin": "https://contact.bol.wo.cn",
                "Referer": "https://contact.bol.wo.cn/"
            }
            mobile = getattr(self, "account_mobile", getattr(self, "mobile", ""))
            payload = {
                "isReceive": None,
                "receiveStatus": None,
                "limit": 20,
                "page": 1,
                "mobile": mobile,
                "businessSources": ["3", "4", "5", "6", "99"],
                "isPromotion": 1,
                "returnFormatType": 1
            }
            res = self.session.post(url, json=payload, headers=headers).json()
            if res.get('code') == 200:
                records = res.get('data', {}).get('recordObjs', [])
                if records:
                    display_records = records[:10]
                    self.log(f"权益超市: 最近 {len(display_records)} 条抽奖记录:", notify=True)
                    for item in display_records:
                        self.log(f"    - [{item.get('receiveTime') or ''}] {item.get('recordName')}", notify=True)
                else:
                    self.log("权益超市: 无近期抽奖记录。")
            else:
                self.log(f"权益超市: 查询抽奖记录失败: {res.get('msg')}")
        except Exception as e:
            self.log(f"query_market_raffle_records error: {e}")

    def query_phone_recharge_records(self, user_token):
        self.log("权益超市: 正在查询本月话费抢购记录...")
        try:
            url = "https://backward.bol.wo.cn/prod-api/market/contactReceive/queryReceiveRecord"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "User-Agent": COMMON_CONSTANTS["MARKET_UA"],
                "Origin": "https://contact.bol.wo.cn",
                "Referer": "https://contact.bol.wo.cn/"
            }
            mobile = getattr(self, "account_mobile", getattr(self, "mobile", ""))
            payload = {
                "isReceive": None,
                "receiveStatus": None,
                "limit": 50,
                "page": 1,
                "mobile": mobile,
                "businessSources": ["3", "4", "5", "6", "99"],
                "isPromotion": 1,
                "returnFormatType": 1
            }
            res = self.session.post(url, json=payload, headers=headers).json()
            if res.get('code') == 200:
                records = res.get('data', {}).get('recordObjs', [])
                total_amount = 0.0
                current_month = datetime.now().strftime('%Y-%m')
                count = 0
                for item in records:
                    create_time = item.get('receiveTime') or ''
                    name = item.get('recordName', '')
                    if not create_time or current_month not in create_time:
                        continue
                    if any(k in name for k in ['话费', '充值', '红包']):
                        match = re.search(r'(\d+(\.\d+)?)元', name)
                        if match:
                            amount = float(match.group(1))
                            total_amount += amount
                            count += 1
                if count > 0:
                     self.log(f"💰 [资产-抢购] 本月权益超市话费累计: {total_amount:.2f}元", notify=True)
                else:
                     self.log("权益超市: 本月暂无话费抢购记录")
            else:
                self.log(f"权益超市: 查询话费记录失败: {res.get('msg')}")
        except Exception as e:
            self.log(f"query_phone_recharge_records error: {e}")

    # 券包接口: 我的卡券(奖品)列表, 走 m.client 域。
    # 与 act.10010.com/SigninApp/convert/phoneDetails(账户明细)不同, 这里直接返回
    # 券本身: 券名/面额/发放时间/生效失效时间, 是判断"券是否真的到账"最权威的数据源。
    #
    # 实测(2026-11-19 18:00 场次): 抢兑接口对 18/10/5 元全部返回 10013
    # "兑换规则达到上限", 但本接口能查到 "10元话费充值抵扣券",
    # winningTime=2026-11-19 18:00:00, 有效期 2026-11-19 ~ 2026-11-26。
    # => 10013 时券其实已经发下来了, 不能再当成"兑换失败"。
    #
    # sysActiveStr 是活动码列表, 取自签到 H5 生产包:
    #   chunk-33b9eb2c.js (我的卡券) / chunk-741c9af2.js (通用卡券)
    #   / chunk-99cbafc2.js (我的礼包)
    SIGN_COUPON_ACT_CODES = (
        "SHAKECLIENT_AC20220811152323,SHAKECLIENT_AC20231127165002,SIGNIN_AC20141230175502,"
        "SHAKECLIENT_AC20230322151845,SHAKECLIENT_AC20240806140724,SHAKECLIENT_AC20241119161231,"
        "SHAKECLIENT_AC20250226023238,SHAKECLIENT_AC20231128140323"
    )
    SIGN_COUPON_BAG_URL = ("https://m.client.10010.com/myPrizeForActivity/openServices/"
                           "listWinningRecordsForDouble11")

    def _fetch_coupon_bag(self):
        """拉取"我的卡券"奖品列表, 返回记录列表(失败返回 None)。

        返回每条含 prizeName / winningTime / prizeUseBeginTime / prizeUseEndTime /
        prizeState / prizeRecordID。
        """
        try:
            url = self.SIGN_COUPON_BAG_URL
            form = {
                "sysActiveStr": self.SIGN_COUPON_ACT_CODES,
                "enMobile": "",
                "otherFlag": "1"
            }
            headers = {"Referer": "https://m.client.10010.com/myPrizeForActivity/tenth517/homePage?channel=nav"}
            res = self.request("post", url, data=form, headers=headers, timeout=20)
            if not res:
                return None
            result = res.json()
            code = str(result.get('code', ''))
            if code != '200':
                # 40002 = 当前用户未登录; 其余为活动码/参数问题
                self.log(f"🔍 [券包] 查询未成功: code={code} {result.get('desc', '')}")
                return None
            data = result.get('data') or {}
            records = data.get('winningRecords') or []
            return records
        except Exception as e:
            self.log(f"🔍 [券包] 查询异常: {e}")
            return None

    def _coupon_fingerprint(self, rec):
        """把券记录归一化成指纹, 用于抢兑前后对比"""
        return "|".join([
            str(rec.get('prizeRecordID', '') or ''),
            str(rec.get('prizeName', '') or ''),
            str(rec.get('winningTime', '') or ''),
            str(rec.get('prizeUseBeginTime', '') or ''),
        ])

    def sign_query_coupon_bag(self):
        """展示"我的卡券"里的券(话费券到账情况)"""
        records = self._fetch_coupon_bag()
        if records is None:
            self.log("🔍 [券包] 查询失败")
            return
        if not records:
            self.log("🔍 [券包] 当前无卡券")
            return
        self.log(f"🔍 [券包] 共 {len(records)} 张券:", notify=True)
        for rec in records[:8]:
            name = rec.get('prizeName', '')
            win = rec.get('winningTime', '')
            use_end = rec.get('prizeUseEndTime', '')
            state = rec.get('prizeState', '')
            self.log(f"   🎫 {name} | 发放:{win} | 有效期至:{use_end} | 状态:{state}")

    def _fetch_phone_details(self):
        """拉取签到区账户明细, 返回记录列表(失败返回 None)。

        记录里含"兑换"字样的条目, 是判断话费券是否真正到账的唯一可靠依据:
        抢兑接口的 0053/10013 只代表"结果查询/兑换规则判定"失败,
        并不能证明券没发下来(实测存在兑换成功但状态查询报错的情况)。
        """
        try:
            url = "https://act.10010.com/SigninApp/convert/phoneDetails"
            form = {
                "log_type": "1",
                "number": "1",
                "list_num": ""
            }
            headers = {"Origin": "https://img.client.10010.com"}
            res = self.request("post", url, data=form, headers=headers)
            if not res:
                return None
            result = res.json()
            if result.get('status') != '0000':
                self.log(f"[账户明细] 查询异常: {result.get('msg', 'Result Error')}")
                return None
            data = result.get('data', {}).get('detailedBO', [])
            if not isinstance(data, list):
                return []
            return data
        except Exception as e:
            self.log(f"sign_query_my_prizes error: {e}")
            return None

    def _pick_exchange_records(self, details):
        """从账户明细里筛出兑换类记录, 返回 [(order_time, remark, amount), ...]

        仅用于"展示"最近兑换记录。
        注意: 到账核对的判据不能用这个关键字过滤 —— 服务端到账记录的
        remark 文案未经验证(可能不含"兑换"字样), 用关键字过滤会漏判,
        所以 sign_verify_grab_result 比对的是记录总数。
        """
        out = []
        for item in (details or []):
            remark = item.get('remark', '') or ''
            buss_name = item.get('from_bussname', '') or ''
            if "兑换" in remark or "兑换" in buss_name:
                order_time = item.get('order_time', '') or ''
                amount = item.get('booksNumber') or item.get('books_number') or "0"
                out.append((order_time, remark, amount))
        return out

    def _detail_summary(self, details):
        """把账户明细归一化成可比对的指纹列表。

        每条记录取 (order_time, remark, amount) 组成指纹。
        用指纹而非条数比对, 可以避免"列表头部插入新记录导致总数不变"的情况
        (账户明细通常按时间倒序返回, 新记录插在头部)。
        """
        out = []
        for item in (details or []):
            order_time = item.get('order_time', '') or ''
            remark = item.get('remark', '') or ''
            amount = item.get('booksNumber') or item.get('books_number') or "0"
            out.append(f"{order_time}|{remark}|{amount}")
        return out

    def sign_query_my_prizes(self):
        self.log("正在查询账户明细 (抢兑)...")
        details = self._fetch_phone_details()
        if details is None:
            return
        records = self._pick_exchange_records(details)
        if records:
            self.log(f"📋 [账户明细] 最近 5 条兑换记录:", notify=True)
            for order_time, remark, amount in records[:5]:
                self.log(f"   🎁 [抢兑] {order_time} | {remark} (变动:{amount})", notify=True)
        else:
            self.log("[账户明细] 暂无兑换记录")

    def sign_verify_grab_result(self, baseline_coupon_fps, baseline_detail_fps,
                                product_name, failed_reason, expect_amount=None):
        """抢兑报错后核对券包/账户明细, 判断券是否其实已经到账。

        背景(均为实测):
          - 0053 "兑换失败": 出现在 prizeConvertResult 结果查询阶段, 提交本身可能已成功
          - 10013 "兑换规则达到上限": 出现在兑换规则校验阶段, 但同场次 18/10/5 元
            全部同时报 10013, 且 prizeList 报告的 user_able_time 仍 > 0,
            无法据此断定没兑成
          - 关键证据: 2026-11-19 18:00 场次报 10013, 但"我的卡券"里查到了
            "10元话费充值抵扣券"(winningTime=18:00:00, 有效期一周) => 券已实际发放。

        所以最终判据是"我的卡券"里有没有新增券, 账户明细作为补充判据。

        baseline_coupon_fps: 抢兑前"我的卡券"的指纹集合
        baseline_detail_fps: 抢兑前账户明细的指纹列表
        expect_amount:      目标面额(int), 用于在新增券里精确匹配面额
        返回 True 表示确认到账
        """
        # ---- 主判据: 我的卡券 ----
        try:
            bag = self._fetch_coupon_bag()
        except Exception as e:
            self.log(f"🔍 [到账核对] 查询券包异常: {e}")
            bag = None
        if bag is not None:
            base = set(baseline_coupon_fps or [])
            new_coupons = [r for r in bag if self._coupon_fingerprint(r) not in base]
            if new_coupons:
                # 优先找面额匹配的那张
                hit = None
                if expect_amount:
                    for r in new_coupons:
                        name = str(r.get('prizeName', '') or '')
                        nums = re.findall(r'(?<![\d.])(\d+)(?![\d.])', name)
                        if nums and int(nums[0]) == int(expect_amount):
                            hit = r
                            break
                hit = hit or new_coupons[0]
                self.log(f"🔍 [到账核对] 【我的卡券】发现新增券 ✅ {hit.get('prizeName')}"
                         f" | 发放:{hit.get('winningTime')}"
                         f" | 有效期:{hit.get('prizeUseBeginTime')}~{hit.get('prizeUseEndTime')}"
                         f" —— 券已实际到账(接口报错 {failed_reason} 不代表兑换失败)", notify=True)
                return True
            self.log(f"🔍 [到账核对] 【我的卡券】未发现新增券 (现有{len(bag)}张)")
        else:
            self.log("🔍 [到账核对] 【我的卡券】查询失败, 改用账户明细辅助判断", notify=True)

        # ---- 辅助判据: 账户明细 ----
        try:
            details = self._fetch_phone_details()
        except Exception as e:
            self.log(f"🔍 [到账核对] 查询账户明细异常: {e}")
            details = None
        if details is None:
            self.log("🔍 [到账核对] 无法确认券是否到账", notify=True)
            return False
        # 用指纹集合比对: 新增了基线里没有的记录 => 券确实到账。
        # 不用条数比对, 因为账户明细按时间倒序返回, 新记录插在头部时总数可能不变。
        current = self._detail_summary(details)
        baseline_set = set(baseline_detail_fps or [])
        new_items = [fp for fp in current if fp not in baseline_set]
        if new_items:
            first = new_items[0]
            parts = first.split("|")
            order_time = parts[0] if parts else ''
            remark = parts[1] if len(parts) > 1 else ''
            amount = parts[2] if len(parts) > 2 else ''
            self.log(f"🔍 [到账核对] 账户明细新增记录 ✅ {order_time} | {remark} (变动:{amount})"
                     f" —— 疑似券已到账(接口报错 {failed_reason} 不代表兑换失败)", notify=True)
            return True
        self.log(f"🔍 [到账核对] 券包与账户明细均无新增记录, "
                 f"本次 {product_name} 很可能未兑换成功 (接口报错: {failed_reason})")
        return False

    def sign_task_main(self):
        self.log("==== 签到区 ====")
        self.sign_getTelephone(is_initial=True)
        self.sign_getContinuous(is_query_only=False)
        self.sign_month_sign_gift()
        self.sign_getTaskList()
        sc = globalConfig.get("sign_config", {})
        if sc.get("run_grab_coupon", False):
            self.sign_grabCoupon()
        else:
            self.log("签到区-抢话费券: ⏭️ 已被子开关关闭，跳过")
        self.sign_getTelephone()
        self.sign_query_my_prizes()
        try:
            self.sign_query_coupon_bag()
        except Exception as e:
            self.log(f"券包查询异常: {e}")

    def execute_daily_tasks(self, query_only=False):
        if query_only:
            self.log("📋 [查询模式] 仅查询资产，跳过任务执行", notify=True)
            try:
                self.queryRemain()
                if globalConfig.get("enable_sign", True):
                    try:
                        self.sign_getContinuous(is_query_only=True)
                        self.sign_month_sign_gift(is_query_only=True)
                        self.sign_getTelephone()
                    except Exception as e:
                        self.log(f"首页签到查询异常: {e}")
                    try:
                        self.sign_query_my_prizes()
                    except Exception as e:
                        self.log(f"抢兑记录查询异常: {e}")
                    try:
                        self.sign_query_coupon_bag()
                    except Exception as e:
                        self.log(f"券包查询异常: {e}")
                if globalConfig.get("enable_ttlxj", True):
                    try:
                        self.ttlxj_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"天天领现金查询异常: {e}")
                if globalConfig.get("enable_ttxc", True):
                    try:
                        self.ttxc_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"通通乡村查询异常: {e}")
                if globalConfig.get("enable_market", True):
                    try:
                        self.market_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"权益超市查询异常: {e}")
                if globalConfig.get("enable_jfsc", True):
                    try:
                        self.jfsc_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"积分商城查询异常: {e}")
                if globalConfig.get("enable_woread", True):
                    try:
                        self.woread_queryTicketAccount()
                    except Exception as e:
                        self.log(f"联通阅读查询异常: {e}")
                if globalConfig.get("enable_aiting", True):
                    try:
                        self.aiting_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"联通爱听查询异常: {e}")
                if globalConfig.get("enable_security", True):
                    try:
                        self.securityButlerTask(is_query_only=True)
                    except Exception as e:
                        self.log(f"安全管家查询异常: {e}")
                if globalConfig.get("enable_ltyp", True):
                    try:
                        self.ltyp_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"联通云盘查询异常: {e}")
                if globalConfig.get("enable_wostore", True):
                    try:
                        self.wostore_cloud_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"沃云手机查询异常: {e}")
                if globalConfig.get("enable_regional", True):
                    try:
                        self.regional_task(is_query_only=True)
                    except Exception as e:
                        self.log(f"区域专区查询异常: {e}")
            except Exception as e:
                self.log(f"查询异常: {e}")
            return
        # 各模块相互隔离: 单个模块异常不应导致后续模块(乃至后续账号)全部跳过
        def _run(name, fn, *args, **kwargs):
            try:
                fn(*args, **kwargs)
            except Exception as e:
                self.log(f"⚠️ {name}执行异常, 已跳过该模块: {e}")

        if globalConfig.get("enable_sign", True):
            _run("签到区", self.sign_task_main)
        else:
            self.log("==== 签到区 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_ltzf", True):
            _run("联通祝福", self.ltzf_task)
        else:
            self.log("==== 联通祝福 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_ttlxj", True):
            _run("天天领现金", self.ttlxj_task)
        else:
            self.log("==== 天天领现金 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_ttxc", True):
            _run("通通乡村", self.ttxc_task)
        else:
            self.log("==== 通通乡村 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_market", True):
            _run("权益超市", self.market_task)
        else:
            self.log("==== 权益超市 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_jfsc", True):
            _run("积分商城", self.jfsc_task)
        else:
            self.log("==== 积分商城 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_woread", True):
            _run("联通阅读", self.woread_task)
        else:
            self.log("==== 联通阅读 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        need_cooldown = globalConfig.get("enable_woread", True) and globalConfig.get("enable_aiting", True)
        if need_cooldown:
            self.log("⏳ 等待120秒（阅读冷却：联通限制两次阅读间隔2分钟）...")
            time.sleep(120)
        if globalConfig.get("enable_aiting", True):
            _run("联通爱听", self.aiting_task)
        else:
            self.log("==== 联通爱听 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_security", True):
            _run("安全管家", self.securityButlerTask)
        else:
            self.log("==== 安全管家 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_ltyp", True):
            _run("联通云盘", self.ltyp_task)
        else:
            self.log("==== 联通云盘 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_wostore", True):
            _run("沃云手机", self.wostore_cloud_task)
        else:
            self.log("==== 沃云手机 ====")
            self.log("⏭️ 已被总开关关闭，跳过")
        if globalConfig.get("enable_regional", True):
            _run("区域专区", self.regional_task)
        else:
            self.log("==== 区域专区 ====")
            self.log("⏭️ 已被总开关关闭，跳过")

def cross_view_security_share_keys(users):
    participants = [
        u for u in users
        if getattr(u, "sec_ai_share_key", "") and getattr(u, "sec_token", "") and getattr(u, "sec_share_task_code", "")
    ]
    if not participants:
        return
    if len(participants) < 2:
        participants[0].log("联通助理-分享AI助手对话：仅 1 个账号拿到分享key，跳过跨账号互看")
        return
    print("")
    print("========= 联通助理-开始跨账号查看AI分享对话 =========")
    n = len(participants)
    for i, viewer in enumerate(participants):
        target = participants[(i + 1) % n]
        viewer.log(f"联通助理-分享AI助手对话：查看账号[{target.index}]分享")
        try:
            viewer.sec_view_share_detail(target.sec_ai_share_key, viewer.sec_token)
        except Exception as e:
            viewer.log(f"联通助理-分享AI助手对话：互看异常 {e}")
        time.sleep(2)
    for u in participants:
        try:
            u.sec_refresh_security_context(refresh_secret=True)
            u.sec_finalize_share_ai_task()
            u.sec_recover_pending_claims(rounds=2, delay=6, refresh_context=True)
        except Exception as e:
            u.log(f"联通助理-分享AI助手对话：互看后领奖异常 {e}")

def do_notify(users):
    if not globalConfig.get("enable_notify", True):
        print("推送通知已关闭")
        return
    notify_content = []
    for u in users:
        if u.notify_logs:
            phone = u.mobile or u.account_mobile
            phone_str = mask_str(phone) if phone else ""
            notify_content.append(f"【账号{u.index}】{phone_str}")
            notify_content.extend(u.notify_logs)
            notify_content.append("")
    if notify_content:
        content = "\n".join(notify_content)
        # 仓库根目录的 notify.py 是推送模块; sendNotify 仅作旧版兜底。
        import importlib
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        send = None
        for module_name in ("notify", "sendNotify"):
            try:
                send = getattr(importlib.import_module(module_name), "send")
                break
            except (ImportError, AttributeError):
                continue
        if send is None:
            print("推送失败，既没有 notify.py 也没有 sendNotify.py")
            return
        try:
            send(f"中国联通 {SCRIPT_VERSION}", content)
            print(f"推送成功 (内容长度: {len(content)})")
        except Exception as e:
            print(f"推送失败: {str(e)}")
    else:
        print("无推送内容")

def main():
    global GRAB_AMOUNT, GRAB_AMOUNTS
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Script Start] chinaUnicom Python {SCRIPT_VERSION}")
    cookies = os.environ.get("chinaUnicomCookie", "")
    if not cookies:
        print("[-] 未在环境变量 chinaUnicomCookie 中找到配置")
        sys.exit(1)
    accounts = [c for c in re.split(r'[&\n]', cookies) if c.strip()]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发现 {len(accounts)} 个账号")
    print("")
    users = []
    for idx, config in enumerate(accounts):
        u = UserService(idx + 1, config.strip())
        users.append(u)
        if u.appId:
             print(f"账号[{idx+1}] 识别到 Token#AppId 模式，使用自定义AppId: {u.appId}")
        elif u.account_mobile:
             print(f"账号[{idx+1}] 识别到纯手机号模式（使用本地Token缓存）: {mask_str(u.account_mobile)}")
        try:
            if u.token_online:
                # 归属地主要来自 onLine 响应的 list, 这里的预取仅作补充, 失败不阻塞
                u.get_city_info()
        except Exception as e:
            print(f"账号[{idx+1}] 预取归属地异常: {e}")
    print(f"共找到{len(accounts)}个账号")
    print("")
    env_amount = os.environ.get("UNICOM_GRAB_AMOUNT", "")
    if env_amount.strip():
        parsed = parse_grab_amounts(env_amount)
        GRAB_AMOUNTS = parsed
        GRAB_AMOUNT = parsed[0]
        if len(parsed) > 1:
            print(f"[配置] 抢兑面额降级链: {' → '.join(f'{a}元' for a in parsed)}")
        else:
            print(f"[配置] 抢兑面额: {parsed[0]}元")
    query_only = os.environ.get("UNICOM_TEST_MODE", "").strip().lower() == "query"
    if query_only:
        print("[Test Mode] 仅查询模式，跳过任务执行")
    sc = globalConfig.get("sign_config", {})
    mc = globalConfig.get("market_config", {})
    rc = globalConfig.get("regional_config", {})
    jc = globalConfig.get("jfsc_config", {})
    grab_mode = False
    ah_friday_grab = False
    hour = datetime.now().hour
    current_min = datetime.now().minute
    is_friday = datetime.now().weekday() == 4
    if not query_only:
        if sc.get("run_grab_coupon", False) and globalConfig.get("enable_sign", True):
            # 定时规则配的是 57 9,17 * * *，窗口必须覆盖 57 分，
            # 否则 9:57 启动会落进日常串行模式，账号 2-5 排队错过开抢
            if hour in [9, 17] and (57 <= current_min <= 59):
                grab_mode = True
        if (AH_FRIDAY_AMOUNT and is_friday and rc.get("run_ah_friday", True)
                and globalConfig.get("enable_regional", True)
                and hour == 9 and (57 <= current_min <= 59)):
            ah_friday_grab = True
            grab_mode = True
    print("-" * 36)
    switch_map = [
        ("enable_sign",     "首页签到"),
        ("enable_ltzf",     "联通祝福"),
        ("enable_ttlxj",    "天天领现金"),
        ("enable_ttxc",     "通通乡村"),
        ("enable_market",   "权益超市"),
        ("enable_jfsc",     "积分商城"),
        ("enable_woread",   "联通阅读"),
        ("enable_aiting",   "联通爱听"),
        ("enable_security", "安全管家"),
        ("enable_ltyp",     "联通云盘"),
        ("enable_wostore",  "沃云手机"),
        ("enable_regional", "区域专区"),
    ]
    for key, label in switch_map:
        enabled = globalConfig.get(key, True)
        if grab_mode:
            if key == "enable_sign" and sc.get("run_grab_coupon", False):
                status = "运行(仅抢兑)"
            elif key == "enable_regional" and ah_friday_grab:
                status = "运行(安徽抢红包)"
            else:
                status = "跳过(抢兑模式)"
        elif query_only:
            status = "仅查询" if enabled else "关闭"
        else:
            status = "运行" if enabled else "关闭"
        print(f"{label}设置为: {status}")
        if key == "enable_sign" and enabled and not query_only:
            print(f"  └─ 抢话费券: {'开启' if sc.get('run_grab_coupon', False) else '关闭'}")
        if key == "enable_regional" and enabled and not query_only:
            ah_status = "开启" if rc.get("run_ah_friday", True) and AH_FRIDAY_AMOUNT else "关闭"
            print(f"  └─ 安徽超级星期五: {ah_status}" + (f" (面额{AH_FRIDAY_AMOUNT}元)" if AH_FRIDAY_AMOUNT else ""))
        if key == "enable_market" and enabled and not query_only and not grab_mode:
            print(f"  └─ 做任务: {'开启' if mc.get('run_task', True) else '关闭'}")
            print(f"  └─ 抽奖: {'开启' if mc.get('run_draw', True) else '关闭'}")
            print(f"  └─ 自动领奖: {'开启' if mc.get('run_claim', False) else '关闭'}")
        if key == "enable_jfsc" and enabled and not query_only and not grab_mode:
            print(f"  └─ 赚积分任务: {'开启' if jc.get('run_task', True) else '关闭'}")
            print(f"  └─ 积分兑换: {'开启' if jc.get('run_exchange', True) else '关闭'}")
    print(f"推送通知设置为: {'开启' if globalConfig.get('enable_notify', True) else '关闭'}")
    print(f"设备ID刷新: {'强制刷新' if globalConfig.get('refresh_device_id', False) else '使用缓存'}")
    print("-" * 36)
    print("")
    if grab_mode:
        print(f"⏰ [自动触发] 检测到抢兑时间点 ({hour}:{current_min:02d})，进入并发抢兑模式")
        tasks_desc = []
        if sc.get("run_grab_coupon", False) and globalConfig.get("enable_sign", True):
            tasks_desc.append(f"{'→'.join(str(a) for a in GRAB_AMOUNTS)}元话费券")
        if ah_friday_grab:
            tasks_desc.append(f"安徽{AH_FRIDAY_AMOUNT}元红包")
        print(f"🚨🚨🚨 [抢兑模式已启动] 目标: {' + '.join(tasks_desc)} 🚨🚨🚨")
        print("")
        from concurrent.futures import ThreadPoolExecutor

        def run_grab_task(u):
            u.configure_proxy()
            if u.ensure_login():
                sub_futures = []
                with ThreadPoolExecutor(max_workers=2) as sub_executor:
                    if sc.get("run_grab_coupon", False) and globalConfig.get("enable_sign", True):
                        sub_futures.append(sub_executor.submit(u.sign_grabCoupon))
                    if ah_friday_grab:
                        sub_futures.append(sub_executor.submit(u.ah_friday_task))
                    for f in sub_futures:
                        try:
                            f.result()
                        except Exception as e:
                            u.log(f"抢兑子任务异常: {e}")
            else:
                u.log("登录流程失败，跳过该账号")

        print(f"🚀 [并发模式] 启动 {len(accounts)} 个账号同时抢兑...")
        with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
            futures = [executor.submit(run_grab_task, u) for u in users]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"[-] Thread Error: {e}")
        do_notify(users)
        return
    print("🚀 开始串行执行日常任务...")
    print("")
    for u in users:
        print("")
        print(f"🔄 正在初始化账号[{u.index}]...")
        try:
            u.configure_proxy()
            if u.ensure_login():
                print("")
                print(f"------------------ 账号[{u.index}][{mask_str(u.account_mobile)}] ------------------")
                print("")
                try:
                    u.execute_daily_tasks(query_only=query_only)
                except Exception as e:
                    u.log(f"⚠️ 账号任务执行异常, 已跳过该账号剩余任务: {e}")
                print("⏳ 账号处理完毕，等待 2 秒...")
                time.sleep(2)
            else:
                u.log("登录流程失败，跳过该账号")
        except Exception as e:
            u.log(f"⚠️ 账号[{u.index}]处理异常: {e}")
    cross_view_security_share_keys(users)
    do_notify(users)
if __name__ == "__main__":
    main()