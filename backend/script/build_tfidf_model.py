import mysql.connector
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from underthesea import word_tokenize
import joblib # Hoặc dùng pickle
import os
import time

# --- Cấu hình ---
# !!! QUAN TRỌNG: Thay đổi thông tin kết nối DB cho phù hợp
# !!! KHÔNG nên hardcode trực tiếp trong code production, dùng biến môi trường!
db_config = {
    'host': 'localhost',
    'user': 'root', # Thay username
    'password': '11082002', # Thay password
    'database': 'datn' # Thay tên database nếu khác
}

# Cột chứa mô tả để huấn luyện TF-IDF ('mo_ta_chi_tiet' hoặc 'mo_ta')
DESCRIPTION_COLUMN = 'mo_ta_chi_tiet'

# Thư mục lưu trữ model và vectorizer
OUTPUT_DIR = 'C:/Users/datsa/OneDrive/Desktop/NewDATN/backend/data/models' 
VECTORIZER_PATH = os.path.join(OUTPUT_DIR, 'tfidf_vectorizer.pkl')
MATRIX_PATH = os.path.join(OUTPUT_DIR, 'tfidf_matrix.pkl')
IDS_PATH = os.path.join(OUTPUT_DIR, 'location_ids.pkl')

# Cấu hình TfidfVectorizer (Tùy chọn - có thể điều chỉnh)
tfidf_params = {
    'max_df': 0.95,  # Bỏ qua từ xuất hiện > 95% số văn bản
    'min_df': 2,     # Bỏ qua từ xuất hiện < 2 lần
    'max_features': None, # None = không giới hạn số từ vựng, hoặc đặt số (vd: 10000)
    'ngram_range': (1, 1) # Chỉ dùng unigram (từ đơn), có thể thử (1, 2) cho cả bigram
}

# --- Hàm xử lý ---

def connect_db():
    """Kết nối tới cơ sở dữ liệu MySQL."""
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(**db_config)
        print("Connection successful!")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def fetch_data(conn):
    """Lấy dữ liệu id_dia_diem và mô tả từ database."""
    if not conn:
        return None
    print(f"Fetching data (id_dia_diem, {DESCRIPTION_COLUMN}) from dia_danh table...")
    try:
        query = f"""
            SELECT id_dia_diem, {DESCRIPTION_COLUMN}
            FROM dia_danh
            WHERE {DESCRIPTION_COLUMN} IS NOT NULL AND {DESCRIPTION_COLUMN} != ''
        """
        df = pd.read_sql(query, conn)
        print(f"Fetched {len(df)} records.")
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
    finally:
        if conn.is_connected():
            conn.close()
            print("Database connection closed.")

def preprocess_text(text):
    """Tiền xử lý văn bản: lowercase và tách từ tiếng Việt."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # Có thể thêm các bước làm sạch khác ở đây (xóa HTML, dấu câu đặc biệt...)
    tokenized_text = word_tokenize(text, format="text")
    return tokenized_text

# --- Luồng chính ---
if __name__ == "__main__":
    start_time = time.time()

    # 1. Kết nối và lấy dữ liệu
    connection = connect_db()
    data_df = fetch_data(connection)

    if data_df is None or data_df.empty:
        print("No data fetched. Exiting.")
        exit()

    # 2. Tiền xử lý mô tả
    print("Preprocessing descriptions...")
    # Đảm bảo cột mô tả là kiểu string
    data_df[DESCRIPTION_COLUMN] = data_df[DESCRIPTION_COLUMN].astype(str)
    # Áp dụng tiền xử lý
    data_df['processed_description'] = data_df[DESCRIPTION_COLUMN].apply(preprocess_text)
    print("Preprocessing completed.")

    # Chuẩn bị dữ liệu cho TF-IDF
    descriptions = data_df['processed_description'].tolist()
    location_ids = data_df['id_dia_diem'].tolist()

    # 3. Huấn luyện TF-IDF Vectorizer
    print("Training TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(**tfidf_params)
    vectorizer.fit(descriptions)
    print("Training completed.")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")

    # 4. Transform dữ liệu thành ma trận TF-IDF
    print("Transforming descriptions to TF-IDF matrix...")
    tfidf_matrix = vectorizer.transform(descriptions)
    print("Transformation completed.")
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}") # (số địa điểm, số từ vựng)

    # 5. Lưu kết quả
    print(f"Saving artifacts to {OUTPUT_DIR}...")
    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Lưu Vectorizer
        joblib.dump(vectorizer, VECTORIZER_PATH)
        print(f"Vectorizer saved to {VECTORIZER_PATH}")

        # Lưu Ma trận TF-IDF (dạng sparse)
        joblib.dump(tfidf_matrix, MATRIX_PATH)
        print(f"TF-IDF matrix saved to {MATRIX_PATH}")

        # Lưu danh sách ID địa điểm (để biết hàng nào trong ma trận ứng với ID nào)
        joblib.dump(location_ids, IDS_PATH)
        print(f"Location IDs saved to {IDS_PATH}")

        print("Artifacts saved successfully.")

    except Exception as e:
        print(f"Error saving artifacts: {e}")

    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")