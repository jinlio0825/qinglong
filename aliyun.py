#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务名称
name: 阿里云社区 每日任务
定时规则
cron: 0 7,13 * * *

阿里云社区每日任务（原 aliyun_web.js 反混淆后的 Python 版）

功能:
- 上午场（13 点前运行）: 各社区签到 + 领签到奖励、电子书评论、
  文章点赞/收藏/分享/评论、问答点赞（5 轮）
- 下午场（13 点后运行）: 领签到奖励、收取积分、取消文章点赞收藏
- 可选: 场景体验(aliyunWeb_scene)、视频播放(aliyunWeb_video)、
  库存查询(aliyunWeb_stock)

获取 Cookie 方式: 阿里云 APP - 首页 - 积分商城 抓 developer.aliyun.com 的 Cookie
    （或浏览器登录 developer.aliyun.com 后复制 Cookie）

环境变量:
    aliyunWeb_data    必填, 多账号用 @ 分隔
    aliyunWeb_time    分场时间, 1-23 整数, 默认 12
                      (运行时刻早于该点 = 上午场, 否则 = 下午场)
    aliyunWeb_scene   "true"/"false", 是否做场景任务, 默认 false
    aliyunWeb_video   "true"/"false", 是否做视频任务, 默认 false
    aliyunWeb_stock   "true"/"false", 是否查询库存, 默认 false
    IS_DEDUG          "true" 打印请求调试信息, 默认 false

依赖: pip install requests beautifulsoup4

注意: 因文章评论需要审核，请按推荐时间执行:
    12 点前执行一次（上午场），12 点后执行一次（下午场）
"""

import hashlib
import json
import math
import os
import random
import re
import sys
import time
from urllib.parse import urlencode

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

HOST = "https://developer.aliyun.com"
API = HOST + "/developer/api"
UCC = "https://ucc.aliyun.com"

UA_PC_122 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
UA_PC_125 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
          "AliApp(Aliyun/6.7.1) WindVane/8.7.2 1170x2532 WK")

# 19 个社区分组
TASK_GROUP = [
    ("", "我的社区"), ("ecs", "弹性计算"), ("computenest", "计算巢"),
    ("yitian", "倚天"), ("wuying", "无影"), ("cloudnative", "云原生"),
    ("storage", "云存储"), ("luoshen", "飞天洛神云网络"), ("database", "数据库"),
    ("polardb", "PolarDB开源"), ("bigdata", "大数据与机器学习"),
    ("modelscope", "ModelScope模型即服务"), ("viapi", "视觉智能"),
    ("dns", "域名解析DNS"), ("iot", "物联网"), ("devops", "云效DevOps"),
    ("aliyun_linux", "龙蜥操作系统"), ("modelstudio", "百炼大模型"),
    ("tongyi", "通义大模型"),
]

REQUEST_INTERVAL = 1.0


def log(msg):
    print(msg, flush=True)


def env(name, default=""):
    return (os.getenv(name) or default).strip()


def is_true(name):
    return env(name, "false").lower() == "true"


def random_int(a, b):
    return round(random.random() * (b - a) + a)


def get_callback(ts=None):
    """ucc 接口的 jsonp callback 名"""
    ts = ts or int(time.time() * 1000)
    return f"jsonp_{ts}_{math.ceil(100000 * random.random())}"


def get_json(text):
    """从 jsonp 响应里提取 JSON"""
    return json.loads(re.sub(r".*\(", "", re.sub(r"\)", "", text)))


def get_session_id(cookie, video_id):
    """sessionId = md5(cna + videoId + 时间戳)，cna 从 Cookie 解析"""
    m = re.search(r"cna=([^;]*)", cookie or "")
    cna = m.group(1) if m else ""
    raw = f"{cna}{video_id}{int(time.time() * 1000)}"
    return hashlib.md5(raw.encode()).hexdigest()


class AliyunUser:
    def __init__(self, token, index):
        self.index = index
        self.token = token
        self.ck_status = True
        self.headers = {
            "Cookie": token,
            "User-Agent": UA_PC_122,
            "Referer": HOST + "/",
        }
        # 场景任务共享状态（原 JS 用全局变量）
        self.scene_id = ""
        self.resource_from = ""
        self.section_id = ""
        self.ip = ""

    # ---------- 基础请求 ----------
    def fetch(self, url, method="get", params=None, body=None,
              data_type="form", headers=None, result_type="data"):
        """统一请求入口。data_type: form/json；返回 JSON 或原文"""
        full_url = url if url.startswith("http") else API + url
        req_headers = headers or self.headers
        try:
            if data_type == "json":
                req_headers = {**req_headers, "Content-Type": "application/json;charset=UTF-8"}
                data = json.dumps(body) if body is not None else None
            else:  # form
                data = urlencode(body) if body else None
                if params and method == "post":
                    full_url += "?" + urlencode(params)
                    params = None
            resp = requests.request(
                method.upper(), full_url, params=params, data=data,
                headers=req_headers, timeout=10)
            text = resp.text
            # jsonp 响应直接返回原文，由调用方处理
            if result_type == "raw":
                return text
            try:
                result = json.loads(text)
            except ValueError:
                result = text
            if isinstance(result, dict) and result.get("code") == 40001:
                raise RuntimeError(result.get("message") or "用户需要去登录")
            return result
        except Exception as exc:
            self.ck_status = False
            log(f"⛔️ 请求发起失败！{exc}")
            return None

    @staticmethod
    def wait():
        time.sleep(random_int(1, 2) * REQUEST_INTERVAL)

    # ---------- 任务流程 ----------
    def get_user(self):
        self.fetch("/my/user/getUser", "get")

    def get_user_space_sign_in_detail(self, excode):
        """查社区分组对应的 taskGroupId"""
        r = self.fetch("/sign/getUserSpaceSignInDetail", "get",
                       params={"excode": excode})
        return (((r or {}).get("data") or {}).get("taskGroupId"))

    def get_tasks(self, group_id):
        """取分组里当前时段可做的签到任务"""
        if not group_id:
            return None
        r = self.fetch("/task/getTaskGroup?groupId=" + str(group_id), "get")
        task_list = ((r or {}).get("data") or {}).get("taskList") or []
        result = {}
        now = int(time.time() * 1000)
        for task in task_list:
            if now >= task.get("gmtEnableStart", 0) and now <= task.get("gmtEnableEnd", 0):
                rule = json.loads(
                    (task.get("finishRule") or "{}").replace("&quot;", '"'))
                actions = rule.get("actions") or [{}]
                result["actionCode"] = actions[0].get("actionCode")
                result["activityCode"] = actions[0].get("actionCode")
                result["objectId"] = actions[0].get("objectId")
        return result

    def sign_in(self, task, group_name):
        if not task:
            log(f"✅ 签到 - {group_name or 'default'}: 该社区无签到任务")
            return
        r = self.fetch("/task/actionLog", "post", body=task)
        msg = (r or {}).get("message") if isinstance(r, dict) else r
        log(f"✅ 签到 - {group_name or 'default'}: {msg}")

    def assess_sign_in_bonus(self, group_id, group_name):
        if not group_id:
            return None
        r = self.fetch("/sign/assessSignInBonusQualification", "get",
                       params={"taskGroupId": group_id})
        return (r or {}).get("data")

    def receive_sign_in_bonus(self, group_id, group_name):
        r = self.fetch("/sign/receiveSignInBonus", "post",
                       body={"taskGroupId": group_id})
        if isinstance(r, dict) and r.get("code") == "200":
            log(f"✅ 抽奖 - {group_name or 'default'}: 获得 {r.get('data') or 0} 积分")
        else:
            msg = r.get("message") if isinstance(r, dict) else r
            log(f"⛔️ 抽奖 - {group_name or 'default'}: {msg}")

    def get_articles(self):
        """从热文列表随机取一篇文章 id"""
        page = random_int(1, 30)
        text = self.fetch(f"{HOST}/group/aliware/article_hot?pageNum={page}",
                          "get", result_type="raw")
        if not text or BeautifulSoup is None:
            return None
        soup = BeautifulSoup(text, "html.parser")
        container = soup.select_one(".community-detail-content")
        items = []
        if container:
            for li in container.select(".community-list"):
                a = li.select_one(".feed-item")
                h3 = li.select_one(".feed-item-content-title h3")
                if a and h3:
                    items.append((a.get("data-id"), h3.get_text()))
        if not items:
            return None
        art_id, name = random.choice(items)
        log(f"✅ 随机获取文章id: {art_id}, 标题: {name}")
        return art_id

    def get_ebooks(self):
        page = random_int(1, 500)
        text = self.fetch(f"{HOST}/ebook/index/__0_0_0_{page}", "get",
                          result_type="raw")
        if not text or BeautifulSoup is None:
            return None
        soup = BeautifulSoup(text, "html.parser")
        items = []
        for item in soup.select(".ebook-home-list .ebook-home-item"):
            href = item.get("href") or ""
            title = item.select_one(".ebook-home-title")
            if href and title:
                items.append((href.replace("/ebook/", ""), title.get_text()))
        if not items:
            return None
        book_id, name = random.choice(items)
        log(f"✅ 随机电子书id: {book_id}, 标题: {name}")
        return book_id

    def get_asks(self):
        page = random_int(1, 30)
        text = self.fetch(f"{HOST}/ask?pageNum={page}", "get", result_type="raw")
        if not text or BeautifulSoup is None:
            return None
        soup = BeautifulSoup(text, "html.parser")
        container = soup.select_one(".askProduct-list")
        items = []
        if container:
            for item in container.select(".askProduct-item"):
                ask_id = item.get("data-id") or ""
                title = item.select_one(".askProduct-item-title-text h3")
                answer = item.select_one(".askProduct-item-info-answer")
                answers = 0
                if answer:
                    try:
                        answers = int(answer.get_text())
                    except ValueError:
                        answers = 0
                if ask_id and answers > 0:
                    items.append({"id": ask_id,
                                  "name": title.get_text() if title else "",
                                  "answer": answers})
        if not items:
            return None
        ask = random.choice(items)
        log(f"✅ 随机获取问答id: {ask['id']}, 标题: {ask['name']}")
        return ask

    def get_ask_detail(self, ask):
        text = self.fetch(f"{HOST}/ask/{ask['id']}", "get", result_type="raw")
        if not text or BeautifulSoup is None:
            return None
        soup = BeautifulSoup(text, "html.parser")
        container = soup.select_one(".answer-list")
        ids = []
        if container:
            ids = [a.get("data-id") or ""
                   for a in container.select(".answer-item")]
        if not ids:
            return None
        pick = ids[math.floor(random.random() * ask["answer"])]
        if pick:
            log(f"✅ 随机获取问题问答id: {pick}")
            return pick
        return None

    def get_ucc_csrf_token(self):
        r = self.fetch(f"{UCC}/uccPagingComponent/getUser", "get",
                       params={"uccCsrfToken": "", "callback": get_callback()},
                       result_type="raw")
        if not r:
            return None
        try:
            start = r.index("{")
            end = r.rindex("}")
            return json.loads(r[start:end + 1])["data"]["uccCsrfToken"]
        except (ValueError, KeyError):
            log("⛔️ 获取UccCsrfToken失败!")
            return None

    def like_or_not_like(self, object_id, action_code, status):
        params = {
            "bizCategory": "yq-article",
            "actionCode": action_code,
            "objectId": object_id,
            "status": status,
            "uccCsrfToken": self.get_ucc_csrf_token() or "",
            "callback": get_callback(),
        }
        self.fetch(f"{UCC}/uccPagingComponent/likeOrNotLike", "get",
                   params=params)
        verb = "取消" if status == 1 else ""
        if action_code == "aliyun-public-like":
            action = "点赞"
        elif action_code == "aliyun-public-favorite":
            action = "收藏"
        elif action_code == "aliyun-public-share":
            action = "分享"
        else:
            action = ""
        log(f"✅ 文章{verb}{action}成功: {object_id}")

    def add_comment(self, object_id):
        params = {
            "content": "很有用的文章，非常受用，感谢博主",
            "objectId": object_id,
            "bizCategory": "yq-comment-type-article",
            "commentType": 0,
            "sourceAppCode": "developer-ecology",
            "sourceBizCategory": "developer-ecology-group",
            "uccCsrfToken": self.get_ucc_csrf_token() or "",
            "callback": get_callback(),
        }
        self.fetch(f"{UCC}/uccPagingComponent/addComment", "get", params=params)
        log(f"✅ 文章评论: {object_id}")

    def get_csrf_token(self, res_id, res_type):
        r = self.fetch(f"{HOST}/csrfToken", "get", headers={
            "Cookie": self.token,
            "User-Agent": UA_IOS,
            "Referer": f"{HOST}/{res_type}/{res_id}",
        })
        return (r or {}).get("token") if isinstance(r, dict) else None

    def add_book_comment(self, book_id, csrf):
        r = self.fetch(f"{HOST}/developer/api/ebook/mark/add", "post",
                       params={"p_csrf": csrf},
                       body={"eBookId": book_id, "score": 10,
                             "content": "很棒的一本书"},
                       data_type="json",
                       headers={"Cookie": self.token, "User-Agent": UA_IOS,
                                "Referer": f"{HOST}/ebook/{book_id}"})
        if isinstance(r, dict) and r.get("code") == "200":
            log(f"✅ 评价电子书: {book_id}")
        else:
            msg = r.get("message") if isinstance(r, dict) else r
            log(f"⛔️ 评价电子书失败! {msg}")

    def vote_answer(self, ask_id, answer_id, csrf, votes):
        self.fetch(f"{HOST}/developer/api/my/ask/voteAnswer", "post",
                   params={"p_csrf": csrf},
                   body={"id": answer_id, "votes": votes},
                   headers={"Cookie": self.token, "User-Agent": UA_IOS,
                            "Referer": f"{HOST}/ask/{ask_id}"})
        log(f"✅ 回答点赞: {ask_id}-{answer_id}")

    def get_favors(self):
        r = self.fetch(f"{HOST}/developer/api/my/subscribe/listUserFavor", "get",
                       params={"pageNum": 1, "pageSize": 10, "type": 1})
        data = ((r or {}).get("data") or {}).get("list") or []
        if data:
            log("✅ 开始取消文章的点赞与收藏记录")
        return data

    # ---------- 场景任务 ----------
    def get_scene_list(self):
        page = random_int(1, 25)
        r = self.fetch(f"{HOST}/adc/api/getSceneList", "get", params={
            "tags": ",", "difficulty": "", "orderBy": "useCountTotal",
            "pageNum": page, "pageSize": 21,
        }, headers={
            "Cookie": self.token,
            "Referer": f"{HOST}/adc/labs/",
            "User-Agent": UA_PC_122,
        })
        scenes = ((r or {}).get("data") or {}).get("list") or []
        if scenes:
            scene = random.choice(scenes)
            self.scene_id = scene.get("id")
            log(f"✅ 获取场景: {scene.get('name')}[{self.scene_id}]")
        else:
            log("⛔️ 获取场景失败! 列表为空")

    def get_scene_detail(self):
        r = self.fetch(f"{HOST}/adc/api/getSceneDetailPageInfoById", "get",
                       params={"id": self.scene_id}, headers={
                           "cookie": self.token,
                           "referer": f"{HOST}/adc/scenario/{self.scene_id}",
                           "user-agent": UA_PC_122,
                       })
        code = (((r or {}).get("data") or {})
                .get("developerAdcExperienceStatusVO") or {}).get("buttonCode")
        data_id = ((r or {}).get("data") or {}).get("id")
        if not code:
            log(f"⛔️ 确认场景状态: {data_id} 状态异常，将重新获取场景")
            return None
        if code == "1":
            log(f"✅ 确认场景状态: {data_id}")
            return data_id
        log(f"⛔️ 确认场景状态: {data_id} 已完成，将重新获取场景")
        return None

    def get_scene_start_info(self):
        r = self.fetch(f"{HOST}/adc/api/getSceneStartPageInfoById", "get",
                       params={"id": self.scene_id}, headers={
                           "cookie": self.token,
                           "referer": f"{HOST}/adc/scenario/exp/{self.scene_id}",
                           "user-agent": UA_PC_122,
                       })
        data = (r or {}).get("data") or {}
        self.ip = data.get("ip")
        self.resource_from = "1" if "1" in str(data.get("resourceFrom") or "") else "2"
        cards = data.get("resourceCardInfoDTOList") or []
        if cards:
            self.section_id = cards[0].get("id")
        log(f"✅ 获取场景初始化信息: {self.scene_id}")

    def start_scene(self, csrf):
        r = self.fetch(f"{HOST}/adc/api/startSceneById", "post",
                       params={"p_csrf": csrf},
                       body={"id": self.scene_id, "resourceFrom": self.resource_from},
                       headers={
                           "Host": "developer.aliyun.com",
                           "H_csrf": csrf,
                           "X-XSRF-TOKEN": csrf,
                           "User-Agent": UA_PC_125,
                           "Cookie": self.token,
                           "Referer": f"{HOST}/adc/scenario/exp/{self.scene_id}",
                       })
        code = (r or {}).get("code")
        msg = (r or {}).get("message")
        log(f"{'✅' if code == '200' else '⛔️'} 开始场景: {self.scene_id}, {msg}")

    def close_scene(self, csrf):
        r = self.fetch(f"{HOST}/adc/api/closeSceneById", "post",
                       params={"p_csrf": csrf},
                       body={"sceneId": self.scene_id, "forceClose": "true"},
                       headers={
                           "Host": "developer.aliyun.com",
                           "H_csrf": csrf,
                           "X-XSRF-TOKEN": csrf,
                           "User-Agent": UA_PC_125,
                           "Cookie": self.token,
                           "Referer": f"{HOST}/adc/scenario/exp/{self.scene_id}",
                       })
        code = (r or {}).get("code")
        msg = (r or {}).get("message")
        log(f"{'✅' if code == '200' else '⛔️'} 结束场景: {self.scene_id}, {msg}")

    def do_scene(self):
        """场景任务主流程；重试上限防死循环"""
        m = re.search(r"c_csrf=([^;]*)", self.token or "")
        csrf = m.group(1) if m else ""
        for _ in range(3):
            self.get_scene_list()
            self.wait()
            detail_id = self.get_scene_detail()
            self.wait()
            if not detail_id:
                continue
            self.get_scene_start_info()
            self.wait()
            if self.resource_from == "2":
                self.start_scene(csrf)
                self.wait()
                self.close_scene(csrf)
                self.wait()
            return
        log("⛔️ 场景任务重试 3 次仍未成功，跳过")

    # ---------- 视频任务 ----------
    def get_video_detail(self, video_id):
        ts = int(time.time() * 1000)
        r = self.fetch(f"{UCC}/api/ucc/live/open/detail", "get", params={
            "_": ts, "callback": get_callback(ts), "version": "1.1.23",
            "id": video_id,
        }, headers={"User-Agent": UA_PC_125, "Cookie": self.token,
                    "Referer": f"{HOST}/live/{video_id}"})
        try:
            data = get_json(r) if isinstance(r, str) else r
            live = ((data or {}).get("data") or {}).get("live") or {}
            log(f"✅ 获取视频信息成功: {live.get('name')}, 时长: {live.get('duration')} 秒")
            return live.get("name"), live.get("duration") or 0
        except (ValueError, AttributeError):
            log("⛔️ 获取视频信息失败!")
            return None, 0

    def _ucc_live(self, path, video_id, extra_params, refer_video_id):
        ts = int(time.time() * 1000)
        params = {"_": ts, "callback": get_callback(ts), "version": "1.1.23",
                  "id": video_id, **extra_params}
        self.fetch(f"{UCC}/api/ucc/live/open/{path}", "get", params=params,
                   headers={"User-Agent": UA_PC_125, "Cookie": self.token,
                            "Referer": f"{HOST}/live/{refer_video_id}"})

    def play_video(self):
        video_id = "253842"
        session_id = get_session_id(self.token, video_id)
        name, duration = self.get_video_detail(video_id)
        self.wait()
        self._ucc_live("view", video_id, {"sessionId": session_id}, video_id)
        self.wait()
        self._ucc_live("play", video_id, {"sessionId": session_id}, video_id)
        log(f"✅ 开始播放视频: {name}")
        self.wait()
        for sec in range(3, duration, 3):
            self._ucc_live("danmu", video_id, {"seek": sec}, video_id)
            log(f"✅ 获取第 {sec} 秒弹幕")
            time.sleep(3)
            if sec == 60:
                self._ucc_live("online", video_id,
                               {"sessionId": session_id}, video_id)
                log("✅ 在线心跳确认成功")
        log(f"✅ 视频播放完毕: {name}")

    # ---------- 积分 ----------
    def get_group_items(self):
        r = self.fetch("/lm/getGroupItems?pageNum=1&pageSize=50", "get")
        items = ((r or {}).get("data") or {}).get("list") or []
        if items:
            log("✅ 开始查询库存:")
            for item in items:
                title = re.sub(r"【.*?】", "", item.get("itemTitle") or "")
                log(f"🎁 {title}: {item.get('points')} 分【{item.get('statusStr')}】")

    def get_user_score(self):
        r = self.fetch("/my/score/getUserScore?appCode=developer", "get")
        return (r or {}).get("data")

    def get_pending_score(self):
        r = self.fetch("/score/pending/getUserTotalPendingScore?appCode=developer",
                       "get")
        log(f"✅ 待领取积分: {(r or {}).get('data')}")
        return (r or {}).get("data")

    def collect(self):
        r = self.fetch("/score/pending/receiveAllPendingScore?appCode=developer",
                       "get")
        log(f"✅ 收取积分: {(r or {}).get('data')}")
        return (r or {}).get("data")


def run_morning(u):
    """上午场：签到 + 内容互动"""
    for code, name in TASK_GROUP:
        group_id = u.get_user_space_sign_in_detail(code)
        task = u.get_tasks(group_id)
        u.sign_in(task, name)
        u.wait()
        can_bonus = u.assess_sign_in_bonus(group_id, name)
        u.wait()
        if can_bonus:
            u.receive_sign_in_bonus(group_id, name)
            u.wait()

    book_id = u.get_ebooks()
    u.wait()
    csrf = u.get_csrf_token(book_id, "ebook")
    u.wait()
    if book_id and csrf:
        u.add_book_comment(book_id, csrf)
    u.wait()

    for i in range(5):
        art_id = u.get_articles()
        u.wait()
        if art_id:
            u.like_or_not_like(art_id, "aliyun-public-like", 0)
            u.wait()
            u.like_or_not_like(art_id, "aliyun-public-favorite", 0)
            u.wait()
        if i == 0 and art_id:
            u.add_comment(art_id)
            u.wait()
            u.like_or_not_like(art_id, "aliyun-public-share", 0)
            u.wait()
        ask = u.get_asks()
        u.wait()
        if ask and ask.get("id"):
            csrf = u.get_csrf_token(ask["id"], "ask")
            u.wait()
            answer_id = u.get_ask_detail(ask)
            u.wait()
            if answer_id:
                u.vote_answer(ask["id"], answer_id, csrf, 1)
                u.wait()

    if is_true("aliyunWeb_scene"):
        u.do_scene()
        u.wait()
    if is_true("aliyunWeb_video"):
        u.play_video()
        u.wait()
    if is_true("aliyunWeb_stock"):
        u.get_group_items()


def run_afternoon(u):
    """下午场：领奖励 + 收积分 + 清理点赞收藏"""
    for code, name in TASK_GROUP:
        group_id = u.get_user_space_sign_in_detail(code)
        can_bonus = u.assess_sign_in_bonus(group_id, name)
        u.wait()
        if can_bonus:
            u.receive_sign_in_bonus(group_id, name)
            u.wait()

    u.collect()
    u.wait()

    favors = u.get_favors() or []
    u.wait()
    for fav in favors:
        obj_id = fav.get("objectId")
        if obj_id:
            u.like_or_not_like(obj_id, "aliyun-public-like", 1)
            u.wait()
            u.like_or_not_like(obj_id, "aliyun-public-favorite", 1)
            u.wait()

    if is_true("aliyunWeb_stock"):
        u.get_group_items()


def notify(message):
    try:
        from notify import send
    except ImportError:
        try:
            from sendNotify import send
        except ImportError:
            log(message)
            return
    try:
        send("阿里云社区", message)
    except Exception as exc:
        log(f"推送失败: {exc}")
        log(message)


def main():
    cookie_str = env("aliyunWeb_data")
    if not cookie_str:
        notify("⛔️ 未检测到ck，请添加环境变量 aliyunWeb_data")
        return 1

    cookies = [c.strip() for c in cookie_str.split("@") if c.strip()]
    log(f"共找到 {len(cookies)} 个账号")

    control_time = int(env("aliyunWeb_time", "12") or 12)
    is_morning = time.localtime().tm_hour < control_time
    log(f"当前 {time.strftime('%H:%M')}，执行{'上午' if is_morning else '下午'}场任务")

    summary = []
    for idx, cookie in enumerate(cookies, 1):
        log(f"\n🔷账号{idx} >> Start work")
        u = AliyunUser(cookie, idx)
        u.get_user()
        if not u.ck_status:
            summary.append(f"账号{idx}: ck 失效")
            continue
        try:
            score = u.get_user_score()
            if is_morning:
                run_morning(u)
                pending = u.get_pending_score()
                summary.append(f"账号{idx}: 当前积分 {score}, 待领取 {pending}")
            else:
                run_afternoon(u)
                score_after = u.get_user_score()
                summary.append(f"账号{idx}: 当前积分 {score_after}")
        except Exception as exc:
            log(f"⛔️ 账号{idx} 异常: {exc}")
            summary.append(f"账号{idx}: 异常 {exc}")
        u.wait()

    log("\n----------- 结果汇总 -----------")
    notify("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
