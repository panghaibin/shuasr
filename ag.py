# -*- coding: UTF-8 -*-
import os
import re
import json
import math
import base64
import random
import logging
import datetime
from time import sleep
from PIL import Image, ImageOps, ImageEnhance
from utils import abs_path, getUsers, login, html2JsLine, jsLine2Json, getTime, sendMsg, getSendApi

if os.path.exists(abs_path + '/ag.yaml'):
    config = abs_path + '/ag.yaml'
else:
    config = abs_path + '/config.yaml'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def _sleep():
    os_sleep = os.getenv('sleep_time', '')
    os_sleep = 5 if os_sleep == '' else os_sleep
    if os_sleep == 'random':
        sleep_time = random.randint(2 * 60, 30 * 60)
    else:
        sleep_time = int(os_sleep)
    logging.info(f'休眠 {sleep_time}s，约{sleep_time // 60}分钟')
    sleep(sleep_time)
    logging.info("休眠结束")


def compress_img(img_path):
    cur_img = Image.open(img_path)
    cur_img = ImageOps.exif_transpose(cur_img)
    raw_width, raw_height = cur_img.size
    angle = random.randint(1, 6)
    cur_img = cur_img.rotate(angle, expand=True)
    new_width, new_height = cur_img.size
    blank_width = int(math.tan(math.radians(angle)) * raw_height + 10)
    blank_height = int(math.tan(math.radians(angle)) * raw_width + 10)
    left = blank_width
    top = blank_height
    right = new_width - blank_width
    bottom = new_height - blank_height
    cur_img = cur_img.crop((left, top, right, bottom))

    width, height = cur_img.size
    crop_width = width * 0.90
    crop_height = height * 0.90
    left = random.randint(0, int(width - crop_width))
    top = random.randint(0, int(height - crop_height))
    right = left + crop_width
    bottom = top + crop_height
    cur_img = cur_img.crop((left, top, right, bottom))

    bri_enhancer = ImageEnhance.Brightness(cur_img)
    cur_img = bri_enhancer.enhance(random.randint(8, 12) / 10)
    col_enhancer = ImageEnhance.Color(cur_img)
    cur_img = col_enhancer.enhance(random.randint(9, 11) / 10)

    cps_time = getTime().strftime('%M%S%f')
    new_img_path = img_path.replace('.jpg', f'_{cps_time}_compress.jpg')
    target_size = 3 * 1024 * 1024
    quality = 90
    step = 5

    cur_img.save(new_img_path)
    cur_img_size = os.path.getsize(new_img_path)
    while cur_img_size > target_size and quality > 10:
        cur_img.save(new_img_path, quality=quality, optimize=True)
        cur_img = Image.open(new_img_path)
        cur_img_size = os.path.getsize(new_img_path)
        quality -= step

    return new_img_path


def upload_Ag_img(username, password):
    session = login(username, password)
    if not session:
        logging.info('登录失败')
        return False
    logging.info('登录成功')

    ag_url = 'https://selfreport.shu.edu.cn/HSJC/HeSJCSelfUploads.aspx'
    ag_html = session.get(url=ag_url).text
    logging.info('获取页面成功')

    even_target = 'p1$P_Upload$btnUploadImage'
    view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', ag_html).group(1)
    view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', ag_html).group(1)

    notice_url = 'https://selfreport.shu.edu.cn/HSJC/kydaynotice.aspx'
    notice_html = session.get(url=notice_url).text
    notice_event_target = re.search(r'Submit\',name:\'(.*?)\',disabled:true', notice_html).group(1)
    notice_form = {
        '__EVENTTARGET': notice_event_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        'F_TARGET': 'p1_ctl01_btnSubmit',
        'p1_ctl00_Collapsed': 'false',
        'p1_Collapsed': 'false',
        'F_STATE': 'eyJwMV9jdGwwMCI6eyJJRnJhbWVBdHRyaWJ1dGVzIjp7fX0sInAxIjp7IklGcmFtZUF0dHJpYnV0ZXMiOnt9fX0=',
    }
    notice_result = session.post(url=notice_url, data=notice_form).text

    t = getTime()
    t -= datetime.timedelta(minutes=2)
    test_date = t.strftime('%Y-%m-%d %H:%M')
    test_date_check = f'{t.year}/{t.month}/{t.day} {t.hour}:{t.minute}'
    test_times = "1" if getTime().hour < 12 else "2"

    id_num = username
    name = ""
    ag_line = html2JsLine(ag_html)
    for i, line in enumerate(ag_line):
        if 'p1_XingMing' in line:
            name = jsLine2Json(ag_line[i - 1])['Text']
            break

    ag_b64str = 'eyJwMV9Hb25nSGFvIjogeyJUZXh0IjogIiJ9LCAicDFfWGluZ01pbmciOiB7IlRleHQiOiAiIn0sICJwMV9QX1VwbG9hZF9DaGVuZ051byI6IHsiQ2hlY2tlZCI6IHRydWV9LCAicDFfUF9VcGxvYWRfY3RsMDAiOiB7IklGcmFtZUF0dHJpYnV0ZXMiOiB7fX0sICJwMV9QX1VwbG9hZF9TaGVuVFpLIjogeyJGX0l0ZW1zIjogW1si5ZCmIiwgIjxzcGFuIHN0eWxlPSdjb2xvcjpncmVlbic+5peg5Lul5LiK55eH54q2KE5vKTwvc3Bhbj4iLCAxXSwgWyLmmK8iLCAiPHNwYW4gc3R5bGU9J2NvbG9yOnJlZCc+5pyJ5Lul5LiK55eH54q25LmL5LiAKFllcyk8L3NwYW4+IiwgMV1dLCAiU2VsZWN0ZWRWYWx1ZSI6ICLlkKYifSwgInAxX1BfVXBsb2FkX0ppYW5DTFgiOiB7IkZfSXRlbXMiOiBbWyLmipfljp8iLCAiPHNwYW4gc3R5bGU9J2ZvbnQtd2VpZ2h0OmJvbGRlcjsnPuaKl+WOnyhBbnRpZ2VuIFRlc3QpPC9zcGFuPiIsIDFdLCBbIuaguOmFuCIsICLmoLjphbgoTnVjbGVpYyBBY2lkIFRlc3QpIiwgMV1dLCAiU2VsZWN0ZWRWYWx1ZSI6ICLmipfljp8ifSwgInAxX1BfVXBsb2FkX0NhaVlGUyI6IHsiRl9JdGVtcyI6IFtbIum8u+iFlOaLreWtkCIsICLpvLvohZTmi63lrZAoTm9zZSkiLCAxXSwgWyLpvLvlkr3mi63lrZAiLCAi6by75ZK95out5a2QKE5vc2UrVGhyb2F0KSIsIDFdLCBbIuWPo+iFlOaLreWtkCIsICLlj6PohZTmi63lrZAoVGhyb2F0KSIsIDFdXSwgIlNlbGVjdGVkVmFsdWUiOiAi6by76IWU5out5a2QIn0sICJwMV9QX1VwbG9hZF9IZVNKQ1JRIjogeyJUZXh0IjogIiJ9LCAicDFfUF9VcGxvYWRfQ2lTaHUiOiB7IkZfSXRlbXMiOiBbWyIxIiwgIuesrDHmrKEoRmlyc3QpIiwgMV0sIFsiMiIsICLnrKwy5qyhKFNlY29uZCkiLCAxXSwgWyIzIiwgIuesrDPmrKEoVGhpcmQpIiwgMV1dLCAiU2VsZWN0ZWRWYWx1ZSI6ICIxIn0sICJwMV9QX1VwbG9hZF9KaWFuQ0pHIjogeyJGX0l0ZW1zIjogW1si6Zi05oCnIiwgIjxzcGFuIHN0eWxlPSdjb2xvcjpncmVlbic+6Zi05oCnKE5lZ2F0aXZlKTwvc3Bhbj4iLCAxXSwgWyLpmLPmgKciLCAiPHNwYW4gc3R5bGU9J2NvbG9yOnJlZCc+6Ziz5oCnKFBvc2l0aXZlKTwvc3Bhbj4iLCAxXSwgWyLml6DmlYgiLCAi5peg5pWIKEludmFsaWQpIiwgMV0sIFsi5pqC5peg57uT5p6cIiwgIuaaguaXoOe7k+aenChObyBSZXN1bHQpIiwgMV1dLCAiU2VsZWN0ZWRWYWx1ZSI6ICLpmLTmgKcifSwgInAxX1BfVXBsb2FkIjogeyJJRnJhbWVBdHRyaWJ1dGVzIjoge319LCAicDFfR3JpZERhdGEiOiB7IlJlY29yZENvdW50IjogMCwgIkZfUm93cyI6IFtdLCAiSUZyYW1lQXR0cmlidXRlcyI6IHt9fSwgInAxIjogeyJJRnJhbWVBdHRyaWJ1dGVzIjoge319LCAiV19TaG93UGljIjogeyJJRnJhbWVBdHRyaWJ1dGVzIjoge319fQ=='
    ag_json = json.loads(base64.b64decode(ag_b64str).decode('utf-8'))
    ag_json['p1_GongHao']['Text'] = id_num
    ag_json['p1_XingMing']['Text'] = name
    ag_json['p1_P_Upload_HeSJCRQ']['Text'] = test_date
    ag_json['p1_P_Upload_CiShu']['SelectedValue'] = test_times
    fstate = base64.b64encode(json.dumps(ag_json, ensure_ascii=False).encode("utf-8")).decode("utf-8")

    report_form = {
        '__EVENTTARGET': even_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        'p1$P_Upload$ChengNuo': 'p1_P_Upload_ChengNuo',
        'p1$P_Upload$ShenTZK': b'\xe5\x90\xa6'.decode(),
        'p1$P_Upload$JianCLX': b'\xe6\x8a\x97\xe5\x8e\x9f'.decode(),
        'p1$P_Upload$CaiYFS': b'\xe9\xbc\xbb\xe8\x85\x94\xe6\x8b\xad\xe5\xad\x90'.decode(),
        'p1$P_Upload$HeSJCRQ': test_date,
        'p1$P_Upload$CiShu': test_times,
        'p1$P_Upload$JianCJG': b'\xe9\x98\xb4\xe6\x80\xa7'.decode(),
        'p1_P_Upload_ctl00_Collapsed': 'false',
        'p1_P_Upload_Collapsed': 'false',
        'p1_GridData_Collapsed': 'false',
        'p1_GridData_HiddenColumns': '["p1_GridData_ctl00"]',
        'p1_Collapsed': 'false',
        'W_ShowPic_Collapsed': 'false',
        'W_ShowPic_Hidden': 'true',
        'F_STATE': fstate,
        'F_TARGET': 'p1_P_Upload_btnUploadImage',
        'X-FineUI-Ajax': 'true',
    }
    img_list = os.listdir(abs_path + '/ag_img/')
    img_path = random.choice(img_list)
    img_path = abs_path + '/ag_img/' + img_path
    img_path = compress_img(img_path)
    img = open(img_path, 'rb')
    file = {
        'p1$P_Upload$FileHeSJCBG': (f'{id_num}.jpg', img, 'image/jpeg', {'Content-Type': 'image/jpeg'}),
    }
    ag_upload = 'https://selfreport.shu.edu.cn/HSJC/HeSJCSelfUploads.aspx'

    upload_times = 0
    while True:
        sleep(5)
        result = session.post(url=ag_upload, data=report_form, files=file).text
        upload_times += 1
        if '上传成功' in result or test_date_check in result or '更新失败' in result or upload_times >= 2:
            break
        logging.info(result)

    send_api = getSendApi(config)
    title = f'{id_num[-3:]}的第{test_times}次结果'
    now = t.strftime('%Y-%m-%d %H:%M:%S')
    if '上传成功' in result or test_date_check in result:
        title += '上传成功'
        desp = f'{now}\n\n{id_num[:-3]}{title}'
    elif '更新失败' in result:
        title += '已上传过'
        desp = f'{now}\n\n{id_num[:-3]}{title}'
    else:
        title += '上传失败'
        logging.info(result)
        result = result.split('F.alert')[-1]
        result = result.split('&#39;')[1]
        desp = f'{now}\n\n{id_num[:-3]}{title}\n\n{result}'
    logging.info(title)
    send_result = sendMsg(title, desp, send_api['api'], send_api['key'])
    logging.info('消息发送成功') if send_result else logging.info('消息发送失败')
    img.close()
    os.remove(img_path)


def main():
    users = getUsers(config)
    users = [(user, id_num) for user in users for id_num in users[user]]
    random.shuffle(users)
    for i, j in enumerate(users):
        username, password = j
        upload_Ag_img(username, password)
        if i < len(users) - 1:
            sleep_time = random.randint(5, 10)
            logging.info(f'休眠{sleep_time}分钟')
            sleep(sleep_time * 60)


if __name__ == '__main__':
    _sleep()
    if main():
        exit(0)
    else:
        exit(1)
