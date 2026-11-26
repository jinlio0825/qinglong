#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 小蚕霸王餐
定时规则
cron: 10 8 * * *

==================================
小蚕霸王餐
==================================
小蚕 每日自动任务脚本，多账号支持，功能:

  登录验证 → 每日签到抽奖 → 开宝箱
  → 元宝领取 + 元宝闪购兑换(可配抢购) → 挑战赛自动报名
  → 日常任务×20 (含看广告加抽奖次数) → 抽奖×6 + 额外抽奖×2
  → 红包雨(自动选场次/等待开场/报名/抢包/广告加奖)
  → 余额≥1元 自动提现到支付宝(默认关)
  → 汇总推送钉钉机器人(可配)

 token 过期自动检测并钉钉提醒。
 依赖: pip install requests

---------- 双端模式 ----------
同一套 RPC 协议(网关/签名/token 完全一致), 伪装成两种客户端:
  mini (默认)   微信小程序特征: x-platform=mini, 微信 WebView UA,
                Referer=servicewechat.com, body 注入 app_id=20,
                默认请求间隔 3 秒(降低风控)
  app           安卓 APP 特征: x-platform=Android, xcapp UA, body 不带 app_id,
                默认请求间隔 1 秒
凭证两种模式通用(x-sivir token / x-teemo silk_id / x-vayne userId 不变),
抓 APP 或抓小程序的包都能用。

---------- 青龙面板使用 ----------
脚本管理新建 xc.py，环境变量添加:
  XCBWC_DATA   必填, 账号 JSON 数组(见下)
  其余变量选配, 不设走默认值

环境变量一览:
  XCBWC_DATA           账号数据, JSON 数组:
                       [{"userId":"123456","teemo":"1234567","token":"eyJ...","userName":"昵称"}, ...]
                       userId = x-vayne, teemo = x-teemo(silk_id), token = x-sivir, 抓包请求头复制即可
  XCBWC_PLATFORM       端模式: mini(默认)/app
  XCBWC_WALLET         true=余额≥1元自动提现支付宝, 默认 false 不提现
  XCBWC_INTERVAL       请求间隔秒数, mini 模式默认 3.0, app 模式默认 1.0
  XCBWC_BASE_URL       RPC 网关, 默认 https://gw.xiaocantech.com/rpc
  XCBWC_UA             User-Agent, mini 模式默认微信 WebView, app 模式默认 xcapp
  XCBWC_VERSION        x-version, mini 默认 3.22.9.93, app 默认 3.18.3.6
  XCBWC_REFERER        mini 模式 Referer, 默认 servicewechat.com/wx52ae177248081591/824
  XCBWC_MODEL          x-model, mini 默认 "PKR110 OnePlus", app 模式不设
  XCBWC_APP_SR         x-app-sr, mini 默认 20, app 模式默认不设
  XCBWC_CHANNEL        x-channel, 默认不设
  XCBWC_APP_ID         body 注入的 app_id, mini 默认 20
  XCBWC_DD_BOT_TOKEN   钉钉机器人 access_token, 不设不推送
  XCBWC_DD_BOT_SECRET  钉钉机器人加签密钥 SEC 开头
  XCBWC_YB_FLASH_IDS   元宝闪购要抢的 exchange_id, 逗号分隔, 不设只看列表不兑换
  XCBWC_YB_NEW_LEVEL   元宝闪购等级筛选, 默认 3
  XCBWC_YB_IS_PLUS     元宝闪购含 svip, 默认 true
  XCBWC_RAIN_CLICK_NUM 红包雨抢包点击次数, 默认 19
  XCBWC_RAIN_EVENT_ID  指定红包雨场次 id, 默认 0 自动选
  XCBWC_RAIN_ENABLE    false=关闭红包雨, 默认开
  XCBWC_RAIN_AD_ENABLE false=关闭红包雨广告加奖, 默认开
"""
import json
import os
import re
import time
import uuid
import base64
import hashlib
import hmac as hmac_mod
import random

# 网关启用腾讯云 WAF 的 TLS 指纹(JA3)校验, python requests 一律 403,
# 必须用 curl_cffi impersonate 浏览器指纹 (依赖: pip install curl_cffi)
try:
    from curl_cffi import requests as _curl_requests
    HTTP_IMPERSONATE = os.getenv("XCBWC_IMPERSONATE", "chrome")
except ImportError:
    _curl_requests = None
    HTTP_IMPERSONATE = None
import requests

BASE_URL = os.getenv("XCBWC_BASE_URL", "https://gw.xiaocantech.com/rpc")
# 端模式: mini=微信小程序(默认) / app=安卓APP
# 两者协议同一套(RPC 网关/签名/token 通用), 区别仅在请求头特征与 body 的 app_id 字段
PLATFORM = os.getenv("XCBWC_PLATFORM", "mini").strip().lower()
if PLATFORM == "mini":
    UA = os.getenv("XCBWC_UA",
          "Mozilla/5.0 (Linux; Android 16; PKR110 Build/AP3A.240617.008; wv) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/156.0.8078.79 "
          "Mobile Safari/537.36 XWEB/1560023 MMWEBSDK/20260902 MMWEBID/3250 "
          "MicroMessenger/8.0.80.3220(0x280050C7) WeChat/arm64 Weixin NetType/WIFI "
          "Language/zh_CN ABI/arm64 MiniProgramEnv/android")
    X_VERSION = os.getenv("XCBWC_VERSION", "3.22.9.93")
    REFERER = os.getenv("XCBWC_REFERER",
                        "https://servicewechat.com/wx52ae177248081591/824/page-frame.html")
    X_MODEL = os.getenv("XCBWC_MODEL", "PKR110 OnePlus")
    X_APP_SR = os.getenv("XCBWC_APP_SR", "20")
    X_CHANNEL = os.getenv("XCBWC_CHANNEL", "")
    APP_ID = int(os.getenv("XCBWC_APP_ID", "20"))
    DEFAULT_INTERVAL = 3.0     # 小程序模式默认 3 秒/请求(降低风控)
else:
    UA = os.getenv("XCBWC_UA",
          "Mozilla/5.0 (Linux; Android 15; PKR110 Build/AP3A.240617.008; wv) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.159 "
          "Mobile Safari/537.36 AgentWeb/5.0.8  UCBrowser/11.6.4.950  xcapp;3.18.3.6;Android")
    X_VERSION = os.getenv("XCBWC_VERSION", "3.18.3.6")
    REFERER = os.getenv("XCBWC_REFERER", "")
    X_MODEL = os.getenv("XCBWC_MODEL", "")
    X_APP_SR = os.getenv("XCBWC_APP_SR", "")        # 如 16 (3.22.x 抓包)
    X_CHANNEL = os.getenv("XCBWC_CHANNEL", "")      # 如 YYB
    APP_ID = 0                                      # APP 模式 body 不带 app_id
    DEFAULT_INTERVAL = 1.0
CITY_CODE = 4501                      # 挑战赛城市码
DEFAULT_CITY = "330109"
RECOMMEND_ID = 12159598643

IS_WALLET = os.getenv("XCBWC_WALLET", "false") != "false"
REQUEST_INTERVAL = float(os.getenv("XCBWC_INTERVAL", str(DEFAULT_INTERVAL)))

# 钉钉机器人 (不设则不发)
DD_BOT_TOKEN = os.getenv("XCBWC_DD_BOT_TOKEN", "")
DD_BOT_SECRET = os.getenv("XCBWC_DD_BOT_SECRET", "")
SCRIPT_NAME = "小蚕霸王餐"

AD_SIGN_KEY = "lcjkbqadfrzsewxy"

NOTIFY = []          # 通知消息
SUCCESS = 0          # 成功账号数


def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "ignore").decode("utf-8", "ignore"))
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
    """钉钉机器人 text 消息 (加签模式)。未配置 token/secret 则跳过。"""
    if not (DD_BOT_TOKEN and DD_BOT_SECRET):
        return
    ts = str(round(time.time() * 1000))
    sign = base64.b64encode(
        hmac_mod.new(DD_BOT_SECRET.encode(), f"{ts}\n{DD_BOT_SECRET}".encode(), hashlib.sha256).digest()
    ).decode()
    try:
        r = requests.post(
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
    raw = os.getenv("XCBWC_DATA", "")
    if not raw:
        for p in ("xcbwc_data.json", "accounts.json"):
            if os.path.exists(p):
                raw = open(p, encoding="utf-8").read()
                break
    if not raw:
        raise SystemExit("请设置环境变量 XCBWC_DATA=[{userId,teemo,token,userName},...]")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def ad_sign(silk_id, bus_type, extra=""):
    """看广告/红包雨抽奖的签名: HMAC-SHA256(key, silk_id=..&timestamp=..&nonce=..&bus_type=..) → Base64"""
    ts = int(time.time())
    nonce = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))
    if extra:
        msg = f"silk_id={silk_id}&{extra}&timestamp={ts}&nonce={nonce}"
    else:
        msg = f"silk_id={silk_id}&timestamp={ts}&nonce={nonce}&bus_type={bus_type}"
    mac = hmac_mod.new(AD_SIGN_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(mac).decode(), ts, nonce


class XiaocanUser:

    def __init__(self, acc, index):
        self.index = index
        self.userId = str(acc.get("userId", ""))
        self.teemo = str(acc.get("teemo") or acc.get("silk_id") or "")
        self.silk_id = int(self.teemo) if self.teemo.isdigit() else self.teemo
        self.token = acc.get("token") or acc.get("x-sivir") or ""
        self.userName = acc.get("userName") or self.userId
        self.city = str(acc.get("city") or DEFAULT_CITY)
        self.session_id = acc.get("sessionId") or str(uuid.uuid4())
        self.ck_status = True
        self.draw_status = True
        self.red_pack_rain_done = False
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "user-agent": UA,
            "content-type": "application/json; charset=utf-8",
            "x-teemo": self.teemo,
            "x-annie": "XC",
            "x-version": X_VERSION,
            "x-vayne": self.userId,
            "x-sivir": self.token,
            "x-platform": "mini" if PLATFORM == "mini" else "Android",
            "x-city": self.city,
            "x-session-id": self.session_id,
        }
        if PLATFORM == "mini":
            self.headers["referer"] = REFERER
        if X_MODEL:
            self.headers["x-model"] = X_MODEL
        if X_APP_SR:
            self.headers["x-app-sr"] = X_APP_SR
        if X_CHANNEL:
            self.headers["x-channel"] = X_CHANNEL

    # ---------- RPC ----------
    @staticmethod
    def _sign_headers(silk_id, server, method):
        ts = str(int(time.time() * 1000))
        u = uuid.uuid4().hex
        sid = str(silk_id)
        nami = u[:4] + sid + u[4:20 - len(sid) - 4]
        ashe = hashlib.md5(
            (hashlib.md5(f"{server}.{method}".lower().encode()).hexdigest() + ts + nami).encode()
        ).hexdigest()
        return {"x-ashe": ashe, "x-garen": ts, "x-nami": nami}

    def rpc(self, server, method, body):
        # 小程序模式: 所有 body 统一注入 app_id=20 (抓包实证, APP 模式不带)
        if PLATFORM == "mini" and isinstance(body, dict) and "app_id" not in body:
            body = {**body, "app_id": APP_ID}
        headers = {**self.headers, "servername": server, "methodname": method,
                   **self._sign_headers(self.teemo, server, method)}
        # TLS 指纹: 有 curl_cffi 用之(绕 WAF), 无则回落 requests(会被 403)
        send = _curl_requests.post if _curl_requests else requests.post
        kwargs = {"json": body, "headers": headers, "timeout": 20}
        if _curl_requests:
            kwargs["impersonate"] = HTTP_IMPERSONATE
        try:
            r = send(BASE_URL, **kwargs)
            if r.status_code != 200:
                log(f"[ERROR] {method}: HTTP {r.status_code}")
                return {}
            data = r.json()
            if is_cookie_expired(data) and not getattr(self, "_expired_notified", False):
                self._expired_notified = True
                self.ck_status = False
                name = self.userName or self.userId or f"账号{self.index}"
                msg = f"[{name}] Cookie 已过期，请重新登录更新 xcbwc_data"
                log(msg)
                dingtalk_send(f"{SCRIPT_NAME} Cookie 失效通知\n\n{msg}")
            return data
        except Exception as e:
            log(f"[ERROR] {method}: {e}")
            return {}
        finally:
            time.sleep(REQUEST_INTERVAL)

    def yb_rpc(self, server, method, body):
        """元宝社区通道: H5 头。小程序模式下 app_id 同样注入。"""
        if PLATFORM == "mini" and isinstance(body, dict) and "app_id" not in body:
            body = {**body, "app_id": APP_ID}
        headers = {**self.headers,
                   "origin": "https://gw.djtaoke.cn",
                   "referer": "https://gw.djtaoke.cn/",
                   "x-platform": "h5",
                   "x-version": "3.18.3",
                   "servername": server,
                   "methodname": method,
                   **self._sign_headers(self.teemo, server, method)}
        try:
            send = _curl_requests.post if _curl_requests else requests.post
            kwargs = {"json": body, "headers": headers, "timeout": 20}
            if _curl_requests:
                kwargs["impersonate"] = HTTP_IMPERSONATE
            r = send(BASE_URL, **kwargs)
            return r.json() if r.status_code == 200 else {}
        except Exception as e:
            log(f"[ERROR] {method}: {e}")
            return {}
        finally:
            time.sleep(REQUEST_INTERVAL)

    # ---------- 基础方法 ----------
    def GetUserInfo(self):
        d = self.rpc("Silkworm", "SilkwormService.GetClientUserInfo", {"silk_id": self.silk_id})
        if d.get("status", {}).get("code") != 0:
            self.ck_status = False
            log(f"[FAIL] 账号{self.index} token 失效: {d.get('status', {}).get('msg')}")
            return {}
        return d.get("user_info") or {}

    def GetPoint(self):
        d = self.rpc("ActivityTask", "ActivityTaskMobileService.UserTaskV2", {"silk_id": self.silk_id})
        return (d.get("data") or {}).get("point") or 0

    def GetRedPack(self):
        d = self.rpc("RedPackService", "RedPackService.GetAppRedPackList", {
            "silk_id": self.silk_id, "page_size": 1000, "page": 1})
        # 红包雨自动执行
        if os.getenv("XCBWC_RAIN_ENABLE", "true") != "false":
            self.RedPackRainAuto()
        return len(d.get("unused_items") or [])

    def GetCard(self):
        d = self.rpc("SilkwormCard", "SilkwormCardService.GetUserCardList", {
            "silk_id": self.silk_id, "status": 0})
        return len(d.get("list") or [])

    def GetDailyTask(self, task_type):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.AddLotteryTimes", {
            "silk_id": self.silk_id, "type": task_type})
        if (d.get("status") or {}).get("code") == 0:
            log(f"[任务] type={task_type} 完成, 抽奖次数+1")

    def OnAdViewed(self, bus_type):
        silk = int(self.teemo) if self.teemo.isdigit() else 0
        sign, ts, nonce = ad_sign(silk, bus_type)
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.OnAdViewed", {
            "silk_id": silk, "timestamp": ts, "nonce": nonce, "bus_type": bus_type, "sign": sign})
        if (d.get("status") or {}).get("code") == 0:
            log(f"[广告] bus_type={bus_type} 完成")

    def LotteryInfo(self):
        """转盘抽奖信息, lucky_times 是当前可用抽奖次数。"""
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.LotteryInfo", {"silk_id": self.silk_id})
        return d.get("lottery_info") or {}

    def Lottery(self):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.Lottery", {
            "silk_id": self.silk_id, "prize_type": 1})
        prize = d.get("prize")
        if prize:
            log(f"[抽奖] {prize.get('name')}")
        else:
            st = d.get("status", {})
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

    def ListNormalPromotionsByUser(self):
        d = self.rpc("SilkwormChallenge", "ChallengeService.ListNormalPromotionsByUser", {
            "city_code": CITY_CODE, "silk_id": self.silk_id})
        return d.get("promotions") or []

    def CreateUserPromotion(self, promotion_id, name=""):
        d = self.rpc("SilkwormChallenge", "ChallengeService.CreateUserPromotion", {
            "city_code": CITY_CODE, "promotion_id": promotion_id, "silk_id": self.silk_id})
        st = d.get("status", {})
        label = name or f"id={promotion_id}"
        log(f"[挑战赛] 报名「{label}」: {'OK' if st.get('code') == 0 else st.get('msg', st.get('code'))}")

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

    def SignInLottery(self):
        d = self.rpc("SilkwormVip", "VipRightsService.SignInLottery", {"silk_id": self.silk_id})
        data = d.get("data") or {}
        if data:
            score = (data.get("score") or 0) / 100
            prices = data.get("price") or []
            log(f"[签到] 成功! 奖 {score} 充值金" + (f" {prices[0]}元券" if prices else ""))
        else:
            st = d.get("status", {})
            log(f"[签到] {st.get('msg', st.get('code'))}")

    def BindInviter(self):
        self.rpc("InviteWord", "InviteWordService.BindInviter", {
            "inviter_silk_id": RECOMMEND_ID,
            "user_silk_id": self.silk_id,
        })

    # ---------- 元宝闪购 ----------
    def ListYbFlashSaleExchanges(self):
        new_level = int(os.getenv("XCBWC_YB_NEW_LEVEL", "3"))
        is_plus = os.getenv("XCBWC_YB_IS_PLUS", "true") != "false"
        d = self.yb_rpc("SilkwormCommunity", "SilkwormMobileCommunityService.ListFlashSaleExchanges", {
            "silk_id": self.silk_id, "is_plus": is_plus,
            "new_level": new_level, "user_id": int(self.userId) if self.userId.isdigit() else 0})
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
        d = self.yb_rpc("SilkwormCommunity", "SilkwormMobileCommunityService.ExchangeGoodsV2", {
            "silk_id": self.silk_id, "exchange_id": int(exchange_id)})
        st = d.get("status")
        log(f"[元宝兑换] id={exchange_id} 结果: {json.dumps(st, ensure_ascii=False)[:100] if st else d}")
        return d

    def CollectYbPoints(self):
        d = self.yb_rpc("ActivityTask", "ActivityTaskMobileService.UserTaskV2", {"silk_id": self.silk_id})
        data = d.get("data") or {}
        log(f"[元宝] 余额 {data.get('yb_point', 0)} 待领取 {data.get('unreceived_points', 0)}")
        if data.get("unreceived_points"):
            d2 = self.yb_rpc("ActivityTask", "ActivityTaskMobileService.CollectPoints", {"silk_id": self.silk_id})
            st = d2.get("status") or {}
            log(f"[元宝] 领取返回: {json.dumps(st, ensure_ascii=False)[:100]}")
            after = self.yb_rpc("ActivityTask", "ActivityTaskMobileService.UserTaskV2", {"silk_id": self.silk_id})
            log(f"[元宝] 领取后余额 {(after.get('data') or {}).get('yb_point', 0)}")

    def YbFlashSale(self):
        self.CollectYbPoints()
        ids = [int(x) for x in re.split(r"[,，\s]+", os.getenv("XCBWC_YB_FLASH_IDS", "")) if x.strip()]
        items = self.ListYbFlashSaleExchanges()
        if not ids:
            log("[元宝闪购] 未配置 XCBWC_YB_FLASH_IDS, 仅展示列表不兑换")
            return
        wait_max = float(os.getenv("XCBWC_YB_FLASH_WAIT_MAX_MS", "180000")) / 1000
        before = float(os.getenv("XCBWC_YB_FLASH_BEFORE_MS", "200")) / 1000
        attempts = max(1, int(os.getenv("XCBWC_YB_FLASH_ATTEMPTS", "3")))
        interval = float(os.getenv("XCBWC_YB_FLASH_INTERVAL_MS", "300")) / 1000
        for eid in ids:
            item = next((x for x in items if int(x.get("exchange_id") or 0) == eid), None)
            if not item:
                log(f"[闪购] id={eid} 不在列表中")
                continue
            start = item.get("flash_sale_start_at") or 0
            end = item.get("flash_sale_end_at") or 0
            now = time.time()
            if end and now > end:
                log(f"[闪购] id={eid} 已结束")
                continue
            delay = (start - now - before) if start else 0
            if delay > wait_max:
                log(f"[闪购] id={eid} 距开抢 {int(delay)}s 超过最大等待, 跳过")
                continue
            if delay > 0:
                log(f"[闪购] id={eid} 等待 {delay:.1f}s 后提交")
                time.sleep(delay)
            for att in range(1, attempts + 1):
                d = self.ExchangeYbGoodsV2(eid)
                if (d.get("status") or {}).get("code") == 0:
                    log(f"[闪购] id={eid} 第{att}次提交成功!")
                    break
                if att < attempts:
                    time.sleep(interval)

    # ---------- 红包雨 ----------
    def GetRedPackRainEventsByDate(self, date):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainEventsByDate", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0,
            "city_code": int(self.city) if self.city.isdigit() else 0,
            "date": date})
        events = d.get("events") or []
        for e in events:
            t = "-"
            if e.get("time"):
                t = time.strftime("%H:%M:%S", time.localtime(e["time"]))
            log(f"[红包雨] 场次 id={e.get('event_id')} 时间={t} 状态={e.get('status')}")
        return events

    def GetRedPackRainHomeCurrentEventV2(self):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainHomeCurrentEvent", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0,
            "city_code": int(self.city) if self.city.isdigit() else 0})

    def GetRedPackRainEventInfoV2(self, event_id):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.GetRedPackRainEventInfo", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0,
            "event_id": int(event_id),
            "city_code": int(self.city) if self.city.isdigit() else 0})

    def JoinRedPackRainEventV2(self, event_id):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.JoinRedPackRainEvent", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0,
            "event_id": int(event_id),
            "city_code": int(self.city) if self.city.isdigit() else 0})
        log(f"[红包雨] 报名 id={event_id} 返回: {json.dumps(d, ensure_ascii=False)[:120]}")
        return d

    def RedPackRainGrabNumV2(self, event_id, click_num):
        d = self.rpc("SilkwormLottery", "SilkwormLotteryMobile.RedPackRainGrabNum", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0,
            "event_id": int(event_id), "click_num": int(click_num)})
        item = (d.get("items") or [None])[0]
        log(f"[红包雨] 抢包: {item.get('name') + ':' + str(item.get('prize_value')) if item else json.dumps(d.get('status') or {}, ensure_ascii=False)[:80]}")
        return d

    def IsRedPackRainAdViewedV2(self):
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.IsAdViewed", {
            "silk_id": int(self.teemo) if self.teemo.isdigit() else 0, "bus_type": 1})

    def OnRedPackRainAdViewedV2(self):
        silk = int(self.teemo) if self.teemo.isdigit() else 0
        sign, ts, nonce = ad_sign(silk, 1)
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.OnAdViewed", {
            "silk_id": silk, "timestamp": ts, "nonce": nonce, "bus_type": 1, "sign": sign})

    def AdRedPackRainLotteryV2(self, click_num):
        silk = int(self.teemo) if self.teemo.isdigit() else 0
        sign, ts, nonce = ad_sign(silk, 1, extra=f"click_num={int(click_num)}")
        return self.rpc("SilkwormLottery", "SilkwormLotteryMobile.AdRedPackRainLottery", {
            "silk_id": silk, "click_num": int(click_num),
            "timestamp": ts, "nonce": nonce, "bus_type": 1, "sign": sign})

    def RedPackRainAdAuto(self, click_num):
        if os.getenv("XCBWC_RAIN_AD_ENABLE", "true") == "false":
            return
        d0 = self.IsRedPackRainAdViewedV2()
        if d0.get("is_viewed") is True:
            log("[红包雨] 广告加奖已领取, 跳过")
            return
        d1 = self.OnRedPackRainAdViewedV2()
        if (d1.get("status") or {}).get("code") != 0:
            log("[红包雨] 广告确认失败")
            return
        d2 = self.AdRedPackRainLotteryV2(click_num)
        prize = d2.get("prize")
        if (d2.get("status") or {}).get("code") == 0:
            log(f"[红包雨] 广告加奖: {prize.get('name') if prize else '无奖品'}")
        else:
            log(f"[红包雨] 广告加奖失败: {json.dumps(d2.get('status') or {}, ensure_ascii=False)[:80]}")

    def RedPackRainAuto(self):
        click_num = int(os.getenv("XCBWC_RAIN_CLICK_NUM", "19"))
        wait_max = float(os.getenv("XCBWC_RAIN_WAIT_MAX_MS", "120000")) / 1000
        before = float(os.getenv("XCBWC_RAIN_BEFORE_MS", "200")) / 1000
        join_after = float(os.getenv("XCBWC_RAIN_JOIN_AFTER_MS", "300")) / 1000
        fixed_event = int(os.getenv("XCBWC_RAIN_EVENT_ID", "0"))
        today = time.strftime("%Y-%m-%d")
        events = self.GetRedPackRainEventsByDate(today)
        now = time.time()
        ev = None
        if fixed_event:
            ev = next((e for e in events if int(e.get("event_id") or 0) == fixed_event), None)
        if not ev:
            ev = next((e for e in events if (e.get("time") or 0) <= now <= (e.get("end_time") or 0)
                       and int(e.get("status") or 0) != 3), None)
        if not ev:
            ev = next((e for e in events if (e.get("time") or 0) >= now
                       and int(e.get("status") or 0) != 3), None)
        if not ev:
            log("[红包雨] 今日无可参与场次")
            return
        start = (ev.get("time") or 0)
        end = (ev.get("end_time") or 0)
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
            cur = self.GetRedPackRainHomeCurrentEventV2()
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
        info = self.GetRedPackRainEventInfoV2(ev.get("event_id"))
        ue = (info or {}).get("user_event") or {}
        if ue.get("joined_event") is True:
            log(f"[红包雨] 已参与, 奖品数 {len(ue.get('items') or [])}")
            self.red_pack_rain_done = True
            self.RedPackRainAdAuto(click_num)
            return
        d = self.JoinRedPackRainEventV2(ev.get("event_id"))
        joined = d.get("success") is True or ((d.get("status") or {}).get("code") == 0 and d.get("success") is not False)
        if not joined:
            info = self.GetRedPackRainEventInfoV2(ev.get("event_id"))
            ue = (info or {}).get("user_event") or {}
            if ue.get("joined_event") is True:
                log("[红包雨] 报名返回失败但服务端已记录, 继续抢包")
            else:
                log("[红包雨] 报名失败, 放弃")
                return
        self.RedPackRainGrabNumV2(ev.get("event_id"), click_num)
        self.red_pack_rain_done = True
        self.RedPackRainAdAuto(click_num)

    def GetActivityTaskStatusV2(self):
        return self.yb_rpc("ActivityTask", "ActivityTaskMobileService.UserTaskV2", {"silk_id": self.silk_id})


# ---------- 主流程 ----------
def run_account(u):
    info = u.GetUserInfo()
    if not u.ck_status:
        return False
    log(f"\n-------------账号{u.index}-------------")
    log(f"[INFO] 「{info.get('nickname', u.userName)}」登录成功!")

    u.BindInviter()
    u.SignInLottery()
    u.OpenBox()
    u.YbFlashSale()

    # 挑战赛: 先拉可报名列表, 只报列表里实际存在的, 不写死 id
    try:
        promos = u.ListNormalPromotionsByUser()
        if not promos:
            log("[挑战赛] 当前无可报名的挑战")
        for p in promos:
            u.CreateUserPromotion(p.get("id"), p.get("name"))
    except Exception as e:
        log(f"[挑战赛] 异常: {e}")

    # 日常任务 ×20 (12/13 号位走广告)
    for t in range(1, 21):
        if t == 12:
            u.OnAdViewed(2)
        elif t == 13:
            u.OnAdViewed(4)
        else:
            u.GetDailyTask(t)

    # 抽奖: 用幸运次数决定抽几次, 0 次不发请求(与 xc_mini 一致)
    li = u.LotteryInfo()
    lucky = int((li or {}).get("lucky_times") or 0)
    if lucky:
        log(f"[抽奖] 幸运次数 {lucky}, 开始抽奖")
        for _ in range(min(lucky, 6)):
            u.Lottery()
    else:
        log("[抽奖] 无抽奖次数, 跳过")

    # 额外抽奖 ×2
    for s in (1, 2):
        u.ReceiveExtraLottery(s)

    # 提现 (≥1 元)
    if IS_WALLET:
        balance = u.GetAgencyInfo()
        log(f"[INFO] 当前余额: {(balance or 0) / 100}")
        if balance and balance >= 1:
            u.ClientWithdraw(balance)

    # 资产汇总 (红包雨在 GetRedPack 内自动触发)
    red_packs = u.GetRedPack()
    points = u.GetPoint()
    cards = u.GetCard()
    log(f"[汇总] 积分:{points} 红包:{red_packs} 卡票:{cards}")
    return True


def main():
    accounts = env_data()
    log(f"共 {len(accounts)} 个账号")
    ok = 0
    for i, acc in enumerate(accounts, 1):
        try:
            u = XiaocanUser(acc, i)
            if run_account(u):
                ok += 1
        except Exception as e:
            log(f"[账号{i}] 异常: {e}")
    log(f"\n共{len(accounts)}账号, 成功{ok}个, 失败{len(accounts) - ok}个")
    # 汇总推送钉钉
    dingtalk_send(f"{SCRIPT_NAME} 运行结束\n\n" + "\n".join(NOTIFY))


if __name__ == "__main__":
    main()
