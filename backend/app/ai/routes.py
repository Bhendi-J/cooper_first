from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.ai.predict import expense_predictor

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/predict-trip', methods=['POST'])
@jwt_required()
def predict_trip():
    data = request.get_json()
    
    result = expense_predictor.predict_trip_expenses(
        destination=data.get('destination'),
        duration_days=data.get('duration_days', 3),
        num_people=data.get('num_people', 2),
        trip_type=data.get('trip_type', 'casual'),
        preferences=data.get('preferences')
    )
    
    return jsonify(result)

@ai_bp.route('/analyze-receipt', methods=['POST'])
@jwt_required()
def analyze_receipt():
    if 'image' not in request.files:
        return jsonify({'error': "No image provided"}), 400
    
    image = request.files['image']
    image_data = image.read()
    
    result = expense_predictor.analyze_receipt(image_data)
    return jsonify(result)