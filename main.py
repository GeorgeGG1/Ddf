from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import time

app = Flask(__name__)
CORS(app)  # عشان يسمح بالاتصال من HTML

IMGBB_API_KEY = "64ce798f34602675b2243f8c4f962484"

# هيدرز PicsArt
PICSART_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': "application/json",
    'x-touchpoint': "ai_enhance",
    'x-app-authorization': "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ijk3MjFiZTM2LWIyNzAtNDlkNS05NzU2LTlkNTk3Yzg2YjA1MSJ9.eyJzdWIiOiJhdXRoLXNlcnZpY2UtYW5kcm9pZCIsImF1ZCI6ImF1dGgtc2VydmljZS1hbmRyb2lkIiwibmJmIjoxNjg3NDI5ODI4LCJzY29wZSI6W10sImlhdCI6MTY4NzQ0MDYyOCwiaXNzIjoiaHR0cHM6Ly9wYS1hdXRob3JpemF0aW9uLXNlcnZlci5zdGFnZS5waWNzYXJ0LnRvb2xzL2FwaS9vYXV0aDIiLCJqdGkiOiJiNGRjNTUzMC1jMTM4LTQzMGYtYWI2NS1hMzI0NmViYzA1ZTcifQ.VWXSiEBZJdNuP1RrAXEwy91AtMa8c8P8iNRoSFffic-5uMMHgqN4R2xY96u90vToxJGXUa66oljPPm2DDj8DH_9YRoYfX9yw6Bi2zMq4sYXK76wQmZJhrI1lMzWee_y9y9tY4v2S-kE8NxsVH0F7bICFmP1pmq3067gAuxxIUzC7MsoUc2OPkXQx40-VvIBKmTktRlagx9EOjcGvxQqxul8Q5EenQR0v725SncMdEtpt6arWsC0UwnYzcOuleyGnX_1s8vzDLFYX-xDv8TTaj06VdO4rbW-un28Ztg_Ia113CdQB0WCLE5fkCxwJGqQFbS4lmpWgfg8iv5cypA2SOg",
    'device-model': "24116RACCG",
    'app': "com.picsart.studio",
    'deviceid': "d_a2da635c298830898d6d37ba961360b9",
    'platform': "android",
    'content-type': "application/json; charset=UTF-8"
}

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response

@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    return jsonify({"status": "ok", "message": "AI Image Enhancer API"})

@app.route('/enhance', methods=['POST', 'OPTIONS'])
def enhance_image():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
        
        file = request.files['image']
        image_bytes = file.read()
        
        # رفع إلى ImgBB
        imgbb_url = upload_to_imgbb(image_bytes)
        
        # تحسين عبر PicsArt
        enhanced_bytes, picsart_url = enhance_with_picsart(imgbb_url)
        
        return jsonify({
            'success': True,
            'enhanced_base64': base64.b64encode(enhanced_bytes).decode('utf-8'),
            'picsart_url': picsart_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def upload_to_imgbb(image_bytes: bytes) -> str:
    url = "https://api.imgbb.com/1/upload"
    response = requests.post(url, data={
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_bytes).decode('utf-8')
    })
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 200:
            return data['data']['url']
    raise Exception("فشل رفع الصورة")

def enhance_with_picsart(image_url: str):
    submit_url = "https://api.picsart.com/gw-v2/workflows/ai-enhance/diffbir/submit"
    
    payload = {
        "params": {
            "image_url": image_url,
            "misc_params": {
                "image_width": 2152,
                "image_height": 3000,
                "device_ram": 12218580992,
                "faces_count": 0
            },
            "preset": "default"
        }
    }
    
    response = requests.post(submit_url, json=payload, headers=PICSART_HEADERS)
    
    if response.status_code not in [200, 201]:
        raise Exception(f"فشل الطلب: {response.status_code}")
    
    task_id = response.json()['response']['id']
    result_url = f"https://api.picsart.com/gw-v2/workflows/ai-enhance/diffbir/{task_id}/result"
    
    for _ in range(30):
        time.sleep(2)
        result_response = requests.get(result_url, headers=PICSART_HEADERS)
        if result_response.status_code == 200:
            data = result_response.json()
            if data['response']['status'] == 'COMPLETED':
                final_url = data['response']['result']['url']
                return requests.get(final_url).content, final_url
    
    raise Exception("انتهى الوقت")
