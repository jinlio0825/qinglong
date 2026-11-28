#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 小蚕霸王餐(小程序版)
定时规则
cron: 20 8 * * *

==================================
小蚕霸王餐 · 微信小程序协议版
==================================
与 xc.py（APP 版）功能对等，但请求特征完全复刻微信小程序：
  x-platform=mini / x-version=3.22.9.93 / 微信 WebView UA
  Referer=servicewechat.com/wx52ae177248081591/824/page-frame.html
  每个请求 body 注入 app_id=20（APP 版不带此字段）
  默认请求间隔 3 秒（比 APP 版更保守）

功能:
  登录验证 → 每日签到抽奖 → 成长值签到状态查询 → 开宝箱
  → 元宝领取 + 元宝闪购兑换(可配抢购)
  → 日常任务×20 (含看广告加抽奖次数) → 抽奖×6 + 额外抽奖×2
  → 红包雨(自动选场次/等待开场/报名/抢包/广告加奖)
  → 余额≥1元 自动提现到支付宝(默认关)
  → 汇总推送钉钉机器人(可配)

---------- 重要：网关 WAF 与 TLS 指纹 ----------
gw.xiaocantech.com 网关启用了腾讯云 WAF 的 TLS 指纹(JA3)校验，
python 标准 requests 的 TLS 指纹会被直接拦截并返回 403 WAF 页面。
本脚本因此使用 curl_cffi 模拟浏览器 TLS 指纹：
    pip install curl_cffi
未安装时自动回落 requests，此时大概率全部 403。

另：若服务器出口 IP 已被 WAF 标记为风险源，即便 TLS 指纹正确也会 403
（现象：/g/pa 端点 200，/rpc 端点 403）。此时只能换出口 IP（代理）或等待解封。

---------- 青龙面板使用 ----------
脚本管理新建 xc_mini.py，环境变量:

  XC_DATA            必填, 账号 JSON 数组:
                       [{"userId":"123456","teemo":"1234567","token":"eyJ...","userName":"昵称"}]
                       userId = x-vayne, teemo = x-teemo(silk_id), token = x-sivir
                       抓小程序「我的」页面的请求头复制即可

  XC_BRAND_ENABLE    抢兑开关, 默认开启(true)。填 false 只跑日常不抢兑

  XC_YB_GOODS_ID     元宝闪购要抢的商品, 默认 200 = svip⚡️1元红包(4000元宝)
                       可填其他 exchange_id: 199=svip 2元红包(8000)、
                       198=svip 3元红包(12000)、190=vip 1元红包(8000)
                       多个用逗号: "200,199"

其余参数全部写死在脚本里(需要时直接改代码), 不用配环境变量。

---------- 三场活动的时间(抓包实证) ----------
  09:00  元宝闪购   svip⚡️1元红包 4000元宝 (exchange_id=200)
  09:30  大牌券     通用大牌券, 每天仅此一场
  日常   其余任意时间

---------- 抢兑模式(照联通写法) ----------
脚本开头判断时间, 命中则走「并发抢兑」, 所有账号同时跑, 不做任何日常任务:

  8:40  ~ 9:05   启动 → 抢元宝闪购
  9:06  ~ 9:35   启动 → 抢大牌券
  其余时间        → 跑日常任务

  建议 cron (三条):
    40 8 * * *    元宝闪购
    20 9 * * *    大牌券
    0 7 * * *     日常任务

  抢兑全程请求间隔为 0(临时压到 0, 抢完恢复), 10 次冲击约 2.7 秒。
  日常流程 58 次请求 × 3 秒 ≈ 3 分钟。

  验证标志: 抢兑日志应出现
    ⏰ [自动触发] 检测到抢兑时间点 (8:40)，进入并发抢兑模式
    🚨🚨🚨 [抢兑模式已启动] 目标: 元宝闪购 (开抢 09:00) 🚨🚨🚨
    🚀 [并发模式] 启动 N 个账号同时抢元宝闪购...

大牌券数据源说明(抓包实证):
    VipRightsService.BrandCardInfo      type=1   已持有/可用的券
    VipRightsService.ExtraBrandCardPool type=99  可抢的券池(带 start_time 开抢时间)
    SilkwormCardService.GetUserCardList card_types=[13,3] 已抢到的券明细

    ⚠ 抢券动作接口 BRAND_GRAB_METHOD 默认为 VipRightsService.GrabBrandCard,
      该名称未经抓包验证(你抢券那次没被录到)。若实际不同, 直接改脚本里的
      常量 BRAND_GRAB_METHOD 即可。抓包方法: 在小程序点一次「抢大牌」看 methodName。

---------- 小程序协议要点(抓包实证) ----------
  1. 端点: POST https://gw.xiaocantech.com/rpc
  2. RPC 路由不在 body，而在请求头: serverName + methodName
     服务端按 header 解析路由, 请求体只传业务参数 —— 因此 APP 与小程序的
     可用接口是同一套, 端差异仅体现在请求头特征上。
  3. 签名头: x-nami / x-garen / x-ashe（算法与 APP 版完全一致）
  4. 身份头: x-sivir(token) / x-teemo(silk_id) / x-vayne(userId) / x-annie=XC
  5. body 全部带 app_id:20（APP 版不带，这是服务端区分端的实际字段）
"""

import base64
import hashlib
import hmac as hmac_mod
import json
import os
import random
import re
import time
import uuid

# ---------- HTTP 层: WAF 需要浏览器 TLS 指纹 ----------
try:
    from curl_cffi import requests as http
    HAS_CURL_CFFI = True
except ImportError:
    import requests as http
    HAS_CURL_CFFI = False

# ---------- 小程序端常量(全部来自抓包, 写死不用配) ----------
BASE_URL = "https://gw.xiaocantech.com/rpc"
APP_ID = 20
X_VERSION = "3.22.9.93"
X_APP_SR = "20"
X_MODEL = "PKR110 OnePlus"
DEFAULT_CITY = "330109"
REFERER = "https://servicewechat.com/wx52ae177248081591/824/page-frame.html"
UA = ("Mozilla/5.0 (Linux; Android 16; PKR110 Build/AP3A.240617.008; wv) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/156.0.8078.79 "
      "Mobile Safari/537.36 XWEB/1560023 MMWEBSDK/20260902 MMWEBID/3250 "
      "MicroMessenger/8.0.80.3220(0x280050C7) WeChat/arm64 Weixin NetType/WIFI "
      "Language/zh_CN ABI/arm64 MiniProgramEnv/android")
IMPERSONATE = "chrome"                # curl_cffi TLS 指纹(绕 WAF)
PROXY = ""                            # 需要代理时改这里

REQUEST_INTERVAL = 3.0                # 请求间隔秒
IS_WALLET = False                     # 自动提现, 需要时改 True

# ---------- 抢大牌(JS 原版 BrandCardAuto 移植, 11-28 修正) ----------
# XC_BRAND_ENABLE 默认开启: true=抢大牌+元宝闪购, false=只跑日常
# 关键修正(11-28 实证): 抢券接口是 GrabExtraBrandCard(不是 GrabBrandCard, 打它会 500),
# 且必须走 BrandCardRpc 独立通道(APP 特征头 + hzaiguojiang origin + 显式 SilkwormVip)
BRAND_ENABLE = os.getenv("XC_BRAND_ENABLE", "true").lower() != "false"
BRAND_TYPE = 99                        # 9:30 限量券
BRAND_BEFORE_MS = int(os.getenv("XC_BRAND_BEFORE_MS", "300"))
BRAND_INTERVAL_MS = int(os.getenv("XC_BRAND_INTERVAL_MS", "100"))
BRAND_ATTEMPTS = int(os.getenv("XC_BRAND_ATTEMPTS", "5"))
BRAND_WAIT_MAX_MS = int(os.getenv("XC_BRAND_WAIT_MAX_MS", "180000"))
BRAND_GRAB_METHOD = "VipRightsService.GrabExtraBrandCard"

# 元宝闪购要抢的商品 exchange_id, 默认 200 = svip⚡️1元红包(4000元宝)
# 可用 XC_YB_GOODS_ID 环境变量覆盖; 也可写多个: "200,199"
YB_GOODS_ID = os.getenv("XC_YB_GOODS_ID", "200").strip()

# 转盘抽奖次数任务: true=逐个试探(1~20, 连续3个"参数错误"即停)
# false=只发抓包验证过的 2/8/9/10/11

RECOMMEND_ID = 12159598643            # 推荐人
PHONE_MIDDLE_GLOBAL = os.getenv("XC_PHONE_MIDDLE", "")   # 手机中间4位全局兜底(账号字段优先)

DD_BOT_TOKEN = ""                     # 钉钉 token, 留空不推送
DD_BOT_SECRET = ""
SCRIPT_NAME = "小蚕霸王餐(小程序版)"

# 元宝闪购/红包雨的固定参数(需要时改这里, 不走环境变量)
RAIN_ENABLE = True       # 红包雨开关
RAIN_AD_ENABLE = True    # 红包雨广告加奖
RAIN_CLICK_NUM = 19      # 抢包点击次数

AD_SIGN_KEY = "lcjkbqadfrzsewxy"      # 看广告/红包雨签名密钥(APP 版实证)

NOTIFY = []
SUCCESS = 0


def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "ignore").decode("utf-8", "ignore"), flush=True)
    NOTIFY.append(msg)


def is_cookie_expired(resp):
    """token 失效判断: code=401 或消息含登录/凭证失效类关键词。"""
    status = (resp or {}).get("status") or {}
    code = status.get("code")
    if not status or code == 0:
        return False
    if code == 401:
        return True
    msg = status.get("msg") or status.get("message") or ""
    return bool(re.search(
        r"未登录|请.*登录|重新登录|需要.*登录"
        r"|(?:cookie|token|session|登录|凭证).*(?:失效|过期|无效)"
        r"|(?:失效|过期|无效).*(?:cookie|token|session|凭证)"
        r"|unauthori[sz]ed|unauthenticated|not[\s_-]*log(?:ged)?[\s_-]*in"
        r"|(?:cookie|token|session).*(?:expired|invalid)"
        r"|(?:expired|invalid).*(?:cookie|token|session)", msg, re.IGNORECASE))


def dingtalk_send(content):
    """钉钉机器人 text 消息(加签模式)。未配置则跳过。用标准 requests 即可，钉钉不校验 TLS 指纹。"""
    if not (DD_BOT_TOKEN and DD_BOT_SECRET):
        return
    import requests as _rq
    ts = str(round(time.time() * 1000))
    sign = base64.b64encode(
        hmac_mod.new(DD_BOT_SECRET.encode(), f"{ts}\n{DD_BOT_SECRET}".encode(),
                     hashlib.sha256).digest()
    ).decode()
    try:
        r = _rq.post(
            "https://oapi.dingtalk.com/robot/send",
            params={"access_token": DD_BOT_TOKEN, "timestamp": ts, "sign": sign},
            json={"msgtype": "text", "text": {"content": content}},
            timeout=10)
        d = r.json()
        if d.get("errcode") == 0:
            log("[INFO] 钉钉通知发送成功")
        else:
            log(f"[ERROR] 钉钉通知失败: {d}")
    except Exception as e:
        log(f"[ERROR] 钉钉通知异常: {e}")


def env_data():
    raw = os.getenv("XC_DATA", "")
    if not raw:
        for p in ("xcbwc_data.json", "accounts.json"):
            if os.path.exists(p):
                raw = open(p, encoding="utf-8").read()
                break
    if not raw:
        raise SystemExit("请设置环境变量 XC_DATA=[{userId,teemo,token,userName},...]")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


# ---------- 抢兑时间窗(写死, 抓包实证) ----------
# 大牌券: 每天 09:30 开抢, 仅此一场
BRAND_HOUR = 9
BRAND_MIN = 30
BRAND_CRON_START = 20        # 提前 10 分钟启动(9:20), 留出查询券池的时间
# 元宝闪购: 每天 09:00 开抢, svip 1元红包 4000 元宝
YB_FLASH_HOUR = 9
YB_FLASH_MIN = 0


def ad_sign(silk_id, bus_type, extra=""):
    """看广告/红包雨抽奖签名: HMAC-SHA256(key, silk_id=..&timestamp=..&nonce=..&bus_type=..) → Base64"""
    ts = int(time.time())
    nonce = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))
    if extra:
        msg = f"silk_id={silk_id}&{extra}&timestamp={ts}&nonce={nonce}"
    else:
        msg = f"silk_id={silk_id}&timestamp={ts}&nonce={nonce}&bus_type={bus_type}"
    mac = hmac_mod.new(AD_SIGN_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(mac).decode(), ts, nonce


class XiaocanMiniUser:
    """小程序协议的账号对象。RPC 路由走请求头, body 注入 app_id。"""

    def __init__(self, acc, index):
        self.index = index
        self.userId = str(acc.get("userId", ""))
        self.teemo = str(acc.get("teemo") or acc.get("silk_id") or "")
        self.silk_id = int(self.teemo) if self.teemo.isdigit() else 0
        self.token = acc.get("token") or acc.get("x-sivir") or ""
        self.userName = acc.get("userName") or self.userId
        self.city = str(acc.get("city") or DEFAULT_CITY)
        self.interval = REQUEST_INTERVAL    # 每账号独立间隔(抢兑时改这里, 不动全局)
        self.phone_middle = str(acc.get("phone_middle") or PHONE_MIDDLE_GLOBAL or "").strip()
        self.session_id = acc.get("sessionId") or str(uuid.uuid4())
        self.ck_status = True
        self.red_pack_rain_done = False
        # 小程序端请求头(抓包逐项对齐)
        self.headers = {
            "user-agent": UA,
            "content-type": "application/json",
            "charset": "utf-8",
            "version": X_VERSION,
            "x-teemo": self.teemo,
            "x-annie": "XC",
            "x-version": X_VERSION,
            "x-vayne": self.userId,
            "x-sivir": self.token,
            "x-platform": "mini",
            "x-city": self.city,
            "x-session-id": self.session_id,
            "x-app-sr": X_APP_SR,
            "x-model": X_MODEL,
            "referer": REFERER,
        }

    # ---------- RPC 基础设施 ----------
    @staticmethod
    def _sign_headers(silk_id, server, method):
        """小程序签名头, 算法与 APP 版一致(抓包实证)。
        x-nami = uuid前4位 + silk_id + uuid剩余(补齐到20位)
        x-garen = 毫秒时间戳
        x-ashe = md5(md5(server.method 小写) + ts + nami)
        """
        ts = str(int(time.time() * 1000))
        u = uuid.uuid4().hex
        sid = str(silk_id)
        nami = u[:4] + sid + u[4:20 - len(sid) - 4]
        ashe = hashlib.md5(
            (hashlib.md5(f"{server}.{method}".lower().encode()).hexdigest() + ts + nami).encode()
        ).hexdigest()
        return {"x-ashe": ashe, "x-garen": ts, "x-nami": nami}

    def _post(self, headers, body):
        """统一出口: curl_cffi 浏览器指纹 + 可选代理。"""
        kwargs = {"json": body, "headers": headers, "timeout": 20}
        if HAS_CURL_CFFI:
            kwargs["impersonate"] = IMPERSONATE
        if PROXY:
            kwargs["proxies"] = {"http": PROXY, "https": PROXY}
        r = http.post(BASE_URL, **kwargs)
        if r.status_code != 200:
            return r.status_code, None
        return 200, r.json()

    def rpc(self, server, method, body, no_delay=False):
        """小程序主通道: body 自动注入 app_id。

        no_delay=True 时不插入请求间隔 —— 抢兑路径必须用这个, 否则
        3 秒间隔会让 10 次冲击拖到 30 秒, 完全错过开抢窗口。
        """
        if isinstance(body, dict) and "app_id" not in body:
            body = {**body, "app_id": APP_ID}
        headers = {**self.headers,
                   "servername": server,
                   "methodname": method,
                   **self._sign_headers(self.teemo, server, method)}
        try:
            code, data = self._post(headers, body)
            if code != 200:
                # 403 大概率是 WAF 拦截(TLS 指纹或 IP 黑名单)
                hint = " (WAF拦截: 检查 curl_cffi 是否安装 / 出口IP是否被拉黑)" if code == 403 else ""
                log(f"[ERROR] {method}: HTTP {code}{hint}")
                return {}
            if is_cookie_expired(data) and not getattr(self, "_expired_notified", False):
                self._expired_notified = True
                self.ck_status = False
                name = self.userName or self.userId or f"账号{self.index}"
                msg = f"[{name}] token 已过期，请重新抓包更新 XC_DATA"
                log(msg)
                dingtalk_send(f"{SCRIPT_NAME} token 失效通知\n\n{msg}")
            return data
        except Exception as e:
            log(f"[ERROR] {method}: {e}")
            return {}
        finally:
            if not no_delay:
                time.sleep(self.interval)

    # ---------- 账号与资产 ----------
    def GetUserInfo(self):
        d = self.rpc("Silkworm", "SilkwormService.GetClientUserInfo", {
            "silk_id": self.silk_id,
            "up": {"rcp": 1, "rc": 0, "dm": "OnePlus", "re_ch": "", "rct": 0},
            "from_po_id": 0, "from_aid": 0})
        if (d.get("status") or {}).get("code") != 0:
            self.ck_status = False
            log(f"[FAIL] 账号{self.index} token 失效: {(d.get('status') or {}).get('msg')}")
            return {}
        return d.get("user_info") or {}

    def GetUserTaskV2(self):
        return (self.rpc("ActivityTask", "ActivityTaskMobileService.UserTaskV2",
                         {"silk_id": self.silk_id,
                          "user_id": int(self.userId) if self.userId.isdigit() else 0}).get("data") or {})

    def GetPoint(self):
        return self.GetUserTaskV2().get("point") or 0

    def GetYbPoint(self):
        return self.GetUserTaskV2().get("yb_point") or 0

    def GetCard(self):
        d = self.rpc("SilkwormCard", "SilkwormCardService.GetUserCardNumber",
                     {"silk_id": self.silk_id, "card_number_mode": 1})
        return d.get("can_use_number") or 0

    def GetRedPackNum(self):
        d = self.rpc("RedPackService", "RedPackService.GetUserRedPackNum",
                     {"silk_id": self.silk_id})
        return d.get("num") or 0

    def GetAgencyInfo(self):
        d = self.rpc("Silkworm", "SilkwormService.GetAgencyInfo", {"silk_id": self.silk_id})
        silk = (d.get("client_user") or {}).get("silk")
        return silk if silk is not None else 0

    def ClientWithdraw(self, silk):
        d = self.rpc("Silkworm", "SilkwormService.ClientWithdraw", {
            "silk_id": self.silk_id, "channel": 0, "silk": silk})
        cw_list = d.get("cw_list") or []
        got = (cw_list[0].get("silk") if cw_list else 0) or 0
        if (d.get("status") or {}).get("code") == 0:
            log(f"[提现] 成功! {got / 100} 元已到账支付宝")
        else:
            log(f"[提现] {(d.get('status') or {}).get('msg')}")

    # ---------- 签到 ----------
    def SignInLottery(self):
        """每日签到(小程序抓包: VipRightsService.SignInLottery, 与 APP 版同接口)。"""
        d = self.rpc("SilkwormVip", "VipRightsService.SignInLottery", {"silk_id": self.silk_id})
        # score/price 在响应顶层(实测: data 层不存在, 旧代码读 data.score 恒为 0)
        if (d.get("status") or {}).get("code") == 0:
            score = (d.get("score") or 0) / 100
            prices = d.get("price") or []
            p0 = (prices[0] or {}).get("name") if prices and isinstance(prices[0], dict) else (prices[0] if prices else "")
            log(f"[签到] 成功! 奖 {score} 成长值" + (f" {p0}" if p0 else ""))
        else:
            st = d.get("status") or {}
            log(f"[签到] {st.get('msg', st.get('code'))}")

    def SignInInfo(self):
        """签到状态查询: 连续天数 / 今日是否已签 / 下一个成长值节点。"""
        d = self.rpc("SilkwormVip", "VipRightsService.UserSignInDays", {"silk_id": self.silk_id})
        days = d.get("days")
        signed = d.get("is_today_signed")
        if days is not None:
            log(f"[签到状态] 连续 {days} 天 | 今日{'已' if signed else '未'}签")
        # 成长值签到节点(7/14/21...天)
        n = self.rpc("SilkwormVip", "VipRightsService.SignInNode",
                     {"silk_id": self.silk_id, "need_status": True})
        nodes = n.get("nodes") or []
        nxt = next((x for x in nodes if not x.get("rewarded")), None)
        if nxt:
            log(f"[成长值] 下一节点 {nxt.get('days')}天 → +{nxt.get('value')} 成长值")
        return days, signed

    # ---------- 挑战赛 ----------
    def ListNormalPromotionsByUser(self):
        """拉可报名的挑战赛列表(与 APP 版同一接口, 小程序实测 200 可用)。"""
        d = self.rpc("SilkwormChallenge", "ChallengeService.ListNormalPromotionsByUser", {
            "city_code": int(self.city) if self.city.isdigit() else 330109,
            "silk_id": self.silk_id})
        return d.get("promotions") or []

    def CreateUserPromotion(self, promotion_id, name=""):
        d = self.rpc("SilkwormChallenge", "ChallengeService.CreateUserPromotion", {
            "city_code": int(self.city) if self.city.isdigit() else 330109,
            "promotion_id": promotion_id, "silk_id": self.silk_id,
            "if_use_ali_go": False})   # JS 原版带此字段, 对齐
        st = d.get("status") or {}
        label = name or f"id={promotion_id}"
        log(f"[挑战赛] 报名「{label}」: {'OK' if st.get('code') == 0 else st.get('msg', st.get('code'))}")

    def ListProcessingUserPromotion(self):
        """查进行中的挑战(抓包实证: 返回 user_promotions, 含进度)。"""
        d = self.rpc("SilkwormChallenge", "ChallengeService.ListProcessingUserPromotion", {
            "silk_id": self.silk_id})
        return d.get("user_promotions") or []

    def ChallengeFlow(self):
        """挑战赛: 报告进行中的 → 拉可报名列表 → 只报列表里实际存在的。"""
        # 进行中的挑战(报进度, 不重复报名)
        try:
            processing = self.ListProcessingUserPromotion()
            for up in processing:
                p = up.get("promotion") or {}
                ut = up.get("user_task") or {}
                log(f"[挑战赛] 进行中: {p.get('name')} (已邀 {ut.get('current_number')}"
                    f"/{(p.get('stage_tasks') or [{}])[0].get('expect_num', '?')} 人)")
        except Exception as e:
            log(f"[挑战赛] 查询进行中异常: {e}")
        # 可报名列表
        try:
            promos = self.ListNormalPromotionsByUser()
            if not promos:
                log("[挑战赛] 当前无可报名的挑战")
                return
            for p in promos:
                self.CreateUserPromotion(p.get("id"), p.get("name"))
        except Exception as e:
            log(f"[挑战赛] 异常: {e}")

    def BindInviter(self):
        self.rpc("InviteWord", "InviteWordService.BindInviter", {
            "inviter_silk_id": RECOMMEND_ID,
            "user_silk_id": self.silk_id,
        })

    def RiskPhoneCheck(self):
        """手机号中间四位风控校验(JS 原版 RiskPhoneCheck 移植)。

        签到/开宝箱前调用。phone_middle 缺省时跳过(JS 同行为)。
        """
        if not self.phone_middle:
            return
        if getattr(self, "_risk_checked", False):
            return
        d = self.rpc("Brs", "RiskCheckService.PhoneCheck", {
            "silk_id": self.silk_id, "number": self.phone_middle})
        self._risk_checked = bool(d and d.get("pass"))
        log(f"[风控] 手机中间四位校验: {'pass' if self._risk_checked else json.dumps(d.get('status') or d, ensure_ascii=False)[:80]}")

    # ---------- 日常任务(积分/元宝) ----------
    def GetDailyTaskList(self):
        """拉取日常任务列表, 返回可执行项。

        响应字段(抓包实证): id/title/point/completed_num/limit_num/platform/action_type
        platform 含 3 表示 APP 专属任务(小程序端入口不可见)。
        """
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.GetDailyTask", {
            "silk_id": self.silk_id, "city_code": int(self.city) if self.city.isdigit() else 0,
            "user_id": int(self.userId) if self.userId.isdigit() else 0})
        lst = ((d.get("data") or {}).get("list")) or []
        if lst:
            log(f"[任务列表] 共 {len(lst)} 项")
            for t in lst:
                limit = t.get("limit_num") or 0
                done = t.get("completed_num") or 0
                mark = "✓" if limit and done >= limit else " "
                log(f" [{mark}] id={t.get('id')} {t.get('brief_title') or t.get('title')} "
                    f"+{t.get('point')}分 {done}/{limit} platform={t.get('platform')}")
        return lst

    def AddLotteryTimes(self, task_type):
        """做转盘抽奖次数任务。

        type 是独立编号体系, 与 GetDailyTask 的 id/action_type 无关:
          type=1  签到        type=2  分享
          type=4  沾一沾      type=8/9/10/11  浏览类
        type=3/5/6 不存在(服务端回"请求参数错误")。

        返回 (是否成功, 服务端提示):
          - code=0            → (True, "")
          - 提示含"限一次"等  → (False, 提示)  有效 type 但今天已做完
          - 提示"请求参数错误" → (False, None)  type 不存在, 应跳过
        """
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.AddLotteryTimes", {
            "silk_id": self.silk_id, "type": task_type})
        st = d.get("status") or {}
        if st.get("code") == 0:
            log(f"[抽奖次数] type={task_type} 完成, 次数+1")
            return True, ""
        msg = str(st.get("msg") or st.get("code") or "")
        if "请求参数错误" in msg:
            return False, None            # type 不存在
        log(f"[抽奖次数] type={task_type}: {msg}")
        return False, msg

    def GetLotteryInfo(self):
        """转盘抽奖信息。

        lottery_info 里的 is_xxx 字段表示该任务今天做没做, 是判断依据:
          if_shared            分享
          is_get_meituan_redpack / is_get_eleme_redpack   美团/饿了么红包
          is_view_bwc_page     浏览霸王餐页
          is_view_welfare_page 浏览福利页
          is_view_tp_ad        看第三方广告
          is_view_douyin_mall  浏览抖音商城
        """
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.LotteryInfo", {"silk_id": self.silk_id})
        info = d.get("lottery_info") or {}
        times = d.get("lottery_times") or {}
        log(f"[抽奖] 幸运次数={info.get('lucky_times')} | 今日抽了 {info.get('day_num')} 次")
        not_done = []
        for k, v in info.items():
            if k.startswith("is_view_") or k == "if_shared":
                if not v:
                    not_done.append(k)
        log(f"[抽奖] 未完成任务: {not_done if not_done else '全部已完成'}")
        return {"lottery_info": info, "lottery_times": times}

    def OnAdViewed(self, bus_type):
        """看广告加抽奖次数。bus_type: 2/4 为日常任务位(APP 版 12/13 号位)。"""
        sign, ts, nonce = ad_sign(self.silk_id, bus_type)
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.OnAdViewed", {
            "silk_id": self.silk_id, "timestamp": ts, "nonce": nonce,
            "bus_type": bus_type, "sign": sign})
        if (d.get("status") or {}).get("code") == 0:
            log(f"[广告] bus_type={bus_type} 完成")
            return True
        return False

    def Lottery(self):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.Lottery", {
            "silk_id": self.silk_id, "prize_type": 1})
        prize = d.get("prize")
        if prize:
            log(f"[抽奖] {prize.get('name')}")
        else:
            st = d.get("status") or {}
            if st.get("code") not in (0, None):
                log(f"[抽奖] {st.get('msg', st.get('code'))}")

    def ReceiveExtraLottery(self, step):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.ReceiveExtraLottery", {
            "silk_id": self.silk_id, "step": step})
        prize = d.get("prize")
        if prize:
            log(f"[额外抽奖{step}] {prize.get('name')}")

    def OpenBox(self):
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.OpenBox", {"silk_id": self.silk_id})
        prize = (d.get("prize") or {}).get("name") or (d.get("status") or {}).get("msg") or "无可领取奖励"
        log(f"[开宝箱] {prize}")

    # ---------- 元宝抽奖(小程序抓包实证) ----------
    def YbLotteryInfo(self):
        """元宝抽奖活动信息: 每日上限/单次消耗/活动与宝箱 id 列表。"""
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.YbLotteryInfo", {"silk_id": self.silk_id})
        info = d.get("lottery_info") or {}
        if info:
            log(f"[元宝抽奖] 每日上限 {info.get('daily_limit')} 次, 单次消耗 {info.get('cost')} 元宝")
        return info

    def YbLottery(self):
        """元宝抽奖一次(消耗元宝)。send_channel=3 来自抓包。"""
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.YbLottery", {
            "silk_id": self.silk_id, "send_channel": 3})
        prizes = d.get("prizes") or []
        if prizes:
            log(f"[元宝抽奖] 获得 {len(prizes)} 个奖品")
        else:
            st = d.get("status") or {}
            log(f"[元宝抽奖] {st.get('msg', st.get('code'))}")
        return d

    # ---------- 礼包/日常奖励(小程序有独立入口) ----------
    def TakeGift(self):
        """领取渠道自动化礼包(ChannelService.TakeGift)。"""
        d = self.rpc("MarketingAutomationChannel", "ChannelService.TakeGift", {"silk_id": self.silk_id})
        st = d.get("status") or {}
        if st.get("code") == 0:
            log("[礼包] 领取成功")
            return True
        log(f"[礼包] {st.get('msg', st.get('code'))}")
        return False

    def GetLotteryProgress(self):
        """转盘抽奖进度(首档/二档宝箱是否可领)。"""
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetLotteryProgress",
                     {"silk_id": self.silk_id})
        p = d.get("lottery_progress") or {}
        if p:
            log(f"[抽奖进度] 首档 {p.get('first_step_count')} 二档 {p.get('second_step_count')} "
                f"已抽 {p.get('lottery_count')} 次"
                f" | 首档宝箱{'已领' if p.get('has_got_first_step_prize') else '可领'}"
                f" 二档宝箱{'已领' if p.get('has_got_second_step_prize') else '可领'}")
        return p

    def TodayExchange(self, ingot=None):
        """今日可兑换商品(元宝够才能兑)。"""
        new_level = 3
        is_plus = True
        if ingot is None:
            ingot = self.GetYbPoint()
        d = self.rpc("SilkwormCommunity", "SilkwormMobileCommunityService.TodayExchange", {
            "silk_id": self.silk_id, "new_level": new_level, "is_plus": is_plus,
            "ingot": int(ingot)})
        goods = d.get("goods") or []
        if goods:
            log(f"[今日兑换] {len(goods)} 项")
            for g in goods:
                log(f"  {g.get('goods_name')} 需 {g.get('ingot')} 元宝")
        return goods

    def GetUserMaxRedPack(self):
        """当前可用红包(平台红包/美团/饿了么)。"""
        d = self.rpc("RedPackService", "RedPackService.GetUserMaxRedPack", {"silk_id": self.silk_id})
        packs = d.get("platform_red_packs") or []
        mt = d.get("meituan_red_pack")
        ele = d.get("eleme_red_pack")
        log(f"[红包] 平台 {len(packs)} 个 | 美团{'有' if mt else '无'} 饿了么{'有' if ele else '无'}")
        return d

    def GetUserPointHistory(self, page=1, page_size=10):
        """积分/元宝流水, 便于核对每日任务是否真到账。"""
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.UserPointHistory", {
            "silk_id": self.silk_id, "page": page, "page_size": page_size,
            "type": 1, "action": 1})
        lst = ((d.get("data") or {}).get("list")) or []
        if lst:
            log(f"[流水] 最近 {len(lst)} 条")
            for it in lst[:10]:
                log(f"  {it.get('time')} {it.get('title')} +{it.get('point')}")
        return lst

    def GetUpgradeTask(self):
        """成长值任务列表(看视频/下单/邀请等)。source=2 来自抓包。"""
        d = self.rpc("SilkwormVip", "SilkwormVipPoint.UpgradeTask", {
            "silk_id": self.silk_id, "source": 2})
        tasks = d.get("tasks") or []
        if tasks:
            log(f"[成长值任务] {len(tasks)} 项")
            for t in tasks[:8]:
                prog = t.get("progress") or {}
                log(f"  {t.get('title')} +{t.get('score')}成长值 "
                    f"({prog.get('daily_completed_count')}/{prog.get('daily_limit')})")
        return tasks

    # ---------- 抢大牌(独立模块, 参考联通抢兑) ----------
    def GetBrandCardInfo(self):
        """大牌券持有状态(BrandCardInfo)。

        pools[].type=1 表示已持有的通用大牌券; 抓包中该接口的
        has_inventory 反映的是卡券库存而非可抢名额, 抢兑判断请看
        GetExtraBrandCardPool。
        """
        d = self.rpc("SilkwormVip", "VipRightsService.BrandCardInfo", {
            "silk_id": self.silk_id, "include_card_summary": True})
        info = d.get("info") or {}
        pools = info.get("pools") or []
        if pools:
            log(f"[大牌] 持有状态: 今日已抢 {'是' if info.get('today_grabbed') else '否'}"
                f" | 今日 {info.get('user_day_num')} 次 | 本月 {info.get('user_month_num')} 次")
            for p in pools:
                log(f"  type={p.get('type')} {p.get('name')} "
                    f"(门槛{p.get('order_threshold')}元) 库存={p.get('has_inventory')}")
        return info

    def GetExtraBrandCardPool(self):
        """可抢的大牌券池(ExtraBrandCardPool) —— 真正的抢兑数据源。

        抓包实证: 该接口返回的通用大牌券 type=99 (limited_type=1),
        与 BrandCardInfo 里的 type=1 是两个不同券池:
          BrandCardInfo.type=1    已持有/可用的券
          ExtraBrandCardPool.type=99  可抢的券池(有 start_time 开抢时间)
        """
        d = self.rpc("SilkwormVip", "VipRightsService.ExtraBrandCardPool", {"silk_id": self.silk_id})
        info = d.get("info") or {}
        pools = info.get("pools") or []
        if pools:
            log(f"[大牌] 可抢券池 {len(pools)} 个 | 今日已抢 "
                f"{'是' if info.get('today_grabbed') else '否'} "
                f"| 今日 {info.get('user_day_num')} 次 | 本月 {info.get('user_month_num')} 次")
            for p in pools:
                st = "有库存" if p.get("has_inventory") else "无库存"
                t = ""
                if p.get("start_time"):
                    try:
                        t = " 开抢 " + time.strftime("%m-%d %H:%M:%S",
                                                     time.localtime(p["start_time"]))
                    except OSError:
                        pass
                log(f"  type={p.get('type')} {p.get('name')} "
                    f"(门槛{p.get('order_threshold')}元, limited_type={p.get('limited_type')}) "
                    f"{st}{t}")
        return info

    def HasExtraBrandCardPool(self):
        """是否有额外大牌券池(抓包返回 has=true)。"""
        d = self.rpc("SilkwormVip", "VipRightsService.HasExtraBrandCardPool", {"silk_id": self.silk_id})
        return bool(d.get("has"))

    def GetBrandCardExpiredTime(self, card_type=1):
        """已持有大牌券的过期时间。"""
        d = self.rpc("SilkwormVip", "VipRightsService.GetBrandCardExpiredTime",
                     {"silk_id": self.silk_id, "type": int(card_type)})
        ts = d.get("expired_at")
        if ts:
            log(f"[大牌] type={card_type} 券过期时间: "
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}")
        return ts

    def GetOwnedBrandCards(self):
        """查已持有的大牌券(card_types=[13,3], 抓包实证 card_type=13 即通用大牌券)。"""
        d = self.rpc("SilkwormCard", "SilkwormCardService.GetUserCardList", {
            "silk_id": self.silk_id, "status": 0, "offset": 0, "number": 1000,
            "card_types": [13, 3], "card_ids": None})
        lst = d.get("list") or []
        cards = []
        for it in lst:
            c = it.get("card") or {}
            if "大牌" in (c.get("name") or ""):
                cards.append(it)
                exp = it.get("expire_time")
                et = time.strftime("%m-%d %H:%M", time.localtime(exp)) if exp else "?"
                log(f"[大牌] 已持有: {c.get('name')} (card_type={c.get('card_type')}) 过期 {et}")
        if not cards:
            log("[大牌] 当前未持有大牌券")
        return cards

    def CountOwnedBrandCards(self):
        """卡包内大牌券数量(静默, 不打日志), 用于抢券前后对比核验。"""
        d = self.rpc("SilkwormCard", "SilkwormCardService.GetUserCardList", {
            "silk_id": self.silk_id, "status": 0, "offset": 0, "number": 1000,
            "card_types": [13, 3], "card_ids": None})
        return sum(1 for it in (d.get("list") or [])
                   if "大牌" in ((it.get("card") or {}).get("name") or ""))

    def GetUserTencentVipInfo(self):
        """腾讯 VIP 权益(含 grab_time/next_time, 抓包实证可用于判断抢券节奏)。"""
        d = self.rpc("SilkwormVip", "VipRightsService.UserTencentVipInfo", {"silk_id": self.silk_id})
        info = d.get("info") or {}
        if info:
            nt = info.get("next_time")
            nts = time.strftime("%m-%d %H:%M", time.localtime(nt)) if nt else "?"
            log(f"[腾讯VIP] 有额度={info.get('has_quota')} 可抢={info.get('available_count')} "
                f"抢过={info.get('grab_time')} 有库存={info.get('has_inventory')} 下次 {nts}")
        return info

    def BrandCardRpc(self, method, body, no_delay=False):
        """大牌券专用通道(JS BrandCardRpc 移植): APP 特征 + hzaiguojiang origin + 显式 SilkwormVip。

        11-28 实证: 抢券走普通小程序 rpc 通道会 HTTP 500 —— JS 原版用的是
        独立通道(x-platform: Android + origin/referer: gw.hzaiguojiang.com)。
        """
        headers = {**self.headers,
                   "origin": "https://gw.hzaiguojiang.com",
                   "referer": "https://gw.hzaiguojiang.com/",
                   "content-type": "application/json",
                   "servername": "SilkwormVip",
                   "methodname": method,
                   **self._sign_headers(self.teemo, "SilkwormVip", method)}
        try:
            code, data = self._post(headers, body)
            if code != 200:
                log(f"[ERROR] {method}: HTTP {code}")
                return {}
            return data
        except Exception as e:
            log(f"[ERROR] {method}: {e}")
            return {}
        finally:
            if not no_delay:
                time.sleep(self.interval)

    def HasExtraBrandCardPool(self):
        return self.BrandCardRpc("VipRightsService.HasExtraBrandCardPool", {"silk_id": self.silk_id})

    def ExtraBrandCardPoolRpc(self):
        return self.BrandCardRpc("VipRightsService.ExtraBrandCardPool", {"silk_id": self.silk_id})

    def GetServerTimeOffset(self):
        """服务器时钟偏差 ms(JS GetServerTimeOffset): 响应 Date 头校准开抢等待。"""
        try:
            t0 = time.time()
            r = self.HasExtraBrandCardPool()
            t1 = time.time()
            date_str = ""
            if r is not None and hasattr(r, "headers"):
                date_str = r.headers.get("Date") or r.headers.get("date") or ""
            if not date_str:
                self.server_offset_ms = 0
                return 0
            from email.utils import parsedate_to_datetime
            server_ms = parsedate_to_datetime(date_str).timestamp() + (t1 - t0) / 2
            self.server_offset_ms = int((server_ms - t1) * 1000)
            log(f"[大牌] 服务器时钟偏差 {self.server_offset_ms}ms")
            return self.server_offset_ms
        except Exception:
            self.server_offset_ms = 0
            return 0

    def GrabExtraBrandCard(self, btype):
        """抢券(JS GrabExtraBrandCard): body={"silk_id", "type"}。"""
        d = self.BrandCardRpc(BRAND_GRAB_METHOD, {"silk_id": self.silk_id, "type": int(btype)},
                              no_delay=True)
        card_id = ((d or {}).get("info") or {}).get("card_id")
        st = (d or {}).get("status") or {}
        log(f"[大牌] 抢券 type={btype} 返回: {json.dumps(st, ensure_ascii=False)[:120]}"
            + (f" card_id={card_id}" if card_id else ""))
        return d

    def BrandCardAuto(self):
        """大牌券抢兑主流程(JS BrandCardAuto 逐行对照移植)。

        判断逻辑照 JS 原版(字段是正确的, 与之前误判的 user_day_num 无关):
          has===false 跳过 / today_grabbed || is_grabbed 跳过 /
          无库存且已到开抢时间跳过 / 超等待上限放弃本次(绝不提前提交)
        """
        if not BRAND_ENABLE:
            log("[大牌] 未开启(XC_BRAND_ENABLE=false), 跳过")
            return False
        self.GetServerTimeOffset()
        a2 = self.HasExtraBrandCardPool()
        if a2 and a2.get("has") is False:
            log("[大牌] 没有额外券池, 跳过")
            return False
        a3 = self.ExtraBrandCardPoolRpc()
        a4 = (a3 or {}).get("info") or {}
        a5 = next((p for p in (a4.get("pools") or []) if int(p.get("type") or 0) == BRAND_TYPE), None)
        if not a5:
            log(f"[大牌] type={BRAND_TYPE} 未在券池中找到")
            return False
        if a4.get("today_grabbed") or a5.get("is_grabbed"):
            log(f"[大牌] type={BRAND_TYPE} 今日已领取, 跳过")
            return False
        before_cnt = self.CountOwnedBrandCards()
        start_ms = 1000 * (a5.get("start_time") or 0)
        now_ms = time.time() * 1000
        if a5.get("has_inventory") is False and (not start_ms or now_ms >= start_ms):
            log("[大牌] 暂无库存, 跳过")
            return False
        wait_ms = start_ms - now_ms - BRAND_BEFORE_MS - getattr(self, "server_offset_ms", 0)
        if wait_ms > BRAND_WAIT_MAX_MS:
            log(f"[大牌] 距开抢 {int(wait_ms / 1000)}s 超过最大等待 {BRAND_WAIT_MAX_MS // 1000}s, 放弃本次")
            return False
        # 连接预热(JS: 提前 2 发查询, 避免首包吃 TLS 建连延迟)
        for _ in range(2):
            try:
                self.ExtraBrandCardPoolRpc()
            except Exception:
                pass
        if wait_ms > 0:
            log(f"[大牌] 目标: {a5.get('name')} 等待 {wait_ms:.0f}ms 后抢券 "
                f"(offset={getattr(self, 'server_offset_ms', 0)}ms)")
            time.sleep(wait_ms / 1000)
        else:
            log(f"[大牌] 目标: {a5.get('name')} 已开放, 立即冲击")
        saved = self.interval
        self.interval = 0            # 抢兑窗口内零间隔(实例级, 不动全局)
        try:
            for i in range(1, BRAND_ATTEMPTS + 1):
                self.GrabExtraBrandCard(BRAND_TYPE)
                if i < BRAND_ATTEMPTS and BRAND_INTERVAL_MS > 0:
                    time.sleep(BRAND_INTERVAL_MS / 1000)
        finally:
            self.interval = saved
        log(f"[大牌] 已连发 {BRAND_ATTEMPTS} 包 (间隔 {BRAND_INTERVAL_MS}ms)")
        # 卡包核验
        after_cnt = self.CountOwnedBrandCards()
        if after_cnt > before_cnt:
            log(f"🎉 [大牌] 核验通过: 卡包新增 {after_cnt - before_cnt} 张大牌券")
            return True
        log(f"💔 [大牌] 卡包数量未变化({before_cnt} → {after_cnt}), 本次未抢到")
        return False

    def BrandCardGrabFlow(self, *_args, **_kw):
        """抢大牌主流程 —— 11-28 重写为 JS BrandCardAuto 移植版, 见 BrandCardAuto。"""
        return self.BrandCardAuto()

    # ---------- 元宝体系 ----------
    def CollectYbPoints(self):
        """领取待入账元宝。抓包实证: unreceived_points>0 时调 CollectPoints 即可入账。"""
        data = self.GetUserTaskV2()
        before = data.get("yb_point") or 0
        pending = data.get("unreceived_points") or 0
        log(f"[元宝] 余额 {before} 待领取 {pending}")
        if not pending:
            return before
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.CollectPoints", {"silk_id": self.silk_id})
        st = d.get("status") or {}
        if st.get("code") == 0:
            after = self.GetUserTaskV2()
            gained = (after.get("yb_point") or 0) - before
            log(f"[元宝] 领取 +{gained} → 余额 {after.get('yb_point') or 0}")
        else:
            log(f"[元宝] 领取失败: {st.get('msg', st.get('code'))}")
        return self.GetYbPoint()

    def GetUnreceivedPointRecords(self):
        """未领取积分明细(含即将过期的), 仅做提示。"""
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.GetUnReceivedPointRecords", {
            "silk_id": self.silk_id, "page": 1, "page_size": 20, "status": 1})
        point = d.get("point") or {}
        items = point.get("items") or []
        expiring = [i for i in items if i.get("will_expired")]
        if items:
            log(f"[未领积分] {len(items)} 条 共 {point.get('points')} 分"
                + (f"，其中 {len(expiring)} 条即将过期" if expiring else ""))
            for i in expiring[:5]:
                log(f"  即将过期: {i.get('task_name')} +{i.get('point')}")
        return items

    def GetPointTaskAwardProgress(self):
        """任务进度里程碑(3/5/8 个任务各领 500 分)。"""
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.GetPointTaskAwardProgress",
                     {"silk_id": self.silk_id})
        nodes = d.get("nodes") or []
        total = d.get("total_count") or 0
        done = d.get("completed_count") or 0
        avail = [n for n in nodes if n.get("available")]
        log(f"[任务里程碑] 已完成 {done}/{total} 个任务"
            + (f"，可领 {len(avail)} 个奖励" if avail else ""))
        for n in avail:
            log(f"  可领取: {n.get('task_count')}个任务 → {n.get('points')}分")
        return nodes

    def ListYbExchanges(self, ingot=None):
        """元宝兑换商品列表。ingot 传当前元宝余额(抓包实证该字段=余额, 非固定值)。"""
        new_level = 3
        is_plus = True
        if ingot is None:
            ingot = self.GetYbPoint()
        d = self.rpc("SilkwormCommunity", "SilkwormMobileCommunityService.ListExchangesV2", {
            "silk_id": self.silk_id, "new_level": new_level, "is_plus": is_plus,
            "ingot": int(ingot), "plus_only": False, "is_available": False})
        lst = d.get("list") or []
        log(f"[元宝兑换] 列表 {len(lst)} 项")
        for it in lst[:12]:
            log(f"  id={it.get('exchange_id')} {it.get('goods_name')} "
                f"价={it.get('community_silk')} 库存={it.get('daily_stock')} "
                f"限兑={it.get('user_quota_limit')}")
        return lst

    def ListYbFlashSaleExchanges(self):
        new_level = 3
        is_plus = True
        d = self.rpc("SilkwormCommunity", "SilkwormMobileCommunityService.ListFlashSaleExchanges", {
            "silk_id": self.silk_id, "is_plus": is_plus,
            "new_level": new_level,
            "user_id": int(self.userId) if self.userId.isdigit() else 0})
        items = []
        for group in ("vip", "svip"):
            for it in ((d.get("list") or {}).get(group) or []):
                it["yb_group"] = group
                items.append(it)
        items.sort(key=lambda x: (x.get("flash_sale_start_at") or 0, x.get("exchange_id") or 0))
        log(f"[元宝闪购] 列表 {len(items)} 项")
        for it in items[:12]:
            start = "-"
            if it.get("flash_sale_start_at"):
                try:
                    start = time.strftime("%m-%d %H:%M:%S", time.localtime(it["flash_sale_start_at"]))
                except OSError:
                    pass
            log(f"  闪购 {it.get('yb_group')} id={it.get('exchange_id')} {it.get('goods_name')} "
                f"价={it.get('community_silk')} left={it.get('flash_sale_stock', '?')} 开抢={start}")
        return items

    def ExchangeYbGoodsV2(self, exchange_id):
        d = self.rpc("SilkwormCommunity", "SilkwormMobileCommunityService.ExchangeGoodsV2", {
            "silk_id": self.silk_id, "exchange_id": int(exchange_id)})
        st = d.get("status")
        ok = (st or {}).get("code") == 0
        log(f"[元宝兑换] id={exchange_id} {'成功' if ok else '失败'}: "
            f"{json.dumps(st, ensure_ascii=False)[:100] if st else d}")
        return d

    def YbFlashSale(self):
        """元宝闪购抢兑(9:00 场)。日常流程里只查询展示, 抢兑在 shot 模式下单独跑。"""
        yb_now = self.CollectYbPoints()
        self.GetUnreceivedPointRecords()
        self.GetPointTaskAwardProgress()
        items = self.ListYbFlashSaleExchanges()
        self.ListYbExchanges(ingot=yb_now)
        return items

    def YbFlashSaleGrab(self):
        """元宝闪购抢兑主流程: 查列表 → 定位目标商品 → 等 9:00 → 冲击。

        目标商品由 XC_YB_GOODS_ID 指定(默认 200 = svip⚡️1元红包, 4000 元宝)。
        抢兑窗口内本账号零间隔(实例级, 不动全局 —— 并发账号不再互踩)。
        """
        saved = self.interval
        self.interval = 0
        try:
            return self._yb_flash_grab_inner()
        finally:
            self.interval = saved

    def _yb_flash_grab_inner(self):
        ids = [int(x) for x in re.split(r"[,，\s]+", YB_GOODS_ID) if x.strip().isdigit()]
        if not ids:
            log(f"[闪购] XC_YB_GOODS_ID 无效: {YB_GOODS_ID!r}")
            return False
        yb_now = self.GetYbPoint()
        self._yb_balance_cache = yb_now   # 供慢响应核验
        log(f"[闪购] 目标 {ids} | 当前元宝 {yb_now}")
        items = self.ListYbFlashSaleExchanges()
        for eid in ids:
            item = next((x for x in items if int(x.get("exchange_id") or 0) == eid), None)
            if not item:
                log(f"[闪购] id={eid} 不在闪购列表中")
                continue
            need = int(item.get("community_silk") or 0)
            log(f"[闪购] 目标: {item.get('goods_name')} 需 {need} 元宝")
            if yb_now < need:
                log(f"[闪购] 元宝不足({yb_now} < {need}), 跳过")
                continue
            start = item.get("flash_sale_start_at") or 0
            end = item.get("flash_sale_end_at") or 0
            now = time.time()
            if end and now > end:
                log(f"[闪购] id={eid} 已结束")
                continue
            if start and start > now:
                wait_s = start - time.time() - (BRAND_BEFORE_MS / 1000.0)
                if wait_s > BRAND_WAIT_MAX_MS / 1000.0:
                    log(f"[闪购] id={eid} 距开抢 {wait_s:.0f}s 超过最大等待 {BRAND_WAIT_MAX_MS // 1000}s, 放弃本次")
                    continue
                log(f"[闪购] 正在等待开抢... (剩余 {wait_s:.1f} 秒)")
                while (start - time.time() - (BRAND_BEFORE_MS / 1000.0)) > 1.0:
                    time.sleep(0.5)
                while (start - time.time() - (BRAND_BEFORE_MS / 1000.0)) > 0.0:
                    time.sleep(0.02)
                log("⚡ 已到开抢时间, 开始冲击")
            # 异步打击: 按 150ms 节奏持续投递, 不等响应, 成功即停
            if self.ExchangeYbGoodsAsync(eid):
                log(f"🎉 [闪购] 抢到 {item.get('goods_name')}!")
                return True
        log("[闪购] 未抢到")
        return False

    def ExchangeYbGoodsAsync(self, exchange_id):
        """元宝闪购异步打击: 不等响应, 每 BRAND_INTERVAL_MS 一发, 成功即停。"""
        from concurrent.futures import ThreadPoolExecutor
        import threading

        results = []
        lock = threading.Lock()
        stop = threading.Event()
        sent = {"n": 0}

        def fire(_):
            try:
                d = self.rpc("SilkwormCommunity",
                             "SilkwormMobileCommunityService.ExchangeGoodsV2",
                             {"silk_id": self.silk_id, "exchange_id": int(exchange_id)},
                             no_delay=True)
            except Exception as e:
                with lock:
                    results.append({"ok": False, "err": str(e)})
                return
            st = (d or {}).get("status") or {}
            with lock:
                results.append({"ok": st.get("code") == 0, "code": st.get("code"),
                                "msg": st.get("msg"), "raw": d})

        def success_found():
            with lock:
                return next((r for r in results if r.get("ok")), None)

        log(f"[闪购] 🚀 异步打击: 每 {BRAND_INTERVAL_MS:.0f}ms 一发, "
            f"最多 {BRAND_ATTEMPTS} 发, 不等响应")
        with ThreadPoolExecutor(max_workers=16) as ex:
            for i in range(1, BRAND_ATTEMPTS + 1):
                if stop.is_set():
                    break
                ex.submit(fire, i)
                sent["n"] = i
                hit = success_found()
                if hit:
                    stop.set()
                    log(f"🎉 [闪购] 兑换成功! "
                        f"{json.dumps(hit.get('raw'), ensure_ascii=False)[:150]}")
                    return True
                if i < BRAND_ATTEMPTS:
                    stop.wait(BRAND_INTERVAL_MS / 1000.0)
            if not stop.is_set():
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    hit = success_found()
                    if hit:
                        log(f"🎉 [闪购] 兑换成功!(延迟回收) "
                            f"{json.dumps(hit.get('raw'), ensure_ascii=False)[:150]}")
                        return True
                    with lock:
                        if len(results) >= sent["n"]:
                            break
                    time.sleep(0.05)
        with lock:
            codes = {}
            for r in results:
                k = r.get("code") if r.get("code") is not None else "ERR"
                codes[k] = codes.get(k, 0) + 1
        log(f"💔 [闪购] {sent['n']} 发全部未成功 | 分布: {codes}")
        # 慢响应兜底(P2-8): 全部未确认成功时查一次元宝余额变化, 判断是否实际兑换成功
        try:
            before = self._yb_balance_cache
            after = self.GetYbPoint()
            if before is not None and after is not None and after < before:
                log(f"🎉 [闪购] 慢响应核验: 元宝 {before}→{after}, 实际已兑换成功!")
                return True
        except Exception:
            pass
        return False

    def GetRedPackRainEventsByDate(self, date):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainEventsByDate", {
            "silk_id": self.silk_id,
            "city_code": int(self.city) if self.city.isdigit() else 0,
            "date": date})
        events = d.get("events") or []
        for e in events:
            t = "-"
            if e.get("time"):
                t = time.strftime("%H:%M:%S", time.localtime(e["time"]))
            log(f"[红包雨] 场次 id={e.get('event_id')} 时间={t} 状态={e.get('status')}")
        return events

    def GetRedPackRainHomeCurrentEvent(self):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainHomeCurrentEvent", {
            "silk_id": self.silk_id,
            "city_code": int(self.city) if self.city.isdigit() else 0})

    def GetRedPackRainEventInfo(self, event_id):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainEventInfo", {
            "silk_id": self.silk_id, "event_id": int(event_id),
            "city_code": int(self.city) if self.city.isdigit() else 0})

    def JoinRedPackRainEvent(self, event_id):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.JoinRedPackRainEvent", {
            "silk_id": self.silk_id, "event_id": int(event_id),
            "city_code": int(self.city) if self.city.isdigit() else 0})
        log(f"[红包雨] 报名 id={event_id} 返回: {json.dumps(d, ensure_ascii=False)[:120]}")
        return d

    def RedPackRainGrabNum(self, event_id, click_num):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.RedPackRainGrabNum", {
            "silk_id": self.silk_id, "event_id": int(event_id), "click_num": int(click_num)})
        item = (d.get("items") or [None])[0]
        if item:
            log(f"[红包雨] 抢包: {item.get('name')}:{item.get('prize_value')}")
        else:
            log(f"[红包雨] 抢包: {json.dumps(d.get('status') or {}, ensure_ascii=False)[:80]}")
        return d

    def IsRedPackRainAdViewed(self):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.IsAdViewed", {
            "silk_id": self.silk_id, "bus_type": 1})

    def OnRedPackRainAdViewed(self):
        sign, ts, nonce = ad_sign(self.silk_id, 1)
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.OnAdViewed", {
            "silk_id": self.silk_id, "timestamp": ts, "nonce": nonce,
            "bus_type": 1, "sign": sign})

    def AdRedPackRainLottery(self, click_num):
        sign, ts, nonce = ad_sign(self.silk_id, 1, extra=f"click_num={int(click_num)}")
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.AdRedPackRainLottery", {
            "silk_id": self.silk_id, "click_num": int(click_num),
            "timestamp": ts, "nonce": nonce, "bus_type": 1, "sign": sign})

    def RedPackRainAdAuto(self, click_num):
        if not RAIN_AD_ENABLE:
            return
        d0 = self.IsRedPackRainAdViewed()
        if d0.get("is_viewed") is True:
            log("[红包雨] 广告加奖已领取, 跳过")
            return
        d1 = self.OnRedPackRainAdViewed()
        if (d1.get("status") or {}).get("code") != 0:
            log("[红包雨] 广告确认失败")
            return
        d2 = self.AdRedPackRainLottery(click_num)
        prize = d2.get("prize")
        if (d2.get("status") or {}).get("code") == 0:
            log(f"[红包雨] 广告加奖: {prize.get('name') if prize else '无奖品'}")
        else:
            log(f"[红包雨] 广告加奖失败: {json.dumps(d2.get('status') or {}, ensure_ascii=False)[:80]}")

    def RedPackRainAuto(self):
        if not RAIN_ENABLE:
            log("[红包雨] 已关闭")
            return
        if self.red_pack_rain_done:
            log("[红包雨] 本次运行已完成, 跳过(防重复进入)")
            return
        click_num = RAIN_CLICK_NUM
        wait_max = 120.0
        before = 0.2
        join_after = 0.3
        fixed_event = 0
        today = time.strftime("%Y-%m-%d")
        events = self.GetRedPackRainEventsByDate(today)
        now = time.time()
        ev = None
        if fixed_event:
            ev = next((e for e in events if int(e.get("event_id") or 0) == fixed_event), None)
        if not ev:
            ev = next((e for e in events
                       if (e.get("time") or 0) <= now <= (e.get("end_time") or 0)
                       and int(e.get("status") or 0) != 3), None)
        if not ev:
            ev = next((e for e in events
                       if (e.get("time") or 0) >= now and int(e.get("status") or 0) != 3), None)
        if not ev:
            log("[红包雨] 今日无可参与场次")
            return
        start = ev.get("time") or 0
        end = ev.get("end_time") or 0
        if now > end:
            log(f"[红包雨] id={ev.get('event_id')} 已结束")
            return
        delay = start - now - before
        if delay > wait_max:
            log(f"[红包雨] id={ev.get('event_id')} 距开始 {int(delay)}s 超过最大等待, 跳过")
            return
        if delay > 0:
            log(f"[红包雨] id={ev.get('event_id')} 等待 {delay:.1f}s 后报名")
            time.sleep(max(delay, 0) + join_after)
        for poll in range(3):
            cur = self.GetRedPackRainHomeCurrentEvent()
            ce = cur.get("current_event") or {}
            if int(ce.get("event_id") or 0) == int(ev.get("event_id") or 0):
                ev["status"] = ce.get("status", ev.get("status"))
                if int(ce.get("status") or 0) == 2:
                    break
            if poll < 2:
                time.sleep(0.5)
        if ev.get("status") and int(ev["status"]) != 2:
            log(f"[红包雨] 尚未开场 status={ev.get('status')}, 不提前报名")
            return
        info = self.GetRedPackRainEventInfo(ev.get("event_id"))
        ue = (info or {}).get("user_event") or {}
        if ue.get("joined_event") is True:
            log(f"[红包雨] 已参与, 奖品数 {len(ue.get('items') or [])}")
            self.red_pack_rain_done = True
            self.RedPackRainAdAuto(click_num)
            return
        d = self.JoinRedPackRainEvent(ev.get("event_id"))
        joined = d.get("success") is True or (
            (d.get("status") or {}).get("code") == 0 and d.get("success") is not False)
        if not joined:
            info = self.GetRedPackRainEventInfo(ev.get("event_id"))
            ue = (info or {}).get("user_event") or {}
            if ue.get("joined_event") is True:
                log("[红包雨] 报名返回失败但服务端已记录, 继续抢包")
            else:
                log("[红包雨] 报名失败, 放弃")
                return
        self.RedPackRainGrabNum(ev.get("event_id"), click_num)
        # 抢包后复查实际所得(JS 行为): RedPackRainGrabNum 只回一包, 实际可能多包
        info2 = self.GetRedPackRainEventInfo(ev.get("event_id"))
        ue2 = (info2 or {}).get("user_event") or {}
        items = ue2.get("items") or []
        if items:
            log(f"[红包雨] 最终所得 {len(items)} 项: "
                + ", ".join(f"{(it.get('name') or '?')}x{it.get('prize_value') or '?'}" for it in items[:5]))
        self.red_pack_rain_done = True
        self.RedPackRainAdAuto(click_num)


# ---------- 主流程 ----------
def run_daily_account(u):
    """日常任务全流程(不含抢大牌)。"""
    if not HAS_CURL_CFFI:
        log("[WARN] 未安装 curl_cffi, TLS 指纹会被 WAF 拦截, 请先 pip install curl_cffi")

    info = u.GetUserInfo()
    if not u.ck_status:
        return False
    log(f"\n-------------账号{u.index}-------------")
    log(f"[INFO] 「{info.get('nickname', u.userName)}」登录成功!")

    u.RiskPhoneCheck()
    u.BindInviter()
    u.SignInLottery()
    u.SignInInfo()
    u.OpenBox()
    u.TakeGift()

    # 挑战赛: 报告进行中的进度, 可报名列表里有才报名
    u.ChallengeFlow()

    # 元宝: 领取待入账 + 列表/闪购
    u.YbFlashSale()

    # 拉任务列表(积分任务; 元宝抽奖/元宝兑换要按这份列表判断做没做)
    tasks = u.GetDailyTaskList()

    # 元宝抽奖: 只在「元宝抽奖」任务存在且未完成时才抽
    # (任务不存在也不抽 —— 抽了没任务加成, 纯扣元宝; JS 原版无此功能, 按"不发无效请求"原则处理)
    yb_task = next((t for t in tasks if (t.get("brief_title") or "").find("元宝抽奖") >= 0), None)
    yb_todo = False
    if yb_task:
        done = int(yb_task.get("completed_num") or 0)
        limit = int(yb_task.get("limit_num") or 0)
        yb_todo = bool(limit and done < limit)
        log(f"[元宝抽奖] 任务进度 {done}/{limit} → {'未完成, 去抽' if yb_todo else '已完成, 不抽'}")
    else:
        log("[元宝抽奖] 任务列表中无此项, 不抽(抽了无任务加成)")
    if yb_todo:
        yb_info = u.YbLotteryInfo()
        yb_cost = int((yb_info or {}).get("cost") or 0)
        if yb_cost and u.GetYbPoint() >= yb_cost:
            u.YbLottery()
        else:
            log(f"[元宝抽奖] 元宝不足或未取到消耗(需 {yb_cost})")

    # 成长值任务(展示, 看视频类无法脚本化)
    u.GetUpgradeTask()

    # 今日可兑商品(仅展示)
    u.TodayExchange()

    # 转盘抽奖次数任务: 先查 LotteryInfo, 只做 lottery_info 里标记为未完成的任务。
    # type 与 is_xxx 字段的对应(抓包 + 实测确认):
    #   type=8  浏览霸王餐页 (响应提示「浏览霸王餐页面限一次」→ 对应 is_view_bwc_page)
    #   type=9  浏览福利页
    #   type=10 看第三方广告
    #   type=11 浏览抖音商城 (实测响应提示同为「浏览霸王餐页面限一次」,
    #           疑似服务端文案未区分; 保留发送, 以实际加次数为准)
    #   type=2  分享 (if_shared)
    # type=3,5,6 不存在(请求参数错误), 不发。
    # 做完任务加次数后必须重新查 LotteryInfo(旧数据不含刚加的次数, 会少抽)
    li = u.GetLotteryInfo()
    info = (li or {}).get("lottery_info") or {}
    TYPE_BY_FLAG = {
        "is_view_bwc_page": 8,
        "is_view_welfare_page": 9,
        "is_view_tp_ad": 10,
        "is_view_douyin_mall": 11,
        "if_shared": 2,
    }
    todo = [(flag, t) for flag, t in TYPE_BY_FLAG.items() if not info.get(flag)]
    if todo:
        for flag, t in todo:
            ok, _ = u.AddLotteryTimes(t)
        # 关键: 做完任务后重新查 LotteryInfo, 否则用的是加次数前的旧数据(P2-5)
        li = u.GetLotteryInfo()
        info = (li or {}).get("lottery_info") or {}
    else:
        log("[抽奖次数] 所有任务今日已完成")

    # 抽奖: 用幸运次数(lucky_times)决定抽几次, 0 次就不发请求
    u.GetLotteryProgress()
    lucky = int((li.get("lottery_info") or {}).get("lucky_times") or 0)
    lucky = min(lucky, 6)     # 上限 6, 防呆
    if lucky:
        log(f"[抽奖] 幸运次数 {lucky}, 开始抽奖")
        for _ in range(lucky):
            u.Lottery()
    else:
        log("[抽奖] 无抽奖次数, 跳过")

    # 额外抽奖 ×2(进度接口显示宝箱可领才有意义, 先领再抽)
    for s in (1, 2):
        u.ReceiveExtraLottery(s)

    # 提现 (≥1 元)
    if IS_WALLET:
        balance = u.GetAgencyInfo()
        log(f"[INFO] 当前余额: {(balance or 0) / 100}")
        if balance and balance >= 1:
            u.ClientWithdraw(balance)

    # 红包雨(耗时, 放最后)
    u.RedPackRainAuto()

    # 资产汇总
    points = u.GetPoint()
    yb = u.GetYbPoint()
    cards = u.GetCard()
    red_packs = u.GetRedPackNum()
    u.GetUserMaxRedPack()
    log(f"[汇总] 积分:{points} 元宝:{yb} 红包:{red_packs} 卡券:{cards}")

    # 流水核对(确认今日任务奖励是否真的到账)
    u.GetUserPointHistory()
    return True


def main():
    global SUCCESS
    accounts = env_data()
    log(f"共 {len(accounts)} 个账号 | 模式: 微信小程序")
    tls = f"curl_cffi/{IMPERSONATE}" if HAS_CURL_CFFI else "标准requests(会被WAF拦)"
    log(f"请求间隔: {REQUEST_INTERVAL}s | TLS指纹: {tls}")
    if PROXY:
        log(f"代理: {PROXY}")

    # ---------- 抢兑模式判定(照联通写法: 一个 grab_mode 布尔变量) ----------
    # 两场抢兑:
    #   09:00 元宝闪购(svip 1元红包 4000元宝)  → cron 配 40 8 * * *
    #   09:30 大牌券(每天仅此一场)              → cron 配 20 9 * * *
    # 判定窗口放宽到"目标时间前 25 分钟内启动", 由脚本内部精确等待到开抢时刻。
    grab_mode = False
    grab_target = None
    now_lt = time.localtime()
    hour, current_min = now_lt.tm_hour, now_lt.tm_min
    if BRAND_ENABLE:
        now_minutes = hour * 60 + current_min
        # 元宝闪购: 8:40 ~ 9:05 之间启动都算(等待上限 10 分钟足够覆盖 8:57 启动)
        if 540 - 20 <= now_minutes <= 545:
            grab_mode = True
            grab_target = "yb"
        # 大牌券: 9:05 ~ 9:35 之间启动都算
        elif 545 < now_minutes <= 575:
            grab_mode = True
            grab_target = "brand"
    print("-" * 36)
    print(f"抢兑开关: {'开启' if BRAND_ENABLE else '关闭'}")
    if BRAND_ENABLE:
        print(f"  └─ 元宝闪购: {YB_FLASH_HOUR:02d}:{YB_FLASH_MIN:02d} "
              f"(商品 {YB_GOODS_ID})")
        print(f"  └─ 大牌券:   {BRAND_HOUR:02d}:{BRAND_MIN:02d}")
    print("-" * 36)
    print("")
    if grab_mode:
        label = "元宝闪购" if grab_target == "yb" else "大牌券"
        open_at = f"{YB_FLASH_HOUR:02d}:{YB_FLASH_MIN:02d}" if grab_target == "yb" \
            else f"{BRAND_HOUR:02d}:{BRAND_MIN:02d}"
        print(f"⏰ [自动触发] 检测到抢兑时间点 ({hour}:{current_min:02d})，进入并发抢兑模式")
        print(f"🚨🚨🚨 [抢兑模式已启动] 目标: {label} (开抢 {open_at}) 🚨🚨🚨")
        print("")
        from concurrent.futures import ThreadPoolExecutor

        def run_grab_task(u):
            try:
                info = u.GetUserInfo()
                if not u.ck_status:
                    return
                log(f"\n-------------账号{u.index} [抢{label}]-------------")
                log(f"[INFO] 「{info.get('nickname', u.userName)}」登录成功!")
                if grab_target == "yb":
                    u.YbFlashSaleGrab()
                else:
                    u.BrandCardGrabFlow()
            except Exception as e:
                log(f"抢兑异常: {e}")

        print(f"🚀 [并发模式] 启动 {len(accounts)} 个账号同时抢{label}...")
        with ThreadPoolExecutor(max_workers=max(1, len(accounts))) as executor:
            futures = [executor.submit(run_grab_task, XiaocanMiniUser(acc, i))
                       for i, acc in enumerate(accounts, 1)]
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    log(f"抢兑任务异常: {e}")
        log(f"\n共{len(accounts)}账号抢兑结束")
        dingtalk_send(f"{SCRIPT_NAME} 抢兑结束\n\n" + "\n".join(NOTIFY))
        return

    ok = 0
    for i, acc in enumerate(accounts, 1):
        try:
            u = XiaocanMiniUser(acc, i)
            if run_daily_account(u):
                ok += 1
        except Exception as e:
            log(f"[账号{i}] 异常: {e}")
    SUCCESS = ok
    log(f"\n共{len(accounts)}账号, 成功{ok}个, 失败{len(accounts) - ok}个")
    dingtalk_send(f"{SCRIPT_NAME} 运行结束\n\n" + "\n".join(NOTIFY))


if __name__ == "__main__":
    main()
