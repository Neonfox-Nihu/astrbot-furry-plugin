# 兽聚日历（furry）

一个 [AstrBot](https://astrbot.app) 插件：随机发送兽图，并以「合并转发」形式分页展示近期兽展（Furry Convention）日历，支持展会封面图与主办方 Logo。

- 插件 ID：`furry`
- 显示名：兽聚日历
- 版本：2.2.0

## 功能指令

| 指令 | 说明 |
| --- | --- |
| `毛图` | 随机发送一张兽图 |
| `兽聚` | 拉取近期兽展列表并发送第 1 页（每页 5 条） |
| `下一页` | 查看兽展列表的下一页（分页状态按会话独立维护） |

## 使用的 API

插件本身不产生数据，也不代理任何请求，全部数据来自以下公开 HTTP 接口。

### 1. 随机兽图

| 项 | 内容 |
| --- | --- |
| 接口 | `GET https://api.furry.ist/furry-img/?format=json` |
| 鉴权 | 无需鉴权 |
| 用途 | 为 `毛图` 指令提供随机图片 |
| 使用字段 | `url`（图片直链） |

### 2. 兽展日历 · 最近展会

| 项 | 内容 |
| --- | --- |
| 接口 | `GET https://api.furrycons.cn/open/event/recent` |
| 文档 | https://docs.furrycons.cn/docs/api/event/recent |
| 鉴权 | 需在请求头携带 `Authorization`（值为 FCC 应用令牌） |
| 用途 | 为 `兽聚` / `下一页` 提供近期（约 30 天内）兽展数据 |

**请求参数**

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `keepOld` | `true` | 当近期无数据时，返回过期数据作为填充 |
| `current` | 1, 2, 3 … | 页码，逐页拉取直至取满 |
| `pageSize` | 50 | 单次请求条数 |

**使用到的响应字段**

| 字段 | 说明 |
| --- | --- |
| `total` / `current` / `pageSize` | 分页元信息，用于判断是否取满 |
| `data[].id` | 展会唯一 ID（用于去重） |
| `data[].name` | 展会名称 |
| `data[].scale` | 展会规模 |
| `data[].startDate` / `data[].endDate` | 起止时间（ISO 8601） |
| `data[].region` / `data[].address` | 地区与详细地址 |
| `data[].thumbnail` | 展会封面图直链 |
| `data[].detail` | 展会详情文案 |
| `data[].organization.name` | 主办方名称 |
| `data[].organization.logoUrl` | 主办方 Logo 直链 |
| `data[].url` | 展会详情页链接 |

## 工作流程

```
用户发送「兽聚」
      │
      ▼
_get_upcoming_events()  ── 命中缓存(30min)? ── 是 ──▶ 直接返回
      │ 否
      ▼
分页请求 recent 接口（current=1,2,3…，pageSize=50）
      │  按 id 去重，累计条数 ≥ total 或单页不足时停止
      ▼
按 startDate 升序排序，写入缓存
      │
      ▼
_send_page(page)  ── 取第 page 页（每页 5 条）
      │
      ▼
逐条构造合并转发节点：
   封面图(thumbnail) → 文字信息 → 主办方 Logo(logoUrl)
      │
      ▼
追加页脚「第 x/y 页 (共 N 场展会)」并发送
```

## 配置项

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `FCC 接口令牌` | string | 空 | 调用兽展接口所需的令牌。前往 https://dashboard.furrycons.cn 应用中心创建应用后获取 API Key |

> 旧版本配置键为 `fcc_api_token`，插件已做兼容读取，旧配置无需手动迁移。

## 内部常量

| 常量 | 值 | 含义 |
| --- | --- | --- |
| `PAGE_SIZE` | 5 | 每页展示条数 |
| `FETCH_PAGE_SIZE` | 50 | 单次请求条数 |
| `MAX_FETCH_PAGES` | 20 | 分页拉取安全上限 |
| `CACHE_TTL` | 1800 | 展会数据缓存时间（秒） |

## 项目结构

```
furry/
├── main.py            # 插件主逻辑
├── metadata.yaml      # 插件元信息
├── _conf_schema.json  # 配置项定义
└── README.md          # 本文档
```

## 安装

1. 将本目录放入 AstrBot 的插件目录（如 `data/plugins/furry/`）。
2. 重启 AstrBot 或在 WebUI 中重载插件。
3. 在插件配置中填入 `FCC 接口令牌`。

## 环境依赖

- Python 3.10+
- `httpx`（AstrBot 运行时已内置）
- AstrBot `>= 3.x`

## 说明与免责

- 图片地址由接口返回并已做过压缩优化，部分宣传图体积较大，插件仅转发图片直链，不下载、不缓存图片本体。
- 展会数据版权归 [兽展日历（FCC）](https://www.furrycons.cn) 所有，本项目仅作数据展示用途。
- 接口字段可能随时增删，若上游变更导致异常，请以官方文档为准。
