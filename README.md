# AI协同小说编辑器 v1.0.0
(使用agent完成，目前第一版；提示：缺陷众多，持续调优中)
> 一款以「Agent 深度协同 + 本地化隐私保护」为核心的自用小说编辑器

---

## 特性

- **100%本地存储** - 所有数据存储在本地磁盘，绝无云端上传
- **AES-256加密** - 全数据AES-256-CBC加密保护，支持项目独立密码
- **双模式编辑** - 富文本/Markdown一键切换，内容实时同步
- **Agent主动预警** - 人设冲突/世界观矛盾/情节漏洞/重复表述/设定未引用 全覆盖
- **多AI模型接入** - 预设GPT/Claude/文心/通义等模型，支持自定义API
- **设定库管理** - 人设库/世界观库，支持自定义字段与字段联动
- **加密备份分享** - .nev加密备份包，支持外接硬盘迁移
- **多格式导出** - TXT/DOCX/PDF/EPUB，可选版权标记

## 系统要求

- Windows 10+ (64位) / Mac OS 12+
- Python 3.10+
- CPU i5/AMD Ryzen 5，内存 8GB+
- 硬盘剩余空间 >= 10GB

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：
| 包名 | 版本 | 用途 |
|------|------|------|
| PyQt6 | >=6.5.0 | GUI桌面框架 |
| pycryptodome | >=3.19.0 | AES-256加密 |
| markdown | >=3.5.0 | Markdown渲染 |
| python-docx | >=1.1.0 | Word文档导出 |
| reportlab | >=4.0.0 | PDF导出 |
| ebooklib | >=0.18.0 | EPUB电子书导出 |
| httpx | >=0.25.0 | AI模型API通信 |
| Pygments | >=2.17.0 | 代码高亮(Markdown) |

### 2. 启动应用

```bash
cd novel_editor
python main.py
```

### 3. 首次使用流程

1. 启动后设置登录密码 + 预留找回方式（安全问题/邮箱）
2. 进入「设置 → 模型管理」添加AI模型并测试连接
3. 新建小说项目，设置存储路径（可选项目独立加密）
4. 进入设定库添加核心人设/世界观规则
5. 选择编辑模式（富文本/Markdown），开始创作

### 4. 日常创作流程

1. 启动 → 输入密码登录 → 打开项目
2. 编辑正文（Agent实时预警 + 底部字数统计）
3. 卡壳/需要时手动召唤Agent (Ctrl+A) 或等待主动建议
4. 完成章节后自动备份（可设置5/10/30分钟频率）

## 项目结构

```
novel_editor/
├── main.py                    # 入口文件
├── requirements.txt           # 依赖列表
├── config/                    # 全局配置
│   ├── constants.py           # 常量定义
│   └── settings.py            # 配置管理(单例)
├── core/                      # 核心基础设施
│   ├── app.py                 # 应用主控制器
│   ├── auth.py                # 认证模块
│   ├── crypto.py              # AES-256加密
│   ├── storage.py             # 本地存储IO
│   ├── project_manager.py     # 项目管理
│   └── backup.py              # 备份与回滚
├── models/                    # 数据模型
│   ├── project.py             # 项目
│   ├── chapter.py             # 章节
│   ├── character.py           # 人设
│   ├── world.py               # 世界观规则
│   ├── warning.py             # 预警
│   └── backup_item.py         # 备份记录
├── ui/                        # 用户界面
│   ├── main_window.py         # 主窗口
│   ├── login_dialog.py        # 登录对话框
│   ├── project_panel.py       # 项目/章节面板
│   ├── editor/                # 编辑器组件
│   │   ├── text_editor.py     # 富文本编辑器
│   │   ├── markdown_editor.py # Markdown编辑器
│   │   ├── editor_toolbar.py  # 工具栏
│   │   └── status_bar.py      # 状态栏
│   ├── agent/                 # Agent UI
│   │   ├── warning_panel.py   # 预警面板
│   │   ├── suggestion_bar.py  # 建议栏
│   │   └── agent_menu.py      # Agent菜单
│   ├── settings/              # 设置界面
│   │   ├── model_manager.py   # 模型管理
│   │   └── warning_config.py  # 预警配置
│   ├── settings_lib/          # 设定库界面
│   │   ├── character_lib.py   # 人设库
│   │   └── world_lib.py       # 世界观库
│   └── dialogs/               # 对话框
│       ├── export_dialog.py   # 导出对话框
│       └── backup_dialog.py   # 备份管理
├── agent/                     # Agent核心引擎
│   ├── model_client.py        # AI模型API客户端
│   ├── context_builder.py     # 上下文构建器
│   ├── knowledge_base.py      # 创作知识库
│   ├── warning_engine.py      # 预警检测引擎
│   └── suggestion_engine.py   # 主动建议引擎
└── utils/                     # 工具模块
    ├── word_counter.py         # 字数统计
    └── export_utils.py         # 多格式导出
```

## 安全说明

- 所有数据采用 **AES-256-CBC** 加密存储
- 密钥通过 **PBKDF2-HMAC-SHA256** (10万次迭代) 派生
- API密钥加密存储，不写入明文配置文件
- 所有AI通信仅通过用户本地网络直连模型接口，不经过任何中间服务器
- 备份文件支持双重加密（主密码 + 分享密码）
- 定期清理API调用日志（默认保留7天）

## 技术栈

- 语言: Python 3.10+
- GUI: PyQt6
- 加密: pycryptodome
- API通信: httpx
- 文档导出: python-docx / reportlab / ebooklib
- Markdown: python-markdown

## 许可证

自用软件，保留所有权利。
