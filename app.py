from flask import Flask, jsonify, request
import base64
import hmac
import hashlib
import requests
import json
import os
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://sapphire-algae-9ajt.squarespace.com"}})  # Sadece belirli bir domain için CORS izni verildi

# PayTR için gerekli sabit bilgiler
MERCHANT_ID = '492579'  # PayTR tarafından size verilen mağaza numarası
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'  # PayTR tarafından size verilen mağaza anahtarı
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'  # PayTR tarafından size verilen güvenlik tuzu

# PayTR Token oluşturma fonksiyonu
def create_paytr_token(merchant_id, merchant_key, merchant_salt, user_ip, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):
    hash_str = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket.decode()}{no_installment}{max_installment}{currency}{test_mode}"
    return base64.b64encode(hmac.new(merchant_key, hash_str.encode() + merchant_salt, hashlib.sha256).digest())

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    
    # Dinamik olarak kullanıcıdan gelen veriler
    email = data.get('email')  # Kullanıcıdan gelen e-posta
    payment_amount = data.get('payment_amount')  # Ödeme tutarı kuruş cinsinden
    user_name = data.get('user_name')  # Kullanıcıdan gelen isim
    user_address = data.get('user_address')  # Kullanıcı adresi
    user_phone = data.get('user_phone')  # Kullanıcı telefon numarası
    merchant_oid = str(uuid.uuid4())  # Dinamik benzersiz sipariş numarası
    
    # Sepet içeriği (örnek ürün)
    user_basket = base64.b64encode(json.dumps([['Ürün Adı', payment_amount / 100, 1]]).encode())
    
    # PayTR için gerekli parametreler
    params = {
        'merchant_id': MERCHANT_ID,
        'user_ip': request.remote_addr,
        'merchant_oid': merchant_oid,
        'email': email,
        'payment_amount': payment_amount,  # Kuruş cinsinden gönderiliyor
        'paytr_token': create_paytr_token(
            MERCHANT_ID, MERCHANT_KEY, MERCHANT_SALT,
            request.remote_addr, merchant_oid, email, payment_amount,
            user_basket, '0', '12', 'TL', '1'
        ),
        'user_basket': user_basket,
        'debug_on': '1',  # Test sürecinde açık olmalı
        'no_installment': '0',  # Taksit olmasın
        'max_installment': '12',  # En fazla 12 taksit
        'user_name': user_name,
        'user_address': user_address,
        'user_phone': user_phone,
        'merchant_ok_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'merchant_fail_url': 'https://sapphire-algae-9ajt.squarespace.com/cart',
        'timeout_limit': '30',  # 30 dakika
        'currency': 'TL',  # Para birimi TL
        'test_mode': '1'  # Test modunda çalıştır
    }

    # PayTR'ye istek gönder
    response = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)
    res = json.loads(response.text)

    # Yanıtı kontrol et
    if res['status'] == 'success':
        return jsonify({'token': res['token']})
    else:
        return jsonify(res)

# Kök URL için bir rota ekleyelim
@app.route('/')
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render'den gelen portu al
    app.run(host='0.0.0.0', port=port, debug=True)
