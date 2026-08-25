# v2fly cn.txt 中 3 条 regexp 规则的转换

## 原始规则（来自 cn.txt）

```
regexp:.+\.awsdns-cn-[0-9][0-9]\.(biz|com|net|top)$:@cn
regexp:.+\.awsdns-cn-[0-9][a-e0-9]\.cn$:@cn
regexp:^.+-mihayo\.akamaized\.net$:@cn
```

---

## ① Shadowrocket 语法

`DOMAIN-REGEX,<正则>`，可直接放进规则列表文件（如 .list）：

```
DOMAIN-REGEX,.+\.awsdns-cn-[0-9][0-9]\.(biz|com|net|top)$
DOMAIN-REGEX,.+\.awsdns-cn-[0-9][a-e0-9]\.cn$
DOMAIN-REGEX,^.+-mihayo\.akamaized\.net$
```

---

## ② sing-box 语法

`domain_regex` 数组，JSON 中反斜杠需转义为 `\\`：

```json
{
  "version": 2,
  "rules": [
    {
      "domain_regex": [
        ".+\\.awsdns-cn-[0-9][0-9]\\.(biz|com|net|top)$",
        ".+\\.awsdns-cn-[0-9][a-e0-9]\\.cn$",
        "^.+-mihayo\\.akamaized\\.net$"
      ]
    }
  ]
}
```

---

## 备注

`DOMAIN-REGEX` 是 Shadowrocket 较新版本才支持的规则类型，若客户端版本较旧不识别该关键字，规则会被静默忽略而不是报错，建议先小范围测试确认能生效。
