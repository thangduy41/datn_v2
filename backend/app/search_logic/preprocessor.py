from vncorenlp import VnCoreNLP
import re
import os

# Danh sách từ khóa liên quan đến du lịch và đặc điểm
TRAVEL_KEYWORDS = [
    'biển', 'núi', 'thành_phố', 'làng_quê', 'văn_hóa', 'di_sản', 
    'thác_nước', 'rừng', 'động', 'chùa', 'đền', 'bãi_biển', 'đồi', 
    'sông', 'hồ', 'suối', 'đảo', 'công_viên', 'resort', 'phượt', 
    'đông_đúc', 'ồn_ào', 'yên_tĩnh', 'nguy_hiểm', 'sang_trọng', 
    'chùa_chiền', 'vui', 'bình_yên', 'leo_núi', 'địa_điểm'
]

# Danh sách từ phủ định
NEGATIVE_WORDS = ['không', 'chẳng', 'chả', 'ko', 'k', 'hông', 'chớ', 'đừng', 'tránh']

# Danh sách tất cả tỉnh/thành phố Việt Nam (chuẩn hóa: chữ thường, dấu gạch dưới)
COMMON_LOCATIONS = [
    'hà_nội', 'đà_nẵng', 'thành_phố_hồ_chí_minh', 'an_giang', 'bà_rịa_vũng_tàu',
    'bạc_liêu', 'bắc_kạn', 'bắc_giang', 'bắc_ninh', 'bến_tre', 'bình_dương',
    'bình_định', 'bình_phước', 'bình_thuận', 'cà_mau', 'cao_bằng', 'cần_thơ',
    'đắk_lắk', 'đắk_nông', 'điện_biên', 'đồng_nai', 'đồng_tháp', 'gia_lai',
    'hà_giang', 'hà_nam', 'hà_tĩnh', 'hải_dương', 'hải_phòng', 'hậu_giang',
    'hòa_bình', 'hưng_yên', 'khánh_hòa', 'kiên_giang', 'kon_tum', 'lai_châu',
    'lâm_đồng', 'lạng_sơn', 'lào_cai', 'long_an', 'nam_định', 'nghệ_an',
    'ninh_bình', 'ninh_thuận', 'phú_thọ', 'phú_yên', 'quảng_bình', 'quảng_nam',
    'quảng_ngãi', 'quảng_ninh', 'quảng_trị', 'sóc_trăng', 'sơn_la', 'tây_ninh',
    'thái_bình', 'thái_nguyên', 'thanh_hóa', 'thừa_thiên_huế', 'tiền_giang',
    'trà_vinh', 'tuyên_quang', 'vĩnh_long', 'vĩnh_phúc', 'yên_bái'
]

# Khởi tạo VnCoreNLP instance toàn cục
VNCORENLP_INSTANCE = None

def initialize_vncorenlp(jar_path):
    """
    Khởi tạo VnCoreNLP instance toàn cục.
    
    Args:
        jar_path (str): Đường dẫn đến file VnCoreNLP.jar
    """
    global VNCORENLP_INSTANCE
    if VNCORENLP_INSTANCE is None:
        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"File VnCoreNLP.jar không tồn tại tại: {jar_path}")
        VNCORENLP_INSTANCE = VnCoreNLP(jar_path, annotators="wseg,pos,ner,parse", max_heap_size='-Xmx2g')

def preprocess_query(query, vncorenlp_jar_path=os.path.join("lib", "VnCoreNLP-1.2.jar")):
    """
    Xử lý câu truy vấn để trích xuất ba nhóm từ khóa:
    1. Tất cả từ khóa trong câu (ưu tiên từ khóa du lịch)
    2. Từ khóa bị phủ định
    3. Từ khóa chỉ địa danh, vùng miền
    
    Args:
        query (str): Câu truy vấn người dùng nhập
        vncorenlp_jar_path (str): Đường dẫn đến file VnCoreNLP.jar
        
    Returns:
        dict: Chứa ba nhóm từ khóa
            - all_keywords: List các từ khóa trong câu
            - negative_keywords: List các từ khóa bị phủ định
            - location_keywords: List các từ khóa chỉ địa danh
    """
    # Khởi tạo VnCoreNLP nếu chưa khởi tạo
    initialize_vncorenlp(vncorenlp_jar_path)
    
    # Chuẩn hóa câu truy vấn: loại bỏ ký tự đặc biệt, chuyển về chữ thường
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query)
    
    # Phân tích câu với vncorenlp
    annotated_text = VNCORENLP_INSTANCE.annotate(query)
    
    # Lấy danh sách token và thông tin
    sentences = annotated_text['sentences']
    all_tokens = []
    pos_tags = []
    ner_labels = []
    
    for sentence in sentences:
        for token in sentence:
            all_tokens.append(token['form'])
            pos_tags.append(token['posTag'])
            ner_labels.append(token['nerLabel'])
    
    # Debug: In token, nhãn NER và POS để kiểm tra
    print("Debug - Query:", query)
    print("Debug - Tokens, NER, and POS labels:")
    for token, ner, pos in zip(all_tokens, ner_labels, pos_tags):
        print(f"Token: {token}, NER: {ner}, POS: {pos}")
    
    # Trích xuất địa danh
    location_keywords = []
    location_tokens = set()  # Lưu các token thuộc địa danh
    i = 0
    while i < len(all_tokens):
        if ner_labels[i] == 'B-LOC':
            loc = all_tokens[i]
            location_tokens.add(all_tokens[i])
            j = i + 1
            while j < len(all_tokens) and ner_labels[j] in ['I-LOC', 'B-LOC']:
                loc += '_' + all_tokens[j]
                location_tokens.add(all_tokens[j])
                j += 1
            # Loại bỏ tiền tố "tỉnh" hoặc "thành_phố"
            if loc.startswith('tỉnh_'):
                loc = loc[len('tỉnh_'):]
            elif loc.startswith('thành_phố_'):
                loc = loc[len('thành_phố_'):]
            location_keywords.append(loc)
            i = j
        else:
            i += 1
    
    # Fallback: Kiểm tra địa danh phổ biến và các cụm từ
    query_normalized = query.replace(' ', '_').lower()
    for loc in COMMON_LOCATIONS:
        if loc in query_normalized and loc not in location_keywords:
            location_keywords.append(loc)
            location_tokens.add(loc)
    
    # Trích xuất từ khóa phủ định
    negative_keywords = []
    i = 0
    while i < len(all_tokens):
        if all_tokens[i] in NEGATIVE_WORDS:
            j = i + 1
            # Quét đến hết câu hoặc đến từ "nhưng"
            while j < len(all_tokens) and all_tokens[j] != 'nhưng':
                # Xử lý cụm "không quá X"
                if j < len(all_tokens) - 1 and all_tokens[j] == 'quá' and pos_tags[j + 1] in ['N', 'A']:
                    if all_tokens[j + 1] not in location_tokens:
                        negative_keywords.append(all_tokens[j + 1])
                    j += 2
                # Bỏ qua các từ như "phải", "các", "loại" và dấu phẩy
                elif all_tokens[j] in ['phải', 'các', 'loại', ',']:
                    j += 1
                # Lấy danh từ, tính từ, hoặc từ trong TRAVEL_KEYWORDS, trừ các token thuộc địa danh
                elif (pos_tags[j] in ['N', 'A'] or all_tokens[j] in TRAVEL_KEYWORDS) and all_tokens[j] not in location_tokens:
                    negative_keywords.append(all_tokens[j])
                    j += 1
                else:
                    j += 1
            i = j
        else:
            i += 1
    
    # Trích xuất tất cả từ khóa, ưu tiên từ khóa du lịch
    all_keywords = [token for token, pos in zip(all_tokens, pos_tags) 
                   if (token in TRAVEL_KEYWORDS or pos in ['N', 'A']) 
                   and token not in NEGATIVE_WORDS 
                   and token not in negative_keywords 
                   and token not in location_tokens]
    
    # Loại bỏ trùng lặp
    all_keywords = list(dict.fromkeys(all_keywords))
    negative_keywords = list(dict.fromkeys(negative_keywords))
    location_keywords = list(dict.fromkeys(location_keywords))
    
    return {
        'all_keywords': all_keywords,
        'negative_keywords': negative_keywords,
        'location_keywords': location_keywords
    }

def close_vncorenlp():
    """
    Đóng VnCoreNLP instance toàn cục.
    """
    global VNCORENLP_INSTANCE
    if VNCORENLP_INSTANCE is None:
        return
    VNCORENLP_INSTANCE.close()
    VNCORENLP_INSTANCE = None