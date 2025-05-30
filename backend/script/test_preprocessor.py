import sys
import os
import json

# Thêm thư mục `backend` vào PYTHONPATH để có thể import `app`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

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
except Exception as e:
    print(f"LỖI KHÔNG XÁC ĐỊNH KHI IMPORT HOẶC KHỞI TẠO: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("--- Bắt đầu kiểm tra khả năng nhận diện của Preprocessor với truy vấn phức tạp ---")
    print("Định dạng output: Input Query || LocationKws: [...] || AllKws: [...] || NegativeKws: [...]")
    print("-" * 80)

    # Câu truy vấn mẫu chứa sở thích, tên tỉnh, và phủ định
    query = "Biển đẹp ở Quảng Nam không đông đúc"
    expected_location = "quảng_nam"
    expected_all_keywords = ["biển"]  # Có thể bao gồm "đẹp" tùy vào logic của preprocessor
    expected_negative = ["đông_đúc"]

    print(f"\nInput: \"{query}\"")
    print(f"Kỳ vọng: LocationKws chứa '{expected_location}', AllKws chứa {expected_all_keywords}, NegativeKws chứa {expected_negative}")

    try:
        # Gọi hàm preprocess_query
        processed_result = preprocess_query(query)

        # Lấy kết quả
        location_kws = processed_result.get('location_keywords', [])
        all_kws = processed_result.get('all_keywords', [])
        negative_kws = processed_result.get('negative_keywords', [])

        # Chuẩn hóa location_kws để so sánh
        normalized_location_kws = []
        for kw in location_kws:
            normalized_kw = kw.lower()
            if normalized_kw.startswith('tỉnh_'):
                normalized_kw = normalized_kw[len('tỉnh_'):]
            elif normalized_kw.startswith('thành_phố_'):
                normalized_kw = normalized_kw[len('thành_phố_'):]
            normalized_location_kws.append(normalized_kw)

        # Kiểm tra kết quả
        errors = []
        if expected_location not in normalized_location_kws:
            errors.append(f"LocationKws: Không tìm thấy '{expected_location}' trong {location_kws} (Chuẩn hóa: {normalized_location_kws})")
        if not all(kw in all_kws for kw in expected_all_keywords):
            errors.append(f"AllKws: Không tìm thấy {expected_all_keywords} trong {all_kws}")
        if not all(kw in negative_kws for kw in expected_negative):
            errors.append(f"NegativeKws: Không tìm thấy {expected_negative} trong {negative_kws}")

        print(f"LocationKws: {location_kws} || AllKws: {all_kws} || NegativeKws: {negative_kws}")

        if errors:
            print("\nKẾT QUẢ: CÓ LỖI!")
            for error in errors:
                print(f"- {error}")
        else:
            print("\nKẾT QUẢ: NHẬN DIỆN ĐÚNG TẤT CẢ YẾU TỐ!")

    except Exception as e:
        print(f"LỖI khi xử lý truy vấn '{query}': {e}")
        import traceback
        traceback.print_exc()

    print("-" * 80)
    print("\n--- Kiểm tra Preprocessor Functionality hoàn tất ---")

    # Đóng VnCoreNLP
    try:
        from app.search_logic.preprocessor import close_vncorenlp
        close_vncorenlp()
    except Exception as e:
        print(f"LỖI khi đóng VnCoreNLP: {e}")