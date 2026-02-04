import google.generativeai as genai
from flask import current_app
import json
import re

class ExpensePredictor:
    """AI-powered expense prediction using Gemini"""
    
    def __init__(self):
        self.model = None

    def _ensure_configured(self):
        """Lazy initialization of the model"""
        if not self.model:
            try:
                api_key = current_app.config.get('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
            except RuntimeError:
                pass

    
    def predict_trip_expenses(self, destination, duration_days, num_people, 
                            trip_type='casual', preferences=None):
        """Predict trip expenses based on destination and preferences"""
        self._ensure_configured()
        if not self.model:
            return self._fallback_prediction(destination, duration_days, num_people)
        
        prompt = f"""
        As a travel expense expert, predict the total estimated expenses for a trip with these details:
        Destination: {destination}
        Duration: {duration_days} days
        Number of people: {num_people}
        Trip type: {trip_type}
        Preferences: {preferences or 'Standard'}
        
        Provide a detailed breakdown in JSON format with these categories:
        - Accommodation: {{per_night_average}}
        - Food: {{per_day_per_person}}
        - Transportation: {{local}}
        - Activities/entertainment
        - Miscellaneous
        
        Also provide:
        - Total estimated cost
        - Recommended deposit per person: {{slightly_higher_than_average_to_be_safe}}
        - Cost saving tips: {{array_of_3-5_tips}}
        
        Return ONLY valid JSON, no markdown formatting.
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*", "", text)
            prediction = json.loads(text)
            
            return {
                "success": True,
                "data": prediction
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback": self._fallback_prediction(destination, duration_days, num_people)
            }
    
    def analyze_receipt(self, image_data):
        """Analyze receipt image and extract information"""
        self._ensure_configured()
        if not self.model:
            return {"success": False, "error": "Gemini not configured"}
        
        prompt = """
        Analyze this receipt image and extract the following information in JSON format:
        {
            "merchant": "store/restaurant name",
            "total_amount": number,
            "date": "YYYY-MM-DD",
            "items": [
                {"name": "item name", "price": number, "quantity": number}
            ],
            "category": "suggested category (Food, Travel, Entertainment, Shopping, Accommodation, Others)",
            "confidence": number (0-1)
        }
        
        Return ONLY valid JSON, no markdown formatting.
        """
        
        try:
            response = self.model.generate_content([prompt, image_data])
            text = response.text
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*", "", text)
            result = json.loads(text)
            
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fallback_prediction(self, destination, duration_days, num_people):
        """Fallback prediction when AI is unavailable"""
        region_costs = {
            'asia': {'accommodation': 40, 'food': 20, 'transport': 15, 'activities': 25},
            'europe': {'accommodation': 100, 'food': 50, 'transport': 30, 'activities': 40},
            'americas': {'accommodation': 80, 'food': 40, 'transport': 25, 'activities': 35},
            'default': {'accommodation': 60, 'food': 30, 'transport': 20, 'activities': 30}
        }
        
        costs = region_costs.get('default')
        total_per_day = sum(costs.values()) * num_people
        total = total_per_day * duration_days
        
        return {
            "accommodation": costs['accommodation'] * duration_days * num_people,
            "food": costs['food'] * duration_days * num_people,
            "transportation": costs['transport'] * duration_days * num_people,
            "activities": costs['activities'] * duration_days * num_people,
            "miscellaneous": total * 0.1,
            "total_estimated_cost": total * 1.1,
            "recommended_deposit_per_person": (total * 1.2) / num_people,
            "cost_saving_tips": [
                "Book accommodation in advance",
                "Use public transportation",
                "Eat at local restaurants",
                "Look for free activities"
            ],
            "note": "Fallback estimation as AI unavailable"
        }

# Initialize predictor
expense_predictor = ExpensePredictor()