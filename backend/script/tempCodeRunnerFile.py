# backend/scripts/test_preprocessor_functionality.py
import sys
import os
import json # Để in dictionary cho đẹp

# Thêm thư mục `backend` vào PYTHONPATH để có thể import `app`
# Điều này quan trọng khi chạy script từ thư mục `scripts`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Bây giờ mới import các module từ package 'app'
# Giả định rằng preprocessor.py của bạn nằm trong app/search_logic/
try:
    from app.search_logic.preprocessor import preprocess_query
except ModuleNotFoundError:
    print("LỖI: Không thể import `preprocess_query`.")
    print("Hãy đảm bảo rằng bạn đang chạy script này từ thư mục `backend/scripts/`")
    print("Và cấu trúc thư mục của bạn là backend/app/search_logic/preprocessor.py")
    print("Đồng thời, các file __init__.py cần thiết đã được tạo.")
    sys.exit(1)
except ImportError as e:
    print(f"LỖI IMPORT: {e}")
    print("Có thể có lỗi cú pháp trong file preprocessor.py hoặc các file nó import.")
    sys.exit(1)


if __name__ == "__main__":
    print("--- Bắt đầu kiểm tra Preprocessor Functionality ---")

    # Danh sách các câu truy vấn mẫu để kiểm tra
    sample_queries = [
        "Tôi muốn tìm một nơi có bãi biển đẹp và không quá ồn ào",
        "Địa điểm du lịch ở Hà Nội không có chùa chiền",
        "Gợi ý chỗ nào đi phượt ở Miền Bắc",
        "Tôi không thích những nơi đông đúc như thành phố Hồ Chí Minh",
        "Tìm resort sang trọng gần biển Đà Nẵng",
        "Chỗ nào yên tĩnh để trải nghiệm văn hóa?",
        "Tránh xa những khu leo núi nguy hiểm",
        "tôi muốn tìm hiểu về các địa danh ở tỉnh Điện Biên"
    ]

    # (Đảm bảo file synonyms.json và các list trong preprocessor.py có dữ liệu để test)
    # Ví dụ, synonyms.json có:
    # {
    #     "bãi biển": ["biển", "bờ biển"],
    #     "phượt": ["khám phá", "du lịch bụi"],
    #     "sang trọng": ["cao cấp", "luxury"]
    # }
    # Và các list NEGATION_TRIGGERS, POSSIBLE_NEGATED_CONCEPTS, VIETNAM_PROVINCES_NORMALIZED, ...
    # trong preprocessor.py đã được định nghĩa.

    for i, query in enumerate(sample_queries):
        print(f"\n\n--- TEST CASE {i+1} ---")
        print(f"Truy vấn đầu vào: \"{query}\"")

        try:
            processed_result = preprocess_query(query)

            print("\nKết quả từ preprocess_query:")
            print("------------------------------------")
            # In dictionary một cách dễ đọc
            print(json.dumps(processed_result, indent=4, ensure_ascii=False))
            print("------------------------------------")

            # Bạn có thể thêm các assert ở đây để kiểm tra cụ thể nếu muốn tự động hóa việc test
            # Ví dụ:
            # if query == "Địa điểm du lịch ở Hà Nội không có chùa chiền":
            #     assert processed_result['location_entities']['province'] == 'hà nội', "Lỗi nhận diện tỉnh Hà Nội"
            #     assert 'chùa' in processed_result['negated_keywords'], "Lỗi nhận diện từ khóa phủ định 'chùa'"

        except Exception as e:
            print(f"LỖI khi xử lý truy vấn '{query}': {e}")
            import traceback
            traceback.print_exc() # In đầy đủ traceback để dễ debug

        print("="*50)

    print("\n--- Kiểm tra Preprocessor Functionality hoàn tất ---")