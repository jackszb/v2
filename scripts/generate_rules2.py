#!/usr/bin/env python3
"""
从 v2fly/domain-list-community 的 geolocation-!cn.txt 生成:
  1. rules2/v2fly-!cn.list  —— Shadowrocket / Surge 通用的 DOMAIN / DOMAIN-SUFFIX 规则列表
  2. rules2/v2fly-!cn.json  —— sing-box 风格的 domain / domain_suffix 规则集

处理规则:
  - 行前缀 full:   -> DOMAIN        (精确域名)
  - 行前缀 domain: -> DOMAIN-SUFFIX (域名及其子域名)
  - 行前缀 regexp: -> 完全忽略，不出现在任何输出文件中
  - 结尾标签 :@cn   -> 整行忽略
  - 结尾标签 :@ads  -> 整行忽略
  - 结尾标签 :@!cn  -> 提取域名(去掉 :@!cn 标签后保留)
  - 没有任何 :@xxx 标签的行 -> 提取
  - 输出文件不含任何注释和空行
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/v2fly/domain-list-community/release/geolocation-!cn.txt"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "rules2"
LIST_FILE = OUT_DIR / "v2fly-!cn.list"
JSON_FILE = OUT_DIR / "v2fly-!cn.json"

# 匹配形如: full:example.com:@cn / domain:example.com / regexp:xxxx
LINE_RE = re.compile(r"^(?P<type>full|domain|regexp|include|keyword):(?P<value>.*)$")


def fetch_source(url: str = SOURCE_URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "rules-generator"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def split_value_and_tag(value: str):
    """
    把 value 拆成 (真实值, 标签或None)
    标签形如结尾的 ':@cn' / ':@ads' / ':@!cn'，只关心最后一个 @ 标签
    """
    m = re.search(r":(@[!\w-]+)\s*$", value)
    if m:
        tag = m.group(1)
        real = value[: m.start()]
        return real, tag
    return value, None


def parse_source(text: str):
    """
    返回:
      domain_suffix_list: 提取出的 domain: 类域名
      domain_full_list:    提取出的 full: 类域名
    (regexp: 行、以及带 :@cn 或 :@ads 标签的行均忽略；
     无标签的行和带 :@!cn 标签的行均提取，:@!cn 标签本身不写入结果)
    """
    domain_suffix_list = []
    domain_full_list = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = LINE_RE.match(line)
        if not m:
            print(f"[WARN] 无法识别的行，已跳过: {line}", file=sys.stderr)
            continue

        line_type = m.group("type")
        value = m.group("value")

        if line_type == "regexp":
            continue  # 正则规则完全忽略

        if line_type not in ("full", "domain"):
            # include: / keyword: 等本次需求未涉及，直接忽略
            continue

        real, tag = split_value_and_tag(value)

        if tag in ("@cn", "@ads"):
            continue  # 忽略 :@cn 和 :@ads 结尾的行

        # 到这里: tag 为 None(无标签) 或者 tag == '@!cn'，均提取域名(标签已在 split_value_and_tag 中被去掉)
        if line_type == "full":
            domain_full_list.append(real)
        else:
            domain_suffix_list.append(real)

    return domain_suffix_list, domain_full_list


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

    domain_suffix_list, domain_full_list = parse_source(text)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LIST_FILE.write_text(build_list_file(domain_suffix_list, domain_full_list), encoding="utf-8")
    JSON_FILE.write_text(build_json_file(domain_suffix_list, domain_full_list), encoding="utf-8")

    print(f"DOMAIN(full):        {len(domain_full_list)}")
    print(f"DOMAIN-SUFFIX(domain):{len(domain_suffix_list)}")
    print(f"写入: {LIST_FILE}")
    print(f"写入: {JSON_FILE}")


if __name__ == "__main__":
    main()
