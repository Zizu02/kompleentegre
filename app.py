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
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# PayTR için gerekli bilgiler
MERCHANT_ID = '492579'
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'

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
    post_data = request.json

    merchant_oid = post_data.get('merchant_oid')
    status = post_data.get('status')
    total_amount = post_data.get('total_amount')
    received_hash = post_data.get('hash')

    hash_str = f"{merchant_oid}{MERCHANT_SALT.decode()}{status}{total_amount}"
    generated_hash = base64.b64encode(hmac.new(MERCHANT_KEY, hash_str.encode(), hashlib.sha256).digest()).decode()

    if generated_hash != received_hash:
        return 'PAYTR notification failed: Invalid hash', 400

    if status == 'success':
        print(f"Sipariş {merchant_oid} başarılı bir şekilde ödendi.")
    else:
        print(f"Sipariş {merchant_oid} ödemesi başarısız oldu.")

    return 'OK', 200

@app.route('/', methods=['POST'])
def post_ok_response():
    return 'OK', 200

@app.route('/', methods=['GET'])
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
