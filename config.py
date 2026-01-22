import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

    # WhatsApp configuration
    WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY')
    WHATSAPP_PHONE_NUMBER = os.environ.get('WHATSAPP_PHONE_NUMBER')
    ADMIN_PHONE = os.environ.get('ADMIN_PHONE')
    
    # Upload configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    # Server port (useful for hosting platforms)
    PORT = int(os.environ.get('PORT'))