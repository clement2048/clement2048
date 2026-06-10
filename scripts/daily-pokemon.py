#!/usr/bin/env python3
"""
daily-pokemon.py

更新 README.md 中 <!-- DAILY_POKEMON_START --> ... <!-- DAILY_POKEMON_END -->
之间的内容为今日随机宝可梦（限定关都 1-151 号）。

特点：
- 基于日期的伪随机：同一天多次运行结果一致
- 不需要 API key：直接用 PokeAPI 免费接口
- 失败安全：拉取失败时保留原内容，exit 0
- 资源大小：official-artwork 越大越漂亮（O(100KB)），首次加载慢但 GitHub 缓存
"""

import json
import random
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# 限定关都地区（Pokedex 1-151）
MIN_ID = 1
MAX_ID = 151

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
MARKER_START = "<!-- DAILY_POKEMON_START -->"
MARKER_END = "<!-- DAILY_POKEMON_END -->"


def fetch_pokemon(poke_id: int) -> dict:
    """调 PokeAPI 拉一只宝可梦。失败抛异常。"""
    url = f"https://pokeapi.co/api/v2/pokemon/{poke_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "github-profile-daily-pokemon/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def render_block(poke_id: int, data: dict, date_str: str) -> str:
    """把宝可梦数据渲染成 README 片段。"""
    name = data["name"].capitalize()
    types = " · ".join(t["type"]["name"].capitalize() for t in data["types"])
    sprite = (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/other/official-artwork/{poke_id}.png"
    )
    return f"""<div align="center">

<img src="{sprite}" width="120" alt="{name}">

**No.{poke_id:03d}  {name}**  ·  {types}

*Press any button to battle!*

<sub>🕐 Refreshed: {date_str} UTC · auto · <a href="https://pokeapi.co/api/v2/pokemon/{poke_id}">source</a></sub>

</div>"""


def main() -> int:
    # 日期：UTC 当天；支持通过环境变量覆盖（用于测试和 GitHub Action）
    date_str = (
        sys.argv[1]
        if len(sys.argv) > 1
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    # 基于日期的伪随机 seed
    random.seed(sum(ord(c) for c in date_str))
    poke_id = random.randint(MIN_ID, MAX_ID)

    # 拉数据（失败安全）
    try:
        data = fetch_pokemon(poke_id)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f"[daily-pokemon] fetch failed for id={poke_id}: {e}", file=sys.stderr)
        return 0  # 不让 Action 失败，保留旧内容

    # 读取 README
    try:
        readme = README_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[daily-pokemon] README not found at {README_PATH}", file=sys.stderr)
        return 1

    # 替换 marker 区间
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    if not pattern.search(readme):
        print(f"[daily-pokemon] marker not found in README", file=sys.stderr)
        return 1

    new_block = f"{MARKER_START}\n{render_block(poke_id, data, date_str)}\n{MARKER_END}"
    new_readme = pattern.sub(lambda m: new_block, readme)

    if new_readme == readme:
        print(f"[daily-pokemon] no change (id={poke_id} same as before)")
        return 0

    README_PATH.write_text(new_readme, encoding="utf-8")
    print(f"[daily-pokemon] updated to #{poke_id:03d} {data['name']} for {date_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
