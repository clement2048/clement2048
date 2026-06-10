#!/usr/bin/env python3
"""
daily-pokemon.py

更新 README.md 中 <!-- DAILY_POKEMON_START --> ... <!-- DAILY_POKEMON_END -->
之间的内容为今日随机宝可梦（限定关都 1-151 号）。

特点：
- 基于日期的伪随机：同一天多次运行结果一致
- 不需要 API key：直接用 PokeAPI 免费接口
- 失败安全：拉取失败时保留原内容，exit 0
- 中文支持：从 species 端点拉中文名（zh-Hans）
- 中文属性：内置 18 种属性的中英映射
- CDN 友好：sprite 走 jsDelivr（国内访问稳定）
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

# jsDelivr CDN（国内访问稳定，GitHub 仓库镜像）
SPRITE_CDN = "https://cdn.jsdelivr.net/gh/PokeAPI/sprites@master/sprites/pokemon"

# 18 种属性的中文映射（关都 + 现代属性）
TYPE_CN = {
    "normal":   "一般",
    "fire":     "火",
    "water":    "水",
    "electric": "电",
    "grass":    "草",
    "ice":      "冰",
    "fighting": "格斗",
    "poison":   "毒",
    "ground":   "地面",
    "flying":   "飞行",
    "psychic":  "超能力",
    "bug":      "虫",
    "rock":     "岩石",
    "ghost":    "幽灵",
    "dragon":   "龙",
    "dark":     "恶",
    "steel":    "钢",
    "fairy":    "妖精",
}

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
MARKER_START = "<!-- DAILY_POKEMON_START -->"
MARKER_END = "<!-- DAILY_POKEMON_END -->"


def fetch_json(url: str) -> dict:
    """GET 一个 URL 返回 JSON。失败抛异常。"""
    req = urllib.request.Request(
        url, headers={"User-Agent": "github-profile-daily-pokemon/2.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_pokemon(poke_id: int) -> dict:
    return fetch_json(f"https://pokeapi.co/api/v2/pokemon/{poke_id}")


def fetch_species(poke_id: int) -> dict:
    return fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{poke_id}")


def get_chinese_name(species_data: dict) -> str:
    """从 species.names 数组里找 zh-Hans 中文名（大小写不敏感）。fallback 英文。"""
    for entry in species_data.get("names", []):
        if entry.get("language", {}).get("name", "").lower() == "zh-hans":
            return entry["name"]
    return species_data["name"].capitalize()


def types_to_chinese(types: list) -> str:
    """把 [{type: {name: 'fire'}}, ...] 渲染成 '火' 或 '火 · 飞行'。"""
    return " · ".join(TYPE_CN.get(t["type"]["name"], t["type"]["name"].capitalize())
                      for t in types)


def render_block(poke_id: int, name_cn: str, types_cn: str, date_str: str) -> str:
    """把宝可梦数据渲染成中文 README 片段。"""
    sprite = f"{SPRITE_CDN}/other/official-artwork/{poke_id}.png"
    return f"""<div align="center">

<img src="{sprite}" width="120" alt="{name_cn}">

**No.{poke_id:03d}  {name_cn}**  ·  {types_cn}

*按任意键开始对战！*

<sub>🕐 刷新时间：{date_str} UTC · 自动 · <a href="https://pokeapi.co/api/v2/pokemon/{poke_id}">数据源</a></sub>

</div>"""


def main() -> int:
    # 日期：UTC 当天；支持命令行覆盖（用于测试和 GitHub Action）
    date_str = (
        sys.argv[1]
        if len(sys.argv) > 1
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    # 基于日期的伪随机 seed
    random.seed(sum(ord(c) for c in date_str))
    poke_id = random.randint(MIN_ID, MAX_ID)

    # 拉数据（失败安全：拉不到就保留旧内容）
    try:
        data = fetch_pokemon(poke_id)
        species = fetch_species(poke_id)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f"[daily-pokemon] fetch failed for id={poke_id}: {e}", file=sys.stderr)
        return 0

    name_cn = get_chinese_name(species)
    types_cn = types_to_chinese(data["types"])

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

    new_block = (
        f"{MARKER_START}\n"
        f"{render_block(poke_id, name_cn, types_cn, date_str)}\n"
        f"{MARKER_END}"
    )
    new_readme = pattern.sub(lambda m: new_block, readme)

    if new_readme == readme:
        print(f"[daily-pokemon] no change (id={poke_id} same as before)")
        return 0

    README_PATH.write_text(new_readme, encoding="utf-8")
    print(f"[daily-pokemon] updated to No.{poke_id:03d} {name_cn} ({types_cn}) for {date_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
