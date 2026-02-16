import sqlite3
import os
import json
import random
import string
from datetime import datetime
from config import Config

def get_db_connection():
    """Получает подключение к базе данных"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует базу данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица шаблонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            template_name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица полей шаблонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_label TEXT NOT NULL,
            field_type TEXT DEFAULT 'text',
            field_order INTEGER DEFAULT 0,
            FOREIGN KEY (template_name) REFERENCES templates(template_name),
            UNIQUE(template_name, field_name)
        )
    ''')
    
    # Таблица замен для шаблонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_replacements (
            template_name TEXT PRIMARY KEY,
            replacements_json TEXT,
            FOREIGN KEY (template_name) REFERENCES templates(template_name)
        )
    ''')
    
    # Таблица API ключей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key TEXT PRIMARY KEY,
            template_name TEXT NOT NULL,
            limit_count INTEGER NOT NULL,
            used_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (template_name) REFERENCES templates(template_name)
        )
    ''')
    
    # Таблица использования
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            client_ip TEXT,
            status TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (api_key) REFERENCES api_keys(api_key)
        )
    ''')
    
    # Таблица для rate limiting
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            client_ip TEXT NOT NULL,
            request_count INTEGER DEFAULT 0,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(api_key, client_ip)
        )
    ''')
    
    conn.commit()
    conn.close()

# ===== ФУНКЦИИ ДЛЯ ШАБЛОНОВ =====

def create_template(template_name, display_name):
    """Создает новый шаблон"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO templates (template_name, display_name) VALUES (?, ?)',
                      (template_name, display_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_template(template_name):
    """Удаляет шаблон"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM templates WHERE template_name = ?', (template_name,))
    cursor.execute('DELETE FROM template_fields WHERE template_name = ?', (template_name,))
    cursor.execute('DELETE FROM template_replacements WHERE template_name = ?', (template_name,))
    conn.commit()
    conn.close()

def get_all_templates():
    """Получает все шаблоны"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM templates ORDER BY display_name')
    templates = cursor.fetchall()
    conn.close()
    return templates

def get_template_fields(template_name):
    """Получает поля шаблона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT field_name, field_label, field_type, field_order FROM template_fields WHERE template_name = ? ORDER BY field_order', (template_name,))
    fields = cursor.fetchall()
    conn.close()
    return fields

def add_field_to_template(template_name, field_name, field_label, field_type='text'):
    """Добавляет поле к шаблону"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(field_order) FROM template_fields WHERE template_name = ?', (template_name,))
    max_order = cursor.fetchone()[0] or 0
    cursor.execute('INSERT INTO template_fields (template_name, field_name, field_label, field_type, field_order) VALUES (?, ?, ?, ?, ?)',
                   (template_name, field_name, field_label, field_type, max_order + 1))
    conn.commit()
    conn.close()

def delete_field_from_template(template_name, field_name):
    """Удаляет поле из шаблона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM template_fields WHERE template_name = ? AND field_name = ?', (template_name, field_name))
    conn.commit()
    conn.close()

def update_field_in_template(template_name, field_name, field_label, field_type):
    """Обновляет поле шаблона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE template_fields SET field_label = ?, field_type = ? WHERE template_name = ? AND field_name = ?',
                   (field_label, field_type, template_name, field_name))
    conn.commit()
    conn.close()

def save_template_replacements(template_name, replacements_json):
    """Сохраняет JSON замен для шаблона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO template_replacements (template_name, replacements_json) VALUES (?, ?)',
                  (template_name, replacements_json))
    conn.commit()
    conn.close()

def get_template_replacements(template_name):
    """Получает JSON замен для шаблона"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT replacements_json FROM template_replacements WHERE template_name = ?', (template_name,))
    row = cursor.fetchone()
    conn.close()
    return row['replacements_json'] if row else '{}'

# ===== ФУНКЦИИ ДЛЯ КЛЮЧЕЙ =====

def generate_key(template_name, limit_count):
    """Генерирует новый API ключ"""
    api_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO api_keys (api_key, template_name, limit_count) VALUES (?, ?, ?)',
                   (api_key, template_name, limit_count))
    conn.commit()
    conn.close()
    return api_key

def check_key(api_key):
    """Проверяет валидность ключа"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT template_name, limit_count, used_count, status FROM api_keys WHERE api_key = ?', (api_key,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, "Ключ не найден"
    
    if row['status'] != 'active':
        return False, "Ключ деактивирован"
    
    if row['used_count'] >= row['limit_count']:
        return False, "Лимит использования исчерпан"
    
    return True, row['template_name']

def increment_usage(api_key, client_ip, status, details):
    """Увеличивает счетчик использования ключа"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Обновляем счетчик
    cursor.execute('UPDATE api_keys SET used_count = used_count + 1 WHERE api_key = ?', (api_key,))
    
    # Логируем использование
    cursor.execute('INSERT INTO usage_logs (api_key, client_ip, status, details) VALUES (?, ?, ?, ?)',
                   (api_key, client_ip, status, details))
    
    conn.commit()
    conn.close()

def get_all_keys():
    """Получает все ключи"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM api_keys ORDER BY created_at DESC')
    keys = cursor.fetchall()
    conn.close()
    return keys

def deactivate_key(api_key):
    """Деактивирует ключ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE api_keys SET status = ? WHERE api_key = ?', ('inactive', api_key))
    conn.commit()
    conn.close()

def get_key_info(api_key):
    """Получает информацию о ключе"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT limit_count, used_count, created_at, status FROM api_keys WHERE api_key = ?', (api_key,))
    row = cursor.fetchone()
    conn.close()
    return (row['limit_count'], row['used_count'], row['created_at'], row['status']) if row else None

def get_usage_stats():
    """Получает статистику использования"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total_keys FROM api_keys')
    total_keys = cursor.fetchone()['total_keys']
    
    cursor.execute('SELECT COUNT(*) as active_keys FROM api_keys WHERE status = ?', ('active',))
    active_keys = cursor.fetchone()['active_keys']
    
    cursor.execute('SELECT SUM(used_count) as total_usage FROM api_keys')
    total_usage = cursor.fetchone()['total_usage'] or 0
    
    cursor.execute('SELECT COUNT(*) as total_requests FROM usage_logs')
    total_requests = cursor.fetchone()['total_requests']
    
    conn.close()
    
    return {
        'total_keys': total_keys,
        'active_keys': active_keys,
        'total_usage': total_usage,
        'total_requests': total_requests
    }

def check_rate_limit(api_key, client_ip, max_requests, period):
    """Проверяет rate limit"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Очищаем старые записи
    cursor.execute('DELETE FROM rate_limits WHERE window_start < datetime("now", "-" || ? || " seconds")', (period,))
    
    # Проверяем текущий лимит
    cursor.execute('SELECT request_count FROM rate_limits WHERE api_key = ? AND client_ip = ?', (api_key, client_ip))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute('INSERT INTO rate_limits (api_key, client_ip, request_count) VALUES (?, ?, 1)',
                       (api_key, client_ip))
        conn.commit()
        conn.close()
        return True, "OK"
    
    if row['request_count'] >= max_requests:
        conn.close()
        return False, "Превышен лимит запросов. Попробуйте позже."
    
    cursor.execute('UPDATE rate_limits SET request_count = request_count + 1 WHERE api_key = ? AND client_ip = ?',
                   (api_key, client_ip))
    conn.commit()
    conn.close()
    return True, "OK"
