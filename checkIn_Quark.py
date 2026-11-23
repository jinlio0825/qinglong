'''
夸克云盘 自动签到 + 自动抽奖
name: 夸克云盘 自动签到
cron: 0 9 * * *

功能：
    1. 网盘每日签到领容量（drive-m 移动端接口）
    2. 网盘抽奖页自动抽奖（coral lottery 接口，wsg sign 已逆向还原）

抓包流程：
    【手机端】
    ①打开抓包，手机端访问抽奖页
    ②找到 url 为 https://drive-m.quark.cn/1/clouddrive/act/growth/reward 的请求信息
    ③复制整段 url（后面必须带 kps sign vcode 参数），粘贴到环境变量
    环境变量 COOKIE_QUARK，多账户用 回车 或 && 分隔
    user 字段是用户名（随意填写，多账户方便区分）
    例如: user=张三; url=https://drive-m.quark.cn/1/clouddrive/act/growth/reward?xxxx=xxxx&kps=abcdefg&sign=hijklmn&vcode=111111111;
    旧版格式也兼容: user=张三; kps=abcdefg; sign=hijklmn; vcode=111111111;

来源：
    V1 版受 @Cp0204 的 quark-auto-save 项目启发改编（已失效）
    https://github.com/Cp0204/quark-auto-save

Author: BNDou
'''
import hashlib
import hmac
import os
import re
import sys
import time
import uuid

import requests

# ================= 抽奖（wsg sign）相关 =================
# sign 算法逆向自 libunet.so（已用抓包样本验证）：
#   sign = "0003" + HMAC-SHA1(key, text + salt).hex()
#   key 藏在 .so 里 AES-128-CBC 加密的表内，解出的 number=3 真实 key 如下
_LOTTERY_APP_ID = "quark_drive_lottery"
_LOTTERY_MODULE_CODE = "6551287e20c84cfd9388f24d8b15af43"   # 抽奖模块
_BALANCE_MODULE_CODE = "1f3563d38896438db994f118d4ff53cb"   # 余额模块
_WSG_KEY = b"C7fU4ct8b4lbEo9BomWvWA76"
_WSG_NUMBER_HEX = "0003"


def wsg_sign(text, salt):
    """复现 libunet.so DefaultCryptor::Sign(number=3, text+salt)"""
    digest = hmac.new(_WSG_KEY, (text + salt).encode("utf-8"), hashlib.sha1).hexdigest()
    return _WSG_NUMBER_HEX + digest


# ================= 环境变量 =================

def get_env():
    """读取环境变量 COOKIE_QUARK，多账号用 回车 或 && 分隔"""
    if "COOKIE_QUARK" not in os.environ:
        print("❌未添加COOKIE_QUARK变量")
        send("夸克自动签到", "❌未添加COOKIE_QUARK变量")
        sys.exit(0)
    return re.split(r"\n|&&", os.environ.get("COOKIE_QUARK"))


def extract_params(url):
    """从抓包 URL 中提取 kps / sign / vcode 参数"""
    query_start = url.find("?")
    query_string = url[query_start + 1:] if query_start != -1 else ""

    params = {}
    for param in query_string.split("&"):
        if "=" in param:
            key, value = param.split("=", 1)
            params[key] = value

    return {
        "kps": params.get("kps", ""),
        "sign": params.get("sign", ""),
        "vcode": params.get("vcode", ""),
    }


# ================= 抽奖 =================

def _coral_get(path, params):
    """coral2 网关 GET，返回 json"""
    return requests.get(url=f"https://coral2.quark.cn{path}", params=params, timeout=30).json()


def query_balance(kps):
    """查询抽奖次数余额"""
    response = _coral_get("/currency/v1/queryBalance", {
        "appId": _LOTTERY_APP_ID,
        "moduleCode": _BALANCE_MODULE_CODE,
        "kps": kps,
    })
    if response.get("data"):
        return response["data"]["balance"]
    return 0


def lottery_batch_draw(kps, draw_times=1):
    """自动抽奖（复现 H5 lotteryBatchDraw 的签名逻辑）"""
    salt = str(int(time.time() * 1000))
    request_id = str(uuid.uuid4())
    text = _LOTTERY_APP_ID + _LOTTERY_MODULE_CODE + kps + str(draw_times) + request_id
    params = {
        "drawTimes": draw_times,
        "appId": _LOTTERY_APP_ID,
        "moduleCode": _LOTTERY_MODULE_CODE,
        "kps": kps,
        "sign": wsg_sign(text, salt),
        "salt": salt,
        "sceneCode": "quark_drive_618",
        "requestId": request_id,
    }
    return _coral_get("/lottery/v1/batchDraw", params)


def do_lottery(kps, user=""):
    """把余额抽完，返回日志"""
    log = ""
    balance = query_balance(kps)
    if not balance:
        return "🎰 无抽奖次数\n"

    log += f"🎰 剩余抽奖次数: {balance}\n"
    won = []
    for _ in range(balance):
        response = lottery_batch_draw(kps)
        if not response.get("success"):
            log += f"❌ 抽奖失败: {response.get('msg') or response}\n"
            break
        prizes = response.get("data") or []
        if isinstance(prizes, dict):
            prizes = prizes.get("prizeList") or [prizes]
        for p in prizes:
            if isinstance(p, dict) and p.get("win"):
                won.append(p.get("prizeName") or p.get("name") or str(p))
        # 余额抽完自然停止
        if query_balance(kps) <= 0:
            break
    if won:
        log += "🎉 中奖: " + "、".join(won) + "\n"
    else:
        log += "（抽奖完成，未中奖）\n"
    return log


# ================= 签到 =================

class Quark:
    """封装签到相关接口（drive-m 移动端，需 kps/sign/vcode）"""

    def __init__(self, user_data):
        self.param = user_data

    @staticmethod
    def convert_bytes(b):
        """字节转换为可读单位"""
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 1024 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    def _querystring(self):
        return {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get("kps"),
            "sign": self.param.get("sign"),
            "vcode": self.param.get("vcode"),
        }

    def get_growth_info(self):
        """获取用户当前的签到信息"""
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        response = requests.get(url=url, params=self._querystring(), timeout=30).json()
        if response.get("data"):
            return response["data"]
        return False

    def get_growth_sign(self):
        """执行签到，返回 (是否成功, 奖励/错误信息)"""
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        data = {"sign_cyclic": True}
        response = requests.post(url=url, json=data, params=self._querystring(), timeout=30).json()
        if response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        return False, response["message"]

    def do_sign(self):
        """执行签到任务，返回日志"""
        log = ""
        growth_info = self.get_growth_info()
        if not growth_info:
            return "❌ 签到异常: 获取成长信息失败\n"

        cap = growth_info["cap_composition"]
        sign_reward = cap["sign_reward"] if "sign_reward" in cap else 0
        log += (
            f" {'88VIP' if growth_info['88VIP'] else '普通用户'} {self.param.get('user')}\n"
            f"💾 网盘总容量：{self.convert_bytes(growth_info['total_capacity'])}，"
            f"签到累计容量：{self.convert_bytes(sign_reward)}\n"
        )

        if growth_info["cap_sign"]["sign_daily"]:
            log += (
                f"✅ 签到日志: 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}，"
                f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
            )
        else:
            sign, sign_return = self.get_growth_sign()
            if sign:
                log += (
                    f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return)}，"
                    f"连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})\n"
                )
            else:
                log += f"❌ 签到异常: {sign_return}\n"
        return log


# ================= 主流程 =================

def main():
    msg = ""
    accounts = get_env()
    print("✅ 检测到共", len(accounts), "个夸克账号\n")

    for i, account in enumerate(accounts):
        # 解析 user_data
        user_data = {}
        for item in account.replace(" ", "").split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                user_data[key] = value
        # url 形式的变量提取 kps/sign/vcode
        if "url" in user_data:
            user_data.update(extract_params(user_data["url"]))

        msg += f"🙍🏻‍♂️ 第{i + 1}个账号"
        # 每日领空间签到
        msg += Quark(user_data).do_sign()
        # 自动抽奖
        try:
            msg += do_lottery(user_data.get("kps"), user_data.get("user", ""))
        except Exception as err:
            msg += f"❌ 抽奖异常: {err}\n"

    print(msg)
    try:
        send("夸克自动签到", msg)
    except Exception as err:
        print("%s\n❌ 错误，请查看运行日志！" % err)

    return msg[:-1]


try:  # 青龙消息通知模块
    from utils.notify import send
except ImportError:
    try:
        from notify import send
    except ImportError:
        def send(title, content):
            print(f"[通知] {title}\n{content}")


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
