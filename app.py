from flask import Flask, request, jsonify
import requests
import base64
import time

app = Flask(__name__)

# إعدادات APIs
IMGBB_API_KEY = "64ce798f34602675b2243f8c4f962484"

# هيدرز PicsArt
PICSART_HEADERS = {
    'User-Agent': "PicsArt-29.8.5",
    'Accept': "application/json",
    'Accept-Encoding': "br,gzip",
    'x-touchpoint': "ai_enhance",
    'x-touchpoint-referrer': "default",
    'x-app-authorization': "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ijk3MjFiZTM2LWIyNzAtNDlkNS05NzU2LTlkNTk3Yzg2YjA1MSJ9.eyJzdWIiOiJhdXRoLXNlcnZpY2UtYW5kcm9pZCIsImF1ZCI6ImF1dGgtc2VydmljZS1hbmRyb2lkIiwibmJmIjoxNjg3NDI5ODI4LCJzY29wZSI6W10sImlhdCI6MTY4NzQ0MDYyOCwiaXNzIjoiaHR0cHM6Ly9wYS1hdXRob3JpemF0aW9uLXNlcnZlci5zdGFnZS5waWNzYXJ0LnRvb2xzL2FwaS9vYXV0aDIiLCJqdGkiOiJiNGRjNTUzMC1jMTM4LTQzMGYtYWI2NS1hMzI0NmViYzA1ZTcifQ.VWXSiEBZJdNuP1RrAXEwy91AtMa8c8P8iNRoSFffic-5uMMHgqN4R2xY96u90vToxJGXUa66oljPPm2DDj8DH_9YRoYfX9yw6Bi2zMq4sYXK76wQmZJhrI1lMzWee_y9y9tY4v2S-kE8NxsVH0F7bICFmP1pmq3067gAuxxIUzC7MsoUc2OPkXQx40-VvIBKmTktRlagx9EOjcGvxQqxul8Q5EenQR0v725SncMdEtpt6arWsC0UwnYzcOuleyGnX_1s8vzDLFYX-xDv8TTaj06VdO4rbW-un28Ztg_Ia113CdQB0WCLE5fkCxwJGqQFbS4lmpWgfg8iv5cypA2SOg",
    'device-model': "24116RACCG",
    'app': "com.picsart.studio",
    'deviceid': "d_a2da635c298830898d6d37ba961360b9",
    'platform': "android",
    'content-type': "application/json; charset=UTF-8"
}

# إضافة headers لـ CORS يدوياً
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response

@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({"status": "ok", "message": "Server is running"})

@app.route('/enhance', methods=['POST', 'OPTIONS'])
def enhance_image():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
        
        file = request.files['image']
        image_bytes = file.read()
        
        # 1. رفع الصورة إلى ImgBB
        imgbb_url = upload_to_imgbb(image_bytes)
        
        # 2. تحسين الصورة عبر PicsArt
        enhanced_bytes, picsart_url = enhance_with_picsart(imgbb_url)
        
        # 3. تحويل الصورة المحسّنة إلى Base64
        enhanced_base64 = base64.b64encode(enhanced_bytes).decode('utf-8')
        
        return jsonify({
            'success': True,
            'enhanced_base64': enhanced_base64,
            'picsart_url': picsart_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def upload_to_imgbb(image_bytes: bytes) -> str:
    url = "https://api.imgbb.com/1/upload"
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    response = requests.post(url, data={
        "key": IMGBB_API_KEY,
        "image": base64_image
    })
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 200:
            return data['data']['url']
    
    raise Exception("فشل رفع الصورة إلى ImgBB")

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
        raise Exception(f"فشل طلب التحسين: {response.status_code}")
    
    data = response.json()
    if data.get('status') != 'success':
        raise Exception("فشل طلب التحسين")
    
    task_id = data['response']['id']
    
    result_url = f"https://api.picsart.com/gw-v2/workflows/ai-enhance/diffbir/{task_id}/result"
    
    for attempt in range(30):
        time.sleep(2)
        result_response = requests.get(result_url, headers=PICSART_HEADERS)
        
        if result_response.status_code == 200:
            result_data = result_response.json()
            status = result_data.get('response', {}).get('status')
            
            if status == 'COMPLETED':
                final_url = result_data['response']['result']['url']
                img_response = requests.get(final_url)
                if img_response.status_code == 200:
                    return img_response.content, final_url
            elif status == 'FAILED':
                raise Exception("فشلت عملية التحسين")
    
    raise Exception("انتهى وقت الانتظار (60 ثانية)")
