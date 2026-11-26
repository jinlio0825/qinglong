# -*- coding: utf-8 -*-
"""
任务名称
name: NodeSeek 每日签到
定时规则
cron: 23 8 * * *
==================================
NodeSeek 每日签到(纯 HTTP, 无浏览器)
==================================
原理:
  签到接口 POST /api/attendance?random=false, 靠登录态 Cookie 识别用户。
  实测(2026-11-26): 不带 cookie 返回 {"message":"USER NOT FOUND"},
  说明接口本身没有签名/风控头强校验(浏览器里的 preLogin 头只是
  附加风控数据, 缺失时服务端仅按未登录处理), curl_cffi 模拟浏览器
  TLS 指纹即可直连, 不需要 patchright/浏览器内核。

Cookie 获取(一次性, 手动):
  1. 浏览器登录 https://www.nodeseek.com
  2. F12 → Application → Cookies → 复制整段 Cookie 请求头
     (关键是 mmscriptor/Bearer 一类的会话 cookie, 整段复制最稳)
  3. 青龙环境变量 NODESEEK_COOKIE 填入, 多账号用 & 分隔
     (多账号时建议每段用不同浏览器的完整 cookie)

有效期: NodeSeek 会话 cookie 长期有效, 被登出/改密才需要重新抓。
依赖: pip3 install curl_cffi  (青龙 Python3 依赖里加)

环境变量:
  NODESEEK_COOKIE   必填, 完整 Cookie 请求头, 多账号 & 分隔
  NODESEEK_UA       可选, 与抓 cookie 时浏览器一致的 UA(默认 Chrome 134)
"""

import os, sys, time

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

try:
    from curl_cffi import requests as http
    HAS_CURL = True
except ImportError:
    HAS_CURL = False
    print("❌ 未安装 curl_cffi: 青龙依赖管理(Python3)里添加 curl_cffi")

ENV_COOKIE = "NODESEEK_COOKIE"
BASE = "https://www.nodeseek.com"
UA = os.getenv("NODESEEK_UA",
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_accounts():
    """解析环境变量: 整段 Cookie, 多账号 & 分隔"""
    raw = (os.getenv(ENV_COOKIE) or "").strip()
    if not raw:
        print(f"❌ 未设置环境变量 {ENV_COOKIE}")
        print("   格式: 浏览器 F12 复制的完整 Cookie 请求头, 多账号 & 分隔")
        return []
    accounts = []
    for i, item in enumerate(raw.split("&"), 1):
        c = item.strip()
        if c:
            accounts.append((i, c))
    print(f"📋 共加载 {len(accounts)} 个账号")
    return accounts


def checkin(cookie, idx):
    """签到一次。返回 (是否成功, 消息)。"""
    headers = {
        "user-agent": UA,
        "content-type": "application/json",
        "x-requested-with": "XMLHttpRequest",
        "origin": BASE,
        "referer": f"{BASE}/board",
        "cookie": cookie,
    }
    r = http.post(f"{BASE}/api/attendance?random=false",
                  headers=headers, impersonate="chrome", timeout=20, json={})
    if r.text:
        try:
            b = r.json()
        except Exception:
            b = {}
    else:
        b = {}
    msg = str(b.get("message") or b)
    if b.get("success") is True:
        return True, f"签到成功: {msg} (获得 {b.get('gain','?')} 鸡腿, 余额 {b.get('current','?')})"
    if "已签到" in msg or "already" in msg.lower() or "重复" in msg:
        return True, f"今日已签到过: {msg}"
    if "USER NOT FOUND" in msg or b.get("status") == 404:
        return False, "cookie 失效(USER NOT FOUND), 请重新抓取"
    return False, f"HTTP {r.status_code}: {msg[:120]}"


def main():
    if not HAS_CURL:
        sys.exit(1)
    accounts = load_accounts()
    if not accounts:
        sys.exit(1)

    results = []
    for idx, cookie in accounts:
        masked = f"账号{idx}(cookie...{cookie[-8:]})"
        print(f"\n{'='*50}")
        print(f"🟢 开始 {masked}")
        try:
            ok, msg = checkin(cookie, idx)
        except Exception as e:
            ok, msg = False, f"异常: {str(e)[:120]}"
        icon = "✅" if ok else "❌"
        log(f"{icon} {masked} {msg}")
        results.append((masked, ok, msg))
        if idx < len(accounts):
            time.sleep(5)  # 多账号间隔

    # ---------------- 汇总通知 ----------------
    ok_count = sum(1 for _, ok, _ in results if ok)
    lines = [f"NodeSeek 签到完成: {ok_count}/{len(results)}", ""]
    for masked, ok, msg in results:
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} {masked}")
        lines.append(f"   {msg}")
    summary = "\n".join(lines)
    print(f"\n{summary}")

    if hadsend:
        try:
            send(f"NodeSeek签到 {ok_count}/{len(results)}", summary)
            print("✅ 通知发送完成")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")

    sys.exit(0 if ok_count == len(results) else 1)


if __name__ == "__main__":
    main()
