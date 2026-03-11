# 🎧 clipear

在 Windows 电脑上复制文章文字，一键推送到 iPhone，AirPods 自动朗读，全程无需触碰手机。

---

## 工作原理

```
Windows 复制文章文字
       ↓
  Ctrl+Shift+S
       ↓
清洗文本（去图片/链接/广告词等）
       ↓
按 300 字分段
       ↓
通过 Bark 推送到 iPhone
       ↓
iOS「朗读通知」功能自动朗读 🎧
```

- **文本清洗**：自动去除图片占位符、裸 URL、Markdown 标记、广告推广语句、全角空格等噪音
- **智能分段**：按句号边界切割，每段约 300 字，避免通知被 iOS 截断
- **动态间隔**：根据每段字数估算朗读时长，朗读完毕后再发下一段，保证顺序
- **随时中断**：按 `Ctrl+Shift+E` 立即停止当前文章的推送

---

## 环境要求

- Windows 10 / 11
- Python 3.9+
- iPhone（iOS 14+）
- AirPods 或其他蓝牙耳机（可选，有耳机时朗读体验更佳）

---

## 部署步骤

### 第一步：iPhone 安装 Bark 并获取推送地址

1. 在 App Store 搜索并安装 **Bark**（免费）
2. 打开 Bark，首页会显示你的专属推送地址，格式如下：
   ```
   https://api.day.app/xxxxxxxxxxxxxx
   ```
3. 复制这个地址，后面配置时会用到

### 第二步：iPhone 开启「朗读通知」

> 此步骤完成后，iPhone 收到 Bark 推送时会自动朗读通知内容，无需任何操作。

1. 打开「**设置**」→「**辅助功能**」→「**朗读内容**」
2. 开启「**朗读通知**」
3. 建议同时开启「**仅在使用耳机时**」，这样只有 AirPods 在耳时才会朗读，不影响他人

### 第三步：Windows 安装依赖

```bash
pip install -r requirements.txt
```

> ⚠️ `keyboard` 库监听全局热键需要**管理员权限**，请以管理员身份运行终端。

### 第四步：填写配置文件

复制示例配置并填入你的 Bark 地址：

```bash
cp config.example.yaml config.yaml
```

打开 `config.yaml`，将 `bark.url` 替换为第一步获取的地址：

```yaml
bark:
  url: "https://api.day.app/你的token"  # ← 修改这里
```

其他参数保持默认即可，根据需要再调整（详见下方配置说明）。

### 第五步：启动程序

以**管理员身份**打开 PowerShell 或命令提示符，进入项目目录后运行：

```bash
python iphone_reader.py
```

看到以下输出说明启动成功：

```
2026-03-10 10:00:00 [INFO] clipear 启动
2026-03-10 10:00:00 [INFO] 操作说明：复制文章文字后按 Ctrl+SHIFT+S 开始朗读，按 Ctrl+SHIFT+E 停止
2026-03-10 10:00:00 [INFO] 热键已注册 — 开始：Ctrl+SHIFT+S　结束：Ctrl+SHIFT+E
```

---

## 日常使用

| 步骤 | 操作 |
|------|------|
| ① | 在浏览器 / 微信 / 读书 App 中，**全选并复制**文章正文 |
| ② | 按 **`Ctrl+Shift+S`** 触发推送 |
| ③ | iPhone 收到通知，AirPods 自动开始朗读 🎧 |
| ④ | 中途想停止，按 **`Ctrl+Shift+E`** 即可 |

> **提示**：复制前不需要做任何清理，程序会自动去除图片、链接、广告等内容。

---

## 配置说明

`config.yaml` 所有可配置项：

```yaml
bark:
  url: "https://api.day.app/your_token"   # Bark 推送地址（必填）

logging:
  file: "logs/reader.log"                 # 日志文件路径，按天自动滚动

split:
  chars_per_segment: 300                  # 每段字数上限，建议 200～400

reading:
  speed_cps: 4.5        # 朗读速度（字/秒），Siri 语速快可调大，慢可调小
  buffer_seconds: 2.0   # 每段朗读结束后的额外缓冲（秒），网络差可调大

cleaner:
  ad_keywords:          # 包含这些词的整行会被删除，可自行添加
    - "长按关注"
    - "点击阅读原文"
    - "广告"
    - "推广"
    # ... 更多关键词
```

**调整朗读速度**：如果总感觉下一段来得太早或太晚，先调 `speed_cps`：
- 朗读还没结束下一段就来了 → 调小 `speed_cps`（如 `3.5`）
- 朗读结束后等待太久 → 调大 `speed_cps`（如 `5.5`）

---

## 项目结构

```
clipear/
├── iphone_reader.py      # 主入口，while True 监听热键
├── config.py             # 配置加载与校验
├── config.yaml           # 用户配置文件（本地保留，不提交 Git）
├── config.example.yaml   # 配置模板（提交 Git，供参考）
├── cleaner.py            # 文本清洗（去噪音、广告词过滤）
├── splitter.py           # 按句子边界分段
├── notifier.py           # Bark 推送封装（含重试）
├── scheduler.py          # 分段发送调度，动态 sleep，支持中断
├── hotkey.py             # 全局热键注册（Ctrl+Shift+S / E）
├── clipboard.py          # 剪贴板读取
├── logger.py             # 日志初始化（屏幕+文件按天滚动）
├── requirements.txt
├── .gitignore
└── logs/                 # 日志目录（自动创建，不提交 Git）
    └── reader.log
```

---

## 常见问题

**Q：按热键没有反应？**
确认程序是以**管理员身份**运行的，`keyboard` 库需要管理员权限才能监听全局热键。

**Q：推送收到了但没有自动朗读？**
检查 iPhone「设置 → 辅助功能 → 朗读内容 → 朗读通知」是否已开启；若开启了「仅耳机时」，确认 AirPods 已连接并佩戴。

**Q：微信公众号文章复制后内容很乱？**
网页端复制（在浏览器打开公众号文章）比在微信 App 内复制干净很多，推荐用浏览器打开后全选复制。

**Q：朗读顺序乱掉了？**
适当增大 `buffer_seconds`（如改为 `3.0`），给网络抖动留更多余量。

**Q：想添加自定义广告词？**
在 `config.yaml` 的 `cleaner.ad_keywords` 列表中追加即可，无需修改代码，改完重启程序生效。
