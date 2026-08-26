#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载多个 ipv4 / ipv6 网段列表，合并、去重、排序，
生成 Clash 规则格式的 geoip-!cn.list 文件到仓库根目录。

来源列表在 config/sources.txt 中配置，格式为：
    ipv4,<url>
    ipv6,<url>
增加或删除链接时只需编辑该文件，无需改动本脚本。
"""

import ipaddress
import os
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT_DIR / "config" / "sources.txt"
OUTPUT_FILE = ROOT_DIR / "geoip-!cn.list"

REQUEST_TIMEOUT = 30
REQUEST_RETRIES = 3


def load_sources(sources_file: Path):
    """读取配置文件，返回 [(type, url), ...] 列表"""
    sources = []
    if not sources_file.exists():
        print(f"[错误] 找不到配置文件: {sources_file}", file=sys.stderr)
        sys.exit(1)

    with sources_file.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",", 1)
            if len(parts) != 2:
                print(f"[警告] 第 {line_no} 行格式不正确，已跳过: {raw_line!r}")
                continue
            ip_type, url = parts[0].strip().lower(), parts[1].strip()
            if ip_type not in ("ipv4", "ipv6"):
                print(f"[警告] 第 {line_no} 行类型未知（应为 ipv4/ipv6），已跳过: {raw_line!r}")
                continue
            if not url:
                continue
            sources.append((ip_type, url))
    return sources


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


def parse_networks(text: str, expected_version: int):
    """从文本中解析出合法的 CIDR 网段"""
    nets = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            net = ipaddress.ip_network(line, strict=False)
        except ValueError:
            print(f"[警告] 无法解析的网段，已跳过: {line!r}")
            continue
        if net.version != expected_version:
            print(f"[警告] 网段版本与来源类型不符，已跳过: {line!r}")
            continue
        nets.append(net)
    return nets


def collect(sources):
    """按类型下载并解析所有来源，返回 (ipv4_set, ipv6_set)"""
    ipv4_nets = set()
    ipv6_nets = set()

    for ip_type, url in sources:
        print(f"[信息] 正在下载 [{ip_type}] {url}")
        text = download(url)
        if not text:
            continue
        version = 4 if ip_type == "ipv4" else 6
        nets = parse_networks(text, version)
        print(f"[信息] 解析到 {len(nets)} 条 {ip_type} 网段")
        if ip_type == "ipv4":
            ipv4_nets.update(nets)
        else:
            ipv6_nets.update(nets)

    return ipv4_nets, ipv6_nets


def build_lines(ipv4_nets, ipv6_nets):
    """去重后按网段大小排序，生成 Clash 规则行"""
    sorted_v4 = sorted(ipv4_nets, key=lambda n: (n.network_address, n.prefixlen))
    sorted_v6 = sorted(ipv6_nets, key=lambda n: (n.network_address, n.prefixlen))

    lines = []
    for net in sorted_v4:
        lines.append(f"IP-CIDR,{net.with_prefixlen},no-resolve")
    for net in sorted_v6:
        lines.append(f"IP-CIDR6,{net.with_prefixlen},no-resolve")
    return lines


def main():
    sources = load_sources(SOURCES_FILE)
    if not sources:
        print("[错误] 未配置任何有效来源", file=sys.stderr)
        sys.exit(1)

    ipv4_nets, ipv6_nets = collect(sources)

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
