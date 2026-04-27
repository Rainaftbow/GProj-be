import eventlet
eventlet.monkey_patch()

import os
from pathlib import Path
from dotenv import load_dotenv
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path, override=False)

import redis
from flask import Flask, jsonify
from flask_cors import CORS
from celery import Celery

from src.init_instance import db, jwt, redis_client
from src.config import config
from src.services import UserService


def create_app(config_name=None):
    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    redis_url = app.config.get('REDIS_URL')
    redis_client.connection_pool = redis.ConnectionPool.from_url(
        redis_url, decode_responses=True
    )
    
    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    # jwt黑名单与全局拦截器
    user_service = UserService()

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token_in_redis = redis_client.get(jti)
        return token_in_redis is not None

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return user_service.get_user_by_id(identity)

    @jwt.user_lookup_error_loader
    def custom_user_lookup_error(_jwt_header, _jwt_data):
        return jsonify({'error': '用户不存在'}), 404

    # 异常处理
    @jwt.invalid_token_loader
    def invalid_token_callback(_error_string):
        return jsonify({"error": "无效token"}), 400

    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return jsonify({"error": "无效token"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(_jwt_header, _jwt_payload):
        return jsonify({"error": "无效token"}), 401

    # 创建上传目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 注册蓝图
    from src.routes.users import users_bp
    from src.routes.tasks import tasks_bp
    from src.routes.files import files_bp

    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(tasks_bp, url_prefix='/api/v1/tasks')
    app.register_blueprint(files_bp, url_prefix='/api/v1/files')

    # 错误处理
    from werkzeug.exceptions import RequestEntityTooLarge
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_big(_e):
        return jsonify({
            "error": '单个文件上传大小上限是 {} MB'.format(round(app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024), 2)),
        }), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({'error': 'Internal server error'}), 500

    # 健康检查端点
    @app.route('/api/v1/health')
    def health_check():
        return jsonify({'status': 'healthy'}), 200

    return app

def make_celery(app=None):
    """创建Celery应用"""
    app = app or create_app()
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )

    celery.conf.update(
        beat_schedule={
            'auto-clean-uploads-task': {
                'task': 'clean_uploads',
                'schedule': app.config['SCHEDULER']
            },
        }
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# 创建应用实例
app = create_app()

celery = make_celery(app)
from src.workers import tasks

if __name__ == '__main__':
    # 本地调试
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])