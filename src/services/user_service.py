from src.init import db
from src.models import User


class UserService:
    """用户服务"""
    
    def create_user(self, user_name, password, user_role='user'):
        """创建新用户"""
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(userName=user_name).first()
        if existing_user:
            raise ValueError('用户名已存在')
        
        # 创建用户
        user = User(user_name=user_name, password=password, user_role=user_role)
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def authenticate_user(self, user_name, password):
        """验证用户身份"""
        user = User.query.filter_by(userName=user_name).first()
        if user and user.check_password(password):
            return user
        return None
    
    def get_user_by_id(self, uid):
        """根据ID获取用户"""
        return User.query.get(uid)
    
    def get_user_by_username(self, user_name):
        """根据用户名获取用户"""
        return User.query.filter_by(userName=user_name).first()
    
    def update_user_profile_by_id(self, uid, user_data):
        """更新用户信息"""
        user = self.get_user_by_id(uid)
        
        # 更新允许的字段
        if 'user_name' in user_data and user_data['user_name'] != user.userName:
            # 检查新用户名是否已存在
            existing_user = self.get_user_by_username(user_data['user_name'])
            if existing_user and existing_user.id != uid:
                raise ValueError('用户名已存在')
            user.userName = user_data['user_name']

        return user

    def change_password(self, uid, new_password, old_password):
        user = self.get_user_by_id(uid)

        if not user.check_password(old_password):
            raise ValueError("原密码输入错误")

        # 新旧密码重复校验
        if user.check_password(new_password):
            raise ValueError("新密码不能与旧密码相同")

        user.set_password(new_password)
        
        db.session.commit()
        return user
    
    def delete_user_by_id(self, uid):
        """删除用户"""
        user = self.get_user_by_id(uid)
        if not user:
            raise ValueError('用户不存在')
        
        db.session.delete(user)
        db.session.commit()
    
    def get_all_users(self, page=1, per_page=10):
        """获取所有用户（分页）"""
        query = User.query.order_by(User.createdAt.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return pagination.items, pagination.total