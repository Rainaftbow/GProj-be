import os
import time
import requests
from datetime import datetime, timezone
from flask import current_app

from src.init import db
from src.app import celery
from src.models.task import Task
from src.services.task_service import TaskService
from src.utils.extractor import FeatureExtractor

task_service = TaskService()


@celery.task(name='clean_uploads')
def clean_uploads():
    expired_duration = current_app.config.get('FILE_EXPIRED_DURATION')
    cutoff_time = datetime.now(timezone.utc) - expired_duration

    expired_tasks = Task.query.filter(
        Task.createdAt < cutoff_time,
        Task.status != 'expired'
    ).all()

    count = 0
    for task in expired_tasks:
        try:
            if os.path.exists(task.filePath):
                os.remove(task.filePath)

            task.status = 'expired'
            task.progress = -1
            count += 1
        except Exception as e:
            print(f"清理文件失败 {task.id}: {str(e)}")

    db.session.commit()
    return f"共清理了uploads中 {count} 个过期文件"

@celery.task(bind=True, name='scan_file')
def scan_file(self, uid, task_id):
    """处理文件检测任务"""
    try:
        # 获取任务
        task = task_service.get_task_by_tid(uid, task_id)
        if not task:
            self.update_state(state='FAILED', meta={'error': '任务不存在'})
            return {'status': 'failed', 'error': '任务不存在'}

        # 更新任务状态为处理中
        task_service.update_task_status(task_id, 'processing', 10)

        # 检查文件是否存在
        if not os.path.exists(task.filePath):
            task_service.update_task_status(task_id, 'failed', 0)
            task_service.set_task_result(task_id, 0, False, '所测文件不存在于服务器中')
            return {'status': 'failed', 'error': '所测文件不存在于服务器中'}

        # 提取特征
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '正在提取特征'})
        task_service.update_task_status(task_id, 'processing', 30)

        try:
            # 加载top_50_api字典
            top_50_api = load_top_50_api()

            # 提取特征
            extractor = FeatureExtractor(task.filePath, top_50_api)
            features = extractor.extract_all_features()

            # 验证特征提取结果
            if not features:
                raise ValueError('特征提取失败')

        except Exception as e:
            task_service.update_task_status(task_id, 'failed', 30)
            task_service.set_task_result(task_id, 0, False, f'特征提取失败: {str(e)}')
            return {'status': 'failed', 'error': f'特征提取失败: {str(e)}'}

        # 调用ML模块进行检测
        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': '正在调用ML模块检测'})
        task_service.update_task_status(task_id, 'processing', 60)

        try:
            # 准备特征数据
            feature_data = prepare_feature_data(features)

            # 调用ML模块
            ml_result = call_ml_module(feature_data)

            if not ml_result:
                raise ValueError('ML模块返回空结果')

        except Exception as e:
            task_service.update_task_status(task_id, 'failed', 60)
            task_service.set_task_result(task_id, 0, False, f'ML检测失败: {str(e)}')
            return {'status': 'failed', 'error': f'ML检测失败: {str(e)}'}

        # 处理检测结果
        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': '正在处理检测结果'})
        task_service.update_task_status(task_id, 'processing', 90)

        try:
            # 解析ML模块返回的结果
            score = ml_result.get('score', 0.0)
            is_malicious = ml_result.get('is_malicious', False)

            # 计算处理时间
            end_time = time.time()
            # 任务开始时间，这里使用任务的创建时间
            start_time = task.createdAt.timestamp() if task.createdAt else time.time()
            duration = end_time - start_time

            # 保存结果
            task_service.set_task_result(task_id, score, is_malicious, None, duration)
            self.update_state(state='PROGRESS', meta={'progress': 100, 'message': '检测完成'})
            task_service.update_task_status(task_id, 'completed', 100)

            return {
                'status': 'completed',
                'task_id': task_id,
                'score': score,
                'is_malicious': is_malicious,
                'duration': duration
            }

        except Exception as e:
            task_service.update_task_status(task_id, 'failed', 90)
            task_service.set_task_result(task_id, 0, False, f'结果处理失败: {str(e)}')
            return {'status': 'failed', 'error': f'结果处理失败: {str(e)}'}

    except Exception as e:
        db.session.rollback()
        # 捕获所有未处理的异常
        task_service.set_task_result(task_id, error_message=str(e))
        task_service.update_task_status(task_id, 'failed', 0)

        return {'status': 'failed', 'error': f'任务处理失败: {str(e)}'}
    finally:
        db.session.remove()

def load_top_50_api():
    """加载top_50_api_2gram数据"""
    try:
        top_50_file = current_app.config.get('TOP_50_API_FILE')
        if os.path.exists(top_50_file):
            with open(top_50_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
    except:
        pass

    # 返回空列表作为默认值
    print("top50字典为空")
    return []

def prepare_feature_data(features):
    """特征数据转换准备"""

    feature_data = {
        # 文件统计特征
        'file_size': features.get('file_size', 0),
        'global_entropy': features.get('global_entropy', 0.0),

        # DOS头特征
        'e_magic': features.get('e_magic', 0),

        # PE头特征
        'machine': features.get('machine', 0),
        'number_of_sections': features.get('number_of_sections', 0),
        'time_date_stamp': features.get('time_date_stamp', 0),
        'address_of_entry_point': features.get('address_of_entry_point', 0),
        'image_base': features.get('image_base', 0),
        'section_alignment': features.get('section_alignment', 0),
        'subsystem': features.get('subsystem', 0),

        # 节区特征
        'all_sections_size_ratio': features.get('all_sections_size_ratio', 1.0),
        'wx_section_ratio': features.get('wx_section_ratio', 0.0),
        'max_section_entropy': features.get('max_section_entropy', 0.0),
        'is_abnormal_section_name': features.get('is_abnormal_section_name', 0),

        # 导入导出表特征
        'num_imported_dlls': features.get('num_imported_dlls', 0),
        'is_export_present': features.get('is_export_present', 0),
        'resource_size': features.get('resource_size', 0),

        # 字符串特征
        'num_printable_strings': features.get('num_printable_strings', 0),
        'suspicious_str_count': features.get('suspicious_str_count', 0),

        # 字节直方图 (256个值)
        'byte_histogram': features.get('byte_histogram', []),

        # API组合特征 (50个值)
        'top_50_api_2gram': features.get('top_50_api_2gram', [0] * 50)
    }

    return feature_data


def call_ml_module(feature_data):
    """调用ML模块API"""
    try:
        ml_module_url = current_app.config.get('ML_MODULE_URL')

        # 如果ML模块URL为空
        if not ml_module_url or ml_module_url == '':
            raise ValueError('ML模块api路径不可用')

        data_to_send = feature_data.copy()

        # 发送请求到ML模块的/predict接口
        response = requests.post(
            f'{ml_module_url}/predict',
            json=data_to_send,
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f'ML模块返回错误: {response.status_code}')

    except Exception as e:
        raise ValueError(f'调用ML模块失败: {str(e)}')