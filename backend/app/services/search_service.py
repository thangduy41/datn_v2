# backend/app/services/search_service.py
import mysql.connector
import re
import os

# Import các module/lớp đã tạo
from app.search_logic.preprocessor import preprocess_query
# Giả sử VnCoreNLP được khởi tạo bên trong preprocess_query khi cần
# from app.search_logic.preprocessor import initialize_vncorenlp, close_vncorenlp

from app.search_logic.tfidf_engine import TFIDFEngine
from app.core.database import get_db_connection # Hàm lấy kết nối DB

# Lấy đường dẫn JAR từ config hoặc đặt mặc định
try:
    from app.core.config import VNCORENLP_JAR_PATH
except ImportError:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    VNCORENLP_JAR_PATH = os.path.join(BASE_DIR, "lib", "VnCoreNLP-1.2.jar") # Đặt đường dẫn mặc định của bạn ở đây
    print(f"SERVICE CẢNH BÁO: Không tìm thấy VNCORENLP_JAR_PATH trong config, sử dụng mặc định: {VNCORENLP_JAR_PATH}")

# Khởi tạo TFIDFEngine một lần
print("Khởi tạo TFIDFEngine từ search_service...")
tfidf_engine_instance = TFIDFEngine()

# --- CÁC DANH SÁCH CHUẨN HÓA CHO ĐỊA DANH ---
# !!! NÊN CHUYỂN CÁC LIST NÀY VÀO config.py hoặc một module tiện ích !!!
VIETNAM_PROVINCES_STANDARDIZED = [
    "an giang", "ba ria vung tau", "bac lieu", "bac kan", "bac giang", "bac ninh",
    "ben tre", "binh duong", "binh dinh", "binh phuoc", "binh thuan", "ca mau",
    "cao bang", "can tho", "da nang", "dak lak", "dak nong", "dien bien", "dong nai",
    "dong thap", "gia lai", "ha giang", "ha nam", "ha noi", "ha tinh", "hai duong",
    "hai phong", "hau giang", "hoa binh", "hung yen", "khanh hoa", "kien giang",
    "kon tum", "lai chau", "lam dong", "lang son", "lao cai", "long an", "nam dinh",
    "nghe an", "ninh binh", "ninh thuan", "phu tho", "phu yen", "quang binh", "quang nam",
    "quang ngai", "quang ninh", "quang tri", "soc trang", "son la", "tay ninh", "thai binh",
    "thai nguyen", "thanh hoa", "thua thien hue", "tien giang", "tp ho chi minh", "tra vinh",
    "tuyen quang", "vinh long", "vinh phuc", "yen bai"
]
PROVINCE_TO_REGION_MAP = {
    "ha noi": "miền bắc", "hai phong": "miền bắc", "lao cai": "tây bắc bộ", "quang ninh": "đông bắc bộ",
    "thua thien hue": "miền trung", "da nang": "nam trung bộ", "quang nam": "nam trung bộ", "khanh hoa": "nam trung bộ",
    "tp ho chi minh": "miền nam", "can tho": "đồng bằng sông cửu long", "an giang": "đồng bằng sông cửu long",
    "dien bien": "tây bắc bộ", "dak lak": "tây nguyên", "lam dong": "tây nguyên",
    # ... (Thêm đầy đủ)
}
VIETNAM_REGIONS_KEYWORDS_MAP = {
    "bắc bộ": "miền bắc", "miền bắc": "miền bắc",
    "trung bộ": "miền trung", "miền trung": "miền trung",
    "nam bộ": "miền nam", "miền nam": "miền nam",
    "tây bắc bộ": "tây bắc bộ", "tây bắc": "tây bắc bộ",
    "đông bắc bộ": "đông bắc bộ", "đông bắc": "đông bắc bộ",
    "bắc trung bộ": "bắc trung bộ",
    "nam trung bộ": "nam trung bộ", "duyên hải nam trung bộ": "nam trung bộ",
    "tây nguyên": "tây nguyên",
    "đông nam bộ": "đông nam bộ",
    "đồng bằng sông cửu long": "đồng bằng sông cửu long", "miền tây": "đồng bằng sông cửu long"
}
# Tên cột chứa thông tin vùng miền trong DB (nếu có)
# Giả sử bạn sẽ thêm cột 'vung_mien' vào bảng 'dia_danh'
VUNG_MIEN_COLUMN_NAME_IN_DB = "vung_mien" # Thay đổi nếu tên cột khác
# ----------------------------------------------------

def _normalize_for_location_matching(text: str) -> str:
    """Chuẩn hóa text để so khớp địa danh (tương tự như trong preprocessor)."""
    if not text: return ""
    text = text.lower()
    text = text.replace("_", " ")
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE) # Giữ lại ký tự tiếng Việt
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_target_location_from_keywords(location_keywords_from_preprocessor: list) -> dict:
    target_province = None
    target_region = None
    sorted_loc_kws = sorted(location_keywords_from_preprocessor, key=len, reverse=True)

    for loc_kw in sorted_loc_kws:
        normalized_loc = _normalize_for_location_matching(loc_kw)
        if normalized_loc in VIETNAM_PROVINCES_STANDARDIZED:
            target_province = normalized_loc
            if normalized_loc in PROVINCE_TO_REGION_MAP:
                target_region = PROVINCE_TO_REGION_MAP[normalized_loc]
            break

    if not target_region:
        sorted_region_keys = sorted(VIETNAM_REGIONS_KEYWORDS_MAP.keys(), key=len, reverse=True)
        for loc_kw in sorted_loc_kws: # Có thể dùng query gốc hoặc các token khác
            normalized_loc_for_region_check = _normalize_for_location_matching(loc_kw)
            for region_input_keyword in sorted_region_keys:
                if re.search(r'\b' + re.escape(region_input_keyword) + r'\b', normalized_loc_for_region_check):
                    target_region = VIETNAM_REGIONS_KEYWORDS_MAP[region_input_keyword]
                    break
            if target_region:
                break
    
    print(f"Service (get_target_location): Target Province: {target_province}, Target Region: {target_region}")
    return {'province': target_province, 'region': target_region}

def _fetch_location_data_by_ids(location_ids: list, columns: str = "id_dia_diem, ten, mo_ta") -> list:
    """
    Lấy dữ liệu các cột cụ thể cho danh sách ID địa điểm.
    Trả về list các dict, mỗi dict là một dòng dữ liệu.
    Thứ tự có thể không được bảo toàn.
    """
    if not location_ids:
        return []
    conn = None
    fetched_data = []
    try:
        conn = get_db_connection()
        if conn is None: return []
        cursor = conn.cursor(dictionary=True)
        placeholders = ', '.join(['%s'] * len(location_ids))
        query = f"SELECT {columns} FROM dia_danh WHERE id_dia_diem IN ({placeholders})"
        cursor.execute(query, tuple(location_ids))
        fetched_data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi truy vấn CSDL (_fetch_location_data_by_ids): {err}")
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    return fetched_data

def _fetch_all_ids_from_location_filter(target_province: str = None, target_region: str = None) -> list:
    """Lấy tất cả ID địa điểm dựa trên tỉnh hoặc vùng (nếu query TF-IDF rỗng)."""
    if not target_province and not target_region:
        return []
    
    conn = None
    all_ids = []
    sql_conditions = []
    sql_params = []
    try:
        conn = get_db_connection()
        if conn is None: return []
        cursor = conn.cursor(dictionary=True)

        if target_province:
            sql_conditions.append(f"LOWER(tinh) = %s")
            sql_params.append(target_province)
        
        if target_region: # Giả sử có cột VUNG_MIEN_COLUMN_NAME_IN_DB
            sql_conditions.append(f"LOWER({VUNG_MIEN_COLUMN_NAME_IN_DB}) = %s")
            sql_params.append(target_region)

        if not sql_conditions: return []

        condition_str = " AND ".join(sql_conditions)
        query = f"SELECT id_dia_diem FROM dia_danh WHERE {condition_str}"
        
        cursor.execute(query, tuple(sql_params))
        results = cursor.fetchall()
        all_ids = [row['id_dia_diem'] for row in results]
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi lấy ID từ tỉnh/vùng (_fetch_all_ids_from_location_filter): {err}")
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    print(f"Service: Tìm thấy {len(all_ids)} địa điểm cho bộ lọc địa danh thuần túy (tỉnh: {target_province}, vùng: {target_region})")
    return all_ids


def search_locations_by_tfidf(user_query_text: str, num_results: int = 5) -> list:
    print(f"Service: Nhận truy vấn: '{user_query_text}'")

    try:
        processed_data = preprocess_query(user_query_text, vncorenlp_jar_path=VNCORENLP_JAR_PATH)
    except FileNotFoundError as e:
        print(f"Service Lỗi: Không tìm thấy file VnCoreNLP.jar. Chi tiết: {e}")
        return [{"error": f"Lỗi cấu hình server NLP: {e}"}]
    except Exception as e:
        print(f"Service Lỗi trong quá trình tiền xử lý: {e}")
        import traceback
        traceback.print_exc()
        return [{"error": "Lỗi xử lý truy vấn"}]

    all_keywords_list = processed_data['all_keywords']
    query_string_for_tfidf = " ".join(all_keywords_list)
    negative_keywords = processed_data['negative_keywords']
    location_keywords_from_preprocessor = processed_data['location_keywords']
    
    target_location_info = _get_target_location_from_keywords(location_keywords_from_preprocessor)
    target_province = target_location_info['province']
    target_region = target_location_info['region']

    top_matches_with_scores = [] # List các tuple (id, score)

    # Ưu tiên 1: Nếu có query cho TF-IDF và engine sẵn sàng
    if query_string_for_tfidf and tfidf_engine_instance.is_ready():
        print(f"Service: Thực hiện tìm kiếm TF-IDF với query: '{query_string_for_tfidf}'")
        candidate_multiplier = 5 
        initial_candidates_count = num_results * candidate_multiplier
        top_matches_with_scores = tfidf_engine_instance.calculate_similarity(
            query_string_for_tfidf,
            initial_candidates_count 
        )
        print(f"Service: Tìm thấy {len(top_matches_with_scores)} ứng viên từ TF-IDF.")

        # Lọc ngay các ứng viên TF-IDF này theo tỉnh/vùng nếu có
        if (target_province or target_region) and top_matches_with_scores:
            ids_from_tfidf = [match[0] for match in top_matches_with_scores]
            # Truy vấn CSDL để lọc các ID này theo tỉnh/vùng
            conn = None
            valid_ids_after_location_filter = []
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    placeholders = ', '.join(['%s'] * len(ids_from_tfidf))
                    sql_conditions_filter = []
                    sql_params_filter = list(ids_from_tfidf) # Params cho IN clause

                    if target_province:
                        sql_conditions_filter.append(f"LOWER(tinh) = %s")
                        sql_params_filter.append(target_province)
                    if target_region: # Giả sử có cột vung_mien
                        sql_conditions_filter.append(f"LOWER({VUNG_MIEN_COLUMN_NAME_IN_DB}) = %s")
                        sql_params_filter.append(target_region)
                    
                    if sql_conditions_filter:
                        condition_filter_str = " AND ".join(sql_conditions_filter)
                        db_filter_query = f"SELECT id_dia_diem FROM dia_danh WHERE id_dia_diem IN ({placeholders}) AND ({condition_filter_str})"
                        
                        # Tách params cho IN và params cho điều kiện
                        final_filter_params = tuple(ids_from_tfidf) + tuple(sql_params_filter[len(ids_from_tfidf):])
                        cursor.execute(db_filter_query, final_filter_params)
                        rows = cursor.fetchall()
                        valid_ids_after_location_filter = [row['id_dia_diem'] for row in rows]
                        top_matches_with_scores = [m for m in top_matches_with_scores if m[0] in valid_ids_after_location_filter]
                        print(f"Service: Số ứng viên TF-IDF sau khi lọc địa danh: {len(top_matches_with_scores)}")
            except mysql.connector.Error as err:
                print(f"Service Lỗi khi lọc kết quả TF-IDF theo địa danh: {err}")
            finally:
                if conn and conn.is_connected():
                    if 'cursor' in locals() and cursor is not None: cursor.close()
                    conn.close()
    
    # Ưu tiên 2: Nếu query TF-IDF rỗng (hoặc engine không sẵn sàng) nhưng có địa danh cụ thể
    elif not query_string_for_tfidf and (target_province or target_region):
        print(f"Service: Query TF-IDF rỗng. Lấy tất cả địa điểm theo Tỉnh: {target_province}, Vùng: {target_region}.")
        all_ids_in_location = _fetch_all_ids_from_location_filter(target_province, target_region)
        # Gán điểm TF-IDF giả là 0.0 vì không có thông tin từ TF-IDF
        # Hoặc có thể gán 1.0 để ưu tiên hiển thị nếu không có yếu tố nào khác
        top_matches_with_scores = [(loc_id, 0.0) for loc_id in all_ids_in_location]
        print(f"Service: Lấy được {len(top_matches_with_scores)} địa điểm từ lọc địa danh thuần túy.")
    
    # Nếu TF-IDF engine không sẵn sàng và có query string
    elif query_string_for_tfidf and not tfidf_engine_instance.is_ready():
        print("Service: TFIDFEngine chưa sẵn sàng. Không thể thực hiện tìm kiếm TF-IDF.")
        return [{"error": "Lỗi hệ thống tìm kiếm (TF-IDF engine not ready)"}]
    
    # Nếu không có gì cả
    if not top_matches_with_scores:
        print("Service: Không tìm thấy ứng viên nào sau các bước tìm kiếm/lọc ban đầu.")
        return []

    # Lấy thông tin chi tiết cho các ứng viên còn lại
    # Giới hạn số lượng ID cần lấy chi tiết, ví dụ gấp đôi số kết quả mong muốn
    # để có chỗ cho việc lọc phủ định.
    ids_for_details = [match[0] for match in top_matches_with_scores][:num_results * 2 + 5] 
    
    location_details_list_with_score = []
    if ids_for_details:
        details_data = _fetch_location_data_by_ids(ids_for_details, "id_dia_diem, ten, mo_ta") # Chỉ lấy các cột cần thiết
        details_map = {item['id_dia_diem']: item for item in details_data}

        # Kết hợp lại với score và đảm bảo thứ tự ban đầu của top_matches_with_scores
        for loc_id, score in top_matches_with_scores:
            if loc_id in details_map: # Chỉ xử lý những ID đã lấy được chi tiết
                detail = details_map[loc_id].copy()
                detail['tfidf_score'] = round(score, 4) # Giữ lại điểm TF-IDF
                location_details_list_with_score.append(detail)
    
    # Lọc dựa trên negative_keywords
    results_after_negation_filter = []
    if negative_keywords:
        print(f"Service: Áp dụng bộ lọc phủ định với các từ khóa: {negative_keywords}")
        for loc_data in location_details_list_with_score:
            is_negated_match = False
            # Kiểm tra trong tên và mô tả ngắn
            text_to_check = (loc_data.get('ten', '') + " " + loc_data.get('mo_ta', '')).lower()
            for neg_kw in negative_keywords:
                if neg_kw.lower() in text_to_check: # neg_kw từ preprocessor đã là lowercase
                    is_negated_match = True
                    print(f"Service: Địa điểm ID {loc_data['id_dia_diem']} ({loc_data['ten']}) bị loại do khớp từ khóa phủ định '{neg_kw}'")
                    break 
            if not is_negated_match:
                results_after_negation_filter.append(loc_data)
    else:
        results_after_negation_filter = location_details_list_with_score
            
    # Trả về top N kết quả cuối cùng
    final_results_to_return = results_after_negation_filter[:num_results]
                
    print(f"Service: Kết quả cuối cùng trả về: {len(final_results_to_return)} địa điểm")
    # Cân nhắc việc đóng VnCoreNLP nếu nó được khởi tạo mỗi lần gọi preprocess_query
    # Nếu VnCoreNLP là instance toàn cục trong preprocessor, thì không cần đóng ở đây.
    # close_vncorenlp() 
    return final_results_to_return

def get_location_details_by_id(location_id: str) -> dict:
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print(f"Service: Không thể kết nối DB để lấy chi tiết cho ID {location_id}")
            return None # Hoặc raise một exception cụ thể
        cursor = conn.cursor(dictionary=True)
        # Lấy tất cả các cột bạn muốn hiển thị trên trang chi tiết
        query = "SELECT id_dia_diem, ten, mo_ta, dia_chi, tinh, mo_ta_chi_tiet FROM dia_danh WHERE id_dia_diem = %s"
        cursor.execute(query, (location_id,))
        result = cursor.fetchone() # Trả về một dictionary hoặc None nếu không tìm thấy
        if result:
            print(f"Service: Đã tìm thấy chi tiết cho ID {location_id}: {result.get('ten')}")
        else:
            print(f"Service: Không tìm thấy chi tiết cho ID {location_id} trong DB.")
        return result
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi lấy chi tiết địa điểm ID {location_id}: {err}")
        return None # Hoặc raise exception
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            conn.close()