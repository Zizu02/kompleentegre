from flask import Flask, jsonify, request
import base64
import hmac
import hashlib
import requests
import json

app = Flask(__name__)

# PayTR için gerekli bilgiler
MERCHANT_ID = '492579'  # PayTR panelinden alınacak Merchant ID
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'  # PayTR panelinden alınacak Merchant Key
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'  # PayTR panelinden alınacak Merchant Salt

# PayTR Token oluşturma
def create_paytr_token(merchant_id, merchant_key, merchant_salt, user_ip, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):
    hash_str = f"{merchant_id}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket.decode()}{no_installment}{max_installment}{currency}{test_mode}"
    return base64.b64encode(hmac.new(merchant_key, hash_str.encode() + merchant_salt, hashlib.sha256).digest())

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    email = data.get('email')
    payment_amount = data.get('payment_amount')
    user_name = data.get('user_name')
    user_address = data.get('user_address')
    user_phone = data.get('user_phone')
    merchant_oid = data.get('merchant_oid')
    
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

    # PayTR'ye istek gönder
    response = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)
    res = json.loads(response.text)

    if res['status'] == 'success':
        return jsonify({'token': res['token']})
    else:
        return jsonify(res)

if __name__ == '__main__':
    app.run(debug=True)
