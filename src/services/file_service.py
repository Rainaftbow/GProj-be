import os
import hashlib
from flask import current_app
from flask_jwt_extended import current_user
from werkzeug.utils import secure_filename

from src.services import TaskService


def allowed_ext(filename):
    """检查文件扩展名是否允许"""
    if '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def calculate_file_hashes(file_path):
    """计算文件的MD5和SHA256哈希值"""
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as f:
        # 分块读取大文件
        for chunk in iter(lambda: f.read(4096), b''):
            md5_hash.update(chunk)
            sha256_hash.update(chunk)

    return md5_hash.hexdigest(), sha256_hash.hexdigest()


class FileService:
    def __init__(self):
        self.task_service = TaskService()

    def upload_file(self, file):
        """处理文件上传业务逻辑"""
        if not allowed_ext(file.filename):
            raise ValueError('不支持的文件类型')

        # 基础信息
        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        # 保存文件
        file.save(file_path)
        
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 计算文件哈希
            file_md5, file_sha256 = calculate_file_hashes(file_path)
            
            # 创建检测任务
            task = self.task_service.create_task(
                uid=current_user.id,
                file_name=filename,
                file_path=file_path,
                file_size=str(file_size),
                file_md5=file_md5,
                file_sha256=file_sha256
            )
            
            return task
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    
    def get_file_download_info(self, uid, task_id):
        task = self.task_service.get_task_by_tid(uid, task_id)

        """获取文件下载信息"""
        if not os.path.exists(task.filePath):
            raise ValueError('文件不存在')
        
        return {
            'fileName': task.fileName,
            'fileSize': task.fileSize,
            'downloadUrl': f'/api/files/download/{task.id}/raw'
        }

    def check_validation(self, uid, task_id):
        task = self.task_service.get_task_by_tid(uid, task_id)
        return task



