# -*- coding: utf-8 -*-
"""
任务名称
name: 晓晓优选 每日签到
定时规则
cron: 16 7 * * *

晓晓优选每日任务（原 xxyx_signin.js 的 Python 版）

功能:
1. 每日签到 (taskId=1)
2. 分享任务 (taskId=2, 每日 1 次)
3. 观看任务 (taskId=3, 每日 20 次)

依赖: pip install requests

环境变量:
    fmz200_xxyx_token   必填, JSON 数组:
        [{"token":"xxx","username":"昵称","avatar":"头像URL"}, ...]

    token 获取方式: 用抓包工具抓 APP「我的」页面
        ^https://xxyx-client-api\\.xiaoxiaoyouxuan\\.com/my
        响应体里的 token 字段
"""

import json
import os
import random
import sys
import time

import requests

ENV_NAME = "fmz200_xxyx_token"
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


def sign_in(token):
    """每日签到，返回是否成功。"""
    url = f"{BASE_URL}/client/energy/mall/signIn"
    try:
        resp = requests.post(
            url, headers=build_headers(token), json={"platform": "ios"}, timeout=20)
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"🔴 签到请求失败! {exc}")
        return False

    log(f"   签到响应: {body.get('message') or body.get('success')}")
    return bool(body.get("success"))


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
