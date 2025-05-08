# backend/app/search_logic/tfidf_engine.py
import joblib
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer # Để Python hiểu type hint
from scipy.sparse import csr_matrix # Để Python hiểu type hint

# Import đường dẫn từ config
from app.core.config import VECTORIZER_PATH, TFIDF_MATRIX_PATH, LOCATION_IDS_PATH

class TFIDFEngine:
    def __init__(self):
        """
        Khởi tạo TFIDFEngine bằng cách tải các model đã được huấn luyện.
        Việc tải này chỉ nên xảy ra một lần khi đối tượng TFIDFEngine được tạo.
        """
        self.vectorizer: TfidfVectorizer = None
        self.tfidf_matrix: csr_matrix = None
        self.location_ids: list = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Tải các thành phần TF-IDF từ file .pkl."""
        print("TFIDFEngine: Đang tải các thành phần TF-IDF...")
        try:
            if not os.path.exists(VECTORIZER_PATH):
                raise FileNotFoundError(f"Không tìm thấy file vectorizer tại: {VECTORIZER_PATH}")
            if not os.path.exists(TFIDF_MATRIX_PATH):
                raise FileNotFoundError(f"Không tìm thấy file ma trận TF-IDF tại: {TFIDF_MATRIX_PATH}")
            if not os.path.exists(LOCATION_IDS_PATH):
                raise FileNotFoundError(f"Không tìm thấy file ID địa điểm tại: {LOCATION_IDS_PATH}")

            self.vectorizer = joblib.load(VECTORIZER_PATH)
            self.tfidf_matrix = joblib.load(TFIDF_MATRIX_PATH)
            self.location_ids = joblib.load(LOCATION_IDS_PATH)
            print("TFIDFEngine: Tải thành công vectorizer, ma trận TF-IDF, và danh sách ID.")
            print(f"  - Kích thước từ vựng: {len(self.vectorizer.vocabulary_)}")
            print(f"  - Kích thước ma trận TF-IDF: {self.tfidf_matrix.shape}")
            print(f"  - Số lượng ID địa điểm: {len(self.location_ids)}")

            # Kiểm tra sự nhất quán cơ bản
            if self.tfidf_matrix.shape[0] != len(self.location_ids):
                raise ValueError("Số dòng ma trận TF-IDF không khớp với số lượng ID địa điểm.")
            if self.tfidf_matrix.shape[1] != len(self.vectorizer.vocabulary_):
                 raise ValueError("Số cột ma trận TF-IDF không khớp với kích thước từ vựng của vectorizer.")

        except FileNotFoundError as fnf_err:
            print(f"TFIDFEngine Lỗi: {fnf_err}")
            print("Vui lòng chạy script 'build_tfidf_model.py' để tạo các file cần thiết.")
            # Trong ứng dụng thực tế, bạn có thể muốn raise lỗi này để dừng ứng dụng
            # hoặc xử lý một cách mềm dẻo hơn.
            self.vectorizer = None # Đặt lại để biết là chưa load được
        except Exception as e:
            print(f"TFIDFEngine Lỗi khi tải file .pkl: {e}")
            self.vectorizer = None # Đặt lại

    def is_ready(self) -> bool:
        """Kiểm tra xem engine đã sẵn sàng (đã load model thành công) chưa."""
        return self.vectorizer is not None and \
               self.tfidf_matrix is not None and \
               self.location_ids is not None

    def calculate_similarity(self, processed_query_text: str, num_results: int = 5) -> list:
        """
        Tính toán độ tương đồng và trả về top N địa điểm phù hợp nhất.
        Input:
            processed_query_text: Chuỗi truy vấn đã được tiền xử lý và tách từ.
            num_results: Số lượng kết quả trả về.
        Output:
            List các tuple (location_id, score), đã sắp xếp theo score giảm dần.
            Trả về list rỗng nếu có lỗi hoặc không tìm thấy.
        """
        if not self.is_ready():
            print("TFIDFEngine chưa sẵn sàng. Model chưa được tải.")
            return []
        if not processed_query_text:
            return []

        try:
            # 1. Biến đổi truy vấn thành vector TF-IDF
            # self.vectorizer.transform nhận vào một iterable (ví dụ list)
            query_vector = self.vectorizer.transform([processed_query_text])

            # 2. Tính toán độ tương đồng cosine
            # Kết quả là một ma trận (1, số_lượng_địa_điểm), lấy dòng đầu tiên
            similarity_scores = cosine_similarity(query_vector, self.tfidf_matrix)[0]

            # 3. Lấy ra num_results địa điểm phù hợp nhất
            # argsort trả về chỉ số của các phần tử nếu được sắp xếp tăng dần
            # [::-1] để đảo ngược thành giảm dần
            # [:num_results] để lấy N phần tử đầu tiên
            # Đảm bảo num_results không lớn hơn số lượng địa điểm
            actual_num_results = min(num_results, len(self.location_ids))
            top_indices = np.argsort(similarity_scores)[::-1][:actual_num_results]

            results = []
            for i in top_indices:
                location_id = self.location_ids[i]
                score = float(similarity_scores[i]) # Chuyển sang float cơ bản của Python
                # Chỉ lấy kết quả có điểm > 0 (hoặc một ngưỡng nào đó nếu muốn)
                if score > 0: # Có thể đặt ngưỡng cao hơn, ví dụ 0.01
                    results.append((location_id, score))
            
            return results

        except Exception as e:
            print(f"TFIDFEngine Lỗi khi tính toán độ tương đồng: {e}")
            return []

# (Tùy chọn) Tạo một instance để có thể import và sử dụng từ các module khác
# Việc này giúp model chỉ được load một lần khi module này được import lần đầu
# tfidf_engine_instance = TFIDFEngine()