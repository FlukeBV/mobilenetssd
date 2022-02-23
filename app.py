import os
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import json
import requests
import tempfile, shutil, os
from PIL import Image
from io import BytesIO

from linebot.models import (
    TemplateSendMessage, AudioSendMessage,
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, PostbackEvent, StickerMessage, StickerSendMessage, 
    LocationMessage, LocationSendMessage, ImageMessage, ImageSendMessage
)
from linebot.models.template import *
from linebot import (
    LineBotApi, WebhookHandler
)

app = Flask(__name__, static_url_path="/static")

UPLOAD_FOLDER ='static/uploads/'
DOWNLOAD_FOLDER = 'static/downloads/'
ALLOWED_EXTENSIONS = {'jpg', 'png','.jpeg'}

lineaccesstoken = 'MK+kybDWKaZTTC5SEyUPxeI4xVmTQR0w75DAK24AP9LPpTAX84fuZQInqCeIsitTobn4cVp+jGpguHyKgHWnf2YTOIa4qf5PS1QYtVmsJWPGzssu5zAoc7W79i3uLrzMbvjrPB1sx0dubtlnSnCKtwdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(lineaccesstoken)

# APP CONFIGURATIONS
app.config['SECRET_KEY'] = 'opencv'  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
# limit upload size upto 6mb
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file attached in request')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            process_file(os.path.join(UPLOAD_FOLDER, filename), filename)
            data={
                "processed_img":'static/downloads/'+filename,
                "uploaded_img":'static/uploads/'+filename
            }
            return render_template("index.html",data=data)  
    return render_template('index.html')


def process_file(path, filename):
    detect_object(path, filename)
    
def detect_object(path, filename):    
    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
        "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
        "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
        "sofa", "train", "tvmonitor"]
    COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
    prototxt="ssd/MobileNetSSD_deploy.prototxt.txt"
    model ="ssd/MobileNetSSD_deploy.caffemodel"
    net = cv2.dnn.readNetFromCaffe(prototxt, model)
    image = cv2.imread(path)
    image = cv2.resize(image,(480,360))
    (h, w) = image.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.60:
            idx = int(detections[0, 0, i, 1])
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # display the prediction
            label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
            # print("[INFO] {}".format(label))
            cv2.rectangle(image, (startX, startY), (endX, endY),
                COLORS[idx], 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(image, label, (startX, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

    cv2.imwrite(f"{DOWNLOAD_FOLDER}{filename}",image)

@app.route('/callback', methods=['POST'])
def callback():
    json_line = request.get_json(force=False,cache=False)
    json_line = json.dumps(json_line)
    decoded = json.loads(json_line)
    
    # เชื่อมต่อกับ line 
    no_event = len(decoded['events'])
    for i in range(no_event):
            event = decoded['events'][i]
            event_handle(event,json_line)

    # เชื่อมต่อกับ dialogflow
    #intent = decoded["queryResult"]["intent"]["displayName"] 
    #text = decoded['originalDetectIntentRequest']['payload']['data']['message']['text'] 
    #reply_token = decoded['originalDetectIntentRequest']['payload']['data']['replyToken']
    #id = decoded['originalDetectIntentRequest']['payload']['data']['source']['userId']
    #disname = line_bot_api.get_profile(id).display_name
    #reply(intent,text,reply_token,id,disname)

    return '',200

def reply(intent,text,reply_token,id,disname):
    text_message = TextSendMessage(text="ทดสอบ")
    line_bot_api.reply_message(reply_token,text_message)

def event_handle(event,json_line):
    print(event)
    try: 
        userId = event['source']['userId']
    except:
        print('error cannot get userId')
        return ''

    try:
        rtoken = event['replyToken']
    except:
        print('error cannot get rtoken')
        return ''
    try:
        msgId = event["message"]["id"]
        msgType = event["message"]["type"]
    except:
        print('error cannot get msgID, and msgType')
        sk_id = np.random.randint(1,17)
        replyObj = StickerSendMessage(package_id=str(1),sticker_id=str(sk_id))
        line_bot_api.reply_message(rtoken, replyObj)
        return ''

    if msgType == "text":       
        msg = str(event["message"]["text"])
        if msg == "ขอเมนูอาหาร":
            replyObj = TextSendMessage(text="🍲ต้มยำกุ้ง 40 บาท\n🍝ผัดไทย 30 บาท\n🍛ผัดกระเพรา 30 บาท (หมู/ไก่/หมึก/กุ้ง) พิเศษไข่ดาว 35 บาท\n🍚ข้าวผัด 30 บาท (หมู/ไก่/ปู/หมึก/กุ้ง)\n🍵เเกงเขียวหวาน 30 บาท")
            line_bot_api.reply_message(rtoken,replyObj)
        elif msg == "ขอเมนูอาหารfast food":
            replyObj = TextSendMessage(text="🍕พิซซ่า 279 บาท/ถาด\nเลือกหน้าพิซซ่า\nแฮมและปูอัด\nฮาวายเอี้ยน\nเปปเปอร์โรนี\nดับเบิ้ลชีส\nซีฟู้ดค็อกเทล\n🥪แซนด์วิช 59 บาท/อัน\nเลือกแบบแซนด์วิช\nแฮมชีส\nไข่ดาวและปูอัด\nชีสไข่ดาว\n🍔แฮมเบอร์เกอร์ 69 บาท/ชิ้น\nเลือกแบบแฮมเบอร์เกอร์\nชีสเบอร์เกอร์ (หมู/ไก่)\nเบอร์เกอร์สเต๊ก (หมู/ไก่/เนื้อ)\n🍗ไก่ทอด 139 บาท/set\nเลือกแบบไก่ทอด\nไก่ทอดออริจินัล\nไก่ทอดวิงส์แซ่บ\nไก่เกาหลี\n🍟เฟรนช์ฟรายด์ 49 บาท\nเลือกแบบเฟรนช์ฟรายด์\nออริจินัลราดซอส (ชีส/มะเขือเทศ/มายองเนส)\nเฟรนช์ฟรายด์คลุกผง (ชีส/บาร์บีคิว/ปาปิก้า)\n🍝สปาเกตตี 89 บาท/จาน\nเลือกแบบสปาเกตตี\nคาโบนารา\nซอสแดง\nไข่กุ้ง\nมีตบอล\nครีม (เห็ด/แซลมอน/กุ้ง)\n🍽 เมนูทานเล่นเพิ่มเติม\nมันบด 40 บาท\nโดนัทกุ้ง 35 บาท\nข้าวยำไก่แซ่บ 69 บาท\nชีสทอด 49 บาท")
            line_bot_api.reply_message(rtoken,replyObj)
        elif msg == "การจัดส่งของทางร้าน":
            replyObj = TextSendMessage(text="รับเองที่ร้าน\nบริการส่งแบบ Delivery(ฟรีค่าจัดส่ง)\nช่องทางการโอน\nชื่อบัญชี bear bear chophouse\n000-000-0000(Kbank)\nพร้อมเพย์/PromptPay\n000-000-0000")
            line_bot_api.reply_message(rtoken,replyObj)
        elif msg == "covid" : 
            url = "https://covid19.ddc.moph.go.th/api/Cases/today-cases-all" 
            response = requests.get(url) 
            response = response.json() 
            replyObj = TextSendMessage(text=str(response)) line_bot_api.reply_message(rtoken, replyObj)
        else :   
            headers = request.headers
            json_headers = ({k:v for k, v in headers.items()})
            json_headers.update({'Host':'bots.dialogflow.com'})
            url = "https://dialogflow.cloud.google.com/v1/integrations/line/webhook/5ae824ae-d211-4b1c-82b0-e6313a5fa9a2"
            requests.post(url,data=json_line, headers=json_headers)
    elif msgType == "image":
        try:
            message_content = line_bot_api.get_message_content(event['message']['id'])
            i = Image.open(BytesIO(message_content.content))
            filename = event['message']['id'] + '.jpg'
            i.save(UPLOAD_FOLDER + filename)
            process_file(os.path.join(UPLOAD_FOLDER, filename), filename)

            url = request.url_root + DOWNLOAD_FOLDER + filename
            
            line_bot_api.reply_message(
                rtoken, [
                    TextSendMessage(text='Object detection result:'),
                    ImageSendMessage(url,url)
                ])    
    
        except:
            message = TextSendMessage(text="เกิดข้อผิดพลาด กรุณาส่งใหม่อีกครั้ง")
            line_bot_api.reply_message(event.reply_token, message)

            return 0

    else:
        sk_id = np.random.randint(1,17)
        replyObj = StickerSendMessage(package_id=str(1),sticker_id=str(sk_id))
        line_bot_api.reply_message(rtoken, replyObj)
    return ''

if __name__ == '__main__':
    app.run()
