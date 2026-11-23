#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 顺丰速运 每日任务
定时规则
cron: 11 6,18 * * *

顺丰速运自动任务 v1.5.0

功能：自动执行顺丰速运日常积分任务 + 会员日活动 + 世界杯活动
支持签到、做任务、领积分、会员日抽奖、红包合成与提取、世界杯礼物与射门游戏等

青龙使用:
  脚本管理新建 sfsy.py，环境变量只需填 sfsyUrl（凭证格式见下方 1~6 节）。
  依赖: pip install requests
        用 socks5 代理时另需 pip install PySocks

更新说明:
### 2026.10.30
v1.5.0:
- 🔑 新增 appsign 凭证（最优方案，可长期复用）
  · 原理：重放 APP 的 universalSign 请求，服务端每次都签发【新 sign】，
    再用 sign 换新 sessionId —— 不必自己算 requestSign
  · 格式：appsign=<headers JSON>@<body>
  · 实测：同一次抓包的凭证连续重放 3 次 → 3 个不同有效 sign，每次都能换出 session
  · 已测出【最小必需头】只有 11 个，requestSign/token/memberId 全部可省：
      deviceId regionCode languageCode screenSize mediaCode systemVersion
      clientVersion model jsbundle sytToken timeInterval
  · 缺头报错码即缺失序号：!_0=deviceId !_1=regionCode ... !_9=timeInterval !_10=sytToken
    !_11 = body 有问题（字段缺失/顺序被改/name 非目标域名）
  · 抓包方式：APP「我的 → 积分」时抓 universalSign 请求，
    复制其【请求头】和【请求体】，拼成 appsign=<头JSON>@<体原文>
  · 注意 body 必须原文照抄，切勿重新序列化（否则 !_11）

### 2026.10.30
v1.4.0:
- 🔑 新增 ucmp 直读积分（APP 长期凭证，绕过 mcs 短效 session）
  · 凭证格式 ucmp=<token>|<memberId>|<sytToken>|<requestSign>|<timeInterval>
  · 拆包+抓包实证：ucmp 的 token 跨天不变，配一组签名即可反复读积分
  · 三元组(sytToken/requestSign/timeInterval)必须整套配套，改任一值即校验失败；
    但同一组可跨接口复用，实测 20 分钟后仍可用
  · 可单独使用（只读积分），也可与 sfapp 并存
- 🔍 纠正 v1.3.0 的结论：APP换签用的 sign 实测约 15 分钟即失效，
  并非可长期复用；ucmp 凭证才是更长久的
- 关键实证：ucmp memberId 与 mcs _login_user_id_ 是同一个 userId

### 2026.10.30
v1.3.0:
- 🔑 新增 APP 换签（顺丰速运 APP，拆包 com.sf.activity v9.96.1 实证）：
  · 新凭证格式 sfapp=<token> 或 sfapp=<抓包完整URL>，优先于 suuid
  · 走 APP 端点 share/app/shareRedirect → 服务端现签并下发 sessionId
  · APP 与小程序是两套独立认证体系：APP 无 suuid/_login_mobile_，
    sysCode=NEXT-CCMAS-CORECMOBILE（小程序为 MCS-MIMP-CORE）
  · APP 凭证失效频率远低于小程序 suuid，suuid 链路完整保留向后兼容
- 换签失败时诊断信息更明确：直接打印末跳响应体（如 100012 get.user.info）

### 2026.10.28
v1.2.0:
- 🔑 新增 suuid 自动续期（根治 CK 过期）：
  · 环境变量支持只填 suuid=xxx（小程序打开瞬间 ucmp.sf-express.com 请求头里的 32 位 hex）
  · 每次运行自动走换签链：suuid → sfnewactivity(302) → activityRedirect(302) → 全新 sessionId
  · 加密参数/cx-at-sign 全部由服务端 302 链现签，客户端零计算
  · 有 sessionId 的旧凭证仍然兼容（直接使用，不换签）
  · suuid 失效时推送「suuid失效了」，只需低频重抓 suuid，不再每天抓 sessionId
- 实证结论：JS v3 注释「suuid 与 sessionId 完全隔离」有误——suuid 可反复换新 sessionId

### 2026.10.18
v1.1.2:
- 对齐抓包实证版 (JS v3) 结论：
  · CK 失效识别补充 errorCode 100111（MCS 用户信息失效）
  · 签到幂等：errorCode 3400002 / “已签到” 视为成功
  · 任务列表 channelType 只扫真实值 1/2/3/4（01-04 为别名，完全重复）
  · finishTask 返回 obj:false 视为“服务端未确认完成”，不再当成功
  · fetchIntegral：600005 已领取=幂等成功；600006=需真实业务行为，直接归类跳过，
    不再无效重试 execute_task
- 失效识别支持 errorCode 字段精确匹配

### 2026.07.15
v1.1.1:
- 端午活动替换为世界杯活动，自动按活动日期启停
- 世界杯助力目标使用配置区自有 ID，随机下注默认关闭
- 日常任务码兼容更多跳转字段，人工任务明确跳过

### 2026.06.08
v1.1.0:
- 新增端午活动，支持浏览领奖、砸粽、金币统计和推送汇总
- 新增 CK 失效识别，失效时推送“CK失效了”

配置说明:
1. 账号变量 (sfsyUrl)
   格式: <凭证>[;其他凭证...][#代理地址]
   多账号用 & 分隔
   凭证优先级: appsign > sfapp > suuid > 传统CK

2. ⭐ appsign（推荐，抓一次可长期复用，无需 cookie）

   2.1 它是什么
       APK 里有一条「签名服务」接口：
         POST https://ccsp-egmas.sf-express.com/cx-app-member/member/app/user/universalSign
       你把【目标域名 + 身份信息】发过去，服务端返回一个该域名可用的 sign；
       再用这个 sign 就能换出 mcs 会话（sessionId）。

       appsign 就是这条请求的【请求头 + 请求体】存档。脚本每次运行都重放它，
       服务端每次现签一个新的 sign —— 所以不需要你算签名，也不需要 cookie。

   2.2 怎么抓
       ① 顺丰 APP 打开抓包工具（HttpCanary / Reqable / Stream 等均可）
       ② 在 APP 里点「我的」→「积分」，让它发请求
       ③ 在抓包列表里找这条（按域名 ccsp-egmas.sf-express.com 或关键字 universalSign 过滤）：
            POST /cx-app-member/member/app/user/universalSign
       ④ 打开这条请求，复制两样东西：
            · 请求头（Headers）
            · 请求体（Body / Request Body）—— 复制【原文】，不要格式化

   2.3 怎么拼
       appsign=<请求头JSON>@<请求体原文>
       注意是 @ 分隔：@ 左边放请求头（JSON 对象），@ 右边放请求体原文。

   2.4 请求头：只填这 11 个就够（其余全部可省）

       字段            说明                 会变吗
       ------------    -----------------    ----------
       deviceId        设备标识              固定
       regionCode      地区码，如 CN          固定
       languageCode    语言，如 sc            固定
       screenSize      屏幕尺寸，如 1080x2376  固定
       mediaCode       平台标识，如 AndroidML  固定
       systemVersion   系统版本，如 16         固定
       clientVersion   APP 版本，如 9.96.1     APP 升级时变
       model           机型，如 <你的机型>   固定
       jsbundle        RN bundle 版本         APP 热更时变
       sytToken        会话令牌               ★ 每次抓包都不同
       timeInterval    请求时间戳(13位毫秒)    ★ 每次抓包都不同

       可以完全省略的头（实测去掉照样成功）：
         requestSign、token、memberId、srcDeviceGuid、carrier、
         User-Agent、Accept-Encoding、Connection、Content-Length 等
       其中 requestSign 也不需要——这正是本方案的价值：不用算签名。

   2.5 请求体：6 个字段全部必需，一个不能少
       {
         "mobile":      "132xxxxxxxx",                              手机号
         "userId":      "<你的 userId>",                       用户ID
         "memNo":       "000000000000000000006860",         会员号
         "name":        "mcs-mimp-web.sf-express.com",              目标域名(勿改)
         "extra":       "",
         "needReqTime": "1"
       }
       删任何一个都报 information error!_11；name 不能改成别的域名。

   2.6 完整示例（下列值均为占位符，请替换成你自己抓到的）
       appsign={"deviceId":"<你的deviceId>","regionCode":"CN","languageCode":"sc","screenSize":"1080x2376","mediaCode":"AndroidML","systemVersion":"16","clientVersion":"9.96.1","model":"<你的机型>","jsbundle":"<你的jsbundle>","sytToken":"<抓包的sytToken>","timeInterval":"<抓包的timeInterval>"}@{"mobile":"<手机号>","userId":"<用户ID>","memNo":"<会员号>","name":"mcs-mimp-web.sf-express.com","extra":"","needReqTime":"1"}

   2.7 两个必须注意的地方
       · 请求体必须原文照抄。用工具格式化、或让脚本 json.dumps 重新序列化，
         字段顺序/空白变了会稳定报 information error!_11。
       · 变量值必须是单行，中间不能有换行（青龙里建议用「多行文本」但内容写一行）。

   2.8 有效期与失效处理
       · sytToken + timeInterval 这组实测 1 小时内多次重放均有效；
         更长有效期未验证，可能能活数天。
       · 失效表现：报 information error!_9（缺 timeInterval）
                    或 !_10（缺 sytToken），或「universalSign 续签失败」。
       · 处理：重新抓一次，只替换 sytToken 和 timeInterval 两个值即可，
         其他 9 个头是固定值，不用动。

   2.9 为什么不用 cookie
       全程不发送任何 Cookie。sessionId / _login_mobile_ / _login_user_id_
       都是第 2.1 步服务端在 302 响应里下发的，脚本自动收下并维护，
       不需要你抓、也不需要你填。

3. sfapp（备选，仅在 appsign 不可用时使用）
   sfapp=<activityRedirect完整URL>@<16位token>
   抓法：APP「我的 → 积分」时找请求
         GET /mcs-mimp/share/app/activityRedirect?sign=...&bizCode=...
         复制完整 URL（不要解码），再从同页任意业务请求 body 里取
         {"sysCode":"MCS-MIMP-CORE-1","token":"<16位>"} 的 token。
   缺点：sign 约 15 分钟过期，需频繁重抓。

4. suuid（微信小程序，短效）
   suuid=<32位hex>
   微信打开「顺丰速运」小程序，抓任意 ucmp.sf-express.com 请求，取请求头里的 suuid。

5. 传统 CK（仍兼容）
   sessionId=xxx;_login_mobile_=xxx;_login_user_id_=xxx
   注意：sessionId 短效（实测约 10 分钟），仅作最后兜底。

6. 代理设置（可选，不用代理就不用管）
    - 固定代理：填在账号变量最后，用 # 分隔，如
        appsign=...@...#http://127.0.0.1:1080
    - 动态代理：环境变量 SF_PROXY_API_URL = 你的代理提取链接
    - 代理类型：环境变量 SF_PROXY_TYPE = http 或 socks5（默认 socks5）

7. 任务开关与并发（在下方「配置区域」修改）
    ENABLE_DAILY_TASK    = True/False  日常积分任务
    ENABLE_MEMBER_DAY    = True/False  会员日活动 (每月26-28号)
    ENABLE_WORLD_CUP     = True/False  世界杯活动 (2026.07.02-07.20)
    ENABLE_WORLD_CUP_BET = True/False  世界杯随机下注
    TASK_SCAN_ALIAS      = True/False  任务列表是否补扫 01-04 别名渠道
    CONCURRENT_NUM       = 1~20        并发数量

8. 推送通知（可选）
    环境变量 SFSY_PUSH = 1 开启（默认）, 0 关闭
    依赖青龙自带的 notify.py 模块

9. 关于「积分 +0」
    日志里大量出现「人工任务需在小程序完成」是正常现象，不是故障：
      · 已完成的任务（status=3）当天不会再做
      · 需真实寄件/下单/设顺丰ID/领券的任务，脚本设计上跳过
    若所有任务都不可执行，当日就会显示「积分+0」；
    次日浏览类任务会重置，届时会重新产生积分。

定时规则建议 (Cron):
11 6,18 * * *

From: YaoHuo8648
Email: zheyizzf@188.com
Update: 2026.10.28
"""

import hashlib
import json
import os
import random
import re
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import unquote, urlparse, parse_qs, quote as url_encode, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PUSH_SWITCH = os.getenv("SFSY_PUSH", "1")
try:
    from notify import send as notify_send
    print("✅ 成功加载青龙notify推送模块")
except ImportError:
    print("⚠️ 未找到notify模块，推送功能不可用（本地运行可忽略）")
    notify_send = None

# ==================== 配置区域 ====================
# 功能开关 (True=开启, False=关闭)
ENABLE_DAILY_TASK = True         # 日常积分任务 (签到+做任务+领积分)
ENABLE_MEMBER_DAY = True         # 会员日活动 (每月26-28号自动执行)
ENABLE_WORLD_CUP = True          # 世界杯活动 (2026.07.02-07.20)
ENABLE_WORLD_CUP_BET = False     # 世界杯随机下注，开启会消耗金币
WORLD_CUP_BET_COIN = 10          # 单场下注金币，服务端最低 10
WORLD_CUP_ASSIST_ID = ''  # 主账号助力目标
CONCURRENT_NUM = 1               # 并发数量 (1~20)

TOKEN = 'wwesldfs29aniversaryvdld29'
inviteId = []
SYS_CODE = 'MCS-MIMP-CORE'

# 任务列表渠道：实测 1/2/3/4 为真实值，01-04 是完全相同的别名。
# 需要完整复现抓包时把 TASK_SCAN_ALIAS 设为 True 多扫 4 次请求。
TASK_SCAN_ALIAS = False

# 日常任务跳过列表（含需真实业务行为的任务码，与抓包实证版对齐）
DAILY_SKIP_TASKS = [
    '用行业模板寄件下单', '用积分兑任意礼品', '参与积分活动',
    '每月累计寄件', '完成每月任务', '去使用AI寄件',
    # 以下任务需要真实寄件或在小程序中设置资料，脚本不冒充完成
    '寄一单国际件', '去新增一个收件偏好', '设置你的顺丰ID',
    '去使用AI小丰寄件',
]

# 已实证需真实业务行为的任务码（写标题名不可靠时兜底）
TASK_CODE_BLOCKLIST = {
    'B0C30EA64EFB4828B6CD7BB6F002E6E5': '需真实发起 AI 寄件下单',
    'D66A32227E964E959D19E52004A753F3': '需真实领取生活特权',
    'D95612AEF0D44FEEBE7157017BDBCB1A': '需真实寄国际件',
    '1ED31ACAC5C24A1DAC8660D57701A146': '需真实用模板下单',
    '7A9A0EF217074583935DDB3D84C0DF97': '需真实设置顺丰ID',
    '5645921EFDAD48DE94950DD5DA6C6231': '需真实新增收件偏好',
    '90D8EC03765A422ABC99F01067479485': '需消耗 50 积分参与活动',
    'A431239561DC456289C3E7C1F421DA12': '需消耗 260 积分参与活动',
}

# 会员日跳过任务类型
MEMBER_DAY_SKIP_TASK_TYPES = [
    'SEND_SUCCESS', 'INVITEFRIENDS_PARTAKE_ACTIVITY', 'OPEN_SVIP',
    'OPEN_NEW_EXPRESS_CARD', 'OPEN_FAMILY_CARD', 'CHARGE_NEW_EXPRESS_CARD',
    'INTEGRAL_EXCHANGE',
]

WORLD_CUP_ACTIVITY_CODE = 'WORLD_CUP'
WORLD_CUP_CHANNEL = '26sjbapp'
WORLD_CUP_PLATFORM = 'SFAPP'
WORLD_CUP_CITY_CODE = os.getenv('SF_WORLD_CUP_CITY_CODE', '021')
WORLD_CUP_START = datetime(2026, 7, 2).date()
WORLD_CUP_END = datetime(2026, 7, 20).date()
WORLD_CUP_ENABLE_GAME = True
WORLD_CUP_ENABLE_SETTLE = True
# 不保留来源不明的固定 taskCode，只使用当前任务列表实时返回的 code
WORLD_CUP_SAFE_TASK_NAMES = {
    '浏览积分商城',
    '去看看互寄8折权益',
}

# CK 失效识别：关键字 + 精确错误码
# 100111 = MCS 用户信息失效（抓包实证）
CK_INVALID_KEYWORDS = (
    '未登录', '请登录', '请先登录', '登录失效', '登录已失效',
    '登录过期', '会话失效', 'session失效', 'sessionid失效',
    'sessionid已失效', 'token失效', '重新登录', 'not_login',
    'unauthorized', '用户信息失效',
)
CK_INVALID_ERROR_CODES = {'100111'}

# 任务积分领取（fetchIntegral）错误码语义（抓包实证）
# 600005 已领取 = 幂等成功；600006 任务未完成 = 需真实业务行为
FETCH_ALREADY_CODES = {'600005'}
FETCH_NEED_REAL_CODES = {'600006'}
# 签到幂等错误码：3400002 今日已签到
SIGN_ALREADY_CODES = {'3400002'}

# 代理配置
PROXY_API_URL = os.getenv("SF_PROXY_API_URL", "")
PROXY_TYPE = os.getenv("SF_PROXY_TYPE", "socks5")
PROXY_TIMEOUT = 15
MAX_PROXY_RETRIES = 5
REQUEST_RETRY_COUNT = 3
PROXY_RETRY_DELAY = 2
PROXY_CONTEXT = {'last_fetch_ts': 0}
PROXY_LOCK = threading.Lock()
print_lock = Lock()
# =================================================


def world_cup_active(current_date=None) -> bool:
    current_date = current_date or datetime.now().date()
    return WORLD_CUP_START <= current_date <= WORLD_CUP_END


# ==================== suuid 换签续期 ====================
# 链路（抓包实证 2026.10.28）：
#   GET ucmp  /wechat-act/weixin/activity/sfnewactivity?suuid=xxx
#     → 302 Location: mcs-mimp /share/weChat/activityRedirect?unionId=..&openId=..&memId=..
#        &cx-at-sign=..&cx-at-ts=..&cx-at-nonce=..（全部服务端现签，客户端零计算）
#   GET mcs-mimp /share/weChat/activityRedirect?...（跟随302）
#     → 302 + Set-Cookie: sessionId=<全新> / _login_user_id_ / _login_mobile_
# suuid 可反复换新 sessionId（多次实测），suuid 本身即长效凭证。

WXAPP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI '
    'MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) '
    'UnifiedPCWindowsWechat(0xf2541f37) XWEB/25799 miniProgram/wxd4185d00bf7e08ac'
)

SFNEWACTIVITY_BIZ = (
    '%7B%22path%22%3A%22%2Fup-member%2FnewPoints%22%2C%22linkCode%22%3A'
    '%22SFAC20230803190840424%22%2C%22supportShare%22%3A%22YES%22%2C'
    '%22subCategoryCode%22%3A%221%22%2C%22from%22%3A%22mypoint%22%2C'
    '%22categoryCode%22%3A%221%22%7D'
)


class SuuidRenewer:
    """用 suuid 换取全新 MCS sessionId（自动续期核心）"""

    def __init__(self, suuid: str, fixed_proxy: str = ""):
        self.suuid = suuid.strip()
        self.fixed_proxy = fixed_proxy

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.verify = False
        if self.fixed_proxy:
            proxy_dict = parse_fixed_proxy(self.fixed_proxy)
            if proxy_dict:
                s.proxies = proxy_dict
        else:
            result = get_api_proxy()
            if result:
                s.proxies = result[0]
        return s

    def renew(self, logger=None, verbose=False) -> Tuple[bool, str, str, str]:
        """执行换签链。

        返回 (ok, sessionId, user_id, mobile)
        verbose=True 时打印 302 链每一跳的状态/Location/Set-Cookie（诊断用）
        """
        headers = {'User-Agent': WXAPP_UA}
        url = (
            'https://ucmp.sf-express.com/wechat-act/weixin/activity/sfnewactivity'
            f'?bizCode={SFNEWACTIVITY_BIZ}'
            '&regSource=mypoint&citycode=571&cityname=%E6%9D%AD%E5%B7%9E'
            f'&wxapp-version=V17.80&suuid={self.suuid}'
        )
        for attempt in range(3):
            s = self._session()
            try:
                # 逐跳手动跟随 302（verbose 时记录每跳详情用于诊断）
                cur = url
                hops = []
                for _hop in range(10):
                    r = s.get(cur, headers=headers, timeout=PROXY_TIMEOUT,
                              allow_redirects=False)
                    raw_sc = []
                    try:
                        raw_sc = r.raw.headers.get_all('Set-Cookie') or []
                    except Exception:
                        sc = r.headers.get('Set-Cookie')
                        raw_sc = [sc] if sc else []
                    loc = r.headers.get('Location', '')
                    hops.append((cur, r.status_code, loc, raw_sc, r.text[:150]))
                    if not (300 <= r.status_code < 400 and loc):
                        break
                    cur = urljoin(cur, loc)
                if verbose and logger:
                    logger.info(f'换签链共 {len(hops)} 跳:')
                    for i, (u, st, loc, scs, body) in enumerate(hops, 1):
                        logger.info(f'[hop{i}] {st} {u[:110]}')
                        if loc:
                            logger.info(f'[hop{i}]   → Location: {loc[:160]}')
                        for c in scs:
                            logger.info(f'[hop{i}]   Set-Cookie: {c[:140]}')
                        if st < 300 or st >= 400:
                            logger.info(f'[hop{i}]   body: {body[:140]}')
                cookies = s.cookies.get_dict()
                sid = cookies.get('sessionId', '')
                user_id = cookies.get('_login_user_id_', '')
                mobile = cookies.get('_login_mobile_', '')
                if sid:
                    if logger:
                        logger.success(f'suuid 换签成功: 新 sessionId {sid[:8]}...{sid[-4:]}')
                    return True, sid, user_id, mobile
                # 常见失败：suuid 失效时 ucmp 返回 200 JSON（无跳转）或 401
                if logger:
                    logger.warning(f'suuid 换签第{attempt + 1}次未获得 sessionId')
            except Exception as e:
                if logger:
                    logger.warning(f'suuid 换签第{attempt + 1}次异常: {str(e)[:80]}')
            time.sleep(2)
        return False, '', '', ''

    @staticmethod
    def check_alive(suuid: str, fixed_proxy: str = "") -> bool:
        """只读探测 suuid 是否仍有效（sfnewactivity 是否给出换签 Location）"""
        r = SuuidRenewer(suuid, fixed_proxy)._session()
        try:
            url = (
                'https://ucmp.sf-express.com/wechat-act/weixin/activity/sfnewactivity'
                f'?bizCode={SFNEWACTIVITY_BIZ}&regSource=mypoint'
                f'&wxapp-version=V17.80&suuid={suuid}'
            )
            resp = r.get(url, headers={'User-Agent': WXAPP_UA}, timeout=PROXY_TIMEOUT,
                         allow_redirects=False)
            loc = resp.headers.get('Location', '')
            # 2026.10.29 实测：链路"活着"但身份签发消失（无 unionId/memId）时，
            # 会静默种出匿名会话。判定 suuid 有效必须同时有身份参数
            return ('activityRedirect' in loc
                    and ('memId=' in loc or 'unionId=' in loc or 'openId=' in loc))
        except Exception:
            return False


# ==================== APP 端换签（顺丰速运 APP）====================
# 实证来源（2026.10.30 拆包 com.sf.activity v9.96.1，React Native Hermes bundle）
#   GET mcs-mimp /share/app/shareRedirect      → 未登录返回 {"errorCode":"100012","errorMessage":"error.get.user.info"}
#   GET mcs-mimp /share/app/activityRedirect   → 同上（两条平行入口，均存活）
#   GET ucmp     /wxaccess/app/auth/<BIZ_CODE> → APP 专属认证页（CX_REGION_APP / SIGN_CODE_PAGE_APP 等）
#
# APP 与小程序是两套完全独立的认证体系（拆包实证）：
#   · APP 无 suuid / _login_mobile_ / _login_user_id_（Hermes 字符串表中 0 命中）
#   · APP 用 accessToken / refreshToken + UniversalSign(HMAC) 签名，sysCode = NEXT-CCMAS-CORECMOBILE
#   · 小程序 sysCode = MCS-MIMP-CORE
#
# 因此 APP 换签不能复用 suuid，需要 APP 侧凭证。本类按"凭证 → 换签 → 拿 Cookie"的
# 同一套出口实现，与 SuuidRenewer 保持相同返回签名，便于上层无差别调用。
#
# 凭证获取方式（二选一，需人工做一次）：
#   A. 抓包：APP 登录态下打开「我的 → 积分」，取 share/app/shareRedirect 请求的完整 URL
#      （含 bizCode / source=SFAPP 等参数），整条贴进来，本类直接回放即可换签。
#   B. 本地存储：root 机导出 /data/data/com.sf.activity/ 下的 accessToken / refreshToken，
#      以 sfapp=<token> 形式填写。
# 拿到一次后可反复换新 sessionId，凭证失效频率远低于小程序。

APP_UA = (
    'Mozilla/5.0 (Linux; Android 12; M2011K2C Build/SKQ1.211006.001; wv) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.132 '
    'Mobile Safari/537.36 mediaCode=SFEXPRESSAPP-Android-ML'
)

APP_SYS_CODE = 'NEXT-CCMAS-CORECMOBILE'
APP_SHARE_REDIRECT = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/shareRedirect'
APP_ACTIVITY_REDIRECT = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/activityRedirect'

# APP 换签默认参数（拆包 + 2026.10.30 抓包双重实证）
APP_DEFAULT_BIZCODE = '6115@Ylo0Z3E2MDVNbng5ZHd3ZGtmNnpyNEYzN21jYWxZOE5SZ1V3d3c5NzhGVT0='

# APP 业务接口额外的固定头（抓包实证，缺了会报「权限验证失败」）
APP_BIZ_HEADERS = {
    'X-Requested-With': 'com.sf.activity',
    'channel': 'point240613',
    'platform': 'SFAPP',
    'Origin': 'https://mcs-mimp-web.sf-express.com',
    'Referer': 'https://mcs-mimp-web.sf-express.com/up-member/newPoints',
}


class AppSessionRenewer:
    """用 APP 端凭证换取 MCS sessionId（APP 换签核心）。

    链路（2026.10.30 抓包实证，已跑通）：
      GET mcs-mimp /share/app/activityRedirect?sign=<RSA签名>&source=SFAPP
          &bizCode={"path":"/up-member/newPoints",...}&citycode=571&cityname=杭州
        → 302 + Set-Cookie: sessionId / _login_user_id_ / _login_mobile_
      · sign 是 RSA 私钥签名（base64 后 344 字符 / 256 字节），服务端可反复验证，
        实测可重复使用且每次换出新 sessionId
      · 请求头无需任何 Cookie，sign 即全部身份凭证

    凭证格式（sfsyUrl 里填）：
      sfapp=<activityRedirect完整URL>@<token>
    其中 token 为业务接口 body 里的 16 位串（抓包可见 {"sysCode":...,"token":...}），
    服务端会校验，随机值会报「token错误」。
    """

    def __init__(self, credential: str, fixed_proxy: str = ""):
        self.credential = (credential or '').strip()
        self.fixed_proxy = fixed_proxy
        self.token = ''
        # 凭证格式: <url或签名串>@<token>
        if '@' in self.credential:
            head, _, tail = self.credential.rpartition('@')
            if head and tail and len(tail) <= 64 and '://' not in tail:
                self.credential = head
                self.token = tail.strip()

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.verify = False
        if self.fixed_proxy:
            proxy_dict = parse_fixed_proxy(self.fixed_proxy)
            if proxy_dict:
                s.proxies = proxy_dict
        else:
            result = get_api_proxy()
            if result:
                s.proxies = result[0]
        return s

    def _build_url(self) -> str:
        """把凭证归一成可请求的换签 URL。"""
        cred = self.credential
        if cred.startswith('http://') or cred.startswith('https://'):
            # 抓包得到的完整 URL，原样回放（含 sign / bizCode 等全部参数）
            return cred
        # 裸 sign：回填到 activityRedirect，补齐 APP 必需参数
        return (
            f'{APP_ACTIVITY_REDIRECT}?sign={url_encode(cred, safe="")}'
            '&source=SFAPP&citycode=571&cityname=%E6%9D%AD%E5%B7%9E'
        )

    def renew(self, logger=None, verbose=False) -> Tuple[bool, str, str, str]:
        """执行 APP 换签链，返回 (ok, sessionId, user_id, mobile)。"""
        url = self._build_url()
        headers = {
            'User-Agent': APP_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'com.sf.activity',
        }
        for attempt in range(3):
            s = self._session()
            try:
                cur = url
                hops = []
                # 抓包实证：仅有 1 跳 302（→ 业务页），保留 10 跳冗余
                for _hop in range(10):
                    r = s.get(cur, headers=headers, timeout=PROXY_TIMEOUT,
                              allow_redirects=False)
                    raw_sc = []
                    try:
                        raw_sc = r.raw.headers.get_all('Set-Cookie') or []
                    except Exception:
                        sc = r.headers.get('Set-Cookie')
                        raw_sc = [sc] if sc else []
                    loc = r.headers.get('Location', '')
                    hops.append((cur, r.status_code, loc, raw_sc, r.text[:150]))
                    if not (300 <= r.status_code < 400 and loc):
                        break
                    cur = urljoin(cur, loc)
                if verbose and logger:
                    logger.info(f'APP 换签链共 {len(hops)} 跳:')
                    for i, (u, st, loc, scs, body) in enumerate(hops, 1):
                        logger.info(f'[hop{i}] {st} {u[:110]}')
                        if loc:
                            logger.info(f'[hop{i}]   → Location: {loc[:160]}')
                        for c in scs:
                            logger.info(f'[hop{i}]   Set-Cookie: {c[:140]}')
                        if st < 300 or st >= 400:
                            logger.info(f'[hop{i}]   body: {body[:140]}')
                cookies = s.cookies.get_dict()
                sid = cookies.get('sessionId', '')
                user_id = cookies.get('_login_user_id_', '')
                mobile = cookies.get('_login_mobile_', '')
                if sid:
                    if logger:
                        logger.success(f'APP 换签成功: 新 sessionId {sid[:8]}...{sid[-4:]}')
                    return True, sid, user_id, mobile
                # 未拿到 sessionId 时，打印终止跳的响应体便于定位（sign 过期/参数不全）
                if logger and hops:
                    last = hops[-1]
                    logger.warning(f'APP 换签第{attempt + 1}次未获得 sessionId，'
                                   f'末跳 {last[1]} body={last[4][:100]}')
            except Exception as e:
                if logger:
                    logger.warning(f'APP 换签第{attempt + 1}次异常: {str(e)[:80]}')
            time.sleep(2)
        return False, '', '', ''

    @staticmethod
    def check_alive(credential: str, fixed_proxy: str = "") -> bool:
        """只读探测凭证是否仍有效（换签是否给出 302 跳转）。

        2026.10.30 抓包实证：有效凭证返回 302，Location 指向业务页
        （如 /up-member/newPoints），并 Set-Cookie sessionId。
        故判定依据是「302 + 带身份 Cookie」，而非 Location 含特定关键字。
        """
        renewer = AppSessionRenewer(credential, fixed_proxy)
        r = renewer._session()
        try:
            resp = r.get(renewer._build_url(),
                         headers={'User-Agent': APP_UA},
                         timeout=PROXY_TIMEOUT, allow_redirects=False)
            if not (300 <= resp.status_code < 400):
                return False
            cookies = r.cookies.get_dict()
            return bool(cookies.get('sessionId') and cookies.get('_login_mobile_'))
        except Exception:
            return False


# ==================== ucmp APP 凭证直连（读积分）====================
# 实证（2026.10.30 抓包，已多次实测跑通）：
#   POST https://ucmp.sf-express.com/proxy/esgcempcore/<业务路径>
#   请求头认证三元组：
#     token        : AES 密文，APP 登录后长期不变（跨天可用）
#     memberId     : 明文 userId（与 mcs 的 _login_user_id_ 同一个值）
#     sytToken     : 32位hex，每个请求一对
#     requestSign  : "X1Yx==" + 64字节hex，与 sytToken/timeInterval 配套
#     timeInterval : 13位毫秒时间戳，与上两者配套
#   实测结论（2026.10.30 连续验证，含 25 分钟后复测）：
#     · 三元组(sytToken/requestSign/timeInterval)必须整套原样配套，改任何一个都报
#       「token校验失败」
#     · requestSign 与「Host + HTTP方法 + 路径」绑定：
#         - ucmp.sf-express.com      → L119 那组 25 分钟后仍可用（queryMineInfo/goodsList
#                                      /queryStudentUserInfo 均成功，连续 5 次无降级）
#         - ccsp-egmas.sf-express.com → 复用一律 error!_11（连它自己的原组也不行），
#                                      说明该域对签名时效校验严格
#       故 ucmp 域只读能力可长期复用，ccsp 域不行。
#     · getTodaySign 是 GET，与 POST 签名不匹配，恒 401。
#     · 自动签发 sign 的路走不通：universalSign 仅在 ccsp 域，而该域签名无法复用，
#       必须先有 ccsp 域新签名才能调，形成死循环。
#     · 结论：ucmp 凭证只能「读」（积分/商品/学生认证等），
#       签到与做任务（写）必须在 mcs 域，需 sfapp 或 suuid。
#     · token 本身跨天不变；memberId 明文
#   ⇒ 这套凭证比 mcs 的 sessionId(24h) / sign(约15分钟) 都持久，
#     适合用来「读积分/会员信息」做校验与汇报；积分写入仍走 mcs 任务链。

UCMP_BASE = 'https://ucmp.sf-express.com'
UCMP_APPID = 'sfapp-valid-a85073uy'
UCMP_UA = 'okhttp/4.9.1'


class UcmpAppClient:
    """用 APP 长期凭证直连 ucmp 读积分（绕过 mcs 短效 session）。

    凭证格式（| 分隔，共 8 段，全部来自抓包，均无默认值）：
     ucmp=<token>|<memberId>|<sytToken>|<requestSign>|<timeInterval>|<deviceId>|<model>|<jsbundle>
   说明：这套只具备「读」能力（积分/商品等），签到与做任务仍需 appsign/sfapp/suuid。
         appsign 已能满足全部需求，本类仅作备用与积分复核。
    """

    def __init__(self, credential: str, fixed_proxy: str = ""):
        self.raw = (credential or '').strip()
        self.fixed_proxy = fixed_proxy
        parts = self.raw.split('|')
        self.token = parts[0].strip() if len(parts) > 0 else ''
        self.member_id = parts[1].strip() if len(parts) > 1 else ''
        self.syt_token = parts[2].strip() if len(parts) > 2 else ''
        self.request_sign = parts[3].strip() if len(parts) > 3 else ''
        self.time_interval = parts[4].strip() if len(parts) > 4 else ''
        self.device_id = parts[5].strip() if len(parts) > 5 else ''
        self.model = parts[6].strip() if len(parts) > 6 else ''
        self.jsbundle = parts[7].strip() if len(parts) > 7 else ''

    def _headers(self) -> Dict[str, str]:
        # 设备指纹头：实测缺任何一个都返回 401 Unauthorized
        # 这些值都来自抓包，不提供默认值（默认值会是别人的设备信息，无效）
        h = {
            'Accept-Encoding': 'gzip',
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/json',
            'User-Agent': UCMP_UA,
            'clientVersion': '9.96.1',
            'cxgw-appid': UCMP_APPID,
            'languageCode': 'sc',
            'mediaCode': 'AndroidML',
            'memberId': self.member_id,
            'model': self.model,
            'regionCode': 'CN',
            'systemVersion': '16',
            'deviceId': self.device_id,
            'jsbundle': self.jsbundle,
            'screenSize': '1080x2376',
            'carrier': 'unknown',
            'token': self.token,
        }
        if self.syt_token:
            h['sytToken'] = self.syt_token
        if self.request_sign:
            h['requestSign'] = self.request_sign
        if self.time_interval:
            h['timeInterval'] = self.time_interval
        return h

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.verify = False
        if self.fixed_proxy:
            proxy_dict = parse_fixed_proxy(self.fixed_proxy)
            if proxy_dict:
                s.proxies = proxy_dict
        else:
            result = get_api_proxy()
            if result:
                s.proxies = result[0]
        return s

    def post(self, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        url = f'{UCMP_BASE}/proxy/esgcempcore/{path.lstrip("/")}'
        try:
            r = self._session().post(url, headers=self._headers(),
                                     json=data or {}, timeout=PROXY_TIMEOUT)
            return r.json()
        except Exception:
            return None

    def query_points(self) -> Optional[int]:
        """读取可用积分（queryMineInfo.availablePoints）"""
        j = self.post('memberIntegral/userInfoService/queryMineInfo')
        if isinstance(j, dict) and j.get('success'):
            obj = j.get('obj') or {}
            try:
                return int(obj.get('availablePoints'))
            except (TypeError, ValueError):
                return None
        return None

    def query_member_info(self) -> Optional[Dict]:
        """读取会员摘要（等级/积分/成长值），用于汇报与校验。

        注意：本客户端仅具备「读」能力（实测可用接口：
        queryMineInfo / goodsList / queryStudentUserInfo）。
        签到(getTodaySign 为 GET) 与做任务(写) 均在 mcs 域，需 sfapp 或 suuid。
        """
        j = self.post('memberIntegral/userInfoService/queryMineInfo')
        if isinstance(j, dict) and j.get('success'):
            o = j.get('obj') or {}
            return {
                'points': o.get('availablePoints'),
                'level': o.get('levelName'),
                'grade': o.get('gradeVal'),
                'growth': o.get('growthValue'),
                'user_id': o.get('userId'),
            }
        return None


# ==================== appsign 续签（universalSign 重放）====================
# 原理（2026.10.30 抓包实证）：
#   APP 的 universalSign 是「签名服务」——给它目标域名 + 身份信息，它返回一个
#   该域名可用的 sign，再由 sign 换 mcs session。重放该请求即可反复续签，
#   不必自己算 requestSign（实测服务端根本不看 requestSign）。
#
#   实测：同一次抓包的凭证连续重放 3 次 → 3 个不同的有效 sign，
#         且每个都能换出新 sessionId。
#
#   最小必需头只有 11 个（缺一即 information error!_N，N 为字段序号）：
#     !_0 deviceId      !_1 regionCode    !_2 languageCode  !_3 screenSize
#     !_4 mediaCode     !_5 systemVersion !_6 clientVersion !_7 model
#     !_8 jsbundle      !_9 timeInterval  !_10 sytToken     !_11 body 有问题
#   可省：requestSign / token / memberId / srcDeviceGuid / carrier / User-Agent
#
#   body 必须原文照抄，切勿重新序列化（实测 json.dumps 后稳定返回 !_11）

APPSIGN_MUST_HEADERS = [
    'deviceId', 'regionCode', 'languageCode', 'screenSize', 'mediaCode',
    'systemVersion', 'clientVersion', 'model', 'jsbundle',
    'sytToken', 'timeInterval',
]

UNIVERSAL_SIGN_URL = 'https://ccsp-egmas.sf-express.com/cx-app-member/member/app/user/universalSign'
APP_ACTIVITY_REDIRECT = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/activityRedirect'

# share/app/activityRedirect 的活动码（对应「我的 → 积分」页）
APPSIGN_BIZ_CODE = (
    '{"path":"/up-member/newPoints","linkCode":"SFAC20230803190840424",'
    '"supportShare":"YES","subCategoryCode":"1","from":"point240613","categoryCode":"1"}'
)

# shareRedirect 需要微信 UA，否则服务端只回落地页、不下发会话 Cookie
APPSIGN_WX_UA = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 '
    'MicroMessenger/8.0.49 NetType/WIFI Language/zh_CN'
)


class SfAppSession:
    """用 universalSign 重放换取 mcs 会话。

    凭证（一次抓包即可，可长期重复使用）：
      headers : universalSign 请求的 11 个必需头
      body    : universalSign 请求的 body 原文（勿重新序列化）
    """

    def __init__(self, headers: Dict, body: str, proxy: Dict = None):
        hl = {str(k).lower(): v for k, v in (headers or {}).items()}
        self.headers = {}
        for name in APPSIGN_MUST_HEADERS:
            if name.lower() in hl:
                self.headers[name] = hl[name.lower()]
        self.headers['Content-Type'] = 'application/json'
        self.body = (body or '').strip()
        self.raw_headers = headers or {}

        self.session = requests.Session()
        self.session.verify = False
        if proxy:
            self.session.proxies = proxy

        self.session_id = ''
        self.user_id = ''
        self.mobile = ''

    def missing_headers(self) -> List[str]:
        """返回缺失的必需头（诊断用）"""
        return [h for h in APPSIGN_MUST_HEADERS if h not in self.headers]

    def get_sign(self, timeout: int = 20) -> str:
        """重放 universalSign，返回新 sign（失败返回空串）"""
        if self.missing_headers():
            return ''
        try:
            r = self.session.post(UNIVERSAL_SIGN_URL, headers=self.headers,
                                  data=self.body.encode('utf-8'), timeout=timeout)
            j = r.json()
        except Exception:
            return ''
        ok = (j.get('success') is True or j.get('success') == 'true')
        if not ok:
            return ''
        return str((j.get('obj') or {}).get('sign') or '')

    def renew(self, timeout: int = 25) -> bool:
        """换新 session。成功返回 True，并填充 session_id/user_id/mobile"""
        sign = self.get_sign()
        if not sign:
            return False
        url = (f'{APP_ACTIVITY_REDIRECT}?sign={url_encode(sign, safe="")}'
               f'&source=SFAPP&bizCode={url_encode(APPSIGN_BIZ_CODE, safe="")}'
               f'&citycode=571&cityname={url_encode("杭州", safe="")}')
        self.session_id = ''
        try:
            # 只带微信 UA，不带 Cookie —— 服务端靠 sign 建立新会话
            self.session.get(url, headers={'User-Agent': APPSIGN_WX_UA},
                             allow_redirects=False, timeout=timeout)
        except Exception:
            return False
        ck = self.session.cookies.get_dict()
        self.session_id = ck.get('sessionId', '')
        self.user_id = ck.get('_login_user_id_', '')
        self.mobile = ck.get('_login_mobile_', '')
        return bool(self.session_id and self.mobile)

    def post(self, path: str, data: Optional[Dict] = None,
             timeout: int = 25) -> Optional[Dict]:
        """调用 mcs 业务接口。path 例：'commonPost/~memberIntegral~userInfoService~queryUserInfo'"""
        ts = str(int(round(time.time() * 1000)))
        sig = hashlib.md5(
            f'token={TOKEN}&timestamp={ts}&sysCode={SYS_CODE}'.encode()
        ).hexdigest()
        h = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'Content-Type': 'application/json',
            'User-Agent': APP_UA,
            'X-Requested-With': 'com.sf.activity',
            'channel': 'point240613',
            'platform': 'SFAPP',
            'sysCode': SYS_CODE,
            'timestamp': ts,
            'signature': sig,
        }
        try:
            r = self.session.post(
                'https://mcs-mimp-web.sf-express.com/mcs-mimp/' + path.lstrip('/'),
                headers=h, json=data or {}, timeout=timeout)
            return r.json()
        except Exception:
            return None

    def query_points(self) -> Optional[int]:
        """返回可用积分，失败返回 None"""
        j = self.post('commonPost/~memberIntegral~userInfoService~queryUserInfo',
                      {'sysCode': 'MCS-MIMP-CORE-1', 'token': 'QaeFLkUMV2UjYNkT'})
        if isinstance(j, dict) and (j.get('success') is True or j.get('success') == 'true'):
            o = j.get('obj') or {}
            for k in ('usablePoint', 'totalPoint', 'point'):
                if k in o:
                    try:
                        return int(o[k])
                    except (TypeError, ValueError):
                        pass
        return None


def is_safe_world_cup_task(task: Dict) -> bool:
    task_name = str(task.get('taskName') or '')
    task_code = str(task.get('taskCode') or '')
    return bool(task_code and task_name in WORLD_CUP_SAFE_TASK_NAMES)


class Logger:
    def __init__(self):
        self.messages: List[str] = []
        self.lock = Lock()

    def _log(self, icon: str, msg: str):
        line = f"{icon} {msg}"
        with print_lock:
            print(line)
        with self.lock:
            self.messages.append(line)

    def info(self, msg): self._log('📝', msg)
    def success(self, msg): self._log('✅', msg)
    def warning(self, msg): self._log('⚠️', msg)
    def error(self, msg): self._log('❌', msg)
    def task(self, msg): self._log('🎯', msg)
    def medal(self, msg): self._log('🏅', msg)
    def points(self, pts, prefix="当前积分"): self._log('💰', f"{prefix}: 【{pts}】")


# ==================== 代理管理器 ====================
def _log_global(msg: str):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)


def _build_proxy_url(ip: str, port: int, username: str = "", password: str = "") -> str:
    """构建标准代理URL，认证信息自动URL编码"""
    if username and password:
        safe_user = url_encode(username, safe='')
        safe_pass = url_encode(password, safe='')
        return f"{PROXY_TYPE}://{safe_user}:{safe_pass}@{ip}:{port}"
    return f"{PROXY_TYPE}://{ip}:{port}"


def parse_proxy_response(text: str) -> Optional[Tuple[str, str]]:
    """解析代理API响应，返回(代理URL, 显示用字符串)，支持JSON和纯文本格式"""
    text = text.strip()
    try:
        data = json.loads(text)
        def extract(d: dict) -> Optional[Tuple[str, str]]:
            if 'ip' not in d or 'port' not in d:
                return None
            ip, port = str(d['ip']), int(d['port'])
            user = str(d.get('account', d.get('user', '')) or '')
            pwd = str(d.get('password', d.get('pass', '')) or '')
            url = _build_proxy_url(ip, port, user, pwd)
            display = f"{ip}:{port}" + (" (认证)" if user else "")
            return url, display
        if isinstance(data, dict):
            if 'ip' in data and 'port' in data:
                return extract(data)
            if 'data' in data:
                pd = data['data']
                if isinstance(pd, dict) and 'list' in pd:
                    pl = pd['list']
                    if isinstance(pl, list) and pl:
                        return extract(pl[0])
                if isinstance(pd, list) and pd:
                    return extract(pd[0])
                if isinstance(pd, dict) and 'ip' in pd:
                    return extract(pd)
            if 'result' in data:
                r = data['result']
                if isinstance(r, dict) and 'ip' in r:
                    return extract(r)
    except (json.JSONDecodeError, ValueError):
        pass
    if ':' in text:
        segments = text.split()
        addr_parts = segments[0].split(':')
        if len(addr_parts) == 2 and addr_parts[1].isdigit():
            ip, port = addr_parts[0], int(addr_parts[1])
            user = segments[1] if len(segments) > 1 else ""
            pwd = segments[2] if len(segments) > 2 else ""
            url = _build_proxy_url(ip, port, user, pwd)
            display = f"{ip}:{port}" + (" (认证)" if user else "")
            return url, display
    return None


def get_api_proxy() -> Optional[Tuple[Dict[str, str], str]]:
    """从API获取代理，返回(代理字典, 显示用字符串)"""
    if not PROXY_API_URL:
        return None
    with PROXY_LOCK:
        elapsed = time.time() - PROXY_CONTEXT['last_fetch_ts']
        if elapsed < 3:
            time.sleep(3 - elapsed)
        for i in range(MAX_PROXY_RETRIES):
            try:
                resp = requests.get(PROXY_API_URL, timeout=10)
                if resp.status_code == 200:
                    result = parse_proxy_response(resp.text)
                    if result:
                        proxy_url, display = result
                        PROXY_CONTEXT['last_fetch_ts'] = time.time()
                        _log_global(f"✅ 代理获取成功: {display}")
                        return {'http': proxy_url, 'https': proxy_url}, display
                _log_global(f"⚠️ 第{i+1}次代理格式无效")
            except Exception as e:
                _log_global(f"⚠️ 第{i+1}次获取代理异常: {str(e)[:80]}")
            if i < MAX_PROXY_RETRIES - 1:
                time.sleep(PROXY_RETRY_DELAY)
        PROXY_CONTEXT['last_fetch_ts'] = time.time()
        _log_global(f"❌ 代理获取失败：已重试{MAX_PROXY_RETRIES}次")
        return None


def parse_fixed_proxy(fixed_proxy: str) -> Optional[Dict[str, str]]:
    """解析固定代理字符串为代理字典"""
    if not fixed_proxy:
        return None
    if '://' not in fixed_proxy:
        fixed_proxy = f'{PROXY_TYPE}://{fixed_proxy}'
    return {'http': fixed_proxy, 'https': fixed_proxy}


# ==================== HTTP客户端 ====================
class SFHttpClient:
    def __init__(self, fixed_proxy: str = "", app_token: str = ""):
        self.session = requests.Session()
        self.session.verify = False
        self.proxy_display = '无代理'
        self.ck_invalid = False
        self.ck_invalid_message = ''
        # APP 模式：非空时请求体注入 {"sysCode":"MCS-MIMP-CORE-1","token":<app_token>}
        # 并附加 APP 专属请求头（抓包实证：缺 token 会报「权限验证失败」）
        self.app_token = app_token or ''
        self._setup_proxy(fixed_proxy)
        self.headers = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254173b) XWEB/19027',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'channel': 'xcxpart',
            'platform': 'MINI_PROGRAM',
            'accept-language': 'zh-CN,zh;q=0.9',
        }
        if self.app_token:
            self.headers.update({
                'User-Agent': APP_UA,
                'channel': 'point240613',
                'platform': 'SFAPP',
                'X-Requested-With': 'com.sf.activity',
                'Origin': 'https://mcs-mimp-web.sf-express.com',
            })

    def _setup_proxy(self, fixed_proxy: str):
        if fixed_proxy:
            proxy_dict = parse_fixed_proxy(fixed_proxy)
            if proxy_dict:
                self.session.proxies = proxy_dict
                display = fixed_proxy
                if '@' in fixed_proxy:
                    parts = fixed_proxy.split('@')
                    display = f"***@{parts[-1]}"
                self.proxy_display = display
                return
        result = get_api_proxy()
        if result:
            self.session.proxies = result[0]
            self.proxy_display = result[1]

    def _generate_sign(self) -> Dict[str, str]:
        timestamp = str(int(round(time.time() * 1000)))
        data = f'token={TOKEN}&timestamp={timestamp}&sysCode={SYS_CODE}'
        signature = hashlib.md5(data.encode()).hexdigest()
        return {'syscode': SYS_CODE, 'timestamp': timestamp, 'signature': signature}

    def _check_ck_invalid(self, result: Dict):
        if not isinstance(result, dict) or result.get('success') is True:
            return
        # 精确错误码匹配（100111 等）
        for key in ('errorCode', 'code'):
            code = str(result.get(key, '') or '')
            if code and code in CK_INVALID_ERROR_CODES:
                self.ck_invalid = True
                self.ck_invalid_message = result.get('errorMessage') or 'CK失效了(100111 用户信息失效)'
                return
        text = ' '.join(str(result.get(k, '')) for k in ('errorMessage', 'message', 'msg', 'error', 'code', 'errorCode')).lower()
        if any(keyword in text for keyword in CK_INVALID_KEYWORDS):
            self.ck_invalid = True
            self.ck_invalid_message = result.get('errorMessage') or result.get('message') or result.get('msg') or 'CK失效了'

    @staticmethod
    def error_code_of(result: Optional[Dict]) -> str:
        if not isinstance(result, dict):
            return ''
        return str(result.get('errorCode', '') or result.get('code', '') or '')

    @staticmethod
    def error_msg_of(result: Optional[Dict]) -> str:
        if not isinstance(result, dict):
            return '请求失败'
        return result.get('errorMessage') or result.get('message') or result.get('msg') or '未知错误'

    def request(self, url: str, data: Optional[Dict] = None, extra_headers: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        proxy_retry_count = 0
        retry_count = 0
        # APP 模式：把 token 合进请求体（抓包实证 body 形如
        # {"sysCode":"MCS-MIMP-CORE-1","token":"<16位>"}）
        if self.app_token:
            body = dict(data or {})
            body.setdefault('sysCode', 'MCS-MIMP-CORE-1')
            body.setdefault('token', self.app_token)
        else:
            body = data or {}
        while proxy_retry_count < MAX_PROXY_RETRIES:
            sign_data = self._generate_sign()
            headers = {**self.headers, **sign_data}
            if extra_headers:
                headers.update(extra_headers)
            try:
                resp = self.session.post(url, headers=headers, json=body, timeout=PROXY_TIMEOUT)
                resp.raise_for_status()
                try:
                    result = resp.json()
                    if result is not None:
                        self._check_ck_invalid(result)
                        return result
                except (json.JSONDecodeError, ValueError):
                    pass
                retry_count += 1
                if retry_count < REQUEST_RETRY_COUNT:
                    time.sleep(2)
                    continue
                return None
            except requests.exceptions.RequestException as e:
                retry_count += 1
                error_str = str(e)
                if 'ProxyError' in error_str or 'SSLError' in error_str or 'ConnectionError' in error_str:
                    proxy_retry_count += 1
                    if proxy_retry_count < MAX_PROXY_RETRIES:
                        result = get_api_proxy()
                        if result:
                            self.session.proxies = result[0]
                            self.proxy_display = result[1]
                        retry_count = 0
                    time.sleep(2)
                    continue
                if retry_count < REQUEST_RETRY_COUNT:
                    time.sleep(2)
                    continue
                return None
            except Exception:
                return None
        return None

    def request_app(self, url: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """APP平台请求"""
        original = self.headers.get('platform', 'MINI_PROGRAM')
        self.headers['platform'] = 'SFAPP'
        try:
            return self.request(url, data)
        finally:
            self.headers['platform'] = original

    def login(self, url: str) -> Tuple[bool, str, str]:
        try:
            decoded = unquote(url)
            if decoded.startswith('sessionId=') or '_login_mobile_=' in decoded:
                cookie_dict = {}
                for item in decoded.split(';'):
                    item = item.strip()
                    if '=' in item:
                        k, v = item.split('=', 1)
                        cookie_dict[k] = v
                for k, v in cookie_dict.items():
                    self.session.cookies.set(k, v, domain='mcs-mimp-web.sf-express.com')
                user_id = cookie_dict.get('_login_user_id_', '')
                phone = cookie_dict.get('_login_mobile_', '')
                return (True, user_id, phone) if phone else (False, '', '')
            else:
                self.session.get(decoded, headers=self.headers, timeout=PROXY_TIMEOUT)
                cookies = self.session.cookies.get_dict()
                user_id = cookies.get('_login_user_id_', '')
                phone = cookies.get('_login_mobile_', '')
                return (True, user_id, phone) if phone else (False, '', '')
        except Exception:
            return False, '', ''


# ==================== 日常积分任务执行器 ====================
class DailyTaskExecutor:
    def __init__(self, http: SFHttpClient, logger: Logger, user_id: str):
        self.http = http
        self.logger = logger
        self.user_id = user_id
        self.total_points = 0
        self.taskId = ""
        self.taskCode = ""
        self.strategyId = 0
        self.title = ""
        self.point = 0

    @staticmethod
    def generate_device_id() -> str:
        result = ''
        for char in 'xxxxxxxx-xxxx-xxxx':
            result += random.choice('abcdef0123456789') if char == 'x' else char
        return result

    def _extract_task_id_from_url(self, url: str) -> str:
        if not url:
            return ''
        try:
            parsed = urlparse(str(url))
            params = parse_qs(parsed.query)
            if '_ug_view_param' in params:
                ug_params = json.loads(unquote(params['_ug_view_param'][0]))
                for key in ('taskId', 'taskCode', 'task_id'):
                    if ug_params.get(key):
                        return str(ug_params[key])
        except Exception:
            pass
        match = re.search(
            r"[\"'](?:taskId|taskCode|task_id)[\"']\s*:\s*[\"']([^\"']+)[\"']",
            unquote(str(url)),
        )
        if match:
            return match.group(1)
        return ''

    def _resolve_task_code(self, task: Dict) -> str:
        code = str(task.get('taskCode') or '').strip()
        if code:
            return code
        for key in ('buttonRedirect', 'taskJumpAddress', 'redirectUrl'):
            extracted = self._extract_task_id_from_url(task.get(key, ''))
            if extracted:
                return extracted
        return ''

    def _set_task_attrs(self, task: Dict):
        self.taskId = str(task.get('taskId') or '')
        self.taskCode = self._resolve_task_code(task)
        try:
            self.strategyId = int(task.get('strategyId') or 0)
        except (TypeError, ValueError):
            self.strategyId = 0
        self.title = str(task.get('title') or '未知任务')
        try:
            self.point = int(task.get('point') or task.get('awardIntegral') or 0)
        except (TypeError, ValueError):
            self.point = 0

    def app_sign_in(self) -> Tuple[bool, str]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~getUnFetchPointAndDiscount'
        resp = self.http.request_app(url, {})
        if resp and resp.get('success'):
            obj = resp.get('obj', [])
            if obj and isinstance(obj, list) and len(obj) > 0:
                names = [item.get('packetName', '未知') for item in obj]
                self.logger.success(f'[APP签到] 获得【{", ".join(names)}】')
            else:
                self.logger.info('[APP签到] 今日已签到')
            return True, ''
        error_msg = SFHttpClient.error_msg_of(resp)
        if '没有待领取礼包' in error_msg:
            time.sleep(1)
            resp2 = self.http.request_app(url, {})
            if resp2 and resp2.get('success'):
                obj2 = resp2.get('obj', [])
                if obj2 and isinstance(obj2, list) and len(obj2) > 0:
                    names = [item.get('packetName', '未知') for item in obj2]
                    self.logger.success(f'[APP签到] 二次领取【{", ".join(names)}】')
                else:
                    self.logger.info('[APP签到] 今日已签到，无待领取奖励')
                return True, ''
            self.logger.info('[APP签到] 今日已签到')
            return True, ''
        self.logger.error(f'[APP签到] 失败: {error_msg}')
        return False, error_msg

    def sign_in(self) -> Tuple[bool, str]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
        resp = self.http.request(url, {"comeFrom": "vioin", "channelFrom": "WEIXIN"})
        if resp and resp.get('success'):
            obj = resp.get('obj', {})
            count_day = obj.get('countDay', 0)
            packets = obj.get('integralTaskSignPackageVOList', [])
            if packets:
                self.logger.success(f'签到成功，获得【{packets[0].get("packetName", "未知")}】，累计签到【{count_day + 1}】天')
            else:
                self.logger.info(f'今日已签到，累计签到【{count_day + 1}】天')
            return True, ''
        error_code = SFHttpClient.error_code_of(resp)
        error_msg = SFHttpClient.error_msg_of(resp)
        # 3400002 = 今日已签到，幂等成功（抓包实证）
        if error_code in SIGN_ALREADY_CODES or '已签到' in error_msg:
            self.logger.info('今日已签到')
            return True, ''
        self.logger.error(f'签到失败: {error_msg}')
        return False, error_msg

    def _format_sign_v2_award(self, obj: Any) -> str:
        if not isinstance(obj, dict):
            return ''
        products = obj.get('award', {}).get('productDTOList', [])
        if isinstance(products, list) and products:
            names = []
            for item in products:
                if not isinstance(item, dict):
                    continue
                name = item.get('productName') or item.get('couponName')
                if name:
                    amount = item.get('amount', 1)
                    names.append(f'{name}x{amount}')
            if names:
                return '、'.join(names)
        award = obj.get('award')
        if isinstance(award, dict):
            return award.get('giftBagName') or award.get('giftBagDesc') or ''
        return obj.get('packetName') or obj.get('giftBagName') or ''

    def _sign_v2(self, platform_type: str) -> bool:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralSignV2Service~sign'
        if platform_type == 'SFAPP':
            name = 'APP'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12; M2011K2C Build/SKQ1.211006.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.132 Mobile Safari/537.36 mediaCode=SFEXPRESSAPP-Android-ML',
                'channel': 'doudiappwd',
                'platform': 'SFAPP',
                'deviceid': self.generate_device_id(),
            }
        else:
            name = '小程序'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12; M2011K2C Build/SKQ1.211006.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.177 Mobile Safari/537.36 XWEB/1460075 MMWEBSDK/20250804 MMWEBID/4850 MicroMessenger/8.0.63.2920(0x28003FA6) WeChat/arm64 WeChat NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxd4185d00bf7e08ac',
                'channel': 'wxwddoudi',
                'platform': 'MINI_PROGRAM',
            }
        resp = self.http.request(url, {}, headers)
        if resp and resp.get('success'):
            award_text = self._format_sign_v2_award(resp.get('obj'))
            if award_text:
                self.logger.success(f'[{name}签到] 成功，获得【{award_text}】')
            else:
                self.logger.success(f'[{name}签到] 成功')
            return True
        error_code = SFHttpClient.error_code_of(resp)
        error_msg = SFHttpClient.error_msg_of(resp)
        if error_code in SIGN_ALREADY_CODES or '已签到' in error_msg:
            self.logger.info(f'[{name}签到] 今日已签到')
            return True
        self.logger.error(f'[{name}签到] 失败: {error_msg}')
        return False

    def dual_sign_in(self) -> bool:
        app_ok = self._sign_v2('SFAPP')
        time.sleep(1)
        mini_ok = self._sign_v2('MINI_PROGRAM')
        return app_ok or mini_ok

    def get_task_list(self) -> List[Dict]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES'
        # 实测 channelType 1/2/3/4 为真实值，01-04 为完全相同的别名（抓包实证）
        channels = ['1', '2', '3', '4']
        if TASK_SCAN_ALIAS:
            channels += ['01', '02', '03', '04']
        all_tasks = []
        seen = set()
        for ct in channels:
            data = {'channelType': ct, 'deviceId': self.generate_device_id()}
            resp = self.http.request(url, data)
            if resp and resp.get('success') and resp.get('obj'):
                obj = resp['obj'] or {}
                # totalPoint 以 ct=1 那份为权威值
                if ct == '1' or not self.total_points:
                    self.total_points = int(obj.get('totalPoint', self.total_points) or self.total_points or 0)
                task_items = obj.get('taskTitleLevels') or obj.get('ESobj') or []
                if not isinstance(task_items, list):
                    continue
                for task in task_items:
                    if not isinstance(task, dict):
                        continue
                    task = dict(task)
                    tc = self._resolve_task_code(task)
                    if tc:
                        task['taskCode'] = tc
                    key = tc or f"{task.get('taskId', '')}|{task.get('title', '')}"
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    all_tasks.append(task)
        return all_tasks

    def execute_task(self) -> Tuple[bool, bool]:
        """上报任务完成。

        返回 (accepted, confirmed)：
        - accepted: 请求被服务端接受（success=true）
        - confirmed: 服务端明确确认完成（obj=true）
        实测 obj:false 只代表“上报被接受但未确认”，既不改状态也不发分。
        """
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonRoutePost/memberEs/taskRecord/finishTask'
        resp = self.http.request(url, {'taskCode': self.taskCode})
        if not (resp and resp.get('success')):
            return False, False
        return True, resp.get('obj') is True

    def receive_task_reward(self) -> Tuple[bool, str]:
        """领取任务积分（真正发分的一步）。

        错误码语义（抓包实证）：
        - 600005 已领取积分 = 幂等成功
        - 600006 任务未完成 = 需真实业务行为，脚本拿不到
        """
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~fetchIntegral'
        data = {
            "strategyId": self.strategyId, "taskId": self.taskId,
            "taskCode": self.taskCode, "deviceId": self.generate_device_id()
        }
        resp = self.http.request(url, data)
        if resp and resp.get('success'):
            self.logger.success(f'领取奖励: {self.title}')
            return True, ''
        error_code = SFHttpClient.error_code_of(resp)
        error_msg = SFHttpClient.error_msg_of(resp)
        if error_code in FETCH_ALREADY_CODES or '已领取' in error_msg:
            return True, ''
        if error_code in FETCH_NEED_REAL_CODES or '任务未完成' in error_msg:
            return False, 'need_real'
        return False, error_msg

    def get_welfare_list(self) -> List[Dict]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~mallGoodsLifeService~list'
        data = {"memGrade": 3, "categoryCode": "SHTQ", "showCode": "SHTQWNTJ"}
        resp = self.http.request(url, data)
        if resp and resp.get('success'):
            result = []
            for module in resp.get('obj', []):
                for goods in module.get('goodsList', []):
                    if goods.get('exchangeStatus') == 1:
                        result.append({
                            'goodsNo': goods.get('goodsNo'),
                            'goodsName': goods.get('goodsName'),
                            'showName': goods.get('showName', ''),
                        })
            return result
        return []

    def receive_welfare(self, goods_no: str, goods_name: str) -> bool:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~pointMallService~createOrder'
        data = {
            "from": "Point_Mall", "orderSource": "POINT_MALL_EXCHANGE",
            "goodsNo": goods_no, "quantity": 1, "taskCode": self.taskCode
        }
        resp = self.http.request(url, data)
        if resp and resp.get('success'):
            self.logger.success(f'领取特权: {goods_name}')
            return True
        return False

    def handle_welfare_task(self) -> bool:
        welfare_list = self.get_welfare_list()
        if not welfare_list:
            return False
        for w in welfare_list:
            name = f"{w['showName']} - {w['goodsName']}" if w['showName'] else w['goodsName']
            if self.receive_welfare(w['goodsNo'], name):
                return True
            time.sleep(1)
        return False

    def run(self) -> Tuple[int, int]:
        self.logger.info('正在获取日常任务列表...')
        tasks = self.get_task_list()
        if not tasks:
            self.logger.error('获取任务列表失败')
            return 0, 0
        points_before = self.total_points
        self.logger.points(points_before, "执行前积分")
        for task in tasks:
            title = task.get('title', '未知')
            status = task.get('status')
            try:
                status = int(status)
            except (TypeError, ValueError):
                pass
            if status == 3:
                continue
            self._set_task_attrs(task)
            if title in DAILY_SKIP_TASKS or self.taskCode in TASK_CODE_BLOCKLIST:
                if status == 2 and self.taskCode:
                    ok, _ = self.receive_task_reward()
                    if ok:
                        continue
                self.logger.info(f'人工任务需在小程序完成，未调用自动完成接口: {title}')
                continue
            if not self.taskCode:
                self.logger.info(f'未找到任务码，跳过: {title}')
                continue
            self.logger.task(f'发现任务: {title} (状态: {status})')
            if '领任意生活特权福利' in title:
                if self.handle_welfare_task():
                    time.sleep(2)
                    _, confirmed = self.execute_task()
                    if confirmed:
                        time.sleep(2)
                        self.receive_task_reward()
                time.sleep(3)
                continue
            if status == 1:
                if '连签7天' in title and 'process' in task:
                    cur, tot = map(int, task['process'].split('/'))
                    if cur < tot:
                        self.logger.info(f'【{title}】进度: {task["process"]}')
                        continue
                accepted, confirmed = self.execute_task()
                if confirmed:
                    self.logger.success(f'[{title}] 上报完成（服务端已确认）')
                    time.sleep(2)
                    status = 2
                elif accepted:
                    # 上报被接受但未确认完成：只尝试领奖一次，不再重试上报
                    self.logger.info(f'[{title}] 上报未确认完成，尝试直接领奖')
                    time.sleep(2)
                    status = 2
                else:
                    continue
            if status == 2:
                ok, reason = self.receive_task_reward()
                if ok:
                    continue
                if reason == 'need_real':
                    # fetchIntegral 报“任务未完成”——浏览类任务需要先 finishTask 上报，
                    # 服务端才把状态推进到可领奖。补一次上报闭环再领。
                    accepted, confirmed = self.execute_task()
                    if accepted:
                        time.sleep(2)
                        ok2, reason2 = self.receive_task_reward()
                        if ok2:
                            continue
                        if reason2 == 'need_real':
                            self.logger.info(f'[{title}] 上报后仍需真实业务行为，无法自动完成')
                            continue
                        self.logger.info(f'[{title}] 领奖未成功: {reason2}')
                    else:
                        self.logger.info(f'[{title}] 上报失败，无法自动完成')
                    continue
                # 其他领奖错误：补一次上报再领，仅此一次
                _, confirmed = self.execute_task()
                if confirmed:
                    time.sleep(2)
                    self.receive_task_reward()
            time.sleep(3)
        tasks = self.get_task_list()
        points_after = self.total_points if tasks else points_before
        self.logger.points(points_after, "执行后积分")
        return points_before, points_after


# ==================== 会员日活动执行器 ====================
class MemberDayExecutor:
    MAX_LEVEL = 8

    def __init__(self, http: SFHttpClient, logger: Logger, user_id: str):
        self.http = http
        self.logger = logger
        self.user_id = user_id
        self.black = False
        self.red_packet_map: Dict[int, int] = {}
        self.packet_threshold = 1 << (self.MAX_LEVEL - 1)

    def _check_black(self, error_message: str) -> bool:
        if '没有资格参与活动' in error_message:
            self.black = True
            self.logger.info('会员日任务风控')
            return True
        return False

    def get_index(self) -> Optional[Dict]:
        available = [inv for inv in inviteId if inv != self.user_id]
        invite_user_id = random.choice(available) if available else ''
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~index'
        resp = self.http.request(url, {'inviteUserId': invite_user_id})
        if resp and resp.get('success'):
            return resp.get('obj', {})
        error_msg = SFHttpClient.error_msg_of(resp)
        self.logger.info(f'查询会员日失败: {error_msg}')
        self._check_black(error_msg)
        return None

    def receive_invite_award(self, invite_user_id: str):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~receiveInviteAward'
        resp = self.http.request(url, {'inviteUserId': invite_user_id})
        if resp and resp.get('success'):
            product_name = resp.get('obj', {}).get('productName', '空气')
            self.logger.success(f'会员日邀请奖励: {product_name}')
        else:
            error_msg = SFHttpClient.error_msg_of(resp)
            self.logger.info(f'领取会员日邀请奖励失败: {error_msg}')
            self._check_black(error_msg)

    def lottery(self) -> Optional[str]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayLotteryService~lottery'
        resp = self.http.request(url, {})
        if resp and resp.get('success'):
            product_name = resp.get('obj', {}).get('productName', '空气')
            self.logger.success(f'会员日抽奖: {product_name}')
            return product_name
        error_msg = SFHttpClient.error_msg_of(resp)
        self.logger.info(f'会员日抽奖失败: {error_msg}')
        self._check_black(error_msg)
        return None

    def get_task_list(self) -> Optional[List[Dict]]:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList'
        resp = self.http.request(url, {'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'})
        if resp and resp.get('success'):
            return resp.get('obj', [])
        error_msg = SFHttpClient.error_msg_of(resp)
        self.logger.info(f'查询会员日任务失败: {error_msg}')
        self._check_black(error_msg)
        return None

    def finish_task(self, task: Dict) -> bool:
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'
        resp = self.http.request(url, {'taskCode': task['taskCode']})
        if resp and resp.get('success') and resp.get('obj') is not False:
            self.logger.success(f'完成会员日任务[{task["taskName"]}]')
            self.fetch_mix_task_reward(task)
            return True
        error_msg = SFHttpClient.error_msg_of(resp)
        self.logger.info(f'完成会员日任务[{task["taskName"]}]失败: {error_msg}')
        self._check_black(error_msg)
        return False

    def fetch_mix_task_reward(self, task: Dict):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~fetchMixTaskReward'
        data = {'taskType': task['taskType'], 'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'}
        resp = self.http.request(url, data)
        if resp and resp.get('success'):
            self.logger.success(f'领取会员日任务[{task["taskName"]}]奖励')
        else:
            error_msg = SFHttpClient.error_msg_of(resp)
            self.logger.info(f'领取会员日任务[{task["taskName"]}]奖励失败: {error_msg}')
            self._check_black(error_msg)

    def do_tasks(self):
        tasks = self.get_task_list()
        if not tasks:
            return
        for task in tasks:
            if self.black:
                return
            if task['status'] == 1:
                self.fetch_mix_task_reward(task)
        for task in tasks:
            if self.black:
                return
            if task['status'] == 2:
                if task['taskType'] in MEMBER_DAY_SKIP_TASK_TYPES:
                    continue
                for _ in range(task.get('restFinishTime', 0)):
                    if self.black:
                        return
                    self.finish_task(task)

    def red_packet_status(self):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketStatus'
        resp = self.http.request(url, {})
        if not (resp and resp.get('success')):
            error_msg = SFHttpClient.error_msg_of(resp)
            self.logger.info(f'查询会员日合成失败: {error_msg}')
            self._check_black(error_msg)
            return
        for packet in resp.get('obj', {}).get('packetList', []):
            self.red_packet_map[packet['level']] = packet['count']
        for level in range(1, self.MAX_LEVEL):
            count = self.red_packet_map.get(level, 0)
            while count >= 2:
                self.red_packet_merge(level)
                count -= 2
        summary = [f"[{lv}级]X{ct}" for lv, ct in self.red_packet_map.items() if ct > 0]
        self.logger.info(f'会员日合成列表: {", ".join(summary)}')
        if self.red_packet_map.get(self.MAX_LEVEL):
            self.logger.success(f'会员日已拥有[{self.MAX_LEVEL}级]红包X{self.red_packet_map[self.MAX_LEVEL]}')
            self.red_packet_draw(self.MAX_LEVEL)
        else:
            remaining_needed = sum(
                1 << (int(lv) - 1) for lv, ct in self.red_packet_map.items()
                if ct > 0 and int(lv) < self.MAX_LEVEL
            )
            remaining = self.packet_threshold - remaining_needed
            self.logger.info(f'会员日距离[{self.MAX_LEVEL}级]红包还差: [1级]红包X{remaining}')

    def red_packet_merge(self, level: int):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketMerge'
        resp = self.http.request(url, {'level': level, 'num': 2})
        if resp and resp.get('success'):
            self.logger.success(f'会员日合成: [{level}级]红包X2 -> [{level + 1}级]红包')
            self.red_packet_map[level] -= 2
            self.red_packet_map[level + 1] = self.red_packet_map.get(level + 1, 0) + 1
        else:
            error_msg = SFHttpClient.error_msg_of(resp)
            self.logger.info(f'会员日合成[{level}级]红包失败: {error_msg}')
            self._check_black(error_msg)

    def red_packet_draw(self, level: int):
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketDraw'
        resp = self.http.request(url, {'level': str(level)})
        if resp and resp.get('success'):
            coupon_names = [item['couponName'] for item in resp.get('obj', [])] or []
            self.logger.success(f'会员日提取[{level}级]红包: {", ".join(coupon_names) or "空气"}')
        else:
            error_msg = SFHttpClient.error_msg_of(resp)
            self.logger.info(f'会员日提取[{level}级]红包失败: {error_msg}')
            self._check_black(error_msg)

    def run(self) -> Dict[str, Any]:
        result = {'lottery_prizes': [], 'tasks_done': 0}
        index_info = self.get_index()
        if not index_info or self.black:
            return result
        available = [inv for inv in inviteId if inv != self.user_id]
        invite_user_id = random.choice(available) if available else ''
        if index_info.get('canReceiveInviteAward') and invite_user_id:
            self.receive_invite_award(invite_user_id)
        self.red_packet_status()
        lottery_num = index_info.get('lotteryNum', 0)
        self.logger.info(f'会员日可抽奖 {lottery_num} 次')
        for _ in range(lottery_num):
            if self.black:
                break
            prize = self.lottery()
            if prize:
                result['lottery_prizes'].append(prize)
        if not self.black:
            self.do_tasks()
        if not self.black:
            self.red_packet_status()
        return result


class WorldCupExecutor:
    BASE = 'https://mcs-mimp-web.sf-express.com/mcs-mimp'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 mediaCode=SFEXPRESSAPP-iOS-ML',
        'channel': WORLD_CUP_CHANNEL,
        'platform': WORLD_CUP_PLATFORM,
    }

    def __init__(self, http: SFHttpClient, logger: Logger, user_id: str):
        self.http = http
        self.logger = logger
        self.user_id = user_id

    def _post(self, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        return self.http.request(f'{self.BASE}{path}', data or {}, self.HEADERS)

    def _error(self, action: str, resp: Optional[Dict]):
        message = SFHttpClient.error_msg_of(resp) if resp else '无响应'
        error_code = SFHttpClient.error_code_of(resp) if resp else ''
        code_text = f'[{error_code}]' if error_code else ''
        self.logger.info(f'世界杯{action}失败{code_text}: {message}')

    def _assist(self):
        target = WORLD_CUP_ASSIST_ID.strip()
        if not target:
            self.logger.info('世界杯未配置助力 ID，跳过')
            return
        if target == self.user_id:
            self.logger.info('世界杯当前账号为助力目标，跳过自助')
            return
        resp = self._post(
            '/commonPost/~memberNonactivity~worldCupIndexService~index',
            {'inviteType': 1, 'inviteUserId': target},
        )
        if resp and resp.get('success'):
            self.logger.success(f'世界杯助力主账号 {target[:8]}... 成功')
        else:
            self._error('助力', resp)

    def _daily_gift(self, result: Dict[str, Any]):
        data = {'cityCode': WORLD_CUP_CITY_CODE}
        resp = self._post('/commonPost/~memberNonactivity~worldCupDailyService~getDailyGiftStatus', data)
        if not (resp and resp.get('success')):
            self._error('查询每日礼物', resp)
            return
        status = resp.get('obj') or {}
        if status.get('received'):
            self.logger.info('世界杯每日礼物今日已领取')
            return
        if not status.get('canReceive'):
            self.logger.info('世界杯每日礼物当前不可领取')
            return
        resp = self._post('/commonPost/~memberNonactivity~worldCupDailyService~receiveDailyGift', data)
        if resp and resp.get('success'):
            result['daily_gift'] = True
            self.logger.success('世界杯每日礼物领取成功')
        else:
            self._error('领取每日礼物', resp)

    def _tasks(self, result: Dict[str, Any]):
        task_data = {'activityCode': WORLD_CUP_ACTIVITY_CODE, 'channelType': WORLD_CUP_PLATFORM}
        resp = self._post('/commonPost/~memberNonactivity~activityTaskService~taskList', task_data)
        if not (resp and resp.get('success')):
            self._error('查询任务', resp)
            return
        tasks = resp.get('obj') or []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if not is_safe_world_cup_task(task):
                continue
            name = str(task.get('taskName') or '未知任务')
            status = task.get('status')
            try:
                status = int(status)
            except (TypeError, ValueError):
                pass
            rest_finish = int(task.get('restFinishTime') or 0)
            if status == 3 or (status == 1 and rest_finish <= 0):
                self.logger.info(f'世界杯任务已完成: {name}')
                continue
            finish = self._post(
                '/commonPost/~memberEs~taskRecord~finishTask',
                {'taskCode': task.get('taskCode')},
            )
            # obj:false = 服务端未确认完成，不算成功（抓包实证）
            if finish and finish.get('success') and finish.get('obj') is not False:
                result['tasks_completed'] += 1
                self.logger.success(f'世界杯任务完成: {name}')
            else:
                self._error(f'完成任务[{name}]', finish)
            time.sleep(1)

        reward = self._post(
            '/commonPost/~memberNonactivity~worldCupTaskService~fetchTaskReward',
            task_data,
        )
        if not (reward and reward.get('success')):
            self._error('领取任务奖励', reward)
            return
        received = (reward.get('obj') or {}).get('receivedAccountList') or []
        if received:
            text = ', '.join(f"{x.get('currency', '')} x{x.get('amount', 0)}" for x in received)
            self.logger.success(f'世界杯任务奖励: {text}')
        else:
            self.logger.info('世界杯暂无新任务奖励')

    def _game(self, result: Dict[str, Any]):
        resp = self._post('/commonPost/~memberNonactivity~worldCupGameService~index')
        if not (resp and resp.get('success')):
            self._error('查询射门游戏', resp)
            return
        game = resp.get('obj') or {}
        current_level = int(game.get('curLevel') or 1)
        reward_levels = [
            level for level in game.get('levelList') or []
            if int(level.get('rewardCoins') or 0) > 0
        ]
        if not reward_levels:
            self.logger.info('世界杯射门今日奖励已领取')
            return
        for level in reward_levels:
            level_no = int(level.get('level') or 0)
            if not level_no or level_no < current_level:
                continue
            target = int(level.get('target') or 0)
            passed = self._post(
                '/commonPost/~memberNonactivity~worldCupGameService~passReport',
                {'level': level_no, 'shotNum': target},
            )
            if not (passed and passed.get('success')):
                self._error(f'上报第{level_no}关', passed)
                break
            coin_num = int((passed.get('obj') or {}).get('coinNum') or 0)
            result['levels_passed'] += 1
            result['game_coins'] += coin_num
            self.logger.success(f'世界杯射门第{level_no}关完成，金币+{coin_num}')
            time.sleep(1)

    def _bet_status(self) -> Optional[Dict]:
        resp = self._post('/commonPost/~memberNonactivity~worldCupMatchService~betStatus')
        if resp and resp.get('success'):
            return resp.get('obj') or {}
        self._error('查询竞猜', resp)
        return None

    def _bet(self, result: Dict[str, Any]):
        status = self._bet_status()
        if status is None:
            return
        balance = int((status.get('currentAccount') or {}).get('balance') or 0)
        bet_coin = max(10, int(WORLD_CUP_BET_COIN))
        pending = [
            match for match in status.get('matchList') or []
            if match.get('matchStatus') == 'Fixture' and match.get('recordStatus', 0) == 0
        ]
        for match in pending:
            if balance < bet_coin:
                break
            bet_result = random.randint(0, 2)
            resp = self._post(
                '/commonPost/~memberNonactivity~worldCupMatchService~placeBet',
                {
                    'matchId': match.get('matchId'),
                    'betResult': bet_result,
                    'betCoin': bet_coin,
                },
            )
            if resp and resp.get('success'):
                balance -= bet_coin
                result['bets_placed'] += 1
                self.logger.success(f"世界杯竞猜已下注: {match.get('teamAName', '?')} vs {match.get('teamBName', '?')}")
            else:
                self._error('竞猜下注', resp)
            time.sleep(1)

    def _settle(self, result: Dict[str, Any]):
        resp = self._post('/commonPost/~memberNonactivity~worldCupMatchService~settleBet')
        if not (resp and resp.get('success')):
            self._error('结算竞猜', resp)
            return
        settled = resp.get('obj') or []
        result['settle_pnl'] = sum(
            (item.get('betWinCoin') or 0) - (item.get('betCoin') or 0)
            for item in settled
        )
        if settled:
            self.logger.info(f"世界杯竞猜结算: {result['settle_pnl']:+}")

    def _refresh_balance(self, result: Dict[str, Any]):
        status = self._bet_status()
        if status is None:
            return
        account = status.get('currentAccount') or {}
        result['balance'] = int(account.get('balance') or 0)
        result['total_amount'] = int(account.get('totalAmount') or 0)
        self.logger.points(result['balance'], '世界杯当前金币')

    def run(self) -> Dict[str, Any]:
        result = {
            'daily_gift': False,
            'tasks_completed': 0,
            'levels_passed': 0,
            'game_coins': 0,
            'bets_placed': 0,
            'settle_pnl': 0,
            'balance': 0,
            'total_amount': 0,
        }
        self.logger.info('━━━ 世界杯活动 ━━━')
        self._assist()
        index = self._post('/commonPost/~memberNonactivity~worldCupIndexService~index')
        if not (index and index.get('success')):
            self._error('查询首页', index)
            return result
        info = index.get('obj') or {}
        if info.get('acStartTime') or info.get('acEndTime'):
            self.logger.info(f"世界杯活动周期: {info.get('acStartTime', '')} ~ {info.get('acEndTime', '')}")

        self._daily_gift(result)
        self._tasks(result)
        if WORLD_CUP_ENABLE_GAME:
            self._game(result)
        if ENABLE_WORLD_CUP_BET:
            self._bet(result)
        else:
            self.logger.info('世界杯随机下注已关闭(配置区 ENABLE_WORLD_CUP_BET=True 可开启)')
        if WORLD_CUP_ENABLE_SETTLE:
            self._settle(result)
        self._refresh_balance(result)
        return result


# ==================== 账号执行 ====================
def _grab_appsign(account_raw: str) -> tuple:
    """解析 appsign=<headers JSON>@<body>，返回 (headers_str, body_str) 或 ('', '')。

    appsign 存 universalSign 请求的 headers(JSON 对象) 与 body(原文字符串)。
    因 body 含 { } 且 headers 也含 { }，用 `@<body>` 之前的最后一个 `@` 分隔不可靠，
    这里用「appsign= 之后、第一个 `@` 之前是 headers JSON」的规则，
    body 原样取 `@` 之后全部内容。
    """
    m = re.search(r'(?:^|[;&\s])appsign=(.+)$', (account_raw or '').strip(), re.S)
    if not m:
        return ('', '')
    rest = m.group(1).strip().rstrip(';')
    # headers JSON 与 body 之间用 @ 分隔；headers 以 { 开头
    if not rest.startswith('{'):
        return ('', '')
    depth = 0
    end = -1
    in_str = False
    esc = False
    for i, ch in enumerate(rest):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return ('', '')
    headers_str = rest[:end + 1]
    tail = rest[end + 1:].strip()
    if tail.startswith('@'):
        tail = tail[1:].strip()
    return (headers_str, tail)


def parse_account(account_raw: str) -> Tuple[str, str, str, str, str]:
    """解析单条账号凭证，返回 (凭证串, 代理, suuid, sfapp, ucmp)"""
    if '#' in account_raw and (':' in account_raw.split('#')[-1]):
        last_hash = account_raw.rfind('#')
        account_url = account_raw[:last_hash].strip()
        fixed_proxy = account_raw[last_hash + 1:].strip()
    else:
        account_url = account_raw
        fixed_proxy = ""
    suuid = ''
    sfapp = ''
    ucmp = ''
    raw_input = account_raw.strip()
    # ── 解析各凭证段 ──
    # 注意两个坑：
    #  1) sfapp 的 URL 含 %XX 编码，绝不能 unquote（会把 %2F→/ %2B→+ 破坏 RSA 签名）
    #  2) 各凭证用 ';' 分隔，取值必须截断到下一个 ';'，
    #     否则正则会贪婪吞掉后面的凭证（已实测复现）
    def _grab(key: str) -> str:
        mm = re.search(r'(?:^|[;&\s])' + key + r'=([^;]*)', raw_input)
        return mm.group(1).strip() if mm else ''

    sfapp = _grab('sfapp')
    ucmp = _grab('ucmp')
    decoded = unquote(account_url)
    rest = decoded
    # 从 suuid 检索里剔除其它凭证段，避免误匹配
    for key in ('sfapp', 'ucmp'):
        rest = re.sub(r'(?:^|[;&\s])' + key + r'=[^;]*', '', rest)
    for part in rest.replace(';', '&').split('&'):
        p = part.strip()
        if p.lower().startswith('suuid='):
            suuid = p.split('=', 1)[1].strip()
    return account_url, fixed_proxy, suuid, sfapp, ucmp


def run_account(account_raw: str, index: int) -> Dict[str, Any]:
    logger = Logger()
    account_url, fixed_proxy, suuid, sfapp, ucmp = parse_account(account_raw)
    decoded_account = unquote(account_url)
    http = SFHttpClient(fixed_proxy)
    login_success = False
    phone = ''
    user_id = ''
    renewed = False
    ucmp_points = None
    app_token = ''
    appsign = _grab_appsign(account_raw)
    if appsign:
        # ── appsign 模式（最优）：重放 universalSign 续签，可无限次换新 session ──
        logger.info('检测到 appsign 凭证，走 universalSign 续签...')
        try:
            import json as _json
            _h, _b = appsign
            sess = SfAppSession(_json.loads(_h), _b)
            miss = sess.missing_headers()
            if miss:
                logger.error(f'appsign 缺少必需头: {miss}')
            elif sess.renew():
                logger.success(f'universalSign 续签成功: 新 sessionId '
                               f'{sess.session_id[:8]}...{sess.session_id[-4:]}')
                user_id, phone = sess.user_id, sess.mobile
                # 把新会话灌进 http 客户端
                for k, v in sess.session.cookies.get_dict().items():
                    http.session.cookies.set(k, v, domain='mcs-mimp-web.sf-express.com')
                http.app_token = 'QaeFLkUMV2UjYNkT'
                app_token = 'QaeFLkUMV2UjYNkT'
                login_success = True
                renewed = True
                # 顺手复核积分
                _p = sess.query_points()
                if _p is not None:
                    ucmp_points = _p
                    logger.info(f'appsign 复核积分: {_p}')
            else:
                logger.error('universalSign 续签失败（凭证组过期，需重新抓包）')
        except Exception as _e:
            logger.error(f'appsign 续签异常: {str(_e)[:100]}')
    if ucmp:
        # ── ucmp 直读：用 APP 长期凭证读积分（不依赖 mcs session）──
        logger.info('检测到 ucmp 凭证，直连 APP 积分接口...')
        ucc = UcmpAppClient(ucmp, fixed_proxy)
        ucmp_points = ucc.query_points()
        if ucmp_points is not None:
            logger.success(f'ucmp 直读成功: 可用积分 {ucmp_points}')
        else:
            logger.warning('ucmp 直读失败（凭证组可能过期，需重新抓一组 sytToken/requestSign）')
    if sfapp and not login_success:
        # ── APP 模式：用 APP 端凭证换新 sessionId（优先于 suuid）──
        logger.info('检测到 sfapp 凭证，走 APP 换签...')
        renewer = AppSessionRenewer(sfapp, fixed_proxy)
        ok, sid, user_id, phone = renewer.renew(logger)
        if ok and not phone:
            logger.warning('APP 换签拿到 sessionId 但缺少身份 Cookie，重试换签(附诊断)...')
            time.sleep(2)
            ok, sid, user_id, phone = renewer.renew(logger, verbose=True)
        if ok:
            cookie_str = f'sessionId={sid}'
            if user_id:
                cookie_str += f';_login_user_id_={user_id}'
            if phone:
                cookie_str += f';_login_mobile_={phone}'
            account_url = cookie_str
            # APP 模式必须带业务 token，否则接口报「权限验证失败,token错误」
            app_token = renewer.token
            http = SFHttpClient(fixed_proxy, app_token=app_token)
            for item in cookie_str.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    http.session.cookies.set(k, v, domain='mcs-mimp-web.sf-express.com')
            renewed = True
            login_success = True
            if not renewer.token:
                logger.warning('未提供 APP 业务 token（格式 sfapp=<URL>@<token>），'
                               '接口可能报「权限验证失败」')
        else:
            logger.error('APP 换签未获得 sessionId（凭证失效或参数不全），回退其它方式')
    if suuid and not login_success:
        # ── suuid 模式：先自动换新 sessionId（根治 CK 过期）──
        logger.info('检测到 suuid，自动换签新 sessionId...')
        renewer = SuuidRenewer(suuid, fixed_proxy)
        ok, sid, user_id, phone = renewer.renew(logger)
        # 换到 sessionId ≠ 登录成功：链路可能只种出匿名会话（无 _login_mobile_）
        # 匿名会话跑任务全部报「未登录」，必须校验身份 Cookie
        if ok and not phone:
            logger.warning('换签拿到 sessionId 但缺少身份 Cookie(_login_mobile_)，疑似匿名会话，重试换签(附诊断)...')
            time.sleep(2)
            ok, sid, user_id, phone = renewer.renew(logger, verbose=True)
        if ok and not phone:
            logger.warning('二次换签仍无身份 Cookie，回退传统登录校验')
            login_success = False
            renewed = False
        elif ok:
            cookie_str = f'sessionId={sid}'
            if user_id:
                cookie_str += f';_login_user_id_={user_id}'
            if phone:
                cookie_str += f';_login_mobile_={phone}'
            account_url = cookie_str
            # 把新 Cookie 装进 http 会话
            for item in cookie_str.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    http.session.cookies.set(k, v, domain='mcs-mimp-web.sf-express.com')
            renewed = True
            login_success = True
        else:
            logger.error('suuid 换签未获得 sessionId（suuid 失效或瞬时风控），转传统登录兜底')
            login_success = False
            renewed = False
    if suuid and not login_success:
        # 兜底顺序：凭证带身份 Cookie（双保险格式 suuid=..;sessionId=..;_login_mobile_=..）
        # 时先用存量 Cookie 走 login()；纯 suuid 才重建换签链 URL 重试
        _probe = unquote(account_url).lower()
        if not ('_login_mobile_=' in _probe or 'sessionid=' in _probe):
            account_url = (
                'https://ucmp.sf-express.com/wechat-act/weixin/activity/sfnewactivity'
                f'?bizCode={SFNEWACTIVITY_BIZ}&regSource=mypoint&citycode=571&cityname=%E6%9D%AD%E5%B7%9E'
                f'&wxapp-version=V17.80&suuid={suuid}'
            )
    if not login_success:
        for attempt in range(MAX_PROXY_RETRIES):
            if attempt > 0:
                http = SFHttpClient(fixed_proxy)
            success, user_id, phone = http.login(account_url)
            if success:
                login_success = True
                break
            time.sleep(2)
    if not login_success:
        logger.error(f'账号{index + 1} 登录失败')
        # 先判断具体的凭证失效原因，避免被 ucmp 兜底掩盖
        app_invalid = False
        suuid_invalid = False
        if sfapp:
            app_invalid = not AppSessionRenewer.check_alive(sfapp, fixed_proxy)
        if suuid:
            suuid_invalid = not SuuidRenewer.check_alive(suuid, fixed_proxy)
        if ucmp_points is not None:
            # 只有 ucmp 凭证：能读到积分，但没有 mcs 会话，无法执行任务
            reasons = ['仅 ucmp 凭证：可读积分，无法执行任务（需 sfapp 或 suuid）']
            if sfapp and app_invalid:
                reasons.append('sfapp 凭证已失效，请重新抓取')
            if suuid and suuid_invalid:
                reasons.append('suuid 已失效，请重新抓取')
            for msg in reasons:
                logger.warning(msg)
            return {'success': True, 'phone': '', 'index': index,
                    'points_before': ucmp_points, 'points_after': ucmp_points,
                    'points_earned': 0, 'ucmp_points': ucmp_points,
                    'member_day_prizes': [], 'world_cup': {},
                    'ck_invalid': False, 'suuid_invalid': suuid_invalid,
                    'app_invalid': app_invalid,
                    'ucmp_only': True,
                    'fail_reason': ' / '.join(reasons)}
        if sfapp:
            return {'success': False, 'phone': '', 'index': index,
                    'points_before': 0, 'points_after': 0, 'points_earned': 0,
                    'member_day_prizes': [], 'world_cup': {},
                    'ck_invalid': False, 'suuid_invalid': False,
                    'app_invalid': app_invalid,
                    'fail_reason': ('APP凭证失效了，请重新抓取 share/app/shareRedirect 链接'
                                    if app_invalid else 'APP换签异常(疑似风控)，稍后重试')}
        if suuid:
            return {'success': False, 'phone': '', 'index': index,
                    'points_before': 0, 'points_after': 0, 'points_earned': 0,
                    'member_day_prizes': [], 'world_cup': {},
                    'ck_invalid': False, 'suuid_invalid': suuid_invalid,
                    'fail_reason': ('suuid失效了，请重新抓取 suuid' if suuid_invalid
                                    else 'suuid换签异常(疑似风控)，稍后重试')}
        ck_invalid = 'sessionid=' in decoded_account.lower() or '_login_' in decoded_account.lower()
        return {'success': False, 'phone': '', 'index': index,
                'points_before': 0, 'points_after': 0, 'points_earned': 0,
                'member_day_prizes': [], 'world_cup': {},
                'ck_invalid': ck_invalid,
                'fail_reason': 'CK失效了' if ck_invalid else '登录失败'}
    masked = phone[:3] + "****" + phone[7:] if len(phone) >= 7 else phone
    if appsign and renewed:
        tag = ' (universalSign续签)'
    elif sfapp and renewed:
        tag = ' (APP自动换签)'
    elif renewed:
        tag = ' (suuid自动换签)'
    else:
        tag = ''
    logger.success(f'账号{index + 1}: 【{masked}】登录成功{tag} | 🌐 {http.proxy_display}')
    time.sleep(random.uniform(1, 3))
    result = {
        'success': True, 'phone': phone, 'index': index,
        'points_before': 0, 'points_after': 0, 'points_earned': 0,
        'member_day_prizes': [], 'world_cup': {},
        'ck_invalid': False, 'suuid_invalid': False, 'fail_reason': '',
    }
    # 日常积分任务
    if ENABLE_DAILY_TASK:
        logger.info('━━━ 日常积分任务 ━━━')
        daily = DailyTaskExecutor(http, logger, user_id)
        daily.dual_sign_in()
        time.sleep(1)
        sign_ok, sign_err = daily.sign_in()
        if not sign_ok and '活动太火爆' in sign_err:
            for retry in range(3):
                logger.warning(f'签到IP问题，重试({retry + 1}/3)...')
                time.sleep(2)
                # 重建客户端时必须带上 app_token，否则 APP 模式下接口报「权限验证失败」
                http = SFHttpClient(fixed_proxy, app_token=app_token)
                s, user_id, phone = http.login(account_url)
                if s:
                    daily.http = http
                    daily.user_id = user_id
                    sign_ok, sign_err = daily.sign_in()
                    if sign_ok or '活动太火爆' not in sign_err:
                        break
        pb, pa = daily.run()
        result['points_before'] = pb
        result['points_after'] = pa
        result['points_earned'] = pa - pb
    # ucmp 复核：有 ucmp 凭证时，跑完任务用 APP 直连接口再读一次真实积分
    if ucmp:
        verify = UcmpAppClient(ucmp, fixed_proxy).query_points()
        if verify is not None:
            result['ucmp_points'] = verify
            base = ucmp_points if ucmp_points is not None else result['points_before']
            if result['points_after'] and verify != result['points_after']:
                logger.warning(f'积分不一致: 任务链读到 {result["points_after"]}，'
                               f'ucmp 读到 {verify}（以 ucmp 为准）')
            logger.info(f'ucmp 复核积分: {verify}')
            if base is not None:
                result['points_before'] = base
                result['points_after'] = verify
                result['points_earned'] = verify - base
        else:
            logger.warning('ucmp 复核失败（凭证组过期）')
    # 会员日活动 (每月26-28号)
    if ENABLE_MEMBER_DAY:
        current_day = datetime.now().day
        if 26 <= current_day <= 28:
            logger.info('━━━ 会员日活动 ━━━')
            md = MemberDayExecutor(http, logger, user_id)
            md_result = md.run()
            result['member_day_prizes'] = md_result.get('lottery_prizes', [])
        else:
            logger.info('⏰ 未到会员日(26-28号)，跳过')
    if ENABLE_WORLD_CUP:
        if world_cup_active():
            result['world_cup'] = WorldCupExecutor(http, logger, user_id).run()
        else:
            logger.info('⏰ 不在世界杯活动期(2026.07.02-07.20)，跳过')
    if http.ck_invalid:
        logger.error(f'账号{index + 1} CK失效了')
        result['success'] = False
        result['ck_invalid'] = True
        result['fail_reason'] = http.ck_invalid_message or 'CK失效了'
    return result


# ==================== 主程序 ====================
def split_accounts(env_value: str) -> List[str]:
    """按 & 切分多账号，但保护单个账号内部 URL 里的 &。

    为什么需要：sfapp=<activityRedirect完整URL>@<token> 里本身含
    &source=SFAPP&bizCode=... 等参数，若直接 split('&') 会把一个账号切成多段。
    规则：以「凭证键名=」作为新账号的起点识别，键名外的 & 视为同一账号内部参数。
    """
    value = (env_value or '').strip()
    if not value:
        return []
    # 以 "<key>=" 出现在串首或 & / ; 之后 作为账号边界；key 限定为已知凭证名
    keys = r'(?:suuid|sfapp|ucmp|sessionId|_login_mobile_|_login_user_id_)'
    # 先把真正的账号分隔符（& 后紧跟 已知键名=）替换成占位符
    protected = re.sub(r'&(?=' + keys + r'=)', '\x00', value)
    return [u.replace('\x00', '&').strip()
            for u in protected.split('\x00') if u.strip()]


def main():
    env_name = 'sfsyUrl'
    env_value = os.getenv(env_name)
    if not env_value:
        print(f"❌ 未找到环境变量 {env_name}")
        return
    account_list = split_accounts(env_value)
    if not account_list:
        print(f"❌ 环境变量 {env_name} 为空")
        return
    random.shuffle(account_list)
    task_map = {
        "日常任务": ENABLE_DAILY_TASK,
        "会员日": ENABLE_MEMBER_DAY,
        "世界杯": ENABLE_WORLD_CUP,
    }
    enabled = [f"{k}✓" for k, v in task_map.items() if v]
    print("=" * 60)
    print("🎉 顺丰速运自动任务 v1.5.0")
    print("👨‍💻 From: YaoHuo8648")
    print(f"📱 共 {len(account_list)} 个账号")
    print(f"⚙️ 并发: {CONCURRENT_NUM} | 📋 {' '.join(enabled)}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if PROXY_API_URL:
        _log_global(f"🔌 代理已开启: {PROXY_API_URL[:40]}...")
    print("=" * 60)
    all_results = []
    if CONCURRENT_NUM <= 1:
        for idx, raw in enumerate(account_list):
            result = run_account(raw, idx)
            all_results.append(result)
            if idx < len(account_list) - 1:
                time.sleep(2)
    else:
        with ThreadPoolExecutor(max_workers=CONCURRENT_NUM) as pool:
            futures = {pool.submit(run_account, raw, idx): idx for idx, raw in enumerate(account_list)}
            for f in as_completed(futures):
                all_results.append(f.result())
    all_results.sort(key=lambda x: x['index'])
    # 汇总
    print(f"\n{'='*70}")
    print("📊 执行汇总")
    print("=" * 70)
    total_earned = 0
    show_world_cup = ENABLE_WORLD_CUP and world_cup_active()
    total_world_cup_balance = 0
    for r in all_results:
        phone = r['phone'][:3] + "****" + r['phone'][7:] if r.get('phone') and len(r['phone']) >= 7 else r.get('phone', '未登录')
        earned = r.get('points_earned', 0)
        total_earned += earned
        world_cup = r.get('world_cup') or {}
        total_world_cup_balance += world_cup.get('balance', 0)
        if r.get('app_invalid'):
            extra = '（ucmp 仍可读积分）' if r.get('ucmp_only') else ''
            print(f"❌ {phone}: APP凭证失效了，请重新抓取{extra}")
        elif r.get('suuid_invalid'):
            print(f"❌ {phone}: suuid失效了，请重新抓取")
        elif r.get('ck_invalid'):
            print(f"❌ {phone}: CK失效了")
        elif r.get('ucmp_only'):
            print(f"👁 {r.get('ucmp_points') or r['points_after']} 积分"
                  f"（仅 ucmp 直读，未执行任务）")
        elif not r['success']:
            print(f"❌ {phone}: 登录失败")
        else:
            parts = [f"积分+{earned}"]
            md_prizes = r.get('member_day_prizes', [])
            if md_prizes:
                parts.append(f"会员日: {', '.join(md_prizes)}")
            if show_world_cup:
                parts.append(f"世界杯金币{world_cup.get('balance', 0)}")
                if world_cup.get('game_coins'):
                    parts.append(f"射门+{world_cup.get('game_coins')}")
                if world_cup.get('tasks_completed'):
                    parts.append(f"世界杯任务{world_cup.get('tasks_completed')}")
                if world_cup.get('daily_gift'):
                    parts.append('世界杯礼物✓')
                if world_cup.get('bets_placed'):
                    parts.append(f"竞猜{world_cup.get('bets_placed')}场")
            print(f"✅ {phone}: {' | '.join(parts)}")
    print("-" * 70)
    total_parts = [f"📱 总账号: {len(all_results)}", f"💰 总积分+{total_earned}"]
    if show_world_cup:
        total_parts.append(f"世界杯金币{total_world_cup_balance}")
    print(" | ".join(total_parts))
    print("=" * 70)
    print("🎊 执行完成!")
    push_lines = []
    for r in all_results:
        phone = r['phone'][:3] + "****" + r['phone'][7:] if r.get('phone') and len(r['phone']) >= 7 else r.get('phone', '未登录')
        if r.get('app_invalid'):
            extra = '（ucmp 仍可读积分）' if r.get('ucmp_only') else ''
            push_lines.append(f"❌ {phone}: APP凭证失效了，请重新抓取{extra}")
        elif r.get('suuid_invalid'):
            push_lines.append(f"❌ {phone}: suuid失效了，请重新抓取")
        elif r.get('ck_invalid'):
            push_lines.append(f"❌ {phone}: CK失效了")
        elif r.get('ucmp_only'):
            push_lines.append(f"👁 {r.get('ucmp_points') or r['points_after']} 积分"
                              f"（仅 ucmp 直读，未执行任务）")
        elif not r['success']:
            push_lines.append(f"❌ {phone}: 登录失败")
        else:
            earned = r.get('points_earned', 0)
            parts = [f"积分+{earned}"]
            md_prizes = r.get('member_day_prizes', [])
            if md_prizes:
                parts.append(f"会员日: {', '.join(md_prizes)}")
            world_cup = r.get('world_cup') or {}
            if show_world_cup:
                parts.append(f"世界杯金币{world_cup.get('balance', 0)}")
                if world_cup.get('game_coins'):
                    parts.append(f"射门+{world_cup.get('game_coins')}")
                if world_cup.get('tasks_completed'):
                    parts.append(f"世界杯任务{world_cup.get('tasks_completed')}")
                if world_cup.get('daily_gift'):
                    parts.append('世界杯礼物✓')
            push_lines.append(f"✅ {phone}: {' | '.join(parts)}")
    push_lines.append(" | ".join(total_parts))
    notify_content = "\n".join(push_lines)
    if PUSH_SWITCH == "1" and notify_content:
        print("📤 准备推送消息...")
        try:
            if notify_send:
                notify_send("顺丰速运自动任务", notify_content)
                print("✅ 推送发送成功")
            else:
                print("⚠️ 未找到notify模块，无法推送")
        except Exception as e:
            print(f"❌ 推送发送失败: {e}")
    elif PUSH_SWITCH == "0":
        print("ℹ️ 推送开关未开启 (SFSY_PUSH=0)")


if __name__ == '__main__':
    main()
