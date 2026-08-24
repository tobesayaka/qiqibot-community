# QiqiBot

基于 NoneBot2 + NapCatQQ 的 QQ 机器人。
用于 Mabinogi CN服

## 技术栈

- NoneBot2 v2.5.0
- NapCatQQ v4.18.19
- OneBot v11 协议
- Python 3.12+
- SQLite（数据存储）

## 快速开始

### 方式一：本地开发

```bash
# 安装依赖
uv sync

# 复制配置模板并填写
cp .env.template .env.dev
# 编辑 .env.dev，填写 SUPERUSERS 和 ONEBOT_ACCESS_TOKEN

# 启动（需要先启动 NapCatQQ）
uv run python bot.py
```

### 方式二：Docker Compose 部署

NapCatQQ 和 NoneBot 一起编排，开箱即用。

```bash
# 复制配置模板并填写
cp .env.docker .env
# 编辑 .env，填写 QQ_ACCOUNT、SUPERUSERS、ONEBOT_ACCESS_TOKEN

# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f bot

# 停止
docker compose down
```

首次启动 NapCat 会在终端显示登录二维码，扫码后即可使用。

持久化目录：
- `data/` — 数据库文件
- `downloads/` — 视频临时文件（自动清理）
- `napcat/` — NapCatQQ 配置和登录态

## 插件用法
所有指令均为自然语言，直接在聊天中发送即可，无需斜杠前缀。

### 视频下载

发送 `下载` + 视频链接，支持抖音、B站、YouTube 等平台（基于 yt-dlp）。

```
下载 https://v.douyin.com/xxxxx
```

### 问答知识库

支持自然语言触发的问答增删改查，可记录文字和图片。

| 操作 | 触发方式 |
|------|---------|
| 添加 | `记一下`、`添加问答`、`我来加一条`（交互式），或 `记一下 问题 \| 答案`（一步式） |
| 搜索 | `查一下 <关键词>`、`搜 <关键词>` |
| 列表 | `看看问答`、`最近都记了啥` |
| 详情 | `第<id>条`、`#<id>` |
| 编辑 | `改一下第<id>条` |
| 删除 | `删掉第<id>条` |
| 帮助 | `帮助`、`怎么用` |

### 游戏道具查询（OptionSet）

查询洛奇游戏附魔道具数据，数据来自 prilus 资源服务器。

| 操作 | 触发方式 |
|------|---------|
| 搜索 | `opt <关键词>`，如 `opt 暴风` |
| 精准查询 | `opt <id>`，如 `opt 10709` |

搜索结果以图片形式返回，单条直接展示详情，多条显示列表供选择。

### 制作配方查询（Production）

查询洛奇游戏制作配方，含材料、套装效果、随机属性，数据来自 prilus 资源服务器。

| 操作 | 触发方式 |
|------|---------|
| 搜索 | `prd <关键词>`，如 `prd 释魂 琴` |
| 通配符搜索 | `prd 释魂*琴`，用 `*` 作通配符 |
| 精准查询 | `prd <id>`，如 `prd 13814` |

搜索支持两种模糊匹配：
- **分词模式**：空格分隔，按顺序匹配，如 `prd 释魂 杆` → 释魂者魂域操纵杆
- **通配符模式**：含 `*` 时直接作通配符，如 `prd 释魂*琴` → 释魂者幽咽里拉琴

详情以图片形式返回，含成品图标、材料（带图标和制作方式）、套装效果、随机属性。

### 白名单权限控制

所有插件受白名单控制，只有 `config/allowlist.yml` 中的 QQ 用户/QQ 群才能触发。

```yaml
users:
  - 123456789
groups:
  - 987654321
```

修改后即时生效，无需重启 bot。

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DRIVER` | NoneBot 驱动器 | `~fastapi+~websockets` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8081` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `SUPERUSERS` | 管理员 QQ 号列表 | — |
| `ONEBOT_WS_URLS` | OneBot WebSocket 地址 | `ws://127.0.0.1:3001/onebot/v11/ws` |
| `ONEBOT_ACCESS_TOKEN` | OneBot 访问令牌 | — |
| `VIDEO_PROXY` | 视频下载代理 | — |
| `VIDEO_COOKIES_BROWSER` | 浏览器 cookies 来源 | `chrome` |
| `VIDEO_SAVE_DIR` | 视频临时目录 | `downloads` |
| `QA_LIST_LIMIT` | 问答列表最大条数 | `10` |
| `QA_MAX_IMAGES` | 每条问答最多图片数 | `5` |

完整模板见 [.env.template](.env.template)，Docker 部署见 [.env.docker](.env.docker)。

## 项目结构

```
qiqibot/
├── bot.py                        # NoneBot2 启动入口
├── pyproject.toml                # 项目依赖声明
├── Dockerfile                    # Docker 镜像构建
├── docker-compose.yml            # Docker Compose 编排（NapCat + Bot）
├── config/
│   └── allowlist.yml             # 白名单配置
├── middlewares/
│   └── anti_risk.py              # 随机延迟中间件（防风控）
├── plugins/
│   ├── demo/                     # 复读机插件
│   ├── qa/                       # 问答知识库插件
│   ├── video/                    # 视频下载插件
│   ├── optionset/                # 游戏道具查询插件
│   └── production/               # 制作配方查询插件
├── utils/
│   ├── optionset.py              # 道具 DB 查询
│   ├── production.py             # 配方 DB 查询
│   ├── permission.py             # 白名单权限控制
│   └── video.py                  # yt-dlp 下载工具
├── data/
│   ├── optionset.db              # 道具数据（1821 条附魔）
│   └── production.db             # 配方数据（1251 条配方 + 3200+ 物品图片）

```

## 插件开发

插件统一放在 `plugins/` 目录下，每个插件为一个独立目录。NoneBot2 通过 `pyproject.toml` 中的 `plugin_dirs` 自动发现加载。

```
plugins/my_plugin/
├── __init__.py               # 插件元数据
├── config.py                 # 插件配置（Pydantic BaseModel）
└── handlers.py               # 消息处理器
```

所有插件 handler 注册时需传入 `rule=is_allowed()` 以启用白名单控制：

```python
from utils.permission import is_allowed
handler = on_regex(r"\A...", priority=15, block=True, rule=is_allowed())
```
