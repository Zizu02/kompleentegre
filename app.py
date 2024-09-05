from flask import Flask, jsonify, request, render_template_string
import base64
import hmac
import hashlib
import requests
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://sapphire-algae-9ajt.squarespace.com"}})

MERCHANT_ID = '492579'
MERCHANT_KEY = b'Gxm6ww6x6hbPJmg6'
MERCHANT_SALT = b'RbuMk9kDZ2bCa5K2'

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
        # Başarılı token döndü, frontend'de iFrame'i oluşturmak için bu token'ı kullanacağız.
        token = res['token']
        iframe_code = f'''
            <script src="https://www.paytr.com/js/iframeResizer.min.js"></script> 
            <iframe src="https://www.paytr.com/odeme/guvenli/{token}" id="paytriframe" frameborder="0" scrolling="no" style="width: 100%;"></iframe>
            <script>iFrameResize({{}},'#paytriframe');</script>
        '''
        return render_template_string(iframe_code)
    else:
        return jsonify(res)

@app.route('/')
def home():
    return 'Hello, Render! Uygulama çalışıyor.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
