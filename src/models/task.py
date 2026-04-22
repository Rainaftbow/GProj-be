from datetime import datetime, timezone

from src.init import db


class Task(db.Model):
    """任务表模型"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userId = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    fileName = db.Column(db.String(255), nullable=False)
    filePath = db.Column(db.String(255), nullable=False)
    fileSize = db.Column(db.String(50), nullable=False)
    fileMD5 = db.Column(db.String(32), nullable=False)
    fileSHA256 = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    progress = db.Column(db.Integer, nullable=False, default=0)
    createdAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updatedAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    score = db.Column(db.Float, nullable=True)
    isMalicious = db.Column(db.Boolean, nullable=True)
    duration = db.Column(db.Float, nullable=True)
    errorMessage = db.Column(db.Text, nullable=True)

    # vmName = db.Column(db.String(255), nullable=False)
    # vmSnapshot = db.Column(db.String(255), nullable=False, default="clean_base")
    
    def __init__(self, user_id, file_name, file_path, file_size, file_md5, file_sha256):
        self.userId = user_id
        self.fileName = file_name
        self.filePath = file_path
        self.fileSize = file_size
        self.fileMD5 = file_md5
        self.fileSHA256 = file_sha256
    
    def update_status(self, status, progress=None):
        """更新任务状态"""
        self.status = status
        if progress is not None:
            self.progress = progress
        self.updatedAt = datetime.now(timezone.utc)
    
    def set_result(self, score, is_malicious, duration=None, error_message=None):
        """设置检测结果"""
        self.score = score
        self.isMalicious = is_malicious
        self.duration = duration
        self.errorMessage = error_message
        self.status = 'completed'
        self.progress = 100
        self.updatedAt = datetime.now(timezone.utc)
    
    # def set_vm_info(self, vmName, vmSnapshot):
    #     """设置虚拟机信息"""
    #     self.vmName = vmName
    #     self.vmSnapshot = vmSnapshot
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'userId': self.userId,
            'fileName': self.fileName,
            'filePath': self.filePath,
            'fileSize': self.fileSize,
            'fileMD5': self.fileMD5,
            'fileSHA256': self.fileSHA256,
            'status': self.status,
            'progress': self.progress,
            'createdAt': self.createdAt.isoformat() if self.createdAt else None,
            'updatedAt': self.updatedAt.isoformat() if self.updatedAt else None,
            'score': self.score,
            'isMalicious': self.isMalicious,
            # 'vmName': self.vmName,
            # 'vmSnapshot': self.vmSnapshot,
            'duration': self.duration,
            'errorMessage': self.errorMessage
        }
    
    def __repr__(self):
        return f'<Task {self.id}: {self.fileName}>'

# 删除HOOK
import os
from sqlalchemy import event

@event.listens_for(Task, 'after_delete')
def auto_delete_file_on_task_delete(_mapper, _connection, target):
    try:
        path = getattr(target, 'filePath', None)

        if path and os.path.exists(path):
            os.remove(path)
            print(f"[Hook]物理文件清理成功: {path}")
        else:
            print(f"[Hook]文件不存在: {path}")

    except Exception as e:
        print(f"[Hook]严重错误: 删除文件时崩溃，原因: {e}")