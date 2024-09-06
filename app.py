from flask import Flask, jsonify, request, abort
import base64
import hmac
import hashlib
import requests
import json
import os
import random
import string
import re
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# PayTR için gerekli bilgiler
MERCHANT_ID = '492579'
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect('payments.db')
    conn.row_factory = sqlite3.Row
    return conn

# Token oluşturma fonksiyonu
def create_paytr_token(merchant_id, merchant_key, merchant_salt, user_ip, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):
    hash_str = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket.decode()}{no_installment}{max_installment}{currency}{test_mode}"
    token = base64.b64encode(hmac.new(merchant_key, hash_str.encode() + merchant_salt, hashlib.sha256).digest())
    return token

def generate_merchant_oid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def validate_merchant_oid(merchant_oid):
    return bool(re.match("^[a-zA-Z0-9]*$", merchant_oid))

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    email = data.get('email')
    payment_amount = data.get('payment_amount')
    user_name = data.get('user_name')
    user_address = data.get('user_address')
    user_phone = data.get('user_phone')
    merchant_oid = generate_merchant_oid()

    if not validate_merchant_oid(merchant_oid):
        return jsonify({'error': 'Invalid merchant_oid'}), 400

    # Veritabanı bağlantısını aç
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # İşlem kimliğinin daha önce kullanılıp kullanılmadığını kontrol et
    cursor.execute('SELECT * FROM payments WHERE request_id = ?', (merchant_oid,))
    existing_payment = cursor.fetchone()
    if existing_payment:
        conn.close()
        return jsonify({'error': 'Duplicate request'}), 400
    
    # İşlem kimliğini veritabanına ekle
    cursor.execute('INSERT INTO payments (request_id, status) VALUES (?, ?)', (merchant_oid, 'pending'))
    conn.commit()
    conn.close()

    user_basket = base64.b64encode(json.dumps([['Ürün Adı', payment_amount, 1]]).encode())
    params = {
        'merchant_id': MERCHANT_ID,
        'user_ip': request.remote_addr,
        'merchant_oid': merchant_oid,
        'email': email,
        'payment_amount': payment_amount,
        'paytr_token': create_paytr_token(
            MERCHANT_ID, MERCHANT_KEY, MERCHANT_SALT,
            request.remote_addr, merchant_oid, email, payment_amount,
            user_basket, '0', '12', 'TL', '1'
        ),
        'user_basket': user_basket,
        'debug_on': '1',
        'no_installment': '0',
        'max_installment': '12',
        'user_name': user_name,
        'user_address': user_address,
        'user_phone': user_phone,
        'merchant_ok_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'merchant_fail_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'timeout_limit': '30',
        'currency': 'TL',
        'test_mode': '1'
    }

    response = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)
    res = json.loads(response.text)

    if res['status'] == 'success':
        return jsonify({'token': res['token']})
    else:
        return jsonify(res)

@app.route('/paytr_callback', methods=['POST'])
def paytr_callback():
    # Gelen istek başlıklarını ve verileri logla
    print(f"Headers: {request.headers}")
    print(f"Body: {request.data}")

    # JSON verisini al
    post_data = request.json
    print(f"Post Data: {post_data}")

    # JSON verisi gelmemişse hata döndür
    if post_data is None:
        print("No data received")
        return 'PAYTR notification failed: No data received', 400

    # Gelen verilerden gerekli bilgileri al
    merchant_oid = post_data.get('merchant_oid')
    status = post_data.get('status')
    total_amount = post_data.get('total_amount')
    received_hash = post_data.get('hash')

    # Hash hesapla
    hash_str = f"{merchant_oid}{MERCHANT_SALT.decode()}{status}{total_amount}"
    generated_hash = base64.b64encode(hmac.new(MERCHANT_KEY, hash_str.encode(), hashlib.sha256).digest()).decode()
    print(f"Generated Hash: {generated_hash}")
    print(f"Received Hash: {received_hash}")

    # Hash doğrulamasını yap
    if generated_hash != received_hash:
        return 'PAYTR notification failed: Invalid hash', 400

    # Veritabanını güncelle
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE payments SET status = ? WHERE request_id = ?', (status, merchant_oid))
    conn.commit()
    conn.close()

    # Duruma göre mesaj yaz
    if status == 'success':
        print(f"Sipariş {merchant_oid} başarılı bir şekilde ödendi.")
    else:
        print(f"Sipariş {merchant_oid} ödemesi başarısız oldu.")

    return 'OK', 200



@app.route('/paytr_status', methods=['POST'])
def paytr_status():
    data = request.json
    merchant_oid = data.get('merchant_oid')
    
    # Token hesaplama
    hash_str = f"{MERCHANT_ID}{merchant_oid}{MERCHANT_SALT.decode()}"
    paytr_token = base64.b64encode(hmac.new(MERCHANT_KEY, hash_str.encode(), hashlib.sha256).digest()).decode()

    params = {
        'merchant_id': MERCHANT_ID,
        'merchant_oid': merchant_oid,
        'paytr_token': paytr_token
    }

    response = requests.post('https://www.paytr.com/odeme/durum-sorgu', data=params)
    result = response.json()

    if result['status'] == 'success':
        payment_amount = result.get('payment_amount', '') + result.get('currency', '')
        payment_total = result.get('payment_total', '') + result.get('currency', '')
        returns = result.get('returns', [])

        return jsonify({
            'status': result['status'],
            'payment_amount': payment_amount,
            'payment_total': payment_total,
            'returns': returns
        })
    else:
        return jsonify({
            'status': result['status'],
            'error_number': result.get('err_no'),
            'error_message': result.get('err_msg')
        }), 400

@app.route('/', methods=['POST'])
def post_ok_response():
    return 'OK', 200

@app.route('/', methods=['GET'])
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    # Veritabanı tablo oluşturma
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS payments
                    (request_id TEXT PRIMARY KEY, status TEXT)''')
    conn.close()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

