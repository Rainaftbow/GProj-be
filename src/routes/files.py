from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from flask import send_file

from src.services import FileService

files_bp = Blueprint('files', __name__)
file_service = FileService()


@files_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件并创建检测任务"""
    if 'file' not in request.files:
        return jsonify({'error': '未检测到文件'}), 400

    file = request.files['file']

    try:
        task = file_service.upload_file(file)
        # 传递给broker
        from src.workers import scan_file
        scan_file.delay(current_user.id, task.id)
        
        return jsonify({
            'message': '文件上传成功',
            'user_id': task.userId,
            'task_id': task.id
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '文件上传失败'}), 500

@files_bp.route('/<int:task_id>/download/pre', methods=['GET'])
@jwt_required()
def download_pre_file(task_id):
    """获取已上传的文件下载元信息"""
    try:
        info = file_service.get_file_download_info(current_user.id, task_id)
        
        return jsonify({
            'pre': info
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '获取文件信息失败'}), 500

@files_bp.route('/<int:task_id>/download/raw', methods=['GET'])
@jwt_required()
def download_raw(task_id):
    """发送文件"""
    try:
        uid = current_user.id
        task = file_service.check_validation(uid, task_id)

        return send_file(
            task.filePath,
            as_attachment=True,
            download_name=task.fileName
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '下载文件失败'}), 500