# backend/scripts/test_search_service_flow.py
import sys
import os
import json # Để in dictionary cho đẹp

# Thêm thư mục `backend` (nơi chứa package `app`) vào PYTHONPATH
# Điều này quan trọng khi chạy script từ thư mục `scripts`
project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)

# Bây giờ mới import các module từ package 'app'
try:
    # Hàm tìm kiếm chính trong service của bạn (giữ tên theo yêu cầu)
    from app.services.search_service import search_locations_by_tfidf
except ModuleNotFoundError as e:
    print(f"LỖI: Không thể import module `app.services.search_service`: {e}")
    print("Hãy đảm bảo rằng bạn đang chạy script này từ thư mục `backend/scripts/`")
    print("Và cấu trúc thư mục của bạn là backend/app/services/search_service.py")
    print("Đồng thời, các file __init__.py cần thiết đã được tạo trong các thư mục package.")
    sys.exit(1)
except ImportError as e:
    print(f"LỖI IMPORT: {e}")
    print("Có thể có lỗi cú pháp trong file service hoặc các file nó import.")
    sys.exit(1)
except Exception as e:
    print(f"LỖI KHÔNG XÁC ĐỊNH KHI IMPORT: {e}")
    sys.exit(1)


if __name__ == "__main__":
    print("--- Bắt đầu kiểm tra toàn bộ Search Service ---")

    # Danh sách các câu truy vấn mẫu để kiểm tra
    sample_queries_to_test = [
        {
            "description": "TEST 1: Query có từ khóa mô tả và Tỉnh cụ thể",
            "query": "Tôi muốn đi tham quan các địa điểm du lịch Hà Nội, có thể là chùa chiền, hồ, di tích lịch sử. có địa điểm nào hay không"
        },
        
    ]

    num_results_to_show = 3 # Số lượng kết quả hiển thị cho mỗi mục trong output

    for i, test_case in enumerate(sample_queries_to_test):
        print(f"\n\n--- TEST CASE {i+1}: {test_case['description']} ---")
        query_text = test_case['query']
        print(f"Truy vấn đầu vào: \"{query_text}\"")

        try:
            # Gọi hàm tìm kiếm chính từ service
            # Hàm này nên trả về cấu trúc dict có "query_details", "province_results", "other_results"
            results_data = search_locations_by_tfidf(query_text, num_results=num_results_to_show)

            print("\n--- Kết quả từ Search Service ---")
            
            print("\n[Query Details]:")
            print(json.dumps(results_data.get("query_details", {}), indent=4, ensure_ascii=False))
            
            # Xử lý province_results
            province_res_data = results_data.get("province_results", {})
            print(f"\n[Province Results]: Tỉnh/Vùng ưu tiên: {province_res_data.get('province_name', 'Không xác định')}")
            print(f"  Tiêu đề mục: {province_res_data.get('title', 'N/A')}")
            if province_res_data.get("locations"):
                for rank_prov, item_prov in enumerate(province_res_data["locations"]):
                    print(f"  {rank_prov+1}. ID: {item_prov.get('id_dia_diem')}, Tên: {item_prov.get('ten')}, Score: {item_prov.get('score', 'N/A')}")
                    # print(f"     Mô tả: {item_prov.get('mo_ta')}")
            else:
                print("     (Không có kết quả cho mục này)")

            # Xử lý other_results
            other_res_data = results_data.get("other_results", {})
            print(f"\n[Other Results]: {other_res_data.get('title', 'Các địa điểm khác')}")
            if other_res_data.get("locations"):
                for rank_other, item_other in enumerate(other_res_data["locations"]):
                    print(f"  {rank_other+1}. ID: {item_other.get('id_dia_diem')}, Tên: {item_other.get('ten')}, Score: {item_other.get('score', 'N/A')}")
                    # print(f"     Mô tả: {item_other.get('mo_ta')}")
            else:
                print("     (Không có kết quả cho mục này)")
            
            # Xử lý trường hợp có lỗi trả về từ service (nếu service trả về lỗi dạng dict)
            if results_data.get("error"):
                 print(f"Lỗi từ service: {results_data['error']}")


        except Exception as e:
            print(f"LỖI NGOẠI LỆ không mong muốn khi xử lý truy vấn '{query_text}': {e}")
            import traceback
            traceback.print_exc() # In đầy đủ traceback để dễ debug

        print("="*70)
        
    print("\n--- Kiểm tra toàn bộ Search Service hoàn tất ---")