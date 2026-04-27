from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

from src.init_instance import db


class User(db.Model):
    """用户表模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userRole = db.Column(db.String(50), nullable=False, default='user')
    userName = db.Column(db.String(100), nullable=False, unique=True)
    passwordHash = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # 关系
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, user_name, password, user_role='user'):
        self.userName = user_name
        self.set_password(password)
        self.userRole = user_role
    
    def set_password(self, new_password):
        """设置密码哈希"""
        self.passwordHash = generate_password_hash(new_password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.passwordHash, password)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'userRole': self.userRole,
            'userName': self.userName,
            'createdAt': self.createdAt.isoformat() if self.createdAt else None
        }
    
    def __repr__(self):
        return f'<User {self.userName}>'