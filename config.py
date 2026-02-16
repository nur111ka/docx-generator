import os

class Config:
    """Конфигурация приложения"""
    
    # Секретный ключ для сессий
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Папки
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATES_STORAGE = os.path.join(BASE_DIR, 'templates_storage')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
    
    # Админ пароль
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '10'))
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD', '60'))
    
    # Максимальный размер загружаемого файла (MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
