# -*- coding: utf-8 -*-
"""
任务名称
name: 晓晓优选 每日签到
定时规则
cron: 16 7 * * *

晓晓优选每日任务

功能:
1. 能量商城签到 (POST /client/energy/mall/v2/signIn)
   └─ 档位递增: 第1天50, 每天+6左右(50→55→61→67→74→81→89)
   └─ 连续签到第7天额外获得能量宝箱(随机能量+晓晓红包)
   └─ 签到中断会重置连续天数, 脚本每日运行不会中断
2. 任务签到 (taskId=1, POST /signIn, 独立于商城签到, 两边都要签)
3. 分享任务 (taskId=2, 每日 1 次, +50能量)
4. 观看任务 (taskId=3, 每日 20 次, 每次+20能量)
5. 能量兑换 (默认关闭, 需设 XXYX_EXCHANGE_ENABLE=true)

依赖: pip install requests

环境变量:
    xxyx_token   必填, JSON 数组:
        [{"token":"xxx","username":"昵称","avatar":"头像URL"}, ...]

    token 获取方式: 用抓包工具抓 APP「我的」页面
        ^https://xxyx-client-api\\.xiaoxiaoyouxuan\\.com/my
        响应体里的 token 字段

兑换环境变量(可选, 不设则不兑换):
    XXYX_EXCHANGE_ENABLE    设为 true 开启兑换, 默认关闭
    XXYX_EXCHANGE_GOODS_ID  兑换的商品ID, 默认 1 (晓晓红包·1元)

    可兑换商品(以脚本实际拉取为准):
        1  = 晓晓红包·1元   1000能量  日限1 (经常售罄, 售罄自动跳过)
        17 = 明日预购券      500能量  日限5
        4  = 延迟上传券      800能量  日限1
        10 = 提前抢单券     1000能量  日限1
        11 = 超时复活券     5000能量  日限1

    兑换前置检查: 商品存在 → 未售罄 → 能量余额充足, 任一不满足自动跳过。
    兑换发生在所有任务完成之后(先攒当日能量再兑换)。

示例(开启兑换, 兑换红包):
    export XXYX_EXCHANGE_ENABLE="true"
    export XXYX_EXCHANGE_GOODS_ID="1"
"""

import json
import os
import random
import sys
import time

import requests

ENV_NAME = "xxyx_token"
BASE_URL = "https://xxyx-client-api.xiaoxiaoyouxuan.com"
APP_VERSION = "20480"
APP_UA = "XiaoXiaoYouXuan/20480 CFNetwork/3826.400.120 Darwin/24.3.0"
# 请求间隔（秒）。观看任务 20 次 + 签到 + 分享 + 2 次列表查询 ≈ 24 个请求，
# 间隔 8s 时全程约 3.2 分钟，比 APP 真人速度还慢，降低风控风险
REQUEST_INTERVAL = 8.0


def log(msg):
    print(msg, flush=True)


def build_headers(token, with_time=True):
    """构造通用请求头。签到接口需要 xx-time，其余不需要。"""
    headers = {
        "xx-token": token,
        "xx-version": APP_VERSION,
        "xx-platform": "ios",
        "User-Agent": APP_UA,
        "Content-Type": "application/json;charset=utf-8",
        "Host": "xxyx-client-api.xiaoxiaoyouxuan.com",
    }
    if with_time:
        headers["xx-time"] = str(int(time.time() * 1000))
    return headers


def parse_accounts():
    """解析环境变量里的账号 JSON 数组。"""
    raw = (os.getenv(ENV_NAME) or "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except ValueError as exc:
        log(f"❌ {ENV_NAME} 不是合法 JSON: {exc}")
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        log(f"❌ {ENV_NAME} 应为 JSON 数组")
        return []

    accounts = []
    for item in data:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if not token:
            continue
        accounts.append({
            "token": token,
            "username": item.get("username") or "未知用户",
            "avatar": item.get("avatar") or "",
        })
    return accounts


def get_task_list(token):
    """拉取每日任务列表，失败返回 None。"""
    url = f"{BASE_URL}/client/energy/mall/getTaskList?platform=ios"
    try:
        resp = requests.get(url, headers=build_headers(token), timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 获取任务列表失败! {exc}")
        return None

    if body.get("success"):
        return body.get("data") or []
    log(f"🔴 获取任务列表失败: {body.get('message') or body}")
    return None


def get_sign_info(token):
    """新版签到信息：todaySignIn / todayEnergy / continuousDays，用于日志核对。"""
    url = f"{BASE_URL}/client/energy/mall/v2/info?platform=ios"
    try:
        resp = requests.get(url, headers=build_headers(token), timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError):
        return None
    return body.get("data") if body.get("success") else None


def sign_in(token):
    """每日签到（任务体系签到，档位低）。"""
    url = f"{BASE_URL}/client/energy/mall/signIn"
    try:
        resp = requests.post(
            url, headers=build_headers(token), json={"platform": "ios"}, timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 签到请求失败! {exc}")
        return False

    msg = body.get("message") or body.get("success")
    if body.get("success"):
        log(f"   任务签到成功: {msg}")
    else:
        log(f"   任务签到: {msg or '今日已签过'}")
    return bool(body.get("success"))


def sign_in_v2(token):
    """能量商城日历签到（v2 体系，档位递增 50/55/61...，第7天有宝箱）。

    与上面的 signIn 是两个独立签到，都要做。
    """
    url = f"{BASE_URL}/client/energy/mall/v2/signIn"
    try:
        resp = requests.post(
            url, headers=build_headers(token), json={"platform": "ios"}, timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 商城签到请求失败! {exc}")
        return False

    ok = bool(body.get("success"))
    msg = body.get("msg") or body.get("message") or ""
    info = get_sign_info(token)
    if ok:
        energy = (info or {}).get("todayEnergy")
        days = (info or {}).get("continuousDays")
        nxt = next((d.get("energyValue") for d in (info or {}).get("calendars") or []
                    if d.get("dayIndex") == (info or {}).get("currentDayIndex", 0) + 1), None)
        extra = f"，明日+{nxt}" if nxt else ""
        log(f"🟢 商城签到成功: +{energy}能量, 连续{days}天{extra}")
        if (info or {}).get("boxObtained"):
            log("🎁 第7天能量宝箱已领取!")
    elif "已签到" in str(msg) or "已经签到" in str(msg):
        log("🟢 商城签到: 今日已签过")
    else:
        log(f"⚠️ 商城签到响应: {msg}")
    return ok


def get_goods_list(token):
    """能量商城兑换商品列表，返回 [(id, 名称, 价格, 已售罄, 日限)] 或 None。"""
    url = f"{BASE_URL}/client/energy-goods/list?type=0&page=1&limit=20"
    try:
        resp = requests.get(url, headers=build_headers(token), timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 获取商品列表失败! {exc}")
        return None
    if not body.get("success"):
        log(f"🔴 获取商品列表失败: {body.get('msg') or body}")
        return None
    result = []
    for g in (body.get("data") or {}).get("list") or []:
        result.append({
            "id": g.get("id"),
            "name": g.get("name") or f"商品{g.get('id')}",
            "price": int(g.get("price") or 0),
            "sold_out": bool(g.get("isSoldOut")),
            "daily_limit": g.get("dailyLimit"),
        })
    return result


def exchange_goods(token, goods_id):
    """兑换指定商品，返回是否成功。"""
    url = f"{BASE_URL}/client/energy/mall/placeOrder"
    try:
        resp = requests.post(
            url, headers=build_headers(token), json={"goodsId": int(goods_id)}, timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 兑换请求失败! {exc}")
        return False
    ok = bool(body.get("success"))
    if ok:
        log(f"✅ 兑换成功: goodsId={goods_id}")
    else:
        log(f"🔴 兑换失败(goodsId={goods_id}): {body.get('msg') or body.get('message') or body}")
    return ok


def exchange_flow(token):
    """能量兑换流程：由环境变量控制，默认关闭。

    XXYX_EXCHANGE_ENABLE=true 开启
    XXYX_EXCHANGE_GOODS_ID  商品ID，默认 1（晓晓红包·1元，1000能量）
    商品列表参考:
        1  = 晓晓红包·1元  (1000能量, 日限1)
        17 = 明日预购券    (500能量,  日限5)
        4  = 延迟上传券    (800能量,  日限1)
        10 = 提前抢单券    (1000能量, 日限1)
        11 = 超时复活券    (5000能量, 日限1)
    """
    if os.getenv("XXYX_EXCHANGE_ENABLE", "").strip().lower() != "true":
        return
    goods_id = os.getenv("XXYX_EXCHANGE_GOODS_ID", "").strip() or "1"
    goods_list = get_goods_list(token)
    target = None
    if goods_list:
        for g in goods_list:
            if str(g["id"]) == str(goods_id):
                target = g
                break
        if target is None:
            log(f"⚠️ 未找到 goodsId={goods_id}，可选商品: " +
                ", ".join(f"{g['id']}={g['name']}({g['price']}能量)" for g in goods_list))
            return
        if target["sold_out"]:
            log(f"⏭️ {target['name']} 今日已售罄, 跳过兑换")
            return
        # 余额检查
        bal = get_user_energy(token)
        if bal is not None and bal < target["price"]:
            log(f"⏭️ 能量不足: 当前{bal} < 需要{target['price']}, 跳过兑换 {target['name']}")
            return
        log(f"🟢 开始兑换: {target['name']} ({target['price']}能量)")
    else:
        log("⚠️ 商品列表获取失败, 仍按 goodsId 尝试兑换")
    exchange_goods(token, goods_id)


def get_user_energy(token):
    """查询当前能量余额，失败返回 None。"""
    url = f"{BASE_URL}/client/energy/mall/getUserEnergy?platform=ios"
    try:
        resp = requests.get(url, headers=build_headers(token), timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError):
        return None
    data = body.get("data") if body.get("success") else None
    try:
        return int((data or {}).get("energy"))
    except (TypeError, ValueError):
        return None


def complete_task(token, task_id):
    """完成一次任务（分享/观看），返回是否成功。"""
    url = f"{BASE_URL}/client/energy/mall/completeTask/{task_id}"
    try:
        resp = requests.post(
            url,
            headers=build_headers(token, with_time=False),
            json={"taskId": task_id, "platform": "ios"},
            timeout=20,
        )
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 完成任务[{task_id}]请求失败! {exc}")
        return False

    ok = bool(body.get("success"))
    if not ok:
        log(f"   任务[{task_id}]响应: {body.get('message') or body}")
    return ok


def run_account(account, index):
    """跑单个账号的全部任务，返回本次获得的能量。"""
    token = account["token"]
    username = account["username"]
    energy = 0

    log(f"\n-------------账号{index} [{username}]-------------")

    task_list = get_task_list(token)
    if not task_list:
        log("🔴 任务列表为空，跳过该账号")
        return 0

    # 0) 能量商城日历签到（v2，独立于任务列表的签到）
    log("🟢 开始[能量商城签到]...")
    if sign_in_v2(token):
        energy += int((get_sign_info(token) or {}).get("todayEnergy") or 0)
    time.sleep(REQUEST_INTERVAL + random.uniform(0, 4))

    for task in task_list:
        task_id = task.get("taskId")
        task_name = task.get("taskName") or f"任务{task_id}"
        energy_base = int(task.get("energyBase") or 0)

        # 1) 每日签到
        if task_id == 1:
            log(f"🟢 开始[{task_name}]...")
            if sign_in(token):
                energy += energy_base
            time.sleep(REQUEST_INTERVAL + random.uniform(0, 4))
            continue

        # 2)/3) 分享、观看：按剩余次数循环（只做无需真实消费的任务）
        if task_id in (2, 3):
            remaining = int(task.get("dailyCount") or 0) - int(task.get("completedTimes") or 0)
            log(f"🟢 开始[{task_name}]... 待完成 {remaining} 次")
            if remaining <= 0:
                log(f"   任务[{task_id}]已经完成")
                continue
            for _ in range(remaining):
                if complete_task(token, task_id):
                    energy += energy_base
                time.sleep(REQUEST_INTERVAL + random.uniform(0, 4))
            continue

        # 其他任务（订单/邀请等需要真实消费或拉新）不碰
        log(f"⏭️ 跳过[{task_name}] (taskId={task_id}, 需真实下单/拉新)")

    # 能量兑换（默认关闭，XXYX_EXCHANGE_ENABLE=true 开启）
    try:
        exchange_flow(token)
    except Exception as exc:
        log(f"⚠️ 兑换流程异常: {exc}")

    log(f"✅ [{username}] 本次共获得 {energy} 能量")
    return energy


def notify(message):
    """青龙自带 sendNotify；本地无此模块时静默跳过。"""
    try:
        from notify import send
    except ImportError:
        try:
            from sendNotify import send
        except ImportError:
            log(message)
            return
    try:
        send("晓晓优选签到", message)
    except Exception as exc:
        log(f"推送失败: {exc}")
        log(message)


def main():
    accounts = parse_accounts()
    if not accounts:
        notify("❌ 请先获取晓晓优选 token（环境变量 fmz200_xxyx_token）")
        return 1

    log(f"共 {len(accounts)} 个账号")
    results = []
    for index, account in enumerate(accounts, 1):
        try:
            energy = run_account(account, index)
            results.append((account["username"], energy))
        except Exception as exc:
            log(f"❌ 账号{index} 异常: {exc}")
            results.append((account.get("username", f"账号{index}"), 0))

    summary = "\n".join(f"[{name}]获得{energy}能量" for name, energy in results)
    notify(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
