# backend/app/core/database.py
import mysql.connector
from .config import DB_CONFIG # Import từ file config.py cùng thư mục core

def get_db_connection():
    """Tạo và trả về một kết nối đến cơ sở dữ liệu MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi khi kết nối đến MySQL: {err}")
        # Trong ứng dụng thực tế, bạn có thể muốn log lỗi này
        # và trả về None hoặc raise một exception cụ thể
        return None