from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, current_user, get_jwt

from src.init_instance import redis_client
from src.services import UserService

users_bp = Blueprint('users', __name__)
user_service = UserService()

@users_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()

    if not data or not data.get('userName') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400

    try:
        user = user_service.create_user(
            user_name=data['userName'],
            password=data['password'],
            user_role=data.get('userRole', 'user')
        )
        return jsonify({
            'message': '用户注册成功',
            'user': user.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '注册失败'+str(e)}), 500

@users_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()

    if not data or not data.get('userName') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400

    if not user_service.get_user_by_username(data['userName']):
        return jsonify({'error': '用户名不存在'}), 404

    try:
        user = user_service.authenticate_user(data['userName'], data['password'])
        if not user:
            return jsonify({'error': '密码错误'}), 401

        # 创建访问令牌
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': '登录失败'}), 500

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取用户信息"""
    try:
        return jsonify({
            'message': '获取用户信息成功',
            'user': current_user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': '获取用户信息失败'}), 500

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新用户信息"""
    data = request.get_json()

    try:
        user = user_service.update_user_profile_by_id(
            uid=current_user.id,
            user_data=data
        )

        return jsonify({
            'message': '更新用户信息成功',
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '更新用户信息失败'}), 500

@users_bp.route('/changePwd', methods=['POST'])
@jwt_required()
def change_pwd():
    """修改密码"""
    try:
        data = request.get_json()
        new_password = data.get('new_password')
        old_password = data.get('old_password')
        if not new_password:
            return jsonify({'error': '新密码不能为空'}), 400

        user = user_service.change_password(current_user.id, new_password, old_password)
        blacklist_current_token()
        return jsonify({
            'message': '修改密码成功, 请重新登录',
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '修改密码失败'}), 500


@users_bp.route('/close', methods=['DELETE'])
@jwt_required()
def close():
    """用户注销"""
    try:
        user_service.delete_user_by_id(current_user.id)
        return jsonify({
            'message': '注销成功'
        }), 200
    except Exception as e:
        return jsonify({'error': '注销失败'}), 500

@users_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出，token加入redis黑名单"""
    blacklist_current_token()
    return jsonify({'message': '登出成功'}), 200

def blacklist_current_token():
    """将当前请求的 Token 加入黑名单"""
    jti = get_jwt()["jti"]
    redis_client.set(jti, "", ex=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])