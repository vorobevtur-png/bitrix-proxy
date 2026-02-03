#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitrix24 Proxy Server v10.0 (полный сбор комментариев: старые + новые)
Собирает ПОЛНУЮ хронологию коммуникаций для претензий и судов
"""

from flask import Flask, request, jsonify
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
BITRIX_WEBHOOK = 'https://izyskaniya.bitrix24.ru/rest/13614/rj3pqolk1fiu6hfr/'

def call_bitrix(method, params=None):
    """Вызов API Битрикс24 через POST"""
    url = f"{BITRIX_WEBHOOK}{method}.json"
    try:
        response = requests.post(url, data=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка запроса к {method}: {e}")
        return {'error': str(e)}

@app.route('/proxy')
def proxy():
    action = request.args.get('action')
    if not action:
        return jsonify({'error': 'missing_action'}), 400
    
    try:
        # === СДЕЛКА ===
        if action == 'deal':
            deal_id = request.args.get('deal_id')
            if not deal_id:
                return jsonify({'error': 'missing_deal_id'}), 400
            return jsonify(call_bitrix('crm.deal.get', {'id': deal_id}))
        
        # === КОНТАКТ ===
        elif action == 'contact':
            contact_id = request.args.get('contact_id')
            if not contact_id:
                return jsonify({'error': 'missing_contact_id'}), 400
            return jsonify(call_bitrix('crm.contact.get', {'id': contact_id}))
        
        # === КОМПАНИЯ ===
        elif action == 'company':
            company_id = request.args.get('company_id')
            if not company_id:
                return jsonify({'error': 'missing_company_id'}), 400
            return jsonify(call_bitrix('crm.company.get', {'id': company_id}))
        
        # === ЗАДАЧИ ПО СДЕЛКЕ ===
        elif action == 'tasks':
            deal_id = request.args.get('deal_id')
            if not deal_id:
                return jsonify({'error': 'missing_deal_id'}), 400
            return jsonify(call_bitrix('tasks.task.list', {
                'filter[UF_CRM_TASK][0]': f'D_{deal_id}',
                'order[CREATED_DATE]': 'ASC'
            }))
        
        # === ЗАДАЧА (для получения chatId) ===
        elif action == 'task':
            task_id = request.args.get('task_id')
            if not task_id:
                return jsonify({'error': 'missing_task_id'}), 400
            return jsonify(call_bitrix('tasks.task.get', {'id': task_id}))
        
        # === ВСЕ КОММЕНТАРИИ ЗАДАЧИ (старые + новые) ===
        elif action == 'task_comments':
            task_id = request.args.get('task_id')
            if not task_id:
                return jsonify({'error': 'missing_task_id'}), 400
            
            # Шаг 1: Получаем старые комментарии
            old_comments = call_bitrix('task.commentitem.getlist', {'taskId': task_id})
            if 'error' in old_comments:
                old_comments = {'result': []}
            
            # Шаг 2: Получаем задачу для получения chatId
            task_response = call_bitrix('tasks.task.get', {'id': task_id})
            if 'error' in task_response:
                return jsonify({'error': 'task_not_found', 'message': 'Задача не найдена'})
            
            chat_id = task_response.get('result', {}).get('task', {}).get('chatId')
            
            # Шаг 3: Получаем новые комментарии из чата (если есть)
            new_comments = {'result': {'messages': []}}
            if chat_id:
                new_comments = call_bitrix('im.dialog.messages.get', {
                    'DIALOG_ID': f'chat{chat_id}',
                    'ORDER': 'ASC',
                    'LIMIT': 100
                })
            
            # Шаг 4: Объединяем результаты
            return jsonify({
                'old_comments': old_comments.get('result', []),
                'new_comments': new_comments.get('result', {}).get('messages', []),
                'chat_id': chat_id,
                'total_old': len(old_comments.get('result', [])),
                'total_new': len(new_comments.get('result', {}).get('messages', []))
            })
        
        # === АКТИВНОСТИ (звонки с записями) ===
        elif action == 'activities':
            owner_id = request.args.get('owner_id')
            if not owner_id:
                return jsonify({'error': 'missing_owner_id'}), 400
            return jsonify(call_bitrix('crm.activity.list', {
                'filter[OWNER_TYPE]': '2',
                'filter[OWNER_ID]': owner_id,
                'order[CREATED]': 'ASC',
                'select[]': '*'
            }))
        
        # === СМУРТ-ПРОЦЕСС: СЧЁТ ===
        elif action == 'smart_invoice':
            parent_id = request.args.get('parent_id')
            if not parent_id:
                return jsonify({'error': 'missing_parent_id'}), 400
            return jsonify(call_bitrix('crm.item.list', {
                'entityTypeId': '31',
                'filter[parentId2]': parent_id,
                'select[]': '*'
            }))
        
        # === СМУРТ-ПРОЦЕСС: ПРОИЗВОДСТВО ===
        elif action == 'smart_production':
            parent_id = request.args.get('parent_id')
            if not parent_id:
                return jsonify({'error': 'missing_parent_id'}), 400
            return jsonify(call_bitrix('crm.item.list', {
                'entityTypeId': '1070',
                'filter[parentId2]': parent_id,
                'select[]': '*'
            }))
        
        # === ФАЙЛ ===
        elif action == 'file':
            file_id = request.args.get('file_id')
            if not file_id:
                return jsonify({'error': 'missing_file_id'}), 400
            return jsonify(call_bitrix('disk.file.get', {'id': file_id}))
        
        else:
            return jsonify({'error': 'unknown_action'}), 400
    
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Bitrix Proxy работает'})

@app.route('/')
def index():
    return jsonify({
        'name': 'Bitrix24 Proxy Server v10.0',
        'description': 'Полный сбор комментариев: старые + новые (чат)',
        'working_actions': [
            'deal', 'contact', 'company', 
            'tasks', 'task', 'task_comments', 'activities', 
            'smart_invoice', 'smart_production',
            'file'
        ],
        'example': '/proxy?action=task_comments&task_id=273772'
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 Bitrix24 Proxy Server v10.0 (полный сбор комментариев)")
    print("=" * 70)
    print("✅ Сервер запущен на: http://localhost:5001")
    print("📊 Проверка: http://localhost:5001/health")
    print("=" * 70)
    print("💡 Сбор комментариев:")
    print("   • Старые комментарии → task.commentitem.getlist")
    print("   • Новые комментарии → im.dialog.messages.get (чат)")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5001, debug=True)
