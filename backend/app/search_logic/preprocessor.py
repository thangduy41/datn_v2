# backend/app/search_logic/preprocessor.py
import underthesea
import json
import os
from app.core.config import SYNONYMS_PATH # Import đường dẫn từ config

synonyms_dict = {}
try:
    if os.path.exists(SYNONYMS_PATH):
        with open(SYNONYMS_PATH, 'r', encoding='utf-8') as f:
            synonyms_dict = json.load(f)
        print(f"Preprocessor: Đã tải thành công {len(synonyms_dict)} mục từ điển đồng nghĩa từ {SYNONYMS_PATH}")
    else:
        print(f"Preprocessor Cảnh báo: Không tìm thấy file từ đồng nghĩa tại {SYNONYMS_PATH}")
except Exception as e:
    print(f"Preprocessor Lỗi khi tải file từ đồng nghĩa: {e}")


def preprocess_query(query_text: str) -> dict: # Thay đổi kiểu trả về để có cả token cho TF-IDF và keyword cho Tag
    """
    Tiền xử lý văn bản truy vấn: lowercase, tách từ, mở rộng từ đồng nghĩa.
    Trả về một dictionary chứa:
    - 'tokens_for_tfidf': chuỗi token đã xử lý, nối bằng dấu cách, cho TF-IDF.
    - 'keywords_for_tags': list các token/keyword gốc và mở rộng, cho Tag Engine.
    """
    if not isinstance(query_text, str) or not query_text.strip():
        return {'tokens_for_tfidf': "", 'keywords_for_tags': []}

    normalized_text = query_text.lower()
    # Tách từ bằng underthesea
    original_tokens = underthesea.word_tokenize(normalized_text)

    expanded_tokens_set = set() # Dùng set để tránh trùng lặp từ khóa

    for token in original_tokens:
        expanded_tokens_set.add(token) # Thêm từ gốc
        # Kiểm tra xem token (hoặc dạng có gạch nối của nó nếu underthesea tạo ra) có trong từ điển không
        # underthesea có thể trả về 'du_lịch_bụi', trong khi key có thể là 'du lịch bụi'
        # Nên chúng ta có thể cần chuẩn hóa token trước khi tra cứu, hoặc làm từ điển linh hoạt hơn
        # Ví dụ đơn giản:
        processed_token_for_lookup = token.replace("_", " ") # Chuyển 'du_lịch_bụi' thành 'du lịch bụi'

        if token in synonyms_dict:
            for synonym in synonyms_dict[token]:
                expanded_tokens_set.add(synonym.replace(" ", "_")) # Thêm lại dạng có gạch nối nếu cần
        elif processed_token_for_lookup in synonyms_dict:
            for synonym in synonyms_dict[processed_token_for_lookup]:
                expanded_tokens_set.add(synonym.replace(" ", "_"))


    # Chuỗi token cho TF-IDF (nối lại bằng dấu cách)
    # TF-IDF vectorizer sẽ tự tách từ theo dấu cách hoặc tokenizer riêng của nó
    # Quan trọng là các từ đồng nghĩa phải được đưa vào đây
    # Nên nối lại các token từ expanded_tokens_set
    tokens_for_tfidf_str = " ".join(list(expanded_tokens_set))

    # List keyword cho Tag Engine (bao gồm cả từ gốc và từ đồng nghĩa đã được tách từ)
    # Ở đây ta có thể muốn các từ đơn lẻ hơn là cụm từ ghép
    # Hoặc giữ lại các cụm từ nếu tags của bạn cũng là cụm từ
    keywords_for_tags_list = list(expanded_tokens_set) 

    print(f"Preprocessor: Query gốc: '{query_text}'")
    print(f"Preprocessor: Token gốc: {original_tokens}")
    print(f"Preprocessor: Tokens mở rộng (cho TF-IDF): '{tokens_for_tfidf_str}'")
    print(f"Preprocessor: Keywords mở rộng (cho Tags): {keywords_for_tags_list}")

    return {
        'tokens_for_tfidf': tokens_for_tfidf_str,
        'keywords_for_tags': keywords_for_tags_list
    }
