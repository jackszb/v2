# category-ads-all.txt 中未处理的正则转换

`v2fly-ads.list` / `v2fly-ads.json` 生成时不包含源文件里的 `regexp:` 开头的行
（该文件中共 1 条）。这里把它转换成 Shadowrocket 和 sing-box 各自可用的语法，供需要时单独使用。

原始格式（来自 category-ads-all.txt）：

```
regexp:^speed\.(coe|open)\.ad\.[a-z]{2,6}\.prod\.hosts\.ooklaserver\.net$:@ads
```

转换方式：去掉 `regexp:` 前缀和结尾的 `:@ads` 标签，正则本身是标准 RE2 语法，元字符无需改写。

---

## ① Shadowrocket 语法

格式为 `DOMAIN-REGEX,<正则>`，可直接追加到规则列表文件中：

```
DOMAIN-REGEX,^speed\.(coe|open)\.ad\.[a-z]{2,6}\.prod\.hosts\.ooklaserver\.net$
```

---

## ② sing-box 语法

格式为 `domain_regex` 数组，JSON 字符串中的反斜杠已按 JSON 规范转义为 `\\`：

```json
{
  "version": 2,
  "rules": [
    {
      "domain_regex": [
        "^speed\\.(coe|open)\\.ad\\.[a-z]{2,6}\\.prod\\.hosts\\.ooklaserver\\.net$"
      ]
    }
  ]
}
```

---

## 备注

- 该正则匹配的是 Ookla Speedtest 相关的广告/统计域名（`speed.coe.ad.xx.prod.hosts.ooklaserver.net` 这一类）。
- `DOMAIN-REGEX` 是 Shadowrocket 较新版本才支持的规则类型，若客户端版本较旧不识别该关键字，
  规则会被静默忽略而不是报错，建议先小范围测试确认能生效。
