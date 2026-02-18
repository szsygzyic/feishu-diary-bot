# 飞书日记机器人 (Feishu Diary Bot)

一个基于飞书开放平台的智能日记助手，支持语音、文字、图片等多种方式记录日记，并自动整理成规范的日记文档。

## 已实现功能

### 核心功能
- [x] **语音日记**：支持语音输入，自动转文字并生成日记
- [x] **文字日记**：支持文字输入记录日记
- [x] **智能整理**：使用AI自动整理日记内容，生成规范格式
- [x] **飞书文档**：自动创建飞书文档保存日记
- [x] **文档权限**：创建文档时自动赋予用户编辑和删除权限

### 命令功能
- [x] `/new` - 开始新的日记记录
- [x] `/diary` - 整理并生成今天的日记
- [x] `/list` - 列出所有日记文档（带删除链接）
- [x] `/delete <文档ID>` - 删除指定文档（同时删除数据库记录）
- [x] `/cleantest` - 一键清除所有测试文档和数据库记录
- [x] `/query` - 查询历史日记
- [x] `/help` - 显示帮助信息

### 媒体处理
- [x] **图片接收**：支持接收用户发送的图片
- [x] **图片保存**：下载并保存图片到本地
- [x] **媒体记录**：记录媒体文件信息到数据库

### 数据管理
- [x] **数据库存储**：使用SQLite存储日记记录
- [x] **对话管理**：管理用户对话状态
- [x] **文档ID关联**：保存飞书文档ID到数据库
- [x] **事件处理**：处理文档删除事件，同步删除数据库记录

## 未实现功能

### 图片插入（部分实现）
- [ ] **图片块创建**：已尝试实现，但飞书API限制较多
- [ ] **图片上传到文档**：已尝试实现，但遇到权限和参数问题
- [ ] **图片与文字混排**：暂未实现

### 视频功能
- [ ] **视频接收**：暂未实现
- [ ] **视频保存**：暂未实现
- [ ] **视频插入文档**：暂未实现（飞书文档API限制）

### 高级功能
- [ ] **日记模板**：支持多种日记模板（工作日报、旅行日记等）
- [ ] **统计分析**：日记习惯统计、月度/年度回顾
- [ ] **定时提醒**：每日定时提醒写日记
- [ ] **多平台同步**：支持多设备查看
- [ ] **导出功能**：导出为PDF、Word等格式
- [ ] **AI分析**：心情趋势分析、关键词提取
- [ ] **社交分享**：选择性分享日记到飞书群

## 技术栈

- **后端**：Python + FastAPI
- **数据库**：SQLite
- **AI服务**：OpenAI API（支持自定义配置）
- **部署**：支持本地部署和服务器部署

## 项目结构

```
feishu-diary-bot/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖包
├── src/
│   ├── api/
│   │   └── webhook.py     # 飞书Webhook接口
│   ├── handlers/
│   │   ├── base_handler.py    # 基础处理器
│   │   ├── text_handler.py    # 文字消息处理器
│   │   ├── voice_handler.py   # 语音消息处理器
│   │   └── media_handler.py   # 媒体文件处理器
│   ├── services/
│   │   ├── conversation_service.py  # 对话管理服务
│   │   ├── diary_service.py         # 日记服务
│   │   ├── feishu_doc_service.py    # 飞书文档服务
│   │   ├── llm_service.py           # LLM服务
│   │   ├── media_process_service.py # 媒体处理服务
│   │   └── message_service.py       # 消息服务
│   └── utils/
│       ├── config.py      # 配置管理
│       ├── database.py    # 数据库管理
│       └── logger.py      # 日志管理
└── data/                  # 数据目录
    └── uploads/          # 上传文件存储
```

## 配置说明

创建 `.env` 文件并配置以下环境变量：

```env
# 飞书应用配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_ENCRYPT_KEY=your_encrypt_key
FEISHU_VERIFICATION_TOKEN=your_verification_token

# OpenAI配置（用于日记整理）
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

## 安装和运行

1. 克隆项目
```bash
git clone https://github.com/yourusername/feishu-diary-bot.git
cd feishu-diary-bot
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填写配置
```

4. 运行应用
```bash
python main.py
```

## 飞书应用配置

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 配置权限：
   - `im:message:send` - 发送消息
   - `im:message:receive` - 接收消息
   - `docx:document` - 创建文档
   - `drive:file:read` - 读取文件
   - `drive:file:write` - 写入文件
   - `drive:permission` - 权限管理
4. 配置事件订阅：
   - 订阅 `im.message.receive_v1` 事件
   - 订阅 `drive.file.deleted_completely_v1` 事件（文档删除同步）
5. 发布应用并获取应用凭证

## 已知问题和限制

1. **图片插入限制**：飞书API对图片插入有较多限制，目前图片只能接收保存，无法自动插入到文档中
2. **视频不支持**：飞书文档API暂不支持视频插入
3. **权限问题**：旧版本创建的文档可能没有编辑权限，新版本已修复
4. **API限制**：飞书开放平台API有调用频率限制

## 开发计划

由于飞书API限制较多，建议后续开发方向：

1. **暂停飞书日记功能开发**（保持现有功能）
2. **将飞书机器人改造成其他实用功能**（如智能助手、文件转换器等）
3. **开发独立的Web应用**（不受平台限制，功能更自由）

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License
