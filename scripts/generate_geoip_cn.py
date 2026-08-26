#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 JSON 格式（sing-box 规则集格式）的 ipv4 / ipv6 网段文件，
提取 rules[].ip_cidr 中的所有网段，合并、去重、排序，
生成 Clash 规则格式的 geoip-cn.list 文件到仓库根目录。

上游数据本身已经合并去重过，这里只是把 ipv4 + ipv6 两个文件的内容
汇总成一份 Clash 规则文件；ipv4 网段输出为 IP-CIDR，
ipv6 网段输出为 IP-CIDR6。

如需替换/增减来源，直接修改下面的 SOURCES 列表即可。
"""

import ipaddress
import json
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "geoip-cn.list"

# 上游数据源（已经合并去重好的 ipv4 / ipv6 网段文件）
# 需要替换或增加来源时，直接编辑这个列表即可
SOURCES = [
    "https://raw.githubusercontent.com/jackszb/ip-merge/main/rules/ipv4.json",
]

REQUEST_TIMEOUT = 30
REQUEST_RETRIES = 3


def download(url: str) -> str:
    """下载单个文件内容，失败自动重试"""
    last_err = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[警告] 下载失败（第 {attempt} 次尝试）: {url} -> {e}")
    print(f"[错误] 下载最终失败，跳过该来源: {url} ({last_err})", file=sys.stderr)
    return ""


def extract_cidrs(text: str, url: str):
    """从 JSON 文本中提取所有 rules[].ip_cidr / ip_cidr6 里的网段字符串"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败，跳过该来源: {url} ({e})", file=sys.stderr)
        return []

    cidrs = []
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        print(f"[警告] 来源缺少合法的 rules 数组，跳过: {url}")
        return []

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        # 同时兼容 ip_cidr（ipv4/ipv6 混用）和 ip_cidr6 两种字段名
        for field in ("ip_cidr", "ip_cidr6"):
            values = rule.get(field)
            if isinstance(values, list):
                cidrs.extend(values)

    return cidrs


def parse_networks(cidr_strings):
    """把字符串列表解析为合法的 ipaddress 网段对象，按版本分类"""
    ipv4_nets = set()
    ipv6_nets = set()

    for raw in cidr_strings:
        line = str(raw).strip()
        if not line:
            continue
        try:
            net = ipaddress.ip_network(line, strict=False)
        except ValueError:
            print(f"[警告] 无法解析的网段，已跳过: {line!r}")
            continue
        if net.version == 4:
            ipv4_nets.add(net)
        else:
            ipv6_nets.add(net)

    return ipv4_nets, ipv6_nets


def collect(urls):
    """依次下载所有来源并提取网段"""
    all_ipv4 = set()
    all_ipv6 = set()

    for url in urls:
        print(f"[信息] 正在下载 {url}")
        text = download(url)
        if not text:
            continue
        cidr_strings = extract_cidrs(text, url)
        print(f"[信息] 从该来源提取到 {len(cidr_strings)} 条原始网段字符串")
        ipv4_nets, ipv6_nets = parse_networks(cidr_strings)
        all_ipv4.update(ipv4_nets)
        all_ipv6.update(ipv6_nets)

    return all_ipv4, all_ipv6


def build_lines(ipv4_nets, ipv6_nets):
    """去重后按网段地址、前缀长度排序，生成 Clash 规则行"""
    sorted_v4 = sorted(ipv4_nets, key=lambda n: (n.network_address, n.prefixlen))
    sorted_v6 = sorted(ipv6_nets, key=lambda n: (n.network_address, n.prefixlen))

    lines = []
    for net in sorted_v4:
        lines.append(f"IP-CIDR,{net.with_prefixlen},no-resolve")
    for net in sorted_v6:
        lines.append(f"IP-CIDR6,{net.with_prefixlen},no-resolve")
    return lines


def main():
    if not SOURCES:
        print("[错误] 未配置任何有效来源", file=sys.stderr)
        sys.exit(1)

    ipv4_nets, ipv6_nets = collect(SOURCES)

    if not ipv4_nets and not ipv6_nets:
        print("[错误] 未获取到任何有效网段，放弃写出文件，保留旧文件不变", file=sys.stderr)
        sys.exit(1)

    lines = build_lines(ipv4_nets, ipv6_nets)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[完成] 共写出 {len(lines)} 条规则（ipv4: {len(ipv4_nets)}, ipv6: {len(ipv6_nets)}）")
    print(f"[完成] 输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
