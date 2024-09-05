from flask import Flask, jsonify, request
import base64
import hmac
import hashlib
import requests
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://sapphire-algae-9ajt.squarespace.com"}})  # Belirli bir domain için CORS izni

# PayTR için gerekli bilgiler
MERCHANT_ID = '492579'
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'

# PayTR Token oluşturma
def create_paytr_token(merchant_id, merchant_key, merchant_salt, user_ip, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):
    # Hash string'i oluştur
    hash_str = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket.decode()}{no_installment}{max_installment}{currency}{test_mode}"
    print("Hash String:", hash_str)  # Hash string'i kontrol edin
    token = base64.b64encode(hmac.new(merchant_key, hash_str.encode() + merchant_salt, hashlib.sha256).digest())
    print("PayTR Token:", token)  # Token'ı kontrol edin
    return token

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    email = data.get('email')
    payment_amount = data.get('payment_amount')  # Ödeme miktarı kuruş cinsinden gelmeli
    user_name = data.get('user_name')
    user_address = data.get('user_address')
    user_phone = data.get('user_phone')
    merchant_oid = data.get('merchant_oid')
    
    # Sepet içeriği
    user_basket = base64.b64encode(json.dumps([['Ürün Adı', payment_amount, 1]]).encode())  # Sepet içeriğini encode ediyoruz
    
    # PayTR için gerekli parametreler
    paytr_token = create_paytr_token(
        MERCHANT_ID, MERCHANT_KEY, MERCHANT_SALT,
        request.remote_addr, merchant_oid, email, payment_amount,
        user_basket, '0', '12', 'TL', '0'  # Test modu kapalı
    )

    params = {
        'merchant_id': MERCHANT_ID,
        'user_ip': request.remote_addr,
        'merchant_oid': merchant_oid,
        'email': email,
        'payment_amount': payment_amount,
        'paytr_token': paytr_token,
        'user_basket': user_basket,
        'debug_on': '1',  # Hata ayıklama modu
        'no_installment': '0',  # Taksit yok
        'max_installment': '12',
        'user_name': user_name,
        'user_address': user_address,
        'user_phone': user_phone,
        'merchant_ok_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'merchant_fail_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'timeout_limit': '30',
        'currency': 'TL',
        'test_mode': '0'  # Canlı modda çalışıyoruz
    }

    # PayTR'ye istek gönder
    response = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)
    res = json.loads(response.text)

    print("PayTR Yanıtı:", res)  # Yanıtı gözlemleyin

    if res['status'] == 'success':
        return jsonify({'token': res['token']})
    else:
        return jsonify(res)  # Hata durumunda tüm yanıtı döndür

# Kök URL için bir rota ekleyelim
@app.route('/')
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render'den gelen portu al
    app.run(host='0.0.0.0', port=port, debug=True)
