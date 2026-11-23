#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 金价监控
定时规则
cron: */3 * * * *

京东金融积存金实时金价监控，推送钉钉

功能: 抓取京东金融积存金最新价，按千分之四回购费率折算卖出价，
      本地打印 + 推送钉钉机器人（配置齐全时才推送）

环境变量（优先）:
    DD_BOT_TOKEN    钉钉机器人，支持多机器人：
                    单个: token#secret（# 连接 token 与加签密钥）
                    多个: token1#secret1&token2#secret2（& 连接多组）
                    旧格式（纯 token，secret 走 DD_BOT_SECRET）仍兼容
    DD_BOT_SECRET   钉钉机器人加签密钥（SEC 开头，单机器人时用）
    JD_GOLD_SKU     京东金融积存金 productSku（可选，默认 1961543816）

config 文件（环境变量没配时才读）:
    1. /ql/data/config/config.yaml   青龙面板标准配置目录
       或 /ql/config/config.yaml      旧版青龙路径
    2. 脚本同目录 config.json

    支持两种结构，任选其一:

    # 结构 A：键名与环境变量同名
    DD_BOT_TOKEN: xxx
    DD_BOT_SECRET: SECxxx

    # 结构 B：青龙 notify 段（部分镜像用这种）
    notify:
      DD_BOT_TOKEN: xxx
      DD_BOT_SECRET: SECxxx

【安全提醒】不要把真实 token 写进本文件或任何入库文件。

cron 说明: */3 = 每 3 分钟一次，如嫌频繁可改为 */5
"""

import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP

import requests

JD_GOLD_PRICE_URL = "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice"
JD_GOLD_PRODUCT_SKU = "1961543816"
BUYBACK_FEE_RATE = Decimal("0.004")

# 青龙面板配置目录候选
QL_CONFIG_CANDIDATES = (
    "/ql/data/config/config.yaml",
    "/ql/config/config.yaml",
)
# 脚本同目录配置文件
LOCAL_CONFIG_CANDIDATES = ("config.json",)

# 需要从配置里取的键
CONFIG_KEYS = ("DD_BOT_TOKEN", "DD_BOT_SECRET", "JD_GOLD_SKU")


def _read_json_config(path):
    """读取 JSON 配置文件，失败返回空 dict。"""
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _read_yaml_config(path):
    """读取 YAML 配置文件，失败返回空 dict。

    青龙自带 PyYAML；本地缺依赖时降级为空，交给调用方跳过。
    YAML 语法错误抛的是 YAMLError，不是 ValueError 的子类，必须单独捕获，
    否则配置文件写错会让整个脚本崩掉。
    """
    try:
        import yaml
    except ImportError:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, yaml.YAMLError):
        # ValueError 覆盖 UnicodeDecodeError 等编码问题
        return {}


def _flatten_config(raw):
    """把配置整理成扁平 dict，兼容结构 A（顶层）与结构 B（notify 段）。"""
    flat = {}
    if not isinstance(raw, dict):
        return flat

    for key in CONFIG_KEYS:
        value = raw.get(key)
        if value not in (None, ""):
            flat[key] = str(value).strip()

    notify_section = raw.get("notify")
    if isinstance(notify_section, dict):
        for key in CONFIG_KEYS:
            if key in flat:
                continue
            value = notify_section.get(key)
            if value not in (None, ""):
                flat[key] = str(value).strip()

    return flat


def load_config():
    """读取钉钉配置：环境变量优先，其次 config 文件，最后留空。

    返回 (token, secret, sku)，缺失的键为空字符串。
    """
    config = {}

    # 1) config 文件
    for path in QL_CONFIG_CANDIDATES:
        if os.path.exists(path):
            config.update(_flatten_config(_read_yaml_config(path)))
            break
    for path in LOCAL_CONFIG_CANDIDATES:
        candidate = path
        if not os.path.isabs(path):
            candidate = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), path)
        if os.path.exists(candidate):
            config.update(_flatten_config(_read_json_config(candidate)))
            break

    # 2) 环境变量覆盖（优先）
    for key in CONFIG_KEYS:
        env_value = os.getenv(key)
        if env_value not in (None, ""):
            config[key] = env_value.strip()

    return (
        config.get("DD_BOT_TOKEN", ""),
        config.get("DD_BOT_SECRET", ""),
        config.get("JD_GOLD_SKU", "") or JD_GOLD_PRODUCT_SKU,
    )


def parse_jd_gold_price(payload):
    """Extract the current price from the JD Finance response payload."""
    data = payload.get("resultData", payload) if isinstance(payload, dict) else None
    if isinstance(data, dict) and isinstance(data.get("datas"), dict):
        data = data["datas"]
    if not isinstance(data, dict) or data.get("status") not in (None, "SUCCESS"):
        raise ValueError("京东金融返回状态异常")

    try:
        price = float(data["price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("京东金融返回中缺少有效金价") from exc
    if price <= 0:
        raise ValueError("京东金融返回的金价无效")
    return price


def get_jd_gold_price(timeout=10, sku=JD_GOLD_PRODUCT_SKU):
    response = requests.get(
        JD_GOLD_PRICE_URL,
        params={"productSku": sku},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://m.jr.jd.com/finance-gold/msjgold/homepage",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_jd_gold_price(response.json())


def calculate_buyback_price(price):
    """Deduct the four-per-thousand buyback fee and round to cents."""
    net_price = Decimal(str(price)) * (Decimal("1") - BUYBACK_FEE_RATE)
    return float(net_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_price_notice(price):
    buyback_price = calculate_buyback_price(price)
    return f"京东买入价：{price:.2f}\n卖出价：{buyback_price:.2f}"


def parse_bots(raw_token, raw_secret=""):
    """解析机器人列表。

    新格式：DD_BOT_TOKEN="token1#secret1&token2#secret2"，# 连接 token 与 secret，
    & 连接多组。旧格式（纯 token + 独立 DD_BOT_SECRET）仍兼容。
    返回 [(token, secret), ...]，非法片段跳过。
    """
    bots = []
    for group in re.split(r"&", raw_token or ""):
        group = group.strip()
        if not group:
            continue
        if "#" in group:
            token, _, secret = group.partition("#")
            token, secret = token.strip(), secret.strip()
        else:
            token, secret = group, (raw_secret or "").strip()
        if token:
            bots.append((token, secret))
    return bots


def notify_one(price, token, secret):
    """推送单个机器人，返回 True/False。"""
    content = format_price_notice(price)
    try:
        from notify import send
    except ImportError:
        print("未找到 notify 模块（青龙自带），跳过推送。")
        return False

    try:
        send(
            title="金价",
            content=content,
            HITOKOTO="false",
            DD_BOT_SECRET=secret,
            DD_BOT_TOKEN=token,
        )
    except Exception as exc:
        print(f"钉钉推送失败：{exc}")
        return False

    print("钉钉推送成功。")
    return True


def notify_current_price(price, token="", secret=""):
    """打印金价，配置齐全时才推钉钉（支持多机器人）。

    返回 True 表示至少一台发送成功，False 表示未配置或全部失败（均不抛异常）。
    """
    content = format_price_notice(price)
    print(content)

    bots = parse_bots(token, secret)
    if not bots:
        print("未配置钉钉机器人，跳过推送。")
        print("配置方式：环境变量或 /ql/data/config/config.yaml，详见本文件头部说明。")
        return False

    results = [notify_one(price, t, s) for t, s in bots]
    return any(results)


def main():
    token, secret, sku = load_config()
    try:
        price = get_jd_gold_price(sku=sku)
    except Exception as exc:
        print(f"获取京东金融金价失败：{exc}")
        return 1
    notify_current_price(price, token, secret)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
