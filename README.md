# 兽聚日历（furry）

AstrBot 插件：随机发送兽图，并分页展示近期兽展列表（每页 5 条）。

## 指令

| 指令 | 说明 |
| --- | --- |
| `毛图` | 随机发送一张兽图 |
| `兽聚` | 拉取近期兽展列表，发送第 1 页（每页 5 条） |
| `下一页` | 查看兽展列表下一页（分页状态按会话独立维护） |

## 配置

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `FCC 接口令牌` | string | 空 | 调用兽展接口所需的令牌，前往 https://dashboard.furrycons.cn 应用中心创建应用后获取 API Key |

> 旧版本配置键为 `fcc_api_token`，插件已兼容读取，旧配置无需手动迁移。

## 使用的 API

### 1. 随机兽图

| 项 | 内容 |
| --- | --- |
| 接口 | `GET https://api.furry.ist/furry-img/?format=json` |
| 鉴权 | 无 |
| 使用字段 | `url`（图片直链） |

### 2. 兽展日历 · 最近展会

| 项 | 内容 |
| --- | --- |
| 接口 | `GET https://api.furrycons.cn/open/event/recent` |
| 文档 | https://docs.furrycons.cn/docs/api/event/recent |
| 鉴权 | 请求头 `Authorization`，值为上方配置项 `FCC 接口令牌` |

**请求参数**

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `keepOld` | `true` | 近期无数据时返回过期数据填充 |
| `current` | 1, 2, 3 … | 页码 |
| `pageSize` | 50 | 单次请求条数 |

**使用字段**

| 字段 | 说明 |
| --- | --- |
| `total` / `current` / `pageSize` | 分页信息 |
| `data[].id` | 展会 ID（去重） |
| `data[].name` | 展会名称 |
| `data[].scale` | 规模 |
| `data[].startDate` / `data[].endDate` | 起止时间 |
| `data[].region` / `data[].address` | 地区 · 地址 |
| `data[].thumbnail` | 展会封面图 |
| `data[].organization.name` | 主办方名称 |
| `data[].organization.logoUrl` | 主办方 Logo |
| `data[].url` | 展会详情页链接 |
