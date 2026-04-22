import os
from datetime import timedelta
from celery.schedules import crontab

# 全局基础路径/src/
basedir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.dirname(basedir)

class Config:
    """基础配置类"""
    # 基础安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=10)
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(root_dir, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'exe', 'dll', 'sys'}
    ALLOWED_NUMS_PER_USER = 20
    # 查询排序字段限制
    ALLOWED_SORT_FIELD = {'createdAt', 'updatedAt', 'progress', 'score', 'duration'}
    # 文件有效期
    FILE_EXPIRED_DURATION = timedelta(minutes=10)
    # Celery Beat 配置自动清理uploads中过期文件
    # 计时器
    SCHEDULER = crontab(minute='*/1')

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Celery配置
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # ML模块配置
    ML_MODULE_URL = os.environ.get('ML_MODULE_URL') or 'http://localhost:8000/api/v1'
    
    # API组合字典路径
    TOP_50_API_FILE = os.path.join(basedir, 'utils', 'top_50_api_2gram.txt')

    # ==================== 特征提取配置 ====================
    FEATURE_CONFIG = {
        # 正常节区名称（PE文件）
        "NORMAL_SECTIONS": {
            b".text", b".data", b".rsrc", b".bss",
            b".rdata", b".reloc", b".idata"
        },

        # 连续可打印字符长度阈值
        "NUM_PRINTABLE_STR_LEN": 4,

        # 可疑字符串模式（正则表达式）
        "SUSPICIOUS_PATTERNS": br"(?i)(cmd\.exe|powershell|http|https|SOFTWARE\\\\|shell|inject)",
    }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL')

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """生产环境配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}