#!/usr/bin/env python3
"""
从 v2fly/domain-list-community 的 category-ads-all.txt 生成:
  1. rules3/v2fly-ads.list  —— Shadowrocket / Surge 通用的 DOMAIN / DOMAIN-SUFFIX 规则列表
  2. rules3/v2fly-ads.json  —— sing-box 风格的 domain / domain_suffix 规则集

处理规则:
  - 行前缀 full:   -> DOMAIN        (精确域名)
  - 行前缀 domain: -> DOMAIN-SUFFIX (域名及其子域名)
  - 行前缀 regexp: -> 不写入这两个文件 (整个文件本身就是广告分类，不做 :@ads 等标签过滤，
                      提取每一行的纯域名；regexp 行单独处理，用于生成正则说明 md 文件)
  - 输出文件不含任何注释和空行
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/v2fly/domain-list-community/release/category-ads-all.txt"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "rules3"
LIST_FILE = OUT_DIR / "v2fly-ads.list"
JSON_FILE = OUT_DIR / "v2fly-ads.json"

# 匹配形如: full:example.com:@ads / domain:example.com / regexp:xxxx:@ads
LINE_RE = re.compile(r"^(?P<type>full|domain|regexp|include|keyword):(?P<value>.*)$")


def fetch_source(url: str = SOURCE_URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "rules-generator"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def strip_tag(value: str) -> str:
    """
    去掉结尾的 :@xxx 标签(如果有)，只保留域名/正则本身
    """
    m = re.search(r":(@[!\w-]+)\s*$", value)
    if m:
        return value[: m.start()]
    return value


def parse_source(text: str):
    """
    返回:
      domain_suffix_list: 提取出的 domain: 类域名(纯域名，已去掉 :@xxx 标签)
      domain_full_list:    提取出的 full: 类域名(纯域名，已去掉 :@xxx 标签)
      regexp_list:         提取出的 regexp: 类正则(纯正则，已去掉 :@xxx 标签)
    该文件本身就是广告分类整体，因此不按 :@ads 等标签做二次过滤，
    每一行都提取其纯域名/纯正则部分。
    """
    domain_suffix_list = []
    domain_full_list = []
    regexp_list = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = LINE_RE.match(line)
        if not m:
            print(f"[WARN] 无法识别的行，已跳过: {line}", file=sys.stderr)
            continue

        line_type = m.group("type")
        value = strip_tag(m.group("value"))

        if line_type == "full":
            domain_full_list.append(value)
        elif line_type == "domain":
            domain_suffix_list.append(value)
        elif line_type == "regexp":
            regexp_list.append(value)
        else:
            # include: / keyword: 等本次需求未涉及，直接忽略
            continue

    return domain_suffix_list, domain_full_list, regexp_list


def build_list_file(domain_suffix_list, domain_full_list) -> str:
    lines = []
    for d in domain_full_list:
        lines.append(f"DOMAIN,{d}")
    for d in domain_suffix_list:
        lines.append(f"DOMAIN-SUFFIX,{d}")
    return "\n".join(lines) + "\n"


def build_json_file(domain_suffix_list, domain_full_list) -> str:
    data = {
        "version": 3,
        "rules": [
            {
                "domain": domain_full_list,
                "domain_suffix": domain_suffix_list,
            }
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--local":
        # 本地调试用：直接读本地文件，不联网
        local_path = Path(sys.argv[2])
        text = local_path.read_text(encoding="utf-8")
    else:
        # 正式运行 (包括 GitHub Actions 首次运行) 一律联网从源地址实时拉取
        text = fetch_source()

    domain_suffix_list, domain_full_list, regexp_list = parse_source(text)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LIST_FILE.write_text(build_list_file(domain_suffix_list, domain_full_list), encoding="utf-8")
    JSON_FILE.write_text(build_json_file(domain_suffix_list, domain_full_list), encoding="utf-8")

    print(f"DOMAIN(full):        {len(domain_full_list)}")
    print(f"DOMAIN-SUFFIX(domain):{len(domain_suffix_list)}")
    print(f"regexp(未写入list/json，仅供单独生成md使用): {len(regexp_list)}")
    print(f"写入: {LIST_FILE}")
    print(f"写入: {JSON_FILE}")


if __name__ == "__main__":
    main()
