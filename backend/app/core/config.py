# backend/app/core/config.py

# !!! QUAN TRỌNG: Thay đổi thông tin cho phù hợp với DB của bạn
# !!! Trong production, nên dùng biến môi trường thay vì hardcode
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Thay username
    'password': '11082002',  # Thay password
    'database': 'datn'  # Thay tên database nếu khác
}

# Đường dẫn đến các file model TF-IDF
# Giả định file này nằm trong app/core/, data/ nằm cùng cấp với app/
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # trỏ về backend/
MODEL_DIR = os.path.join(BASE_DIR, 'data', 'models')

VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
TFIDF_MATRIX_PATH = os.path.join(MODEL_DIR, 'tfidf_matrix.pkl')
LOCATION_IDS_PATH = os.path.join(MODEL_DIR, 'location_ids.pkl')

# (Tùy chọn) Đường dẫn đến file từ đồng nghĩa
SYNONYMS_PATH = os.path.join(BASE_DIR, 'data', 'dictionaries', 'synonyms.json')