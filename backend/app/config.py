import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/cooper')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = 24 * 60 * 60  # 24 hours
    
    # Finternet API
    FINTERNET_API_KEY = os.environ.get('FINTERNET_API_KEY', '')
    FINTERNET_BASE_URL = os.environ.get('FINTERNET_BASE_URL', 'https://api.fmm.finternetlab.io/v1')
    
    # Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')