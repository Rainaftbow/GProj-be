import multiprocessing

bind = '0.0.0.0:5000'
worker_class = 'eventlet'
workers = 2 * multiprocessing.cpu_count() + 1
preload_app = True

# 日志设置
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# 超时时间
timeout = 300