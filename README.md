# 恶意软件检测系统 - 后端模块

基于机器学习的PE文件恶意软件检测系统后端模块。

## 功能特性

- 基于JWT的用户认证与授权
- 基于Celery的异步任务处理
- 基于Celery Beat的上传文件管理

## 技术栈

Flask、Celery、Redis、Postgresql、JWT、**Docker + Nginx + Gunicorn**

## 项目结构

```
backend/
├── src/
│   ├── __init__.py
│   ├── init.py             # 初始化
│   ├── config.py           # 配置文件
│   ├── app.py              # Flask应用入口
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   ├── task.py         # 任务模型
│   │   └── user.py         # 用户模型
│   ├── routes/             # API路由
│   │   ├── __init__.py
│   │   ├── files.py        # 文件路由
│   │   ├── tasks.py        # 任务路由
│   │   └── users.py        # 用户路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_service.py # 文件服务
│   │   ├── task_service.py # 任务服务
│   │   └── user_service.py # 用户服务
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── extractor.py    # 特征提取器
│   │   └── top_50_api_2gram.txt
│   └── workers/
│       ├── __init__.py
│       └── tasks.py        # Celery异步任务
├── uploads/                # 文件上传目录
├── requirements.txt
└── README.md
```

## API接口

### 认证相关
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/changePwd` - 用户修改密码
- `GET /api/auth/profile` - 获取用户信息
- `PUT /api/auth/profile` - 更新用户信息
- `POST /api/auth/close` - 用户注销
- `POST /api/auth/logout` - 用户登出

### 文件相关
- `POST /api/files/upload` - 上传文件，celery worker监听并检测任务
- `GET /api/files/{task_id}/download/pre` - 获取文件下载信息
- `GET /api/files/{task_id}/download/raw` - 下载文件

### 任务相关
- `GET /api/tasks` - 分页获取任务预览
- `GET /api/tasks/{task_id}` - 获取任务详情
- `DELETE /api/tasks/delete` - 删除任务（可批量）
- `GET /api/tasks/status` - 获取任务状态


### 系统相关
- `GET /health` - 健康检查
