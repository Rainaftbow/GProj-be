from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import redis

db = SQLAlchemy()
jwt = JWTManager()
redis_client = redis.Redis()