import joblib # Hoặc import pickle nếu bạn dùng pickle để lưu
import os
from scipy.sparse import csr_matrix # Cần thiết nếu bạn lưu ma trận sparse
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Cấu hình ---
# Đảm bảo đường dẫn này đúng với nơi bạn lưu file .pkl
MODEL_DIR = 'C:/Users/datsa/OneDrive/Desktop/NewDATN/backend/data/models' # Đường dẫn tương đối từ scripts/ đến data/models/
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
MATRIX_PATH = os.path.join(MODEL_DIR, 'tfidf_matrix.pkl')
IDS_PATH = os.path.join(MODEL_DIR, 'location_ids.pkl')

print(f"Kiểm tra các file trong thư mục: {MODEL_DIR}\n")

# --- Kiểm tra file Vectorizer ---
print(f"--- Đang kiểm tra {VECTORIZER_PATH} ---")
try:
    loaded_vectorizer = joblib.load(VECTORIZER_PATH)
    print(f"Loại đối tượng: {type(loaded_vectorizer)}")

    if isinstance(loaded_vectorizer, TfidfVectorizer):
        # Kiểm tra các thuộc tính quan trọng
        vocab_size = len(loaded_vectorizer.vocabulary_)
        print(f"Kích thước từ vựng (Vocabulary size): {vocab_size}")

        # Xem một vài từ trong từ vựng
        try:
            # sklearn version mới dùng get_feature_names_out
             feature_names = loaded_vectorizer.get_feature_names_out()
             print(f"Một vài từ đầu tiên trong từ vựng: {list(feature_names[:20])}")
             print(f"Một vài từ cuối cùng trong từ vựng: {list(feature_names[-20:])}")
        except AttributeError:
             # sklearn version cũ hơn dùng vocabulary_
             print(f"Một vài từ trong từ vựng (từ dict): {list(loaded_vectorizer.vocabulary_.keys())[:20]}")


        # Xem các tham số của vectorizer
        print(f"Các tham số của Vectorizer: {loaded_vectorizer.get_params()}")
    else:
        print("Lỗi: Đối tượng load được không phải là TfidfVectorizer.")

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file {VECTORIZER_PATH}")
except Exception as e:
    print(f"Lỗi khi load hoặc kiểm tra vectorizer: {e}")

print("\n" + "="*30 + "\n") # Phân cách

# --- Kiểm tra file Ma trận TF-IDF ---
print(f"--- Đang kiểm tra {MATRIX_PATH} ---")
try:
    loaded_matrix = joblib.load(MATRIX_PATH)
    print(f"Loại đối tượng: {type(loaded_matrix)}")

    # Kiểm tra các thuộc tính của ma trận (thường là sparse matrix)
    print(f"Kích thước ma trận (Shape): {loaded_matrix.shape}")
    # Kích thước này nên là (số_lượng_địa_điểm, kích_thước_từ_vựng)

    # Nếu là ma trận sparse, xem số phần tử khác 0
    if hasattr(loaded_matrix, 'nnz'):
        print(f"Số phần tử khác 0 (Non-zero elements): {loaded_matrix.nnz}")

    # Xem thử một phần nhỏ của ma trận (chuyển thành dense array - CẨN THẬN VỚI BỘ NHỚ nếu ma trận lớn)
    print("Xem thử 5 dòng, 10 cột đầu tiên (nếu là ma trận sparse):")
    try:
        # Chỉ nên xem một phần rất nhỏ để tránh hết RAM
        if loaded_matrix.shape[0] > 5 and loaded_matrix.shape[1] > 10:
             print(loaded_matrix[:5, :10].toarray())
        else:
             print(loaded_matrix.toarray()) # In hết nếu ma trận nhỏ
    except Exception as e:
        print(f"Không thể hiển thị slice ma trận (có thể không phải sparse hoặc lỗi khác): {e}")


except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file {MATRIX_PATH}")
except Exception as e:
    print(f"Lỗi khi load hoặc kiểm tra ma trận: {e}")

print("\n" + "="*30 + "\n") # Phân cách

# --- Kiểm tra file Danh sách ID ---
print(f"--- Đang kiểm tra {IDS_PATH} ---")
try:
    loaded_ids = joblib.load(IDS_PATH)
    print(f"Loại đối tượng: {type(loaded_ids)}")

    if isinstance(loaded_ids, list):
        # Kiểm tra các thuộc tính quan trọng
        num_ids = len(loaded_ids)
        print(f"Số lượng ID địa điểm: {num_ids}")
        # Số lượng ID này PHẢI KHỚP với số dòng của ma trận TF-IDF

        # Xem một vài ID đầu tiên
        print(f"Một vài ID đầu tiên: {loaded_ids[:20]}")
        # Xem một vài ID cuối cùng
        print(f"Một vài ID cuối cùng: {loaded_ids[-20:]}")
    else:
         print("Lỗi: Đối tượng load được không phải là list.")

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file {IDS_PATH}")
except Exception as e:
    print(f"Lỗi khi load hoặc kiểm tra danh sách ID: {e}")

print("\n--- Kiểm tra hoàn tất ---")