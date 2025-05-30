# backend/app/services/search_service.py
import mysql.connector
import re
import os

# Import các module/lớp đã tạo
from app.search_logic.preprocessor import preprocess_query
from app.search_logic.tfidf_engine import TFIDFEngine 
from app.core.database import get_db_connection

# ... (Phần import config và khởi tạo hằng số, TFIDFEngine giữ nguyên như bạn đã gửi) ...
try:
    from app.core.config import (
        VNCORENLP_JAR_PATH,
        VIETNAM_PROVINCES_STANDARDIZED,
        PROVINCE_TO_REGION_MAP,
        VIETNAM_REGIONS_KEYWORDS_MAP,
        VUNG_MIEN_COLUMN_NAME_IN_DB
    )
except ImportError:
    print("SERVICE CẢNH BÁO: Không tìm thấy một số cấu hình trong app.core.config.py. Sử dụng giá trị mặc định.")
    CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = os.path.dirname(CURRENT_FILE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    VNCORENLP_JAR_PATH = os.path.join(BACKEND_DIR, "lib", "VnCoreNLP-1.2.jar")
    # ... (Copy lại các list VIETNAM_PROVINCES_STANDARDIZED etc. nếu cần fallback)
    VIETNAM_PROVINCES_STANDARDIZED = ["an giang", "bà rịa vũng tàu", "bạc liêu", "bắc kạn", "bắc giang", "bắc ninh", "bến tre", "bình dương", "bình định", "bình phước", "bình thuận", "cà mau", "cao bằng", "cần thơ", "đà nẵng", "đắk lắk", "đắk nông", "điện biên", "đồng nai", "đồng tháp", "gia lai", "hà giang", "hà nam", "hà nội", "hà tĩnh", "hải dương", "hải phòng", "hậu giang", "hòa bình", "hưng yên", "khánh hòa", "kiên giang", "kon tum", "lai châu", "lâm đồng", "lạng sơn", "lào cai", "long an", "nam định", "nghệ an", "ninh bình", "ninh thuận", "phú thọ", "phú yên", "quảng bình", "quảng nam", "quảng ngãi", "quảng ninh", "quảng trị", "sóc trăng", "sơn la", "tây ninh", "thái bình", "thái nguyên", "thanh hóa", "thừa thiên huế", "tiền giang", "tp hồ chí minh", "trà vinh", "tuyên quang", "vĩnh long", "vĩnh phúc", "yên bái"]
    PROVINCE_TO_REGION_MAP = {"hà nội": "miền bắc", "tp ho chi minh": "miền nam", "đà nẵng": "miền trung", "điện biên": "tây bắc bộ", "nghệ an": "bắc trung bộ"}
    VIETNAM_REGIONS_KEYWORDS_MAP = {"miền bắc": "miền bắc", "miền tây": "đồng bằng sông cửu long", "miền trung": "miền trung"}
    VUNG_MIEN_COLUMN_NAME_IN_DB = "vung_mien"


print("Khởi tạo TFIDFEngine từ search_service...")
tfidf_engine_instance = TFIDFEngine()

MIN_RELEVANCE_SCORE = 0.1 

# --- CÁC HÀM HELPER (_normalize_for_location_matching, _get_standardized_target_location, 
# _fetch_location_data_by_ids, _fetch_ids_by_location_filter, 
# _attach_scores_and_sort, _apply_negation_filter) giữ nguyên như file bạn đã gửi trước đó.
# Đảm bảo chúng hoạt động đúng.
# Ví dụ:
def _normalize_for_location_matching(text: str) -> str:
    if not text: return ""
    text = text.lower()
    text = text.replace("_", " ")
    text = re.sub(r'[^\w\sàáạảãăằắặẳẵâầấậẩẫđèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_standardized_target_location(location_keywords_from_preprocessor: list) -> dict:
    target_province_std = None; target_region_std = None
    sorted_loc_kws = sorted(location_keywords_from_preprocessor, key=len, reverse=True)
    for loc_kw in sorted_loc_kws:
        normalized_loc = _normalize_for_location_matching(loc_kw)
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
                target_region_std = VIETNAM_REGIONS_KEYWORDS_MAP[region_input_keyword]; break
    print(f"Service (_get_standardized_target_location): Province: {target_province_std}, Region: {target_region_std}")
    return {'province': target_province_std, 'region': target_region_std}

def _fetch_location_data_by_ids(location_ids: list, columns: str = "id_dia_diem, ten, mo_ta, tinh") -> list:
    if not location_ids: return []
    conn = None; fetched_data_map = {}
    try:
        conn = get_db_connection()
        if conn is None: return []
        cursor = conn.cursor(dictionary=True); batch_size = 500; all_db_results = []
        for i in range(0, len(location_ids), batch_size):
            batch_ids = location_ids[i:i + batch_size]
            if not batch_ids: continue
            placeholders = ', '.join(['%s'] * len(batch_ids))
            query = f"SELECT {columns} FROM dia_danh WHERE id_dia_diem IN ({placeholders})"
            cursor.execute(query, tuple(batch_ids))
            all_db_results.extend(cursor.fetchall())
        for row in all_db_results: fetched_data_map[row['id_dia_diem']] = row
    except mysql.connector.Error as err: print(f"Service Lỗi CSDL (_fetch_location_data_by_ids): {err}"); return []
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    return [fetched_data_map[loc_id] for loc_id in location_ids if loc_id in fetched_data_map]


def _fetch_ids_by_location_filter(target_province: str = None, target_region: str = None, exclude_ids: set = None) -> list:
    if not target_province and not target_region: return []
    conn = None; ids_found = []; sql_conditions = []; sql_params = []
    try:
        conn = get_db_connection()
        if conn is None: return []
        cursor = conn.cursor(dictionary=True)
        if target_province:
            sql_conditions.append(f"LOWER(tinh) = %s"); sql_params.append(target_province)
        if target_region:
            if VUNG_MIEN_COLUMN_NAME_IN_DB:
                sql_conditions.append(f"LOWER({VUNG_MIEN_COLUMN_NAME_IN_DB}) = %s"); sql_params.append(target_region)
            elif not target_province: return []
        if not sql_conditions: return []
        base_query_conditions = " AND ".join(sql_conditions)
        base_query = f"SELECT id_dia_diem FROM dia_danh WHERE {base_query_conditions}"
        if exclude_ids and len(exclude_ids) > 0:
            placeholders_exclude = ', '.join(['%s'] * len(exclude_ids))
            base_query += f" AND id_dia_diem NOT IN ({placeholders_exclude})"
            sql_params.extend(list(exclude_ids))
        # Bỏ ORDER BY RAND() LIMIT 500 để lấy hết nếu không có exclude_ids
        if not exclude_ids: # Nếu chỉ lọc tỉnh/vùng (không loại trừ) thì lấy hết
             base_query += " LIMIT 1000" # Giới hạn hợp lý để tránh quá nhiều
        else: # Nếu có exclude, giữ lại giới hạn cũ
             base_query += " ORDER BY RAND() LIMIT 500"

        cursor.execute(base_query, tuple(sql_params))
        results = cursor.fetchall()
        ids_found = [row['id_dia_diem'] for row in results]
    except mysql.connector.Error as err: print(f"Service Lỗi CSDL (_fetch_ids_by_location_filter): {err}")
    finally:
        if conn and conn.is_connected():
            if 'cursor' in locals() and cursor is not None: cursor.close()
            conn.close()
    print(f"Service (_fetch_ids_by_location_filter): Tìm thấy {len(ids_found)} ID cho (Tỉnh: {target_province}, Vùng: {target_region}, Exclude: {len(exclude_ids or set())})")
    return ids_found

def _attach_scores_and_sort(detailed_locations_list: list, scores_map: dict, default_score=0.0) -> list:
    results_with_score = []
    for detail in detailed_locations_list:
        loc_id = detail.get('id_dia_diem')
        if not loc_id: continue
        detail_with_score = detail.copy()
        detail_with_score['score'] = round(scores_map.get(loc_id, default_score), 4)
        results_with_score.append(detail_with_score)
    results_with_score.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results_with_score

def _apply_negation_filter(candidate_list_with_details: list, negative_keywords: list) -> list:
    if not negative_keywords:
        return candidate_list_with_details
    print(f"Service: Áp dụng bộ lọc phủ định: {negative_keywords}")
    final_candidates = []
    for loc_data in candidate_list_with_details:
        is_negated_match = False
        text_to_check = (loc_data.get('ten', '') + " " + loc_data.get('mo_ta', '')).lower()
        for neg_kw in negative_keywords:
            if neg_kw.lower() in text_to_check:
                is_negated_match = True
                break
        if not is_negated_match:
            final_candidates.append(loc_data)
    print(f"Service: Còn {len(final_candidates)} ứng viên sau khi áp dụng bộ lọc phủ định.")
    return final_candidates

# --- Hàm tìm kiếm chính ĐÃ SỬA ĐỔI ---
def search_locations_by_tfidf(user_query_text: str, num_results: int = 5) -> dict: # num_results là giới hạn cho mỗi section KHI CÓ query mô tả
    print(f"Service: Nhận truy vấn (search_locations_by_tfidf): '{user_query_text}'")
    
    output_structure = {
        "query_details": {"original_query": user_query_text, "processed_for_tfidf": None,
                          "identified_raw_locations": None, "target_province": None,
                          "target_region": None, "applied_negations": []},
        "province_results": {"province_name": None, "title": None, "locations": []},
        "other_results": {"title": "Kết quả tìm kiếm", "locations": []}
    }

    try:
        processed_data = preprocess_query(user_query_text, vncorenlp_jar_path=VNCORENLP_JAR_PATH)
    except Exception as e:
        print(f"Service Lỗi nghiêm trọng trong preprocess_query: {e}")
        output_structure["other_results"]["title"] = "Lỗi xử lý truy vấn."
        return output_structure

    query_string_for_tfidf = " ".join(processed_data.get('all_keywords', []))
    negative_keywords = processed_data.get('negative_keywords', [])
    
    output_structure["query_details"].update({
        "processed_for_tfidf": query_string_for_tfidf,
        "identified_raw_locations": processed_data.get('location_keywords', []),
        "applied_negations": negative_keywords
    })
    
    target_location_info = _get_standardized_target_location(processed_data.get('location_keywords', []))
    target_province_std = target_location_info['province']
    target_region_std = target_location_info['region'] 
    output_structure["query_details"]["target_province"] = target_province_std
    output_structure["query_details"]["target_region"] = target_region_std
    
    if target_province_std:
        province_display_name = target_province_std.replace("_", " ").title()
        output_structure["province_results"]["province_name"] = province_display_name
        output_structure["province_results"]["title"] = f"Các địa điểm ở {province_display_name}"

    if not tfidf_engine_instance.is_ready():
        print("Service: TFIDFEngine chưa sẵn sàng.")
        error_title = "Lỗi hệ thống tìm kiếm (TF-IDF)."
        if output_structure["province_results"]["title"]: output_structure["province_results"]["title"] += f" ({error_title})"
        else: output_structure["province_results"]["title"] = error_title
        output_structure["other_results"]["title"] = error_title
        return output_structure

    ids_in_province_results_set = set() 

    # ---- Xử lý Mục Tỉnh Ưu Tiên (province_results) ----
    if target_province_std:
        print(f"Service: Xử lý ưu tiên cho tỉnh: {target_province_std}")
        ids_in_target_province_only = _fetch_ids_by_location_filter(target_province=target_province_std)
        
        province_candidates_list_processed = []
        if ids_in_target_province_only:
            scores_for_province_map = {}
            apply_threshold_for_province_section = False 

            if query_string_for_tfidf: # Có từ khóa mô tả
                scores_tuples_province = tfidf_engine_instance.get_scores_for_specific_ids(
                    query_string_for_tfidf, 
                    ids_in_target_province_only
                )
                scores_for_province_map = dict(scores_tuples_province)
                apply_threshold_for_province_section = True 
                print(f"Service: Đã tính TF-IDF cho {len(scores_for_province_map)} địa điểm thuộc tỉnh ưu tiên.")
            else: # Chỉ có tên tỉnh
                scores_for_province_map = {loc_id: 1.0 for loc_id in ids_in_target_province_only} 
                apply_threshold_for_province_section = False # Không áp ngưỡng, hiển thị hết (sau lọc phủ định)
                print(f"Service: Gán điểm mặc định 1.0 cho {len(scores_for_province_map)} địa điểm thuộc tỉnh ưu tiên.")
            
            province_details_list = _fetch_location_data_by_ids(list(scores_for_province_map.keys()))
            province_candidates_with_score_sorted = _attach_scores_and_sort(
                province_details_list, 
                scores_for_province_map,
                default_score=1.0 if not query_string_for_tfidf else 0.001 
            )
            
            province_candidates_neg_filtered = _apply_negation_filter(province_candidates_with_score_sorted, negative_keywords)
            
            if apply_threshold_for_province_section: # Có query mô tả, áp dụng ngưỡng
                province_candidates_list_processed = [
                    loc for loc in province_candidates_neg_filtered if loc.get('score', 0.0) >= MIN_RELEVANCE_SCORE
                ]
            else: # Chỉ tìm theo tỉnh, hiển thị tất cả (đã lọc phủ định)
                province_candidates_list_processed = province_candidates_neg_filtered
            
            # Nếu chỉ tìm theo tỉnh (không có query mô tả), không giới hạn bởi num_results
            # Ngược lại, nếu có query mô tả, giới hạn bởi num_results
            if query_string_for_tfidf:
                output_structure["province_results"]["locations"] = province_candidates_list_processed[:num_results]
            else: # Hiển thị tất cả kết quả của tỉnh nếu chỉ tìm theo tên tỉnh
                output_structure["province_results"]["locations"] = province_candidates_list_processed
            
            ids_in_province_results_set = {loc['id_dia_diem'] for loc in output_structure["province_results"]["locations"]}
        print(f"Service: {len(output_structure['province_results']['locations'])} kết quả cho tỉnh ưu tiên '{target_province_std}'.")

    # ---- Xử lý Mục Kết Quả Khác (other_results) ----
    if query_string_for_tfidf: # Chỉ tìm "địa điểm khác" nếu có query mô tả
        print("Service: Xử lý mục kết quả khác...")
        all_locations_scores_tuples = tfidf_engine_instance.calculate_similarity(
            query_string_for_tfidf,
            num_results=len(tfidf_engine_instance.location_ids) 
        )
        
        other_candidate_scores_tuples_intermediate = []
        for loc_id, score in all_locations_scores_tuples:
            if loc_id not in ids_in_province_results_set: # Loại bỏ những cái đã ở mục tỉnh rồi
                 other_candidate_scores_tuples_intermediate.append((loc_id, score))
        
        other_candidates_list_processed = []
        if other_candidate_scores_tuples_intermediate:
            ids_for_other_details = [loc_id for loc_id, score in other_candidate_scores_tuples_intermediate]
            # Lấy chi tiết bao gồm 'tinh' để có thể lọc bỏ các địa điểm thuộc target_province_std (nếu có)
            other_details_full_list = _fetch_location_data_by_ids(ids_for_other_details, "id_dia_diem, ten, mo_ta, tinh")
            
            other_details_truly_other_province = []
            if target_province_std: # Nếu có tỉnh ưu tiên, đảm bảo mục "khác" không chứa địa điểm của tỉnh đó
                for detail in other_details_full_list:
                    if _normalize_for_location_matching(detail.get('tinh','')) != target_province_std:
                        other_details_truly_other_province.append(detail)
            else: # Không có tỉnh ưu tiên, thì tất cả đều là "other"
                other_details_truly_other_province = other_details_full_list

            other_scores_map = dict(other_candidate_scores_tuples_intermediate) # Dùng map để tra cứu điểm
            other_candidates_with_score_sorted = _attach_scores_and_sort(other_details_truly_other_province, other_scores_map)
            other_results_neg_filtered = _apply_negation_filter(other_candidates_with_score_sorted, negative_keywords)
            
            # Luôn áp ngưỡng cho other_results và LẤY TẤT CẢ KẾT QUẢ TRÊN NGƯỠNG
            other_candidates_list_processed = [
                loc for loc in other_results_neg_filtered if loc.get('score', 0.0) >= MIN_RELEVANCE_SCORE
            ]
            
        # Bỏ giới hạn num_results cho other_results theo yêu cầu của bạn
        # Tuy nhiên, bạn có thể muốn giới hạn một số lượng tối đa ở đây để API không trả về quá nhiều
        # Ví dụ: output_structure["other_results"]["locations"] = other_candidates_list_processed[:50] # Giới hạn 50
        output_structure["other_results"]["locations"] = other_candidates_list_processed
        print(f"Service: Tìm được {len(output_structure['other_results']['locations'])} kết quả khác.")

    # Cập nhật tiêu đề cuối cùng
    # ... (Logic cập nhật title giữ nguyên như phiên bản trước, có thể cần review lại cho mọi trường hợp) ...
    if target_province_std:
        province_display_name_final = output_structure["province_results"]["province_name"] or "Tỉnh/Thành ưu tiên"
        if not output_structure["province_results"]["locations"]:
            threshold_text = f"(điểm >= {MIN_RELEVANCE_SCORE})" if query_string_for_tfidf and apply_threshold_for_province_section else "(không có mô tả khớp hoặc chỉ tìm theo tỉnh)"
            output_structure["province_results"]["title"] = f"Không có địa điểm nào ở {province_display_name_final} khớp {threshold_text} và không bị phủ định."
        
        if not output_structure["other_results"]["locations"]:
            if query_string_for_tfidf: output_structure["other_results"]["title"] = "Không có địa điểm tương tự nào khác."
            else: output_structure["other_results"]["title"] = "" 
        elif output_structure["province_results"]["locations"] and output_structure["other_results"]["locations"]:
             output_structure["other_results"]["title"] = "Các địa điểm tương tự ở tỉnh khác"
        elif not output_structure["province_results"]["locations"] and output_structure["other_results"]["locations"]:
             output_structure["other_results"]["title"] = "Các địa điểm gợi ý khác"
    elif not output_structure["other_results"]["locations"]:
        output_structure["other_results"]["title"] = "Không tìm thấy kết quả nào phù hợp."
    elif not query_string_for_tfidf and not (target_province_std or target_region_std) :
         output_structure["other_results"]["title"] = "Vui lòng nhập từ khóa tìm kiếm cụ thể hơn."
    else:
        output_structure["other_results"]["title"] = "Các địa điểm gợi ý"

    print(f"Service: Trả về cuối cùng: {len(output_structure['province_results']['locations'])} kết quả tỉnh, {len(output_structure['other_results']['locations'])} kết quả khác.")
    return output_structure

# Hàm get_location_details_by_id giữ nguyên
def get_location_details_by_id(location_id: str) -> dict:
    # ... (code giữ nguyên) ...
    conn = None
    try:
        conn = get_db_connection();
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