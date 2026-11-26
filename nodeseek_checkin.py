# -*- coding: utf-8 -*-
"""
任务名称
name: NodeSeek 每日签到
定时规则
cron: 23 8 * * *
"""

import os, sys, time, json, hashlib
from patchright.sync_api import sync_playwright

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# ---------------- 环境变量 ----------------
# NodeSeek 账号：账号#密码 连接，多账号用 & 连接
# 示例：awemagisi@gmail.com#zxc.123456&test@qq.com#abc123456
ENV_ACCOUNT = "NODESEEK_ACCOUNT"

BASE = "https://www.nodeseek.com"
PROFILE_ROOT = os.path.join(os.path.expanduser("~"), ".nodeseek_profile")


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_accounts():
    """解析环境变量：账号#密码，多账号 & 连接"""
    raw = (os.getenv(ENV_ACCOUNT) or "").strip()
    if not raw:
        print(f"❌ 未设置环境变量 {ENV_ACCOUNT}")
        print(f"   格式：账号#密码，多账号用 & 连接")
        print(f"   示例：export {ENV_ACCOUNT}=\"user@qq.com#pass1&user2@gmail.com#pass2\"")
        return []
    accounts = []
    for i, item in enumerate(raw.split("&"), 1):
        item = item.strip()
        if not item:
            continue
        if "#" not in item:
            print(f"⚠️  第 {i} 个账号格式错误（缺少 # 分隔）：{item[:6]}***")
            continue
        email, password = item.split("#", 1)
        email, password = email.strip(), password.strip()
        if email and password:
            accounts.append((email, password))
        else:
            print(f"⚠️  第 {i} 个账号账号或密码为空，已跳过")
    print(f"📋 共加载 {len(accounts)} 个账号")
    return accounts


def profile_dir(email):
    """每个账号独立的登录态目录（用邮箱 md5 命名，避免特殊字符问题）"""
    return os.path.join(PROFILE_ROOT, hashlib.md5(email.encode()).hexdigest()[:16])


def pass_cf(page, timeout_ms=180000):
    """等 Cloudflare 挑战放行（标志：页面标题含 NodeSeek）。"""
    page.wait_for_function("() => document.title.includes('NodeSeek')", timeout=timeout_ms)
    page.wait_for_timeout(3000)


def api_post(page, path, body=None, query=""):
    """页面上下文内调用站点 API，自动带上 preLogin 风控头。"""
    return page.evaluate("""async ([path, query, body]) => {
        const mod = await import('/assets/preLogin-fiEAKL_6.js');
        const h = mod.g ? await mod.g() : {};
        const resp = await fetch(path + query, {
            method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/json',
                      'X-Requested-With': 'XMLHttpRequest', ...h},
            body: body ? JSON.stringify(body) : undefined
        });
        return {status: resp.status, body: await resp.json().catch(() => null)};
    }""", [path, query, body])


def try_checkin(page):
    page.goto(f"{BASE}/board", timeout=60000)
    pass_cf(page)
    r = api_post(page, "/api/attendance", query="?random=false")
    b = r.get("body") or {}
    msg = str(b.get("message") or b)
    if b.get("success") is True:
        return "ok", f"签到成功：{msg}（获得 {b.get('gain','?')} 鸡腿，余额 {b.get('current','?')}）"
    if "已签到" in msg or "already" in msg.lower() or "重复" in msg:
        return "ok", f"今日已签到过：{msg}"
    if "USER NOT FOUND" in msg or r["status"] in (401, 404):
        return "not_logged_in", msg
    return "fail", f"HTTP {r['status']}: {msg}"


def do_login(page, email, password):
    """账号密码登录；若站点要求邮箱动态验证则直接调用 emailSignIn 提交。"""
    log("未登录，开始自动登录 ...")
    page.goto(f"{BASE}/signIn.html", timeout=60000)
    pass_cf(page)
    r = api_post(page, "/api/account/signIn",
                 body={"username": email, "password": password})
    log(f"signIn: {r['status']} {json.dumps(r.get('body'), ensure_ascii=False)[:150]}")
    if (r.get("body") or {}).get("success") is not True:
        # 若被要求邮箱动态验证，取一个新验证码并提交
        log("需要邮箱动态验证，自动发码 ...")
        import urllib.parse
        page.goto(f"{BASE}/emailSignIn.html?email={urllib.parse.quote(email)}", timeout=60000)
        pass_cf(page)
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('[name=cf-turnstile-response]')).some(e => e.value)",
            timeout=90000)
        r2 = page.evaluate("""async ([email]) => {
            const mod = await import('/assets/preLogin-fiEAKL_6.js');
            const h = mod.g ? await mod.g() : {};
            const token = Array.from(document.querySelectorAll('[name=cf-turnstile-response]'))
                .find(e => e.value)?.value;
            const resp = await fetch('/api/email', {
                method: 'POST', credentials: 'include',
                headers: {'Content-Type': 'application/json', ...h},
                body: JSON.stringify({email, mode: 'totp',
                                      token, source: 'turnstile', version: 'v3'})
            });
            return {status: resp.status, body: await resp.json().catch(() => null)};
        }""", [email])
        log(f"发码: {r2['status']} {json.dumps(r2.get('body'), ensure_ascii=False)}")
        if (r2.get("body") or {}).get("success") is not True:
            return False, f"发码失败: {r2.get('body')}"
        # 验证码通过邮件发送，自动模式下无法读取邮箱内容
        return False, "需要邮箱验证码（登录态已失效且需重新验证设备）"
    return True, "登录成功"


def launch_ctx(p, email):
    """按账号启动持久化浏览器上下文。

    headless 自动判断：有环境变量 NODESEEK_HEADLESS 用它；
    否则有显示器（桌面）时有头（过盾更稳），无显示器（服务器）时无头。
    chrome 渠道不存在时自动回退内置 chromium。
    """
    headless_env = os.getenv("NODESEEK_HEADLESS", "").strip().lower()
    if headless_env in ("true", "false"):
        headless = headless_env == "true"
    else:
        headless = not os.environ.get("DISPLAY")
    channel = os.getenv("NODESEEK_CHANNEL", "chrome").strip() or None
    args = ["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]
    if not headless:
        args.append("--window-position=-32000,-32000")
    kwargs = dict(user_data_dir=profile_dir(email), headless=headless,
                  args=args, no_viewport=True)
    if channel:
        try:
            return p.chromium.launch_persistent_context(channel=channel, **kwargs)
        except Exception as e:
            log(f"⚠️  chrome 渠道启动失败（{str(e)[:80]}），回退内置 chromium")
    return p.chromium.launch_persistent_context(**kwargs)


def run_account(email, password, idx, total):
    """跑单个账号，返回 (是否成功, 结果消息)"""
    masked = email[:3] + "***" + email[email.find("@"):] if "@" in email else email[:3] + "***"
    print(f"\n{'='*50}")
    print(f"🟢 开始账号 [{idx}/{total}]：{masked}")
    print(f"{'='*50}")
    try:
        with sync_playwright() as p:
            ctx = launch_ctx(p, email)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                result, msg = try_checkin(page)
                if result == "not_logged_in":
                    ok, login_msg = do_login(page, email, password)
                    if not ok:
                        log(f"❌ 登录失败: {login_msg}")
                        return False, f"登录失败: {login_msg}"
                    result, msg = try_checkin(page)
                icon = "✅" if result == "ok" else "❌"
                log(f"{icon} {masked} {msg}")
                return result == "ok", msg
            finally:
                ctx.close()
    except Exception as e:
        log(f"❌ 账号异常: {str(e)[:150]}")
        return False, f"异常: {str(e)[:100]}"


def main():
    accounts = load_accounts()
    if not accounts:
        sys.exit(1)

    results = []
    for idx, (email, password) in enumerate(accounts, 1):
        ok, msg = run_account(email, password, idx, len(accounts))
        masked = email[:3] + "***" + email[email.find("@"):] if "@" in email else email[:3] + "***"
        results.append((masked, ok, msg))
        if idx < len(accounts):
            time.sleep(5)  # 多账号间隔，降低风控风险

    # ---------------- 汇总通知 ----------------
    ok_count = sum(1 for _, ok, _ in results if ok)
    lines = [f"NodeSeek 签到完成：{ok_count}/{len(results)}", ""]
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
