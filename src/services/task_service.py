from redis.commands.search import field
from sqlalchemy import or_
from flask import current_app

from src.init_instance import db
from src.models import Task


class TaskService:
    """任务服务"""

    def create_task(self, uid, file_name, file_path, file_size, file_md5, file_sha256):
        """单用户创建任务"""
        task = Task.query.filter(
            Task.userId == uid,
            or_(
                Task.fileMD5 == file_md5,
                Task.fileSHA256 == file_sha256
            )
        ).first()

        if task:
            # 如果是空的异常任务，直接返回
            if task.score is None or task.isMalicious is None or task.duration is None:
                return task

            # 已有结果直接报错
            raise ValueError('该文件已检测，无需重复提交')

        if Task.query.filter_by(userId = uid).count() >= current_app.config['ALLOWED_NUMS_PER_USER']:
            raise ValueError('当前用户已有任务数量超出限制')

        # 创建任务
        task = Task(user_id=uid, file_name=file_name, file_path=file_path ,file_size=file_size, file_md5=file_md5, file_sha256=file_sha256)
        db.session.add(task)
        db.session.commit()

        return task

    def get_all_tasks_preview(self, uid, page=1, per_page=5, sort_params=None):
        """分页获取指定用户所有任务预览"""

        fields_to_query = (
            Task.id,
            Task.userId,
            Task.fileName,
            Task.status,
            Task.progress,
            Task.createdAt,
            Task.score,
            Task.isMalicious
        )

        # 允许字段设置
        allowed_sort_field = current_app.config.get('ALLOWED_SORT_FIELD') or \
                             {'createdAt', 'updatedAt', 'progress', 'score', 'duration'}

        query = db.session.query(*fields_to_query).filter(Task.userId == uid)
        if sort_params:
            order_criteria = []
            for item in sort_params:
                field_name = item.get('field')
                if field_name not in allowed_sort_field:
                    raise ValueError(f"包含不支持排序字段: [{str(field_name)}]")

                order = item.get('order', 'desc').lower()

                # 安全检查：防止前端传入模型中不存在的字段名导致报错
                column = getattr(Task, field_name, None)
                if column:
                    criterion = column.desc() if order == 'desc' else column.asc()
                    order_criteria.append(criterion)

            if order_criteria:
                query = query.order_by(*order_criteria)
        else:
            # 默认排序兜底：按创建时间倒序
            query = query.order_by(Task.createdAt.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination

    def get_task_by_tid(self, uid, task_id):
        """按任务ID指定查询任务"""
        task = Task.query.filter_by(id=task_id).first()
        if not task:
            raise ValueError('任务不存在')
        if task.userId != uid:
            raise ValueError(f'无权访问')

        return task

    def delete_batch_task_by_tid(self, uid, ids):
        """批量删除指定ID任务"""
        tasks = Task.query.filter(Task.id.in_(ids)).all()

        if len(tasks) != len(ids):
            raise ValueError('包含不存在的任务')

        for task in tasks:
            if task.userId != uid:
                raise ValueError(f'无权删除')

        for task in tasks:
            db.session.delete(task)
        db.session.commit()
        return len(tasks), ids


    # celery workers调用
    def update_task_status(self, task_id, status='pending', progress=0):
        """按ID更新任务进度"""
        task = Task.query.filter_by(id=task_id).first()
        if not task:
            raise ValueError('任务不存在')

        task.status = status
        task.progress = progress
        db.session.commit()

        return task

    def set_task_result(self, task_id, score=0, is_malicious=False, error_message=None, duration=0):
        """设置结果"""
        task = Task.query.filter_by(id=task_id).first()
        if not task:
            raise ValueError('任务不存在')

        task.score = score
        task.isMalicious = is_malicious
        task.duration = duration
        task.errorMessage = error_message

        db.session.commit()
        return task

    def get_task_status(self, uid):
        """根据uid获取所有任务状态"""
        form = (
            Task.id,
            Task.status,
            Task.progress,
            Task.errorMessage
        )
        return db.session.query(*form).filter_by(userId=uid)



