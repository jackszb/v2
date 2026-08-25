#!/usr/bin/env python3
"""
从 v2fly/domain-list-community 的 apple.txt 生成两组、共 4 个规则文件:
  1. rules4/apple-cn.list   —— :@cn 结尾的行,  DOMAIN / DOMAIN-SUFFIX 格式 (Shadowrocket/Surge)
  2. rules4/apple-cn.json   —— :@cn 结尾的行,  domain / domain_suffix 数组格式 (sing-box 风格)
  3. rules4/apple-!cn.list  —— 无任何 :@xxx 标签的行, DOMAIN / DOMAIN-SUFFIX 格式
  4. rules4/apple-!cn.json  —— 无任何 :@xxx 标签的行, domain / domain_suffix 数组格式

处理规则:
  - 行前缀 full:   -> DOMAIN        (精确域名)
  - 行前缀 domain: -> DOMAIN-SUFFIX (域名及其子域名)
  - 只分两组: 以 :@cn 结尾的行 -> apple-cn 组；没有任何 :@xxx 标签的行 -> apple-!cn 组
  - 其他标签(如该文件中出现的 :@ads)既不属于 :@cn 也不是无标签，两组均不提取，直接忽略
  - 输出文件不含任何注释和空行
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/v2fly/domain-list-community/release/apple.txt"

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "rules4"

CN_LIST_FILE = OUT_DIR / "apple-cn.list"
CN_JSON_FILE = OUT_DIR / "apple-cn.json"
NOTCN_LIST_FILE = OUT_DIR / "apple-!cn.list"
NOTCN_JSON_FILE = OUT_DIR / "apple-!cn.json"

# 匹配形如: full:example.com:@cn / domain:example.com / domain:example.com:@ads
LINE_RE = re.compile(r"^(?P<type>full|domain|regexp|include|keyword):(?P<value>.*)$")


def fetch_source(url: str = SOURCE_URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "rules-generator"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def split_value_and_tag(value: str):
    """
    把 value 拆成 (真实值, 标签或None)
    标签形如结尾的 ':@cn' / ':@ads'，只关心最后一个 @ 标签
    """
    m = re.search(r":(@[!\w-]+)\s*$", value)
    if m:
        tag = m.group(1)
        real = value[: m.start()]
        return real, tag
    return value, None


def parse_source(text: str):
    """
    返回两组数据:
      cn_group:    {"suffix": [...], "full": [...]}   -- :@cn 结尾的行
      notcn_group: {"suffix": [...], "full": [...]}   -- 无任何 :@xxx 标签的行
    其他标签(如 :@ads)的行两组都不提取。
    """
    cn_suffix, cn_full = [], []
    notcn_suffix, notcn_full = [], []

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

        if line_type not in ("full", "domain"):
            # regexp: / include: / keyword: 等本次需求未涉及，直接忽略
            continue

        real, tag = split_value_and_tag(value)

        if tag == "@cn":
            target_full, target_suffix = cn_full, cn_suffix
        elif tag is None:
            target_full, target_suffix = notcn_full, notcn_suffix
        else:
            continue  # 其他标签(如 @ads)两组均不提取

        if line_type == "full":
            target_full.append(real)
        else:
            target_suffix.append(real)

    return {
        "cn": {"suffix": cn_suffix, "full": cn_full},
        "notcn": {"suffix": notcn_suffix, "full": notcn_full},
    }


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

    groups = parse_source(text)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cn = groups["cn"]
    notcn = groups["notcn"]

    CN_LIST_FILE.write_text(build_list_file(cn["suffix"], cn["full"]), encoding="utf-8")
    CN_JSON_FILE.write_text(build_json_file(cn["suffix"], cn["full"]), encoding="utf-8")
    NOTCN_LIST_FILE.write_text(build_list_file(notcn["suffix"], notcn["full"]), encoding="utf-8")
    NOTCN_JSON_FILE.write_text(build_json_file(notcn["suffix"], notcn["full"]), encoding="utf-8")

    print(f"[apple-cn]   DOMAIN(full): {len(cn['full'])}  DOMAIN-SUFFIX(domain): {len(cn['suffix'])}")
    print(f"[apple-!cn]  DOMAIN(full): {len(notcn['full'])}  DOMAIN-SUFFIX(domain): {len(notcn['suffix'])}")
    print(f"写入: {CN_LIST_FILE}")
    print(f"写入: {CN_JSON_FILE}")
    print(f"写入: {NOTCN_LIST_FILE}")
    print(f"写入: {NOTCN_JSON_FILE}")


if __name__ == "__main__":
    main()
