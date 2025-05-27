# backend/app/api/search_api.py
from flask import Blueprint, request, jsonify

# Import hàm xử lý logic tìm kiếm từ service layer
# Đường dẫn import này dựa trên việc thư mục `backend` là thư mục gốc cho PYTHONPATH
# hoặc bạn đang chạy ứng dụng từ thư mục `backend`
try:
    from app.services.search_service import search_locations_by_tfidf
except ImportError:
    # Xử lý trường hợp import không thành công, có thể do PYTHONPATH
    # Hoặc bạn cần điều chỉnh đường dẫn import tùy theo cách bạn chạy ứng dụng
    print("API Lỗi: Không thể import search_locations_combined từ app.services.search_service")
    # Dummy function để chương trình vẫn chạy được phần nào
    def search_locations_combined(query, num_results=5):
        return {"error": "Search service not available due to import error."}


# Tạo một Blueprint. 
# 'search_api' là tên của blueprint.
# __name__ giúp Flask xác định vị trí của blueprint.
# url_prefix sẽ được thêm vào trước tất cả các route trong blueprint này.
api_bp = Blueprint('api_routes', __name__, url_prefix='/api/v1')

@api_bp.route('/search', methods=['GET']) # Route sẽ là /api/v1/search (do url_prefix)
def handle_search_locations():
    """
    API Endpoint để tìm kiếm địa điểm.
    Nhận 'query' từ query parameter.
    Ví dụ: /api/v1/search?query=biển đẹp&limit=5
    """
    user_query = request.args.get('query')
    
    try:
        limit_str = request.args.get('limit', '5') # Lấy 'limit', mặc định là 5
        num_results = int(limit_str)
        if num_results <= 0 or num_results > 20: # Giới hạn số lượng kết quả
            num_results = 5
    except ValueError:
        num_results = 5 # Mặc định nếu limit không phải là số

    if not user_query:
        return jsonify({"error": "Thiếu tham số 'query' trong yêu cầu."}), 400

    print(f"API: Nhận yêu cầu tìm kiếm với query='{user_query}', limit={num_results}")
    
    try:
        # Gọi hàm xử lý logic từ service layer
        results = search_locations_by_tfidf(user_query, num_results=num_results)
        
        # Kiểm tra xem service có trả về lỗi không (theo cấu trúc bạn đã định nghĩa)
        if isinstance(results, list) and len(results) == 1 and results[0].get("error"):
             return jsonify(results[0]), 500 # Lỗi từ service

        return jsonify(results), 200
    
    except Exception as e:
        print(f"API Lỗi không mong muốn: {e}")
        import traceback
        traceback.print_exc() # In traceback ra console server để debug
        return jsonify({"error": "Đã có lỗi xảy ra ở server."}), 500
    
from app.services.search_service import get_location_details_by_id # Hàm này bạn cần tạo trong service

@api_bp.route('/location/<string:location_id>', methods=['GET'])
def handle_get_location_detail(location_id):
    if not location_id:
        return jsonify({"error": "Thiếu ID địa điểm"}), 400
    
    print(f"API: Nhận yêu cầu chi tiết cho location_id: {location_id}")
    try:
        details = get_location_details_by_id(location_id) # Gọi hàm service
        if details:
            return jsonify(details), 200
        else:
            # Trả về JSON cho lỗi 404
            return jsonify({"error": "Không tìm thấy địa điểm", "id": location_id}), 404
    except Exception as e:
        print(f"API Lỗi không mong muốn khi lấy chi tiết địa điểm {location_id}: {e}")
        import traceback
        traceback.print_exc()
        # Trả về JSON cho lỗi 500
        return jsonify({"error": "Lỗi server khi lấy chi tiết địa điểm"}), 500