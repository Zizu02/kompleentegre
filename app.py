from flask import Flask, jsonify, request
import base64
import hmac
import hashlib
import requests
import json
import os
import random
import string
import re
from flask_cors import CORS  # CORS'ü import et

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://sapphire-algae-9ajt.squarespace.com"}})  # Belirli bir domain için CORS izni

# PayTR için gerekli bilgiler
MERCHANT_ID = '492579'
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'

# Token oluşturma fonksiyonu
def create_paytr_token(merchant_id, merchant_key, merchant_salt, user_ip, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):
    # Token hesaplamadan önceki tüm verileri print ile kontrol edelim
    print(f"merchant_id: {merchant_id}")
    print(f"user_ip: {user_ip}")
    print(f"merchant_oid: {merchant_oid}")
    print(f"email: {email}")
    print(f"payment_amount: {payment_amount}")
    print(f"user_basket: {user_basket.decode()}")
    print(f"no_installment: {no_installment}")
    print(f"max_installment: {max_installment}")
    print(f"currency: {currency}")
    print(f"test_mode: {test_mode}")

    # Hash string oluştur
    hash_str = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket.decode()}{no_installment}{max_installment}{currency}{test_mode}"
    print(f"Hash string: {hash_str}")

    # Token oluşturma işlemi
    token = base64.b64encode(hmac.new(merchant_key, hash_str.encode() + merchant_salt, hashlib.sha256).digest())
    print(f"Generated token: {token}")
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
    merchant_oid = generate_merchant_oid()  # Güncellenmiş benzersiz sipariş numarası

    # `merchant_oid`'u doğrula
    if not validate_merchant_oid(merchant_oid):
        return jsonify({'error': 'Invalid merchant_oid'}), 400

    # Sepet içeriği
    user_basket = base64.b64encode(json.dumps([['Ürün Adı', payment_amount, 1]]).encode())

    # PayTR için gerekli parametreler
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

    # Gönderilen isteği logla
    print("Gönderilen İstek:", params)

    # PayTR'ye istek gönder
    response = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)

    # Gelen yanıtı logla
    print("Gelen Yanıt:", response.text)

    res = json.loads(response.text)

    if res['status'] == 'success':
        return jsonify({'token': res['token']})
    else:
        return jsonify(res)

@app.route('/paytr_callback', methods=['POST'])
def paytr_callback():
    if request.method == 'POST':
        post_data = request.form

        # POST değerlerini al
        merchant_oid = post_data.get('merchant_oid')
        status = post_data.get('status')
        total_amount = post_data.get('total_amount')
        received_hash = post_data.get('hash')

        # Hash doğrulama için hash stringi oluştur
        hash_str = f"{merchant_oid}{MERCHANT_SALT.decode()}{status}{total_amount}"
        generated_hash = base64.b64encode(hmac.new(MERCHANT_KEY, hash_str.encode(), hashlib.sha256).digest())

        # Hash'i karşılaştır, PayTR'den gelen hash ile oluşturduğumuz hash aynı mı?
        if generated_hash != received_hash.encode():
            return 'PAYTR notification failed: Invalid hash', 400

        # Siparişin durumunu kontrol et ve başarı durumuna göre işlem yap
        if status == 'success':
            # Ödeme başarılı, burada siparişi onaylayın
            print(f"Sipariş {merchant_oid} başarılı bir şekilde ödendi.")
        else:
            # Ödeme başarısız, burada iptal işlemi yapın
            print(f"Sipariş {merchant_oid} ödemesi başarısız oldu.")

        # Bildirimin alındığını PayTR sistemine bildir.
        return 'OK', 200

@app.route('/')
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render'den gelen portu al
    app.run(host='0.0.0.0', port=port, debug=True)
