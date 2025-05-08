# backend/app/services/search_service.py
import mysql.connector

# Import các module/lớp đã tạo
from app.search_logic.preprocessor import preprocess_query
from app.search_logic.tfidf_engine import TFIDFEngine
from app.core.database import get_db_connection # Hàm lấy kết nối DB

# Khởi tạo TFIDFEngine một lần khi module service này được import.
# Điều này sẽ kích hoạt việc tải các file .pkl.
# Đây là một pattern phổ biến để đảm bảo model chỉ được load một lần.
print("Khởi tạo TFIDFEngine từ search_service...")
tfidf_engine_instance = TFIDFEngine() # Tạo instance của TFIDFEngine

def _fetch_location_details_by_ids(location_ids: list) -> list:
    """
    Truy vấn database để lấy tên và mô tả (mo_ta) cho danh sách các ID địa điểm.
    Trả về một list các dictionary, mỗi dict chứa thông tin của một địa điểm.
    Thứ tự trong list trả về có thể không giống thứ tự của location_ids đầu vào.
    """
    if not location_ids:
        return []

    conn = None
    location_details_map = {} # Dùng map để dễ truy cập theo ID
    try:
        conn = get_db_connection()
        if conn is None:
            print("Service: Không thể kết nối đến database.")
            return []
        
        cursor = conn.cursor(dictionary=True) # Trả về kết quả dạng dict

        # Tạo chuỗi placeholder %s cho IN clause một cách an toàn
        placeholders = ', '.join(['%s'] * len(location_ids))
        query = f"SELECT id_dia_diem, ten, mo_ta FROM dia_danh WHERE id_dia_diem IN ({placeholders})"
        
        cursor.execute(query, tuple(location_ids))
        results = cursor.fetchall()

        for row in results:
            location_details_map[row['id_dia_diem']] = {
                'id_dia_diem': row['id_dia_diem'],
                'ten': row['ten'],
                'mo_ta': row['mo_ta']
            }
        
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi truy vấn chi tiết địa điểm: {err}")
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            conn.close()
            # print("Service: Đã đóng kết nối DB sau khi lấy chi tiết.")

    # Sắp xếp lại kết quả theo thứ tự của location_ids đầu vào
    # và chỉ bao gồm những ID tìm thấy chi tiết
    ordered_results = []
    for loc_id in location_ids:
        if loc_id in location_details_map:
            ordered_results.append(location_details_map[loc_id])
    return ordered_results


def search_locations_by_tfidf(user_query_text: str, num_results: int = 5) -> list:
    """
    Hàm chính điều phối việc tìm kiếm địa điểm chỉ dựa trên TF-IDF.
    Trả về danh sách các địa điểm (dạng dict) đã có chi tiết.
    """
    print(f"Service: Nhận truy vấn: '{user_query_text}'")

    # 1. Tiền xử lý truy vấn
    processed_data = preprocess_query(user_query_text) # Đây là dictionary
    processed_query_for_tfidf = processed_data['tokens_for_tfidf']
    # keywords_for_tags = processed_data['keywords_for_tags'] # Sẽ dùng sau cho Tag Engine

    if not processed_query_for_tfidf: # Kiểm tra chuỗi token cho TF-IDF
        print("Service: Truy vấn rỗng sau khi tiền xử lý cho TF-IDF.")
        return []
    # Dòng print này đã có trong preprocessor rồi, có thể bỏ ở đây
    # print(f"Service: Truy vấn đã xử lý cho TF-IDF: '{processed_query_for_tfidf}'")

    # 2. Tính toán độ tương đồng và lấy top ID + score bằng TFIDFEngine
    if not tfidf_engine_instance.is_ready():
        print("Service: TFIDFEngine chưa sẵn sàng. Kiểm tra lỗi load model.")
        return []

    top_matches_with_scores = tfidf_engine_instance.calculate_similarity(
        processed_query_for_tfidf, # Truyền chuỗi token đã xử lý
        num_results
    )

    if not top_matches_with_scores:
        print("Service: Không tìm thấy kết quả nào từ TFIDFEngine.")
        return []

    print(f"Service: Top kết quả (ID, Score) từ TF-IDF: {top_matches_with_scores}")

    top_ids = [match[0] for match in top_matches_with_scores]

    # 3. Lấy thông tin chi tiết (tên, mô tả ngắn) từ database
    location_details_list = _fetch_location_details_by_ids(top_ids)

    # 4. Kết hợp điểm số TF-IDF vào thông tin chi tiết
    # ... (phần này giữ nguyên như cũ) ...
    results_with_scores = []
    for detail in location_details_list:
        score = next((s for id, s in top_matches_with_scores if id == detail['id_dia_diem']), None)
        if score is not None:
            detail_with_score = detail.copy() 
            detail_with_score['tfidf_score'] = round(score, 4) 
            results_with_scores.append(detail_with_score)

    final_results_ordered = []
    for loc_id, score in top_matches_with_scores:
        found_detail = next((res for res in results_with_scores if res['id_dia_diem'] == loc_id), None)
        if found_detail:
            final_results_ordered.append(found_detail)

    print(f"Service: Kết quả cuối cùng trả về: {len(final_results_ordered)} địa điểm")
    return final_results_ordered