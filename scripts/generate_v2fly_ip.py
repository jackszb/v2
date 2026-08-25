#!/usr/bin/env python3
"""
从 v2fly/geoip 仓库下载中国大陆 IP CIDR 列表（cn.txt），
生成两种格式的规则文件到 rules5/ 目录：

1. rules5/v2fly-ip.list  （Clash/Surge 风格）
   IP-CIDR,<cidr>,no-resolve

2. rules5/v2fly-ip.json  （sing-box 风格）
   {
     "version": 3,
     "rules": [
       {
         "ip_cidr": [ "<cidr>", ... ]
       }
     ]
   }
"""

import json
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/v2fly/geoip/release/text/cn.txt"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "rules5"
LIST_FILE = OUTPUT_DIR / "v2fly-ip.list"
JSON_FILE = OUTPUT_DIR / "v2fly-ip.json"


def fetch_cidrs(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "v2fly-ip-updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    cidrs = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cidrs.append(line)

    if not cidrs:
        raise ValueError("未从源文件中解析到任何 CIDR，终止以避免生成空文件")

    return cidrs


def write_list_file(cidrs: list[str], path: Path) -> None:
    lines = [f"IP-CIDR,{cidr},no-resolve" for cidr in cidrs]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json_file(cidrs: list[str], path: Path) -> None:
    data = {
        "version": 3,
        "rules": [
            {
                "ip_cidr": cidrs,
            }
        ],
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"正在从 {SOURCE_URL} 下载...")
    cidrs = fetch_cidrs(SOURCE_URL)
    print(f"解析到 {len(cidrs)} 条 CIDR")

    write_list_file(cidrs, LIST_FILE)
    print(f"已生成 {LIST_FILE.relative_to(REPO_ROOT)}")

    write_json_file(cidrs, JSON_FILE)
    print(f"已生成 {JSON_FILE.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
