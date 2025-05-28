# backend/app/services/search_service.py
import mysql.connector
import re
import os
# import numpy as np # Không cần thiết cho logic sắp xếp list dictionary

# Import các module/lớp đã tạo
from app.search_logic.preprocessor import preprocess_query
from app.search_logic.tfidf_engine import TFIDFEngine
from app.core.database import get_db_connection

# Lấy đường dẫn JAR và các cấu hình địa danh
# Nên đặt các list/dict địa danh vào config.py để quản lý tập trung
try:
    from app.core.config import (
        VNCORENLP_JAR_PATH,
        VIETNAM_PROVINCES_STANDARDIZED,
        PROVINCE_TO_REGION_MAP,
        VIETNAM_REGIONS_KEYWORDS_MAP,
        VUNG_MIEN_COLUMN_NAME_IN_DB  # Tên cột vùng miền trong DB
    )
except ImportError:
    print("SERVICE CẢNH BÁO: Không tìm thấy VNCORENLP_JAR_PATH trong config, sử dụng giá trị mặc định.")
    # Xác định BASE_DIR dựa trên vị trí file hiện tại (services) rồi đi lên 2 cấp (app -> backend)
    APP_DIR = os.path.dirname(os.path.abspath(__file__)) # Thư mục services
    # BASE_DIR = os.path.dirname(APP_DIR) # Thư mục app/
    # BASE_DIR_FOR_DATA_AND_LIB = os.path.dirname(BASE_DIR) # Thư mục backend/
    
    # SỬA ĐOẠN NÀY CHO ĐÚNG:
    # Giả sử file search_service.py nằm trong backend/app/services/
    # Chúng ta cần đi lên 2 cấp để ra được thư mục backend/
    CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__)) # -> backend/app/services
    APP_DIR = os.path.dirname(CURRENT_FILE_DIR) # -> backend/app
    BACKEND_DIR = os.path.dirname(APP_DIR) # -> backend/

    VNCORENLP_JAR_PATH = os.path.join(BACKEND_DIR, "lib", "VnCoreNLP-1.2.jar") # Đúng: backend/lib/VnCoreNLP-1.2.jar
    print(f"SERVICE CẢNH BÁO (Đã sửa): Không tìm thấy VNCORENLP_JAR_PATH trong config, sử dụng mặc định: {VNCORENLP_JAR_PATH}")

    VIETNAM_PROVINCES_STANDARDIZED = [
    "an giang", "bà rịa vũng tàu", "bạc liêu", "bắc kạn", "bắc giang", "bắc ninh", 
    "bến tre", "bình dương", "bình định", "bình phước", "bình thuận", "cà mau",
    "cao bằng", "cần thơ", "đà nẵng", "đắk lắk", "đắk nông", "điện biên", "đồng nai",
    "đồng tháp", "gia lai", "hà giang", "hà nam", "hà nội",  # << ĐẢM BẢO CÓ DẤU
    "hà tĩnh", "hải dương", "hải phòng", "hậu giang", "hòa bình", "hưng yên", 
    "khánh hòa", "kiên giang", "kon tum", "lai châu", "lâm đồng", "lạng sơn", 
    "lào cai", "long an", "nam định", "nghệ an", "ninh bình", "ninh thuận", 
    "phú thọ", "phú yên", "quảng bình", "quảng nam", "quảng ngãi", "quảng ninh", 
    "quảng trị", "sóc trăng", "sơn la", "tây ninh", "thái bình", "thái nguyên", 
    "thanh hóa", "thừa thiên huế", "tiền giang", "tp hồ chí minh", # << "thành phố hồ chí minh" cũng là một lựa chọn
    "trà vinh", "tuyên quang", "vĩnh long", "vĩnh phúc", "yên bái"
]
    PROVINCE_TO_REGION_MAP = {
        "ha noi": "miền bắc", "hai phong": "miền bắc", "lao cai": "tây bắc bộ", "quang ninh": "đông bắc bộ",
        "thua thien hue": "miền trung", "da nang": "nam trung bộ", "quang nam": "nam trung bộ", "khanh hoa": "nam trung bộ",
        "tp ho chi minh": "miền nam", "can tho": "đồng bằng sông cửu long", "an giang": "đồng bằng sông cửu long",
        "dien bien": "tây bắc bộ", "dak lak": "tây nguyên", "lam dong": "tây nguyên",
    }
    VIETNAM_REGIONS_KEYWORDS_MAP = {
        "bắc bộ": "miền bắc", "miền bắc": "miền bắc", "trung bộ": "miền trung", "miền trung": "miền trung",
        "nam bộ": "miền nam", "miền nam": "miền nam", "tây bắc bộ": "tây bắc bộ", "tây bắc": "tây bắc bộ",
        "đông bắc bộ": "đông bắc bộ", "đông bắc": "đông bắc bộ", "bắc trung bộ": "bắc trung bộ",
        "nam trung bộ": "nam trung bộ", "duyên hải nam trung bộ": "nam trung bộ", "tây nguyên": "tây nguyên",
        "đông nam bộ": "đông nam bộ", "đồng bằng sông cửu long": "đồng bằng sông cửu long", "miền tây": "đồng bằng sông cửu long"
    }
    VUNG_MIEN_COLUMN_NAME_IN_DB = "vung_mien"


print("Khởi tạo TFIDFEngine từ search_service...")
tfidf_engine_instance = TFIDFEngine()

def _normalize_for_location_matching(text: str) -> str:
    if not text: return ""
    text = text.lower()
    text = text.replace("_", " ")
    text = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_standardized_target_location(location_keywords_from_preprocessor: list) -> dict:
    target_province_std = None
    target_region_std = None
    sorted_loc_kws = sorted(location_keywords_from_preprocessor, key=len, reverse=True)

    for loc_kw in sorted_loc_kws:
        normalized_loc = _normalize_for_location_matching(loc_kw)
        print(f"DEBUG _get_standardized_target_location: loc_kw='{loc_kw}', normalized_loc='{normalized_loc}'") # THÊM DÒNG NÀY
        if normalized_loc in VIETNAM_PROVINCES_STANDARDIZED:
            target_province_std = normalized_loc
            if normalized_loc in PROVINCE_TO_REGION_MAP:
                target_region_std = PROVINCE_TO_REGION_MAP[normalized_loc]
            break

    if not target_region_std:
        full_location_text_normalized = " ".join([_normalize_for_location_matching(kw) for kw in location_keywords_from_preprocessor])
        sorted_region_input_keywords = sorted(VIETNAM_REGIONS_KEYWORDS_MAP.keys(), key=len, reverse=True)
        for region_input_keyword in sorted_region_input_keywords:
            if re.search(r'\b' + re.escape(region_input_keyword) + r'\b', full_location_text_normalized):
                target_region_std = VIETNAM_REGIONS_KEYWORDS_MAP[region_input_keyword]
                break
                
    print(f"Service (_get_standardized_target_location): Province: {target_province_std}, Region: {target_region_std}")
    return {'province': target_province_std, 'region': target_region_std}

def _fetch_location_data_by_ids(location_ids: list, columns: str = "id_dia_diem, ten, mo_ta, tinh") -> list:
    if not location_ids: return []
    conn = None
    fetched_data_map = {}
    try:
        conn = get_db_connection()
        if conn is None:
            print("Service Lỗi: Không thể kết nối CSDL trong _fetch_location_data_by_ids.")
            return []
        
        cursor = conn.cursor(dictionary=True)
        
        batch_size = 500 
        fetched_results_for_batch = []
        for i in range(0, len(location_ids), batch_size):
            batch_ids = location_ids[i:i + batch_size]
            placeholders = ', '.join(['%s'] * len(batch_ids))
            query = f"SELECT {columns} FROM dia_danh WHERE id_dia_diem IN ({placeholders})"
            cursor.execute(query, tuple(batch_ids))
            fetched_results_for_batch.extend(cursor.fetchall())

        for row in fetched_results_for_batch:
            fetched_data_map[row['id_dia_diem']] = row
            
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi truy vấn CSDL (_fetch_location_data_by_ids): {err}")
        return [] 
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    
    ordered_fetched_data = []
    for loc_id in location_ids: # Đảm bảo thứ tự nếu cần, hoặc trả về map nếu không cần thứ tự
        if loc_id in fetched_data_map:
            ordered_fetched_data.append(fetched_data_map[loc_id])
    return ordered_fetched_data

def _fetch_ids_by_location_filter(target_province: str = None, target_region: str = None) -> list:
    if not target_province and not target_region: return []
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
        if target_region:
            if VUNG_MIEN_COLUMN_NAME_IN_DB:
                sql_conditions.append(f"LOWER({VUNG_MIEN_COLUMN_NAME_IN_DB}) = %s")
                sql_params.append(target_region)
            else:
                 print(f"SERVICE CẢNH BÁO: Lọc theo vùng ('{target_region}') bị bỏ qua do VUNG_MIEN_COLUMN_NAME_IN_DB không được cấu hình.")
                 if not target_province: return [] # Nếu chỉ có target_region mà không hỗ trợ thì trả rỗng

        if not sql_conditions: return []
        condition_str = " AND ".join(sql_conditions)
        query = f"SELECT id_dia_diem FROM dia_danh WHERE {condition_str} ORDER BY RAND() LIMIT 200"
        
        cursor.execute(query, tuple(sql_params))
        results = cursor.fetchall()
        all_ids = [row['id_dia_diem'] for row in results]
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi lấy ID từ tỉnh/vùng (_fetch_ids_by_location_filter): {err}")
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    print(f"Service (_fetch_ids_by_location_filter): Tìm thấy {len(all_ids)} ID cho (Tỉnh: {target_province}, Vùng: {target_region})")
    return all_ids

# Hàm tìm kiếm chính, giữ nguyên tên theo yêu cầu của bạn
def search_locations_by_tfidf(user_query_text: str, num_results: int = 5) -> dict:
    print(f"Service: Nhận truy vấn (search_locations_by_tfidf): '{user_query_text}'")
    
    output_structure = {
        "query_details": {
            "original_query": user_query_text, "processed_for_tfidf": None,
            "identified_raw_locations": None, "target_province": None,
            "target_region": None, "applied_negations": []
        },
        "province_results": {"province_name": None, "title": None, "locations": []},
        "other_results": {"title": "Kết quả tìm kiếm", "locations": []}
    }

    try:
        processed_data = preprocess_query(user_query_text, vncorenlp_jar_path=VNCORENLP_JAR_PATH)
    except Exception as e:
        print(f"Service Lỗi nghiêm trọng trong preprocess_query: {e}")
        import traceback
        traceback.print_exc() 
        output_structure["other_results"]["title"] = "Lỗi xử lý truy vấn."
        return output_structure

    query_string_for_tfidf = " ".join(processed_data['all_keywords'])
    negative_keywords = processed_data['negative_keywords']
    
    output_structure["query_details"]["processed_for_tfidf"] = query_string_for_tfidf
    output_structure["query_details"]["identified_raw_locations"] = processed_data['location_keywords']
    output_structure["query_details"]["applied_negations"] = negative_keywords
    
    target_location_info = _get_standardized_target_location(processed_data['location_keywords'])
    target_province_std = target_location_info['province']
    target_region_std = target_location_info['region']
    output_structure["query_details"]["target_province"] = target_province_std
    output_structure["query_details"]["target_region"] = target_region_std
    if target_province_std:
        province_display_name = target_province_std.replace("_", " ").title()
        output_structure["province_results"]["province_name"] = province_display_name
        output_structure["province_results"]["title"] = f"Các địa điểm ở {province_display_name}"

    candidate_ids_with_scores_tuples = [] 

    if not tfidf_engine_instance.is_ready():
        print("Service: TFIDFEngine chưa sẵn sàng.")
        output_structure["other_results"]["title"] = "Lỗi hệ thống tìm kiếm (TF-IDF)."
        return output_structure

    if query_string_for_tfidf:
        print(f"Service: Tính điểm TF-IDF cho query: '{query_string_for_tfidf}'")
        candidate_ids_with_scores_tuples = tfidf_engine_instance.calculate_similarity(
            query_string_for_tfidf,
            num_results=len(tfidf_engine_instance.location_ids) 
        )
        print(f"Service: {len(candidate_ids_with_scores_tuples)} địa điểm có điểm TF-IDF.")
    
    elif target_province_std or target_region_std:
        print(f"Service: Query TF-IDF rỗng. Lấy tất cả địa điểm từ địa danh mục tiêu.")
        ids_from_location_filter = _fetch_ids_by_location_filter(target_province_std, target_region_std)
        candidate_ids_with_scores_tuples = [(loc_id, 0.01) for loc_id in ids_from_location_filter]
        print(f"Service: {len(candidate_ids_with_scores_tuples)} địa điểm từ lọc địa danh thuần túy.")
    
    if not candidate_ids_with_scores_tuples:
        print("Service: Không có ứng viên nào sau khi tính TF-IDF hoặc lọc địa danh ban đầu.")
        output_structure["other_results"]["title"] = "Không tìm thấy kết quả nào phù hợp với từ khóa."
        return output_structure
        
    # Lấy chi tiết (id, ten, mo_ta, tinh) và gắn điểm TF-IDF
    # SỬ DỤNG ĐÚNG TÊN HÀM ĐÃ ĐỊNH NGHĨA: _fetch_location_data_by_ids
    all_candidates_details_list = []
    if candidate_ids_with_scores_tuples: # Chỉ fetch nếu có ID ứng viên
        ids_to_fetch = [loc_id for loc_id, score in candidate_ids_with_scores_tuples]
        fetched_details = _fetch_location_data_by_ids(ids_to_fetch, "id_dia_diem, ten, mo_ta, tinh")
        
        details_map = {detail['id_dia_diem']: detail for detail in fetched_details}
        
        for loc_id, score in candidate_ids_with_scores_tuples:
            if loc_id in details_map:
                detail = details_map[loc_id].copy()
                detail['score'] = round(score, 4) 
                all_candidates_details_list.append(detail)
    
    all_candidates_details_list.sort(key=lambda x: x.get('score', 0), reverse=True)
    print(f"Service: Có {len(all_candidates_details_list)} ứng viên với chi tiết và điểm số, đã sắp xếp.")

    # Lọc phủ định
    final_candidates = []
    if negative_keywords:
        print(f"Service: Áp dụng bộ lọc phủ định: {negative_keywords}")
        for loc_data in all_candidates_details_list:
            is_negated = False
            text_to_check = (loc_data.get('ten', '') + " " + loc_data.get('mo_ta', '')).lower()
            for neg_kw in negative_keywords:
                if neg_kw.lower() in text_to_check:
                    is_negated = True; break
            if not is_negated:
                final_candidates.append(loc_data)
    else:
        final_candidates = all_candidates_details_list
    
    print(f"Service: Còn {len(final_candidates)} ứng viên sau khi lọc phủ định.")
    
    # Phân tách kết quả
    if target_province_std:
        province_specific_results = []
        other_similar_results = []
        for loc_data in final_candidates:
            db_province_normalized = _normalize_for_location_matching(loc_data.get('tinh', ''))
            if db_province_normalized == target_province_std:
                province_specific_results.append(loc_data)
            else:
                other_similar_results.append(loc_data)
        
        # Không cần sort lại vì final_candidates đã được sort
        output_structure["province_results"]["locations"] = province_specific_results[:num_results]
        output_structure["other_results"]["locations"] = other_similar_results[:num_results]
        
        if not output_structure["province_results"]["locations"] and not output_structure["other_results"]["locations"]:
            province_display_name = target_province_std.replace("_", " ").title()
            if output_structure["province_results"]["title"]: 
                 output_structure["province_results"]["title"] += " (Không có kết quả khớp mô tả)"
            else: # Trường hợp title chưa được set
                 output_structure["province_results"]["title"] = f"Không tìm thấy kết quả nào ở {province_display_name} khớp mô tả"
            output_structure["other_results"]["title"] = "Không tìm thấy kết quả nào phù hợp"

        elif not output_structure["province_results"]["locations"]:
            province_display_name = target_province_std.replace("_", " ").title()
            if output_structure["province_results"]["title"]:
                 output_structure["province_results"]["title"] += " (Không có kết quả khớp mô tả)"
            else:
                 output_structure["province_results"]["title"] = f"Không tìm thấy kết quả nào ở {province_display_name} khớp mô tả"

            if output_structure["other_results"]["locations"]: # Nếu có kết quả ở mục other
                output_structure["other_results"]["title"] = "Các địa điểm tương tự ở tỉnh khác"
            else: # Nếu other cũng không có
                output_structure["other_results"]["title"] = "Không có địa điểm tương tự nào khác"


        elif not output_structure["other_results"]["locations"]:
             output_structure["other_results"]["title"] = "Không có địa điểm tương tự nào khác."
        else: 
            output_structure["other_results"]["title"] = "Các địa điểm tương tự ở tỉnh khác"

    else: 
        output_structure["other_results"]["locations"] = final_candidates[:num_results]
        if not query_string_for_tfidf and not target_region_std:
             output_structure["other_results"]["title"] = "Vui lòng nhập từ khóa tìm kiếm cụ thể hơn"
        elif not target_province_std : 
            output_structure["other_results"]["title"] = "Các địa điểm gợi ý"
        if not output_structure["other_results"]["locations"]:
             output_structure["other_results"]["title"] = "Không tìm thấy kết quả nào phù hợp"

    print(f"Service: Trả về {len(output_structure['province_results']['locations'])} kết quả tỉnh, {len(output_structure['other_results']['locations'])} kết quả khác.")
    return output_structure

def get_location_details_by_id(location_id: str) -> dict:
    conn = None
    try:
        conn = get_db_connection()
        if conn is None: return None
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id_dia_diem, ten, mo_ta, dia_chi, tinh, mo_ta_chi_tiet FROM dia_danh WHERE id_dia_diem = %s"
        cursor.execute(query, (location_id,))
        result = cursor.fetchone()
        return result
    except mysql.connector.Error as err:
        print(f"Service Lỗi khi lấy chi tiết địa điểm ID {location_id}: {err}")
        return None
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()