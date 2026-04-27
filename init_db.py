import time

from src.app import app, db


def main(retries=10, delay=3):
    with app.app_context():
        for i in range(retries):
            try:
                print(f"[{i}]正在尝试创建数据库表")
                db.create_all()
                print("数据库初始化成功")
                return
            except Exception as e:
                print(f"数据库还没准备好 (Error: {e})，{delay}秒后重试...")
                time.sleep(delay)
        print("达到最大重试次数，数据库连接失败")
        exit(1)


if __name__ == '__main__':
    main()