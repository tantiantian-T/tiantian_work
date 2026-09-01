#!/usr/bin/env python3
"""读取一周减脂餐单，输出「明天」的三餐。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PLAN_PATH = Path(__file__).resolve().parent.parent / "meal-plan" / "weekly-plan.json"
TZ = ZoneInfo("Asia/Shanghai")

WEEKDAY_KEYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def load_plan() -> dict:
    with PLAN_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def format_meal(meal: dict) -> str:
    items = "、".join(meal["items"])
    return f"**{meal['name']}**（{meal['calories']}）\n  - {items}"


def get_tomorrow_meals(now: datetime | None = None) -> str:
    now = now or datetime.now(TZ)
    tomorrow = now + timedelta(days=1)
    key = WEEKDAY_KEYS[tomorrow.weekday()]
    plan = load_plan()
    day = plan["days"][key]
    profile = plan["profile"]

    lines = [
        f"## 明天（{day['label']}，{tomorrow.strftime('%Y-%m-%d')}）减脂三餐",
        "",
        f"> 目标热量：{profile['daily_calories_target']}",
        "",
        "### 早餐",
        format_meal(day["breakfast"]),
        "",
        "### 午餐",
        format_meal(day["lunch"]),
        "",
        "### 晚餐",
        format_meal(day["dinner"]),
        "",
        "**小提示**：少油少盐；主食每餐约一拳头；加餐可选无糖酸奶或一小把坚果。",
    ]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        now = datetime.now(TZ)
        tomorrow = now + timedelta(days=1)
        key = WEEKDAY_KEYS[tomorrow.weekday()]
        plan = load_plan()
        print(
            json.dumps(
                {
                    "date": tomorrow.strftime("%Y-%m-%d"),
                    "weekday": plan["days"][key]["label"],
                    "meals": plan["days"][key],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(get_tomorrow_meals())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
