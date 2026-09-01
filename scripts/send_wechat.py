#!/usr/bin/env python3
"""把消息推送到微信（Server酱 或 PushPlus）。

用法:
  python3 scripts/send_wechat.py "标题" "正文"

环境变量（二选一）:
  WECHAT_SENDKEY  — Server酱 SendKey  https://sct.ftqq.com/
  PUSHPLUS_TOKEN  — PushPlus token     https://www.pushplus.plus/
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def send_serverchan(sendkey: str, title: str, content: str) -> dict:
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    body = urllib.parse.urlencode({"title": title, "desp": content}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def send_pushplus(token: str, title: str, content: str) -> dict:
    url = "https://www.pushplus.plus/send"
    payload = json.dumps(
        {"token": token, "title": title, "content": content, "template": "txt"},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "Cursor 通知"
    content = sys.argv[2] if len(sys.argv) > 2 else "（无正文）"

    sendkey = os.environ.get("WECHAT_SENDKEY", "").strip()
    pushplus = os.environ.get("PUSHPLUS_TOKEN", "").strip()

    try:
        if sendkey:
            result = send_serverchan(sendkey, title, content)
            print(json.dumps(result, ensure_ascii=False))
            if result.get("code") != 0:
                print("Server酱推送失败", file=sys.stderr)
                return 1
            print("已通过 Server酱 推送到微信")
            return 0

        if pushplus:
            result = send_pushplus(pushplus, title, content)
            print(json.dumps(result, ensure_ascii=False))
            if result.get("code") != 200:
                print("PushPlus 推送失败", file=sys.stderr)
                return 1
            print("已通过 PushPlus 推送到微信")
            return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP 错误: {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode(errors="replace"), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"推送异常: {e}", file=sys.stderr)
        return 1

    print(
        "还没有配置微信推送密钥。\n\n"
        "请任选一种：\n"
        "1) Server酱（推荐）https://sct.ftqq.com/ — 微信扫码后复制 SendKey，\n"
        "   设置 WECHAT_SENDKEY，或把 SendKey 发回这个对话。\n"
        "2) PushPlus https://www.pushplus.plus/ — 微信扫码后复制 token，\n"
        "   设置 PUSHPLUS_TOKEN，或把 token 发回这个对话。\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
