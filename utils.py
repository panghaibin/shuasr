# -*- coding: UTF-8 -*-
import json
import base64
import re
import threading
import time
import traceback
import qrcode
import requests
import rsa
import yaml
import datetime
import os
import random
from PIL import Image, ImageFont, ImageDraw
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

abs_path = os.path.split(os.path.realpath(__file__))[0]

XCM = base64.b64decode('6KGM56iL56CB').decode('utf-8')

GRAB_LOGS = {'success': [], 'fail': []}
READ_MSG_RESULTS = []


def getTime():
    t = datetime.datetime.utcnow()
    t += datetime.timedelta(hours=8)
    return t


# 2021.04.17 更新密码加密
def encryptPass(password):
    key_str = '''-----BEGIN PUBLIC KEY-----
    MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDl/aCgRl9f/4ON9MewoVnV58OL
    OU2ALBi2FKc5yIsfSpivKxe7A6FitJjHva3WpM7gvVOinMehp6if2UNIkbaN+plW
    f5IwqEVxsNZpeixc4GsbY9dXEk3WtRjwGSyDLySzEESH/kpJVoxO7ijRYqU+2oSR
    wTBNePOk1H+LRQokgQIDAQAB
    -----END PUBLIC KEY-----'''
    pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(key_str.encode('utf-8'))
    crypto = base64.b64encode(rsa.encrypt(password.encode('utf-8'), pub_key)).decode()
    return crypto


def login(username, password, try_once=False):
    default_url = "https://selfreport.shu.edu.cn/Default.aspx"
    form_data = {
        'username': username,
        'password': encryptPass(password),
        'login_submit': None,
    }
    login_times = 0
    while True:
        try:
            session = requests.Session()
            session.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (' \
                                            'KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
            session.trust_env = False
            session.keep_alive = False
            retry = Retry(connect=5, backoff_factor=60)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            sso = session.get(url=default_url)
            session.post(url=sso.url, data=form_data, allow_redirects=False)
            index = session.get(url='https://newsso.shu.edu.cn/oauth/authorize?client_id=WUHWfrntnWYHZfzQ5QvXUCVy'
                                    '&response_type=code&scope=1&redirect_uri=https%3A%2F%2Fselfreport.shu.edu.cn'
                                    '%2FLoginSSO.aspx%3FReturnUrl%3D%252fDefault.aspx&state=')
            login_times += 1
            notice_url = 'https://selfreport.shu.edu.cn/DayReportNotice.aspx'
            view_msg_url = 'https://selfreport.shu.edu.cn/ViewMessage.aspx'
            if index.url == default_url and index.status_code == 200:
                return session
            elif index.url.startswith(view_msg_url):
                view_times = 0
                while view_times < 5:
                    index = session.get(url=default_url)
                    view_times += 1
                    if index.url == default_url:
                        return session
            elif index.url == notice_url:
                if readNotice(session, index.text, notice_url, default_url):
                    return session
            else:
                print([u.url for u in index.history] + [index.url])
        except Exception as e:
            print(e)
            traceback.print_exc()

        del session

        if try_once:
            return False
        if login_times > 10:
            print('尝试登录次数过多')
            return False
        time.sleep(60)


def readNotice(session, notice_html, notice_url, index_url):
    view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', notice_html).group(1)
    view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', notice_html).group(1)
    form_data = {'__EVENTTARGET': 'p1$ctl01$btnSubmit',
                 '__EVENTARGUMENT': '',
                 '__VIEWSTATE': view_state,
                 '__VIEWSTATEGENERATOR': view_state_generator,
                 'F_TARGET': 'p1_ctl01_btnSubmit',
                 'p1_ctl00_Collapsed': 'false',
                 'p1_Collapsed': 'false',
                 'F_STATE': 'eyJwMV9jdGwwMCI6eyJJRnJhbWVBdHRyaWJ1dGVzIjp7fX0sInAxIjp7IklGcmFtZUF0dHJpYnV0ZXMiOnt9fX0=',
                 }
    index = session.post(url=notice_url, data=form_data)
    if index.url == index_url:
        return True


def generateFState(json_file, post_day=None, province=None, city=None, county=None, address=None, in_shanghai=None,
                   in_school=None, in_home=None, sui_img=None, sui_code=None, xing_img=None, xing_code=None, ans=None):
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    json_data['p1_BaoSRQ']['Text'] = post_day

    json_data['p1_ddlSheng']['SelectedValueArray'][0] = province
    json_data['p1_ddlSheng']['F_Items'][0][0] = province
    json_data['p1_ddlSheng']['F_Items'][0][1] = province

    json_data['p1_ddlShi']['SelectedValueArray'][0] = city
    json_data['p1_ddlShi']['F_Items'][0][0] = city
    json_data['p1_ddlShi']['F_Items'][0][1] = city

    json_data['p1_ddlXian']['SelectedValueArray'][0] = county
    json_data['p1_ddlXian']['F_Items'][0][0] = county
    json_data['p1_ddlXian']['F_Items'][0][1] = county

    json_data['p1_XiangXDZ']['Text'] = address

    json_data['p1_ShiFSH']['SelectedValue'] = in_shanghai
    json_data['p1_ShiFZX']['SelectedValue'] = in_school
    json_data['p1_ShiFZJ']['SelectedValue'] = in_home

    json_data['p1_pImages_HFimgSuiSM']['Text'] = sui_code
    json_data['p1_pImages_imgSuiSM']['ImageUrl'] = sui_img
    json_data['p1_pImages_HFimgXingCM']['Text'] = xing_code
    json_data['p1_pImages_imgXingCM']['ImageUrl'] = xing_img

    json_data['p1_pnlDangSZS_DangSZS']['SelectedValueArray'] = ans

    fstate = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    return fstate


def convertAddress(province, city):
    if province in ["北京", "上海", "天津", "重庆"]:
        province += "市"
        city = ''
    elif province in ["香港", "澳门"]:
        province += "特别行政区"
        city = ''
    elif province == "广西":
        province += "壮族自治区"
    elif province == "内蒙古":
        province += "自治区"
    elif province == "宁夏":
        province += "回族自治区"
    elif province == "新疆":
        province += "维吾尔自治区"
    elif province == "西藏":
        province += "自治区"
    else:
        province += "省"
    return province + city


def updateRiskArea():
    try:
        api_url = base64.b64decode('aHR0cHM6Ly9kaXF1LmdlemhvbmcudmlwL2FwaS5waHA=').decode('utf-8')
        i = 0
        while True:
            try:
                result = requests.get(api_url, timeout=30).json()
                if result['code'] == 0:
                    break
                else:
                    i += 1
            except Exception as e:
                print(e)
                i += 1
            if i > 5:
                print('获取风险地区失败')
                return False
        result = result['data']
        risk_list = []
        for high in result['highlist']:
            risk_list.append(high['area_name'].replace(' ', ''))
        for middle in result['middlelist']:
            risk_list.append(middle['area_name'].replace(' ', ''))
        with open('src/risk_area.json', 'w', encoding='utf-8') as f:
            json.dump(risk_list, f)
    except Exception as e:
        print(e)


def checkRiskPosition(position):
    try:
        with open('src/risk_area.json', 'r', encoding='utf-8') as f:
            risk_list = json.load(f)
    except Exception as e:
        print(e)
        return position
    risk_tip = '77yI5rOo77yaKuihqOekuuW9k+WJjeivpeWfjuW4guWtmOWcqOS4remjjumZqeaIlumrmOmjjumZqeWcsOWMuu' \
               '+8jOW5tuS4jeihqOekuueUqOaIt+WunumZheWIsOiuv+i/h+i/meS6m+S4remrmOmjjumZqeWcsOWMuuOAgu+8iQ=='
    risk_tip = base64.b64decode(risk_tip).decode('utf-8')
    position_list = position.split(',')
    asterisk = False
    for i in range(len(position_list)):
        for risk in risk_list:
            if position_list[i] in risk:
                position_list[i] += '*'
                asterisk = True
                break
    position = ','.join(position_list)
    if asterisk:
        position += risk_tip
    return position


def segmentText(text):
    words = list(text)
    left_mark = list("（")
    right_mark = list("）。，：,*")
    while any(mark in words for mark in left_mark + right_mark):
        for i in range(len(words)):
            if len(words) > 1 and i > 0 and words[i - 1] in left_mark:
                words[i] = words[i - 1] + words[i]
                del words[i - 1]
                break
            elif len(words) > 1 and i < len(words) and words[i + 1] in right_mark:
                words[i] = words[i] + words[i + 1]
                del words[i + 1]
                break
    return words


def generateXingImage(ph_num, position):
    t = getTime()
    clock = "%s:%s" % (t.hour, t.strftime("%M"))
    phone = ph_num[:3] + '****' + ph_num[-4:] + base64.b64decode('55qE5Yqo5oCB6KGM56iL5Y2h').decode('utf-8')
    update = base64.b64decode('5pu05paw5LqO77ya').decode('utf-8') + t.strftime("%Y.%m.%d %H:%M:%S")
    tip = base64.b64decode('5oKo5LqO5YmNMTTlpKnlhoXliLDovr7miJbpgJTnu4/vvJo=').decode('utf-8')

    if 1644940800 > t.timestamp() > 1643644800:
        image = Image.open("src/zxn_1.2.bin")
    else:
        image = Image.open("src/zxn_1.bin")
    draw = ImageDraw.Draw(image)
    full_width, full_height = image.size

    clock_font = ImageFont.truetype('src/NotoSansSC-Regular.otf', 32)
    phone_font = ImageFont.truetype('src/NotoSansSC-Bold.otf', 45)
    update_font = ImageFont.truetype('src/NotoSansSC-Bold.otf', 48)
    tip_font = ImageFont.truetype('src/NotoSansSC-Regular.otf', 47)
    position_font = ImageFont.truetype('src/NotoSansSC-Bold.otf', 47)

    phone_width, _ = draw.textsize(phone, phone_font)
    update_width, _ = draw.textsize(update, update_font)
    tip_width, _ = draw.textsize(tip, tip_font)
    draw_x_0 = 125
    draw_y = 1457

    draw.text((52, 23), clock, (59, 59, 59), clock_font)
    draw.text(((full_width - phone_width) / 2, 677), phone, (70, 70, 76), phone_font)
    draw.text(((full_width - update_width) / 2, 779), update, (148, 148, 158), update_font)
    draw.text((draw_x_0, draw_y), tip, (148, 148, 158), tip_font)
    draw_x = draw_x_0 + tip_width
    _, word_height = draw.textsize('一', tip_font)
    position = segmentText(position)
    while len(position) > 0:
        word_width, word_height = draw.textsize(position[0], position_font)
        if draw_x + word_width > full_width - draw_x_0:
            draw_x = draw_x_0
            draw_y += word_height + 3
        draw.text((draw_x, draw_y), position[0], (71, 70, 76), position_font)
        draw_x += word_width
        position = position[1:]

    provider_img = Image.open("src/zxn_2.bin")
    _, provider_height = provider_img.size
    draw_y += word_height
    image.paste(provider_img, (0, draw_y))

    draw_y += provider_height
    draw.rectangle([(0, draw_y), (full_width, full_height)], fill=(43, 166, 103), outline=None)

    footer_img = Image.open("src/zxn_3.bin")
    _, footer_height = footer_img.size
    image.paste(footer_img, (0, full_height - footer_height))

    icons_img = Image.open("src/zxn_4.bin")
    icons_width, icons_height = icons_img.size
    icons_num = int(icons_width / icons_height)
    random_icon = random.randint(0, icons_num - 1)
    icon_box = (random_icon * icons_height, 0, (random_icon + 1) * icons_height, icons_height)
    icon_img = icons_img.crop(icon_box)
    image.paste(icon_img, (int((full_width - icons_height) / 2), 885))

    img_path = '%s_xing.jpg' % t.strftime("%Y%m%d%H%M%S%f")
    image.save(img_path, 'jpeg')
    return img_path


def generateSuiImage(name):
    t = getTime()
    t -= datetime.timedelta(seconds=random.randint(10, 30))
    clock = "%s:%s" % (t.hour, t.strftime("%M"))
    name = '*' * (len(name) - 1) + name[-1]
    time1 = t.strftime("%Y-%m-%d %H:%M:")
    time2 = '%02d' % random.randint(1, 6)

    image = Image.open("src/aan_1.bin")
    draw = ImageDraw.Draw(image)
    full_width, full_height = image.size

    clock_font = ImageFont.truetype('src/NotoSansSC-Regular.otf', 32)
    name_font = ImageFont.truetype('src/NotoSansSC-Bold.otf', 56)
    time1_font = ImageFont.truetype('src/NotoSansSC-Regular.otf', 40)
    time2_font = ImageFont.truetype('src/NotoSansSC-Regular.otf', 48)

    name_width, _ = draw.textsize(name, name_font)
    time1_width, time1_height = draw.textsize(time1, time1_font)
    time2_width, time2_height = draw.textsize(time2, time2_font)

    draw.text((52, 23), clock, (59, 59, 59), clock_font)
    draw.text((558 - name_width, 572), name, (0, 0, 0), name_font)
    time1_x = (full_width - time1_width - time2_width) / 2
    time1_y = 828
    time2_x = time1_x + time1_width
    time2_y = time1_y - (time2_height - time1_height)
    draw.text((time1_x, time1_y), time1, (0, 0, 0), time1_font)
    draw.text((time2_x, time2_y), time2, (0, 0, 0), time2_font)

    logo_img = Image.open("src/aan_2.bin")
    logo_width, logo_height = [int(s * 0.9) for s in logo_img.size]
    logo_img = logo_img.resize((logo_width, logo_height))

    qr = qrcode.QRCode(version=5, box_size=15, error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    random_url = base64.b64decode('aHR0cHM6Ly9zLnNoLmdvdi5jbi8=').decode('utf-8')
    random_url += ''.join(random.sample('0123456789abcdef' * 10, 30)) + str(int(t.timestamp() * 1000))
    qr.add_data(random_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=(9, 189, 100), back_color=(255, 255, 255))
    qr_width, qr_height = qr_img.size

    qr_img.paste(logo_img, (int((qr_width - logo_width) / 2), int((qr_height - logo_height) / 2)), logo_img)
    image.paste(qr_img, (270, 938))

    img_path = '%s_sui.jpg' % t.strftime("%Y%m%d%H%M%S%f")
    image.save(img_path, 'jpeg')
    return img_path


def getImgCodeByUpload(session, img_type, view_state, report_url, img_path):
    img_type_dict = {'sui': 'p1$pImages$fileSuiSM', 'xing': 'p1$pImages$fileXingCM'}
    img_upload = open(img_path, 'rb')
    data = {
        '__EVENTTARGET': img_type_dict[img_type],
        '__VIEWSTATE': view_state,
        'X-FineUI-Ajax': 'true',
    }
    file = {
        img_type_dict[img_type]: img_upload,
    }
    upload_result = session.post(url=report_url, data=data, files=file).text
    img_upload.close()
    _ = re.search(r'Text&quot;:&quot;(.*?)&quot;}\)', upload_result)
    _code = None if _ is None else _.group(1)
    _ = re.search(r'ImageUrl&quot;:&quot;(.*?)&quot;}\)', upload_result)
    _img = None if _ is None else _.group(1)
    return _code, _img


def html2JsLine(html):
    js = re.search(r'F\.load.*]>', html).group(0)
    split = js.split(';var ')
    return split


def jsLine2Json(js):
    return json.loads(js[js.find('=') + 1:])


def getLatestInfo(session):
    history_url = 'https://selfreport.shu.edu.cn/ReportHistory.aspx'
    index = session.get(url=history_url).text
    js_str = re.search('f2_state=(.*?);', index).group(1)
    items = json.loads(js_str)['F_Items']
    info_url = 'https://selfreport.shu.edu.cn'
    for i in items:
        if '已按时填报' in i[1] or '已补报' in i[1]:
            info_url += i[4]
            break

    info_html = session.get(url=info_url).text
    info_line = html2JsLine(info_html)

    in_shanghai = '在上海（校内）'
    in_school = '是'
    province = '上海'
    city = '上海'
    county = '宝山区'
    address = '上海大学宝山校区'
    in_home = '否'
    for i, h in enumerate(info_line):
        if 'ShiFSH' in h:
            in_shanghai = jsLine2Json(info_line[i - 1])['Text']
        elif 'ShiFZX' in h:
            in_school = jsLine2Json(info_line[i - 1])['SelectedValue']
        elif 'ddlSheng' in h:
            province = jsLine2Json(info_line[i - 1])['SelectedValueArray'][0]
        elif 'ddlShi' in h:
            city = jsLine2Json(info_line[i - 1])['SelectedValueArray'][0]
        elif 'ddlXian' in h:
            county = jsLine2Json(info_line[i - 1])['SelectedValueArray'][0]
        elif 'XiangXDZ' in h:
            address = jsLine2Json(info_line[i - 1])['Text']
        elif 'ShiFZJ' in h:
            in_home = jsLine2Json(info_line[i - 1])['SelectedValue']

    p_info_url = 'https://selfreport.shu.edu.cn/PersonInfo.aspx'
    p_info_html = session.get(url=p_info_url).text
    p_info_line = html2JsLine(p_info_html)

    phone_number = '18888888888'
    name = '***'
    for i, h in enumerate(p_info_line):
        if 'ShouJHM' in h:
            phone_number = jsLine2Json(p_info_line[i - 1])['Text']
        elif 'XingMing' in h:
            name = jsLine2Json(p_info_line[i - 1])['Text']

    report_url = 'https://selfreport.shu.edu.cn/DayReport.aspx'
    report_html = session.get(url=report_url).text

    _ = re.search(r'ok:\'F\.f_disable\(\\\'(.*?)\\\'\);__doPostBack\(\\\'(.*?)\\\',\\\'\\\'\);\',', report_html)
    f_target = _.group(1)
    even_target = _.group(2)

    view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', report_html).group(1)
    view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', report_html).group(1)

    report_line = html2JsLine(report_html)
    _code = 'odrp1Za3DEU='
    _img = '/ShowImage.ashx?squrl=oyhA3XzMDCTMwyYAn6kyLt3hxsAoCfpvYGMSocfVfx2RRyKXq9QDVV5cVuq9mN8Mt%2bxyoS93C' \
           '%2b9qawY41vXjo7H18V%2b08RW%2fWDwSfK2TQ8Qc7ob' \
           '%2fnXpyYlgzh5aNOE9tpHWs9n7P7dTaa6iBSTv3Yt40C9UuPY0edMplSSzgA4DQn0HMJY3R5GihYy5Hr9PeiSbwSeJ3GOY%3d'
    ans = None
    sui_code = xing_code = None
    sui_img = xing_img = None
    for i, h in enumerate(report_line):
        if 'pnlDangSZS_ckda' in h:
            text = report_line[i - 1]
            if 'pnlDangSZS_DangSZS' not in text:
                ans = re.findall(r'答案：(.*)\'', text)[0]
                ans = [i for i in ans]
        elif 'pnlDangSZS_DangSZS' in h:
            ans = jsLine2Json(report_line[i - 1])['SelectedValueArray']
        elif 'pImages_HFimgSuiSM' in h:
            try:
                sui_code = jsLine2Json(report_line[i - 1])['Text']
                sui_img = jsLine2Json(report_line[i + 1])['ImageUrl']
            except (KeyError, json.JSONDecodeError):
                img_path = generateSuiImage(name)
                sui_code, sui_img = getImgCodeByUpload(session, 'sui', view_state, report_url, img_path)
                os.remove(img_path)
        elif 'pImages_HFimgXingCM' in h:
            try:
                xing_code = jsLine2Json(report_line[i - 1])['Text']
                xing_img = jsLine2Json(report_line[i + 1])['ImageUrl']
            except (KeyError, json.JSONDecodeError):
                position = convertAddress(province, city)
                position = checkRiskPosition(position)
                img_path = generateXingImage(phone_number, position)
                xing_code, xing_img = getImgCodeByUpload(session, 'xing', view_state, report_url, img_path)
                os.remove(img_path)

    ans = ['A'] if ans is None or ans == [] else ans
    sui_code = _code if sui_code is None else sui_code
    sui_img = _img if sui_img is None else sui_img
    xing_code = _code if xing_code is None else xing_code
    xing_img = _img if xing_img is None else xing_img

    info = dict(vs=view_state, vsg=view_state_generator, f_target=f_target, even_target=even_target,
                province=province, city=city, county=county, address=address,
                in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                sui_code=sui_code, sui_img=sui_img, xing_code=xing_code, xing_img=xing_img,
                ans=ans)

    return info


def getReportForm(post_day, info):
    view_state = info['vs']
    view_state_generator = info['vsg']
    province = info['province']
    city = info['city']
    county = info['county']
    address = info['address']
    in_shanghai = info['in_shanghai']
    in_school = info['in_school']
    in_home = info['in_home']
    f_target = info['f_target']
    even_target = info['even_target']
    sui_code = info['sui_code']
    sui_img = info['sui_img']
    xing_code = info['xing_code']
    xing_img = info['xing_img']
    ans = info['ans']

    # temperature = str(round(random.uniform(36.3, 36.7), 1))

    f_state = generateFState(abs_path + '/once.json', post_day=post_day, province=province, city=city, county=county,
                             address=address, in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                             sui_code=sui_code, sui_img=sui_img, xing_img=xing_img, xing_code=xing_code,
                             ans=ans)

    report_form = {
        '__EVENTTARGET': even_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        'p1$ChengNuo': 'p1_ChengNuo',
        'p1$pnlDangSZS$DangSZS': ans,
        'p1$BaoSRQ': post_day,
        'p1$DangQSTZK': '良好',
        'p1$TiWen': '',
        'p1$JiuYe_ShouJHM': '',
        'p1$JiuYe_Email': '',
        'p1$JiuYe_Wechat': '',
        'p1$QiuZZT': '',
        'p1$JiuYKN': '',
        'p1$JiuYSJ': '',
        'p1$GuoNei': '国内',
        'p1$ddlGuoJia$Value': '-1',
        'p1$ddlGuoJia': '选择国家',
        'p1$ShiFSH': in_shanghai,
        'p1$ShiFZX': in_school,
        'p1$ddlSheng$Value': province,
        'p1$ddlSheng': province,
        'p1$ddlShi$Value': city,
        'p1$ddlShi': city,
        'p1$ddlXian$Value': county,
        'p1$ddlXian': county,
        'p1$XiangXDZ': address,
        'p1$ShiFZJ': in_home,
        'p1$pImages$HFimgSuiSM': sui_code,
        'p1$pImages$HFimgXingCM': xing_code,
        'p1$FengXDQDL': '否',
        'p1$TongZWDLH': '否',
        'p1$CengFWH': '否',
        'p1$CengFWH_RiQi': '',
        'p1$CengFWH_BeiZhu': '',
        'p1$JieChu': '否',
        'p1$JieChu_RiQi': '',
        'p1$JieChu_BeiZhu': '',
        'p1$TuJWH': '否',
        'p1$TuJWH_RiQi': '',
        'p1$TuJWH_BeiZhu': '',
        'p1$QueZHZJC$Value': '否',
        'p1$QueZHZJC': '否',
        'p1$DangRGL': '否',
        'p1$GeLDZ': '',
        'p1$FanXRQ': '',
        'p1$WeiFHYY': '',
        'p1$ShangHJZD': '',
        'p1$DaoXQLYGJ': '无',
        'p1$DaoXQLYCS': '无',
        'p1$JiaRen_BeiZhu': '',
        'p1$SuiSM': '绿色',
        'p1$LvMa14Days': '是',
        'p1$Address2': '',
        'F_TARGET': f_target,
        'p1_pnlDangSZS_Collapsed': 'false',
        'p1_pImages_Collapsed': 'false',
        'p1_ContentPanel1_Collapsed': 'true',
        'p1_GeLSM_Collapsed': 'false',
        'p1_Collapsed': 'false',
        'F_STATE': f_state,
        'X-FineUI-Ajax': 'true',
    }
    return report_form


def getUnreadMsg(session):
    msg_url = 'https://selfreport.shu.edu.cn/MyMessages.aspx'
    msg_html = session.get(url=msg_url).text
    msg_raw = re.search(r'f2_state=(.*?);var', msg_html).group(1)
    msg = json.loads(msg_raw)['F_Items']
    blue_url = []
    red_url = []
    red_title = []
    for i in msg:
        if 'red' in i[1] or 'blue' in i[1]:
            url = 'https://selfreport.shu.edu.cn' + i[4]
            if 'blue' in i[1]:
                blue_url.append(url)
            elif 'red' in i[1]:
                title = re.search(r'标题：(.*?)</div>', i[1]).group(1)
                red_url.append(url)
                red_title.append(title)
    unread_msg = dict(blue_url=blue_url, red_url=red_url, red_title=red_title,
                      blue_count=len(blue_url), red_count=len(red_url))
    return unread_msg


def readUnreadMsg(session):
    unread_msg = getUnreadMsg(session)
    blue_count = unread_msg['blue_count']
    red_count = unread_msg['red_count']
    read_result = ''
    if blue_count + red_count > 0:
        for i in (unread_msg['blue_url'] + unread_msg['red_url']):
            session.get(url=i, allow_redirects=False)
        read_result = '阅读了'
        read_result += '%s条非必读消息' % blue_count if blue_count > 0 else ''
        read_result += '，%s条必读消息' % red_count if red_count > 0 else ''
        read_result += '：标题为《' + '》《'.join(unread_msg['red_title']) + '》' if red_count > 0 else ''
    return dict(red_count=red_count, result=read_result, username='')


def sendAllReadMsgResult(results: list, send_api, send_key):
    desp = ''
    for r in results:
        desp += r['username'] + ': ' + r['result'] + '\n\n' if r['red_count'] > 0 else ''
    if desp != '':
        title = '存在必读消息'
        return sendMsg(title, desp, send_api, send_key)
    return False


def getUnreportedDay(session, ignore_today=True):
    today = getTime().strftime("%Y-%m-%d")
    history_url = 'https://selfreport.shu.edu.cn/ReportHistory.aspx'
    index = session.get(url=history_url).text
    js_str = re.search('f2_state=(.*?);', index).group(1)
    items = json.loads(js_str)['F_Items']
    unreported_day = []
    if ignore_today and today in items[0][1]:
        items.pop(0)
    for i in items:
        if '未填报' in i[1]:
            date = re.search(r'\d{4}-\d{2}-\d{2}', i[1]).group(0)
            unreported_day.append(date)
    unreported_day.sort()
    return unreported_day


def reportUnreported(session, info, unreported_day):
    for post_day in unreported_day:
        _form = getReportForm(post_day, info)
        report_result = reportSingleUser(session, _form)
        if report_result == 1:
            print('补报%s成功' % post_day)
        else:
            print('补报%s失败' % post_day)
    print('补报结束')


def reportSingleUser(session, form):
    if not session:
        return -1
    if not form:
        return -2

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'
    report_times = 0
    while True:
        report_result = session.post(url=url, data=form)
        if '提交成功' in report_result.text:
            return 1
        elif XCM in report_result.text:
            return -3
        else:
            print(report_result.text)
        report_times += 1
        if report_times > 5:
            debug_key = ['__EVENTTARGET', 'p1$pnlDangSZS$DangSZS', 'p1$BaoSRQ', 'p1$ShiFSH', 'p1$ShiFZX', 'p1$ShiFZJ',
                         'F_TARGET']
            debug_privacy_key = ['p1$ddlSheng$Value', 'p1$ddlSheng', 'p1$ddlShi$Value', 'p1$ddlShi', 'p1$ddlXian$Value',
                                 'p1$ddlXian', 'p1$XiangXDZ', 'p1$pImages$HFimgSuiSM', 'p1$pImages$HFimgXingCM']
            debug_value = dict([(key, form[key]) for key in debug_key])
            debug_privacy_value = dict([(key, f'***{str(form[key])[-1]}, length: {len(form[key])}')
                                        for key in debug_privacy_key])
            debug_value.update(debug_privacy_value)
            print('调试信息：\n', debug_value)
            return 0
        time.sleep(5)


def getUsers(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        users = yaml.load(f, Loader=yaml.FullLoader)['users']
    return users


def reportAllUsers(config_path, logs_path, post_day):
    users = getUsers(config_path)
    if not users:
        return False
    logs = getLogs(logs_path)
    if not logs:
        return False
    send_msg = getSendApi(config_path)
    if not send_msg:
        return False

    logs_time = getTime().strftime("%Y-%m-%d %H:%M:%S")
    read_msg_results = []
    for username in users:
        session = login(username, users[username][0])
        if not session:
            logs = updateLogs(logs, logs_time, username, -1)
            time.sleep(60)
            continue
        read_msg_result = readUnreadMsg(session)
        read_msg_result['username'] = username
        read_msg_results.append(read_msg_result)

        _info = getLatestInfo(session)
        unreported_day = getUnreportedDay(session)
        if len(unreported_day) > 0:
            print('%s有%s天未填报，开始补报' % (username, len(unreported_day)))
            reportUnreported(session, _info, unreported_day)
        _form = getReportForm(post_day, _info)
        report_result = reportSingleUser(session, _form)
        logs = updateLogs(logs, logs_time, username, report_result)
        time.sleep(60)
    saveLogs(logs_path, logs)
    sendAllReadMsgResult(read_msg_results, send_msg['api'], send_msg['key'])
    time.sleep(5)
    return True


def getSendApi(config_path):
    config = yaml.load(open(config_path, encoding='utf-8').read(), Loader=yaml.FullLoader)
    send_api = config.get('send_api', None)
    send_key = config.get('send_key', None)
    return {'api': send_api, 'key': send_key}


def sendMsg(title, desp, api, key):
    text = ''
    try:
        if api == 1:
            url = "http://sctapi.ftqq.com/%s.send" % key
            data = {
                'text': title,
                'desp': desp,
            }
            text = requests.post(url, data=data).text
            result = json.loads(text)
            return result['code'] == 0
        elif api == 2:
            url = 'http://pushplus.hxtrip.com/send'
            data = {
                "token": key,
                "title": title,
                "content": desp.replace("\n\n", "<br>"),
            }
            body = json.dumps(data).encode(encoding='utf-8')
            headers = {'Content-Type': 'application/json',
                       'accept': 'application/json'}
            text = requests.post(url, data=body, headers=headers).text
            result = json.loads(text)
            return result['code'] == 200
        elif api == 3:
            tg_bot_key, tg_chat_id = key.split('@')
            url = 'https://api.telegram.org/bot%s/sendMessage' % tg_bot_key
            data = {
                'chat_id': tg_chat_id,
                'text': title + '\n' + desp,
            }
            text = requests.post(url, data=data).text
            result = json.loads(text)
            return result['ok']
        elif api == 4:
            url = 'https://api2.pushdeer.com/message/push'
            data = {
                "pushkey": key,
                "text": title,
                "desp": desp,
            }
            text = requests.post(url, data=data).text
            result = json.loads(text)
            return result['code'] == 0

    except Exception as e:
        print(text)
        print(e)
        return False


def getLogs(logs_path, newest=False):
    try:
        with open(logs_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    except Exception as e:
        print(e)
        return False
    if not newest:
        return logs
    else:
        try:
            report_time = max(logs.keys())
            return {report_time: logs[report_time]}
        except Exception as e:
            print(e)
            return False


def updateLogs(logs, logs_time, username, status):
    if logs_time not in logs:
        logs.update({logs_time: {}})
        if 'success' not in logs.get(logs_time, {}):
            logs[logs_time].update({'success': []})
        if 'fail' not in logs.get(logs_time, {}):
            logs[logs_time].update({'fail': []})
        if 'xing_code' not in logs.get(logs_time, {}):
            logs[logs_time].update({'xing_code': []})

    success = logs[logs_time]['success']
    fail = logs[logs_time]['fail']
    xing_code = logs[logs_time]['xing_code']

    if status == 1 and username not in success:
        success.append(username)
    elif status == -3 and username not in xing_code:
        xing_code.append(username)
    elif username not in fail:
        fail.append(username)

    logs[logs_time]['success'] = success
    logs[logs_time]['fail'] = fail
    logs[logs_time]['xing_code'] = xing_code

    return logs


def saveLogs(logs_path, logs):
    with open(logs_path, 'w') as f:
        json.dump(logs, f)


def sendLogs(logs_path, config_path):
    send_msg = getSendApi(config_path)
    if send_msg['api'] == 0 or send_msg['key'] is None:
        print("未配置消息发送API")
        return False

    logs = getLogs(logs_path, newest=True)
    report_time = list(logs.keys())[0]

    title = ''
    desp = '时间：%s\n\n' % report_time
    success = logs[report_time].get('success')
    fail = logs[report_time].get('fail')
    xing_code = logs[report_time].get('xing_code')

    if len(success):
        for username in success:
            title += username[4:] + '.'
            desp += '用户%s填报成功\n\n' % username
        title += '成功'

    if len(xing_code):
        for username in xing_code:
            title += username[4:] + '.'
            desp += '用户%s需要上传%s\n\n' % (username, XCM)
        title += '需要' + XCM
        desp += '请尽快上传%s\n\n' % XCM

    if len(fail):
        for username in fail:
            title += username[4:] + '.'
            desp += '用户%s填报失败\n\n' % username
        title += '失败'
        desp += '请尽快查看控制台输出确定失败原因'

    send_times = 0
    while True:
        send_msg_result = sendMsg(title, desp, send_msg['api'], send_msg['key'])
        if send_msg_result != False and send_msg_result == True:
            return True
        send_times += 1
        if send_times > 10:
            return False


def checkEnv(config_path):
    try:
        users = getUsers(config_path)
        if len(users) == 0:
            print('未配置用户，请执行 python3 main.py add 添加用户')
            return False

        for username in users:
            if len(username) != 8:
                print(f'学号{username}有误')
                return False

    except Exception as e:
        print(e)
        return False
    return True


def initConfig(config_path):
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w') as f:
                config = {'send_api': 0, 'send_key': '', 'users': {}}
                yaml.dump(config, f)
        except Exception as e:
            print(e)
            return False
    return True


def setSendMsgApi(config_path):
    if not initConfig(config_path):
        return False
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    send_msg_api = ['未设置',
                    '方糖气球 https://sct.ftqq.com/',
                    '推送加 https://pushplus.hxtrip.com/',
                    'Telegram Bot (Key 的格式为 `BOT_TOKEN@CHAT_ID` )']
    send_api = config.get('send_api', 0)
    send_key = config.get('send_key', '')
    print('当前消息发送平台设置为：%s' % send_msg_api[send_api])
    print('支持的平台：')
    for i in range(1, len(send_msg_api)):
        print("%s. %s" % (i, send_msg_api[i]))
    while True:
        send_api = input("请选择：")
        try:
            send_api = int(send_api)
        except Exception as e:
            print(e)
            print('输入有误，重新输入')
            continue
        if send_api not in range(1, len(send_msg_api)):
            print('输入有误，重新输入')
        else:
            break
    config['send_api'] = send_api

    print('当前Token为: %s' % send_key)
    send_key = input('设置Token：')
    config['send_key'] = send_key
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    return True


def addUser(config_path):
    while True:
        username = input('学号：')
        if len(username) == 8:
            break
        print('学号应为8位，请重新输入')

    password = input('密码：')
    if not login(username, password, try_once=True):
        print('学号或密码错误，请重新输入')
        return False

    new_user = {username: [password]}

    if not initConfig(config_path):
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    for username in list(config['users'].keys()):
        if len(username) != 8:
            config['users'].pop(username)

    config['users'].update(new_user)
    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    return True


# 上报所有用户，用于测试
def test(config_path, logs_path):
    if not checkEnv(config_path):
        print("请检查是否已添加用户，确保config.yaml与logs.json可读写")
        print("运行 python3 main.py add 添加用户，运行 python3 main.py send 配置消息发送API")
        return False

    updateRiskArea()
    post_day = getTime().strftime("%Y-%m-%d")
    report_result = reportAllUsers(config_path, logs_path, post_day=post_day)
    if not report_result:
        print("填报失败，请检查错误信息")
    send_result = sendLogs(logs_path, config_path)
    if not send_result:
        print("Logs 发送失败，可能未配置消息发送API")
    # print("填报成功")
    return True


def github(get_config=None):
    users = os.environ['users'].split(';')
    send = os.environ.get('send', '').split(',')
    if get_config is not None:
        if get_config == 'u':
            print(users[0].split(',')[0])
        elif get_config == 'p':
            print(users[0].split(',')[1])
        return
    updateRiskArea()
    post_day = getTime().strftime("%Y-%m-%d")
    suc_log = []
    xc_log = []
    err_log = []
    read_msg_results = []
    i = 1
    for user_info in users:
        username, password = user_info.split(',')
        session = login(username, password)
        if session:
            read_msg_result = readUnreadMsg(session)
            if read_msg_result['result'] != '':
                print('%s: %s' % (i, read_msg_result['result']))
            i += 1
            read_msg_result['username'] = username
            read_msg_results.append(read_msg_result)
        _info = getLatestInfo(session)
        unreported_day = getUnreportedDay(session)
        if len(unreported_day) > 0:
            print('%s****%s有%s天未填报，开始补报' % (username[:2], username[-2:], len(unreported_day)))
            reportUnreported(session, _info, unreported_day)
        _form = getReportForm(post_day, _info)
        report_result = reportSingleUser(session, _form)
        if report_result == 1:
            suc_log.append(username)
        elif report_result == -3:
            xc_log.append(username)
        else:
            err_log.append(username)
        time.sleep(90)

    title = '每日一报'
    desp = ''
    if len(suc_log):
        for username in suc_log:
            desp += '用户%s填报成功\n\n' % username
        title += '%s位成功，' % len(suc_log)
    if len(xc_log):
        for username in xc_log:
            desp += '用户%s需要上传%s\n\n' % (username, XCM)
        title += '%s位需要%s，' % (len(xc_log), XCM)
        desp += '请尽快上传%s\n\n' % XCM
    if len(err_log):
        for username in err_log:
            desp += '用户%s填报失败\n\n' % username
        title += '%s位失败，' % len(err_log)
        desp += '请尽快查看控制台输出确定失败原因'

    title += '共%s位' % len(users)

    if len(send) == 2:
        send_api = int(send[0])
        send_key = send[1]
        send_result = sendMsg(title, desp, send_api, send_key)
        print('填报消息发送结果：%s' % send_result)
        time.sleep(5)
        send_read_result = sendAllReadMsgResult(read_msg_results, send_api, send_key)
        print('阅读消息发送结果：%s' % send_read_result)

    print(title)
    if err_log:
        print('填报失败用户：')
        for log in err_log:
            print('%s****%s' % (log[:2], log[-2:]))

    if xc_log:
        print('需要上传XC码用户：')
        for log in xc_log:
            print('%s****%s' % (log[:2], log[-2:]))

    if err_log or xc_log:
        raise Exception


def isTimeToReport():
    now = getTime()
    if now.hour == 0 and now.minute >= 30:
        return 0
    elif now.hour == 1:
        return 3
    elif now.hour == 7:
        return 1
    # elif 20 <= now.hour <= 21:
    #     return 2
    return -1


def getGrabMode(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        grab_mode = yaml.load(f, Loader=yaml.FullLoader).get('grab_mode', True)
    return grab_mode


def grabRank(username, password, post_day):
    global GRAB_LOGS
    global READ_MSG_RESULTS

    try_times = 0
    while True:
        session = login(username, password)
        if session:
            break
        try_times += 1
        if try_times < 20:
            time.sleep(60)
            continue
        else:
            GRAB_LOGS['fail'].append(username)
            return False

    read_msg_result = readUnreadMsg(session)
    read_msg_result['username'] = username
    READ_MSG_RESULTS.append(read_msg_result)

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'

    try_times = 0
    while True:
        _info = getLatestInfo(session)
        form = getReportForm(post_day, _info)
        if form:
            break
        try_times += 1
        if try_times < 10:
            time.sleep(10)
            continue
        else:
            GRAB_LOGS['fail'].append(username)
            return False

    now = getTime()
    sleep_time = 60 * (58 - now.minute)
    sleep_time = sleep_time if sleep_time > 0 and now.hour == 0 else 0
    time.sleep(sleep_time)

    while True:
        now = getTime()
        if (now.hour == 0 and now.minute == 59 and now.second >= 55) or now.hour != 0:
            try_times = 0
            while True:
                report_result = session.post(url=url, data=form)
                if '提交成功' in report_result.text:
                    GRAB_LOGS['success'].append(username)
                    return True
                # else:
                #     print(report_result.text)
                try_times += 1
                if try_times > 800:
                    print(report_result.text)
                    GRAB_LOGS['fail'].append(username)
                    return False
        time.sleep(0.5)


def grabRankUsers(config_path, logs_path, post_day):
    users = getUsers(config_path)
    if not users:
        return False
    send_msg = getSendApi(config_path)
    if not send_msg:
        return False

    global GRAB_LOGS
    GRAB_LOGS = {'success': [], 'fail': []}
    global READ_MSG_RESULTS
    READ_MSG_RESULTS = []

    temp = {}

    for username in users:
        temp[username] = threading.Thread(target=grabRank, args=(username, users[username][0], post_day))
        temp[username].start()
        time.sleep(2 * 60)
    for username in users:
        temp[username].join()

    logs = getLogs(logs_path)
    logs_time = getTime().strftime("%Y-%m-%d %H:%M:%S")
    for username in GRAB_LOGS['success']:
        logs = updateLogs(logs, logs_time, username, True)
    for username in GRAB_LOGS['fail']:
        logs = updateLogs(logs, logs_time, username, False)
    saveLogs(logs_path, logs)
    sendAllReadMsgResult(READ_MSG_RESULTS, send_msg['api'], send_msg['key'])
    time.sleep(5)
    return True


def main(config_path, logs_path):
    if not checkEnv(config_path):
        print("请检查是否已添加用户，确保config.yaml与logs.json可读写")
        print("运行 python3 main.py add 添加用户，运行 python3 main.py send 配置消息发送API")
        return False

    grab_mode = getGrabMode(config_path)

    report_result = False
    while True:
        if not report_result:
            is_reported = False
            is_time = isTimeToReport()
            if (is_time == 0 or is_time == 3) and grab_mode and len(getUsers(config_path)) > 0:
                post_day = getTime().strftime("%Y-%m-%d")
                updateRiskArea()
                report_result = grabRankUsers(config_path, logs_path, post_day)
                is_reported = True
            elif is_time == 1 and len(getUsers(config_path)) > 0 and not grab_mode:
                post_day = getTime().strftime("%Y-%m-%d")
                updateRiskArea()
                report_result = reportAllUsers(config_path, logs_path, post_day=post_day)
                is_reported = True

            if is_reported:
                if not report_result:
                    print("填报失败，请检查错误信息")
                send_result = sendLogs(logs_path, config_path)
                if not send_result:
                    print("Logs 发送失败，可能未配置消息发送API")

        if isTimeToReport() == -1:
            report_result = False
        time.sleep(5 * 60)
