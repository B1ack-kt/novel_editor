"""
AI协同小说编辑器 - 全局常量定义
所有常量均来自PRD文档，不可随意修改
"""

# === 应用信息 ===
APP_NAME = "AI协同小说编辑器"
APP_VERSION = "1.0.0"
APP_ORG = "NovelEditor"

# === 存储相关 ===
DEFAULT_STORAGE_DIR = "NovelEditor"
BACKUP_MAX_VERSIONS = 10           # 保留最近10个版本
BACKUP_INTERVALS = [5, 10, 30]     # 可选备份频率(分钟)
BACKUP_INTERVAL_DEFAULT = 10       # 默认10分钟
DEFAULT_BACKUP_DIR_NAME = "backup"
DEFAULT_EXPORT_DIR_NAME = "exports"
ENCRYPTED_FILE_EXT = ".enc"
ENCRYPTED_BACKUP_EXT = ".nev"      # 加密备份包后缀
ENCRYPTED_KEY_EXT = ".key"         # 密钥文件后缀

# === 加密相关 ===
AES_KEY_SIZE = 32                   # AES-256, 32字节
AES_IV_SIZE = 16                    # CBC模式IV, 16字节
PBKDF2_ITERATIONS = 100000          # PBKDF2迭代次数
PBKDF2_HASH = "sha256"
SALT_SIZE = 32                      # 盐值长度

# === 密码相关 ===
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 64

# === 模型预设 ===
PRESET_MODELS = {
    "GPT-3.5": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model_type": "openai",
        "parameters": {"model": "gpt-3.5-turbo", "temperature": 0.7}
    },
    "GPT-4": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model_type": "openai",
        "parameters": {"model": "gpt-4", "temperature": 0.7}
    },
    "Claude-3": {
        "api_url": "https://api.anthropic.com/v1/messages",
        "model_type": "claude",
        "parameters": {"model": "claude-3-opus-20240229", "max_tokens": 4096}
    },
    "文心一言": {
        "api_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro",
        "model_type": "wenxin",
        "parameters": {"temperature": 0.7}
    },
    "通义千问": {
        "api_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "model_type": "tongyi",
        "parameters": {"model": "qwen-turbo", "temperature": 0.7}
    },
    "Llama": {
        "api_url": "http://localhost:8080/v1/chat/completions",
        "model_type": "llama",
        "parameters": {"temperature": 0.7}
    },
    "ChatGLM": {
        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model_type": "chatglm",
        "parameters": {"model": "glm-4", "temperature": 0.7}
    }
}

# === API调用控制 ===
API_TIMEOUT_DEFAULT = 30           # 默认超时秒数
API_CALL_RATE_LIMIT = 5            # 每分钟最大请求数(默认)
API_LOG_RETENTION_DAYS = 7         # 日志保留天数

# === 预警相关 ===
WARNING_TYPES = {
    "character_conflict": "人设冲突",
    "world_conflict": "世界观矛盾",
    "plot_hole": "情节逻辑漏洞",
    "repetition": "重复表述",
    "unreferenced_setting": "设定未引用"
}

WARNING_AGGRESSIVENESS = {
    "high": "全场景预警+建议",
    "medium": "仅预警+章节结尾建议",
    "low": "仅手动召唤Agent"
}

# 预警样式默认配置
DEFAULT_WARNING_STYLE = {
    "marker_type": "underline",     # underline / wavy / highlight
    "color": "#FF0000",             # 默认红色
    "opacity": 0.5                  # 默认50%透明度
}

# === 建议相关 ===
SUGGESTION_MAX_VERSIONS = 5         # 每条建议最多5个版本
SUGGESTION_TYPES = ["情节分支", "细节补充", "文笔优化"]
SUGGESTION_PANEL_MAX_RATIO = 0.33   # 建议栏最多占编辑区1/3

# === 编辑器相关 ===
WORD_COUNT_RULES = {
    "include_all": "包含标点/空格",
    "text_only": "仅文字"
}

FONT_SIZE_MIN = 10
FONT_SIZE_MAX = 24
FONT_SIZE_DEFAULT = 14

# === 导出格式 ===
EXPORT_FORMATS = ["TXT", "DOCX", "PDF", "EPUB"]
ENCRYPTED_EXPORT_FORMAT = "NEV"     # .nev加密备份包

# === 版权标记 ===
CONTENT_TYPES = {
    "original": "纯原创",
    "ai_generated": "AI生成",
    "ai_assisted": "AI辅助修改"
}

# === 设定管理 ===
CHARACTER_DEFAULT_FIELDS = ["姓名", "性格", "外貌", "背景", "禁忌", "特殊技能"]
FIELD_TYPES = ["text", "image", "dropdown", "richtext"]
WORLD_CATEGORIES = ["魔法体系", "社会制度", "地理设定", "时间线"]

# === 文件系统 ===
SUPPORTED_FILESYSTEMS = ["NTFS", "FAT32", "APFS"]
