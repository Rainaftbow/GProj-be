from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from prompt_toolkit.input.win32 import raw_mode

from src.services import UserService
from src.services import TaskService

tasks_bp = Blueprint('tasks', __name__)
user_service = UserService()
task_service = TaskService()


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_by_tid(task_id):
    try:
        task = task_service.get_task_by_tid(current_user ,task_id)
        return jsonify({
            'detail': task.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': '查询任务失败'}), 500


@tasks_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_tasks():
    """单用户获取所有任务"""
    try:
        page = max(1, request.args.get('page', default=1, type=int))
        per_page = min(50, request.args.get('per_page', default=5, type=int))

        raw_sorts = request.args.getlist('sort')
        sort_params = []
        seen_fields = set() # 哨兵
        for item in raw_sorts:
            item = item.strip('"\'')
            if ':' in item:
                field, order = item.split(':', 1)
                if field in seen_fields:
                    raise ValueError(f'传入排序字段异常: {field}')
                sort_params.append({'field': field, 'order': order})
                seen_fields.add(field)

        if not sort_params:
            sort_params = [{'field': 'createdAt', 'order': 'desc'}]

        raw_tasks = task_service.get_all_tasks_preview(current_user.id, page, per_page, sort_params)

        task_list = [task._asdict() for task in raw_tasks]

        return jsonify({
            'tasks': task_list,
            'page': {
                'total': raw_tasks.total,  # 总记录数
                'pages': raw_tasks.pages,  # 总页数
                'current_page': raw_tasks.page,  # 当前页码
                'per_page': raw_tasks.per_page,  # 每页显示条数
                'has_next': raw_tasks.has_next,  # 是否有下一页
                'has_prev': raw_tasks.has_prev  # 是否有上一页
            }
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '获取任务失败'+str(e)}), 500


@tasks_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_batch_tasks():
    """删除批量任务"""
    data = request.get_json()

    try:
        num, ids = task_service.delete_batch_task_by_tid(current_user.id, data['ids'])
        return jsonify({
            'message': f'共{num}条记录删除成功',
            'ids': ids
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '批量删除失败'}), 500

@tasks_bp.route('/status', methods=['GET'])
@jwt_required()
def get_task_status():
    """获取任务状态"""
    try:
        results = task_service.get_task_status(current_user.id)
        status_list = []
        for r in results:
            status_list.append({
                'id': r.id,
                'status': r.status,
                'progress': r.progress,
                'error': r.errorMessage
            })
        return jsonify({
            'status': status_list
        }), 200

    except Exception as e:
        return jsonify({'error': '获取任务状态失败'}), 500



