# backend/scripts/test_search_service_flow.py
import sys
import os
import json # Để in dictionary cho đẹp

# Thêm thư mục `backend` vào PYTHONPATH để có thể import `app`
# Điều này quan trọng khi chạy script từ thư mục `scripts`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Bây giờ mới import các module từ package 'app'
try:
    # Giả định rằng search_service.py của bạn nằm trong app/services/
    # và nó đã import và sử dụng preprocessor, tfidf_engine đúng cách.
    from app.services.search_service import search_locations_by_tfidf
    # Nếu bạn muốn test trực tiếp preprocessor, bạn có thể import nó ở đây
    # from app.search_logic.preprocessor import preprocess_query
except ModuleNotFoundError as e:
    print(f"LỖI: Không thể import module cần thiết: {e}")
    print("Hãy đảm bảo rằng bạn đang chạy script này từ thư mục `backend/scripts/`")
    print("Và cấu trúc thư mục của bạn là backend/app/services/search_service.py, v.v.")
    print("Đồng thời, các file __init__.py cần thiết đã được tạo trong các thư mục package.")
    sys.exit(1)
except ImportError as e:
    print(f"LỖI IMPORT: {e}")
    print("Có thể có lỗi cú pháp trong các file service, preprocessor, hoặc tfidf_engine, hoặc các file chúng import.")
    sys.exit(1)
except Exception as e:
    print(f"LỖI KHÔNG XÁC ĐỊNH KHI IMPORT: {e}")
    sys.exit(1)


if __name__ == "__main__":
    print("--- Bắt đầu kiểm tra luồng Search Service (Preprocessor -> TFIDF Engine -> Service) ---")

    # --- Các câu truy vấn mẫu để kiểm tra ---
    sample_queries_to_test = [
        {
            "description": "Test cơ bản có từ khóa du lịch",
            "query": "Tôi muốn đi leo núi ngắm cảnh ở nơi có nhiều rừng, cây xanh"
        },
        
    ]

    num_results_to_display = 10 # Số lượng kết quả hiển thị cho mỗi test

    for i, test_case in enumerate(sample_queries_to_test):
        print(f"\n\n--- TEST CASE {i+1}: {test_case['description']} ---")
        query_text = test_case['query']
        print(f"Truy vấn đầu vào: \"{query_text}\"")

        try:
            # Gọi hàm tìm kiếm chính từ service
            # Hàm này sẽ điều phối preprocessor, tfidf_engine, và logic DB
            results = search_locations_by_tfidf(query_text, num_results=num_results_to_display)

            print(f"\n--- Kết quả tìm kiếm (Top {num_results_to_display}) cho TEST CASE {i+1} ---")
            if results and not (len(results) == 1 and results[0].get("error")):
                for rank, item in enumerate(results):
                    print(f"\n{rank+1}. ID: {item.get('id_dia_diem')}")
                    print(f"   Tên: {item.get('ten')}")
                    print(f"   Mô tả ngắn: {item.get('mo_ta')}")
                    print(f"   Điểm TF-IDF (nếu có): {item.get('tfidf_score', 'N/A')}") # Giả sử service trả về điểm
            elif results and results[0].get("error"):
                print(f"Lỗi từ service: {results[0]['error']}")
            else:
                print("Không tìm thấy kết quả nào phù hợp hoặc service không trả về dữ liệu.")

        except Exception as e:
            print(f"LỖI NGOẠI LỆ khi xử lý truy vấn '{query_text}': {e}")
            import traceback
            traceback.print_exc() # In đầy đủ traceback để dễ debug

        print("="*60)

    print("\n--- Kiểm tra luồng Search Service hoàn tất ---")