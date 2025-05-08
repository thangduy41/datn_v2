# backend/scripts/test_search_service_flow.py
import sys
import os

# Thêm thư mục `backend` vào PYTHONPATH để có thể import `app`
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Bây giờ mới import các module từ package 'app'
from app.services.search_service import search_locations_by_tfidf

if __name__ == "__main__":
    print("--- Bắt đầu kiểm tra Search Service với Từ Đồng Nghĩa ---")
    
    # Danh sách các câu truy vấn để kiểm tra
    test_queries = [
        {
            "description": "TEST 1: Truy vấn gốc với từ 'biển'",
            "query": "tôi muốn đến một nơi có biển thật đẹp"
        },
        {
            "description": "TEST 2: Truy vấn với từ đồng nghĩa 'bãi biển'",
            "query": "tôi muốn đến một nơi có bãi biển thật đẹp" # 'bãi biển' là đồng nghĩa của 'biển'
        },
        {
            "description": "TEST 3: Truy vấn gốc với từ 'khám phá' và 'yên tĩnh'",
            "query": "chỗ nào để khám phá mà lại yên tĩnh"
        },
        {
            "description": "TEST 4: Truy vấn với từ đồng nghĩa 'phượt' và 'vắng người'",
            "query": "chỗ nào để phượt mà lại vắng người" # 'phượt' đồng nghĩa 'khám phá', 'vắng người' đồng nghĩa 'yên tĩnh'
        },
        {
            "description": "TEST 5: Truy vấn gốc không có từ đồng nghĩa rõ ràng trong từ điển (để so sánh)",
            "query": "địa điểm có kiến trúc cổ"
        }
    ]

    num_results_to_show = 3 # Hiển thị ít kết quả hơn để dễ so sánh

    for i, test_case in enumerate(test_queries):
        print(f"\n\n--- {test_case['description']} ---")
        print(f"Đang tìm kiếm cho truy vấn: '{test_case['query']}'")
        
        # Gọi hàm tìm kiếm từ service
        # Hàm này sẽ lần lượt gọi preprocessor (với synonym expansion), tfidf_engine, và truy vấn DB
        results = search_locations_by_tfidf(test_case['query'], num_results=num_results_to_show)
        
        print(f"\n--- Kết quả tìm kiếm (Top {num_results_to_show}) cho TEST {i+1} ---")
        if results:
            for rank, item in enumerate(results):
                print(f"\n{rank+1}. ID: {item.get('id_dia_diem')}")
                print(f"   Tên: {item.get('ten')}")
                print(f"   Mô tả ngắn: {item.get('mo_ta')}")
                print(f"   Điểm TF-IDF: {item.get('tfidf_score')}")
        else:
            print("Không tìm thấy kết quả nào phù hợp.")
        print("="*50)
        
    print("\n--- Kiểm tra Search Service với Từ Đồng Nghĩa hoàn tất ---")