import joblib
import os
import underthesea
from sklearn.feature_extraction.text import TfidfVectorizer # Cần để Python hiểu type hint
from scipy.sparse import csr_matrix # Cần để Python hiểu type hint
from sklearn.metrics.pairwise import cosine_similarity
import mysql.connector
import pandas as pd
import numpy as np # Để sắp xếp theo điểm số

# --- Cấu hình ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Thư mục backend/
MODEL_DIR = os.path.join(BASE_DIR, 'data', 'models')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
MATRIX_PATH = os.path.join(MODEL_DIR, 'tfidf_matrix.pkl')
IDS_PATH = os.path.join(MODEL_DIR, 'location_ids.pkl')

# !!! QUAN TRỌNG: Thay đổi thông tin kết nối DB cho phù hợp
# !!! KHÔNG nên hardcode trực tiếp trong code production, dùng biến môi trường!
db_config = {
    'host': 'localhost',
    'user': 'root', # Thay username
    'password': '11082002', # Thay password
    'database': 'datn' # Thay tên database nếu khác
}

# --- Hàm xử lý ---

def load_artifacts():
    """Load vectorizer, ma trận TF-IDF và danh sách ID từ file."""
    print("Đang tải các thành phần TF-IDF từ file .pkl...")
    try:
        vectorizer = joblib.load(VECTORIZER_PATH)
        tfidf_matrix = joblib.load(MATRIX_PATH)
        location_ids = joblib.load(IDS_PATH)
        print("Tải thành công!")
        return vectorizer, tfidf_matrix, location_ids
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy một hoặc nhiều file .pkl. Hãy chạy script build_tfidf_model.py trước.")
        return None, None, None
    except Exception as e:
        print(f"Lỗi khi tải file .pkl: {e}")
        return None, None, None

def preprocess_query(query_text):
    """Tiền xử lý văn bản truy vấn: lowercase và tách từ tiếng Việt."""
    # Trong thực tế, hàm này nên giống hệt hàm bạn dùng trong preprocessor.py
    # Bao gồm cả việc mở rộng từ đồng nghĩa nếu có
    print(f"Truy vấn gốc: '{query_text}'")
    query_text = str(query_text).lower()
    # Giả sử không có từ đồng nghĩa phức tạp trong script test này cho đơn giản
    tokenized_query = underthesea.word_tokenize(query_text, format="text")
    print(f"Truy vấn đã xử lý: '{tokenized_query}'")
    return tokenized_query

def fetch_location_details_from_db(ids_to_fetch):
    """Lấy tên và mô tả (mo_ta) của các địa điểm từ DB dựa trên ID."""
    if not ids_to_fetch:
        return {}

    conn = None
    location_details = {}
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True) # Trả về kết quả dạng dict

        # Tạo chuỗi placeholder cho IN clause an toàn
        placeholders = ', '.join(['%s'] * len(ids_to_fetch))
        query = f"SELECT id_dia_diem, ten, mo_ta FROM dia_danh WHERE id_dia_diem IN ({placeholders})"

        cursor.execute(query, tuple(ids_to_fetch))
        results = cursor.fetchall()

        for row in results:
            location_details[row['id_dia_diem']] = {'ten': row['ten'], 'mo_ta': row['mo_ta']}

    except mysql.connector.Error as err:
        print(f"Lỗi kết nối hoặc truy vấn DB: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return location_details

# --- Luồng chính ---
if __name__ == "__main__":
    # 1. Load các thành phần TF-IDF
    vectorizer, tfidf_matrix, location_ids = load_artifacts()

    if vectorizer is None:
        print("Không thể tiếp tục do lỗi tải file. Kết thúc script.")
        exit()

    # 2. Tạo sẵn câu input của người dùng
    user_query = "tôi muốn tìm một nơi có bãi biển đẹp và không quá ồn ào" # Bạn có thể thay đổi câu này

    # 3. Tiền xử lý câu input
    processed_query = preprocess_query(user_query)

    # 4. Biến đổi câu input thành vector TF-IDF
    # vectorizer.transform nhận vào một iterable (ví dụ list), nên ta truyền [processed_query]
    query_vector = vectorizer.transform([processed_query])
    print(f"Kích thước vector truy vấn: {query_vector.shape}")

    # 5. Tính toán độ tương đồng cosine giữa vector truy vấn và tất cả các địa điểm
    # cosine_similarity nhận vào (vector_hoặc_ma_trận_1, ma_trận_2)
    # Kết quả là một ma trận, ta lấy dòng đầu tiên (vì chỉ có 1 truy vấn)
    similarity_scores = cosine_similarity(query_vector, tfidf_matrix)[0]
    print(f"Số điểm tương đồng tính được: {len(similarity_scores)}")


    # 6. Lấy ra 5 địa điểm phù hợp nhất
    num_recommendations = 5
    # Lấy chỉ số của N điểm cao nhất
    # argsort trả về chỉ số của các phần tử nếu được sắp xếp tăng dần
    # [::-1] để đảo ngược thành giảm dần
    # [:num_recommendations] để lấy N phần tử đầu tiên
    top_indices = np.argsort(similarity_scores)[::-1][:num_recommendations]

    print(f"\n--- {num_recommendations} ĐỊA ĐIỂM PHÙ HỢP NHẤT VỚI TRUY VẤN ---")

    top_location_ids = []
    recommendations_for_db_query = []

    for i, index in enumerate(top_indices):
        location_id = location_ids[index]
        score = similarity_scores[index]
        top_location_ids.append(location_id) # Lưu lại để truy vấn DB
        print(f"\n{i+1}. ID Địa điểm: {location_id} (Điểm TF-IDF: {score:.4f})")
        # Tên và mô tả sẽ được lấy từ DB sau

    # 7. Lấy tên và mô tả (mo_ta) từ database cho 5 địa điểm này
    if top_location_ids:
        details = fetch_location_details_from_db(top_location_ids)
        print("\n--- CHI TIẾT CÁC ĐỊA ĐIỂM (từ Database) ---")
        # In theo thứ tự đã sắp xếp
        rank = 1
        for loc_id in top_location_ids: # Duyệt theo top_location_ids để giữ đúng thứ tự
            if loc_id in details:
                detail = details[loc_id]
                print(f"\nHạng {rank}: {detail['ten']} (ID: {loc_id})")
                print(f"  Mô tả ngắn: {detail['mo_ta']}")
                rank +=1
            else:
                print(f"\nKhông tìm thấy chi tiết cho ID: {loc_id} trong DB (có thể ID không còn tồn tại).")
    else:
        print("Không tìm thấy địa điểm nào phù hợp.")