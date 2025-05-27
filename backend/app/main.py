# backend/app/main.py
from flask import Flask
from flask_cors import CORS # Thêm CORS để frontend có thể gọi API từ domain khác

# Import Blueprint cho API tìm kiếm (sẽ tạo ở bước sau)
from app.api.search_api import api_bp 

def create_app():
    """Hàm factory để tạo và cấu hình ứng dụng Flask."""
    app = Flask(__name__)
    CORS(app) # Cho phép CORS cho tất cả các route, tiện cho phát triển

    # Cấu hình ứng dụng (nếu cần, ví dụ: secret key, config từ file...)
    # app.config.from_object('app.core.config_module') # Nếu bạn có file config riêng cho Flask

    # Đăng ký các Blueprints
    app.register_blueprint(api_bp) # Đăng ký blueprint của search API

    @app.route('/')
    def hello():
        return "Hello! This is the backend server for your travel app."

    return app

if __name__ == '__main__':
    # Khởi tạo và chạy ứng dụng
    # Việc load model TF-IDF và khởi tạo VnCoreNLP (nếu được thiết kế đúng)
    # sẽ xảy ra một lần khi các module service/engine được import lần đầu tiên
    # bởi ứng dụng Flask khi nó khởi động.
    app = create_app()
    print("Starting Flask development server...")
    print("TFIDFEngine and VnCoreNLP should be initializing if not already...")
    # Chạy trên cổng 5000 mặc định, debug=True để tự reload khi có thay đổi code
    app.run(host='0.0.0.0', port=5000, debug=True)