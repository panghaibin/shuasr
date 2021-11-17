# -*- coding: UTF-8 -*-
import random
import json
import base64
import re
import threading
import time
import traceback
import requests
import rsa
import yaml
import datetime
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

abs_path = os.path.split(os.path.realpath(__file__))[0]

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
    index_url = "https://selfreport.shu.edu.cn/Default.aspx"
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

            sso = session.get(url=index_url)
            index = session.post(url=sso.url, data=form_data, allow_redirects=False)
            # 一个非常奇怪的bug，URL编码本应是不区分大小写的，但访问302返回的URL就会出问题，需要将URL中的替换成252f
            # index = session.get(url=index.history[-1].url.replace("252F", "252f"))
            # index = session.get(url=index.next.url.replace("252F", "252f"))
            index = session.get(url='https://newsso.shu.edu.cn/oauth/authorize?client_id=WUHWfrntnWYHZfzQ5QvXUCVy'
                                    '&response_type=code&scope=1&redirect_uri=https%3A%2F%2Fselfreport.shu.edu.cn'
                                    '%2FLoginSSO.aspx%3FReturnUrl%3D%252fDefault.aspx&state=')
            login_times += 1
            notice_url = 'https://selfreport.shu.edu.cn/DayReportNotice.aspx'
            if index.url == index_url and index.status_code == 200:
                return session
            elif index.url == notice_url and index.status_code == 200:
                if readNotice(session, index.text, notice_url, index_url):
                    return session
            else:
                # debug
                print(index.history)
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


def getXingCodeByUpload(session, view_state, report_url, use_last=False):
    if use_last:
        pinfo_url = 'https://selfreport.shu.edu.cn/PersonInfo.aspx'
        pinfo_html = session.get(url=pinfo_url).text
        xing_img = re.search(r'f13_state=\{"ImageUrl":"(.*?)"};var f13', pinfo_html).group(1)
        img_raw = session.get(url=f'https://selfreport.shu.edu.cn/{xing_img}', stream=True).content
        img_path = './temp.jpg'
        with open(img_path, 'wb') as f:
            f.write(img_raw)
    else:
        img_path = 'default.jpg'

    img_upload = open(img_path, 'rb')
    data = {
        '__EVENTTARGET': 'p1$pImages$fileXingCM',
        '__VIEWSTATE': view_state,
        'X-FineUI-Ajax': 'true',
    }
    file = {
        'p1$pImages$fileXingCM': img_upload,
    }
    upload_result = session.post(url=report_url, data=data, files=file).text
    _ = re.search(r'Text&quot;:&quot;(.*?)&quot;\}\);f2', upload_result)
    weekly_xing_code = None if _ is None else _.group(1)
    _ = re.search(r'ImageUrl&quot;:&quot;(.*?)&quot;\}\);f3', upload_result)
    weekly_xing_img = None if _ is None else _.group(1)
    img_upload.close()
    if use_last:
        os.remove(img_path)

    return weekly_xing_code, weekly_xing_img


# 获取用户上报页面的最新上报成功的信息
def getLatestInfo(session, notify_xc=False, use_last=False):
    history_url = 'https://selfreport.shu.edu.cn/ReportHistory.aspx'
    index = session.get(url=history_url).text
    js_str = re.search('f2_state=(.*?);', index).group(1)
    items = json.loads(js_str)['F_Items']
    info_url = 'https://selfreport.shu.edu.cn'
    for i in items:
        if '已按时填报' in i[1] or '已补报' in i[1]:
            info_url += i[4]
            break

    # return info_url
    info_html = session.get(url=info_url).text
    province = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f12=', info_html).group(1)
    city = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f13=', info_html).group(1)
    county = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f14=', info_html).group(1)
    address = re.search(r'"Text":"(((?!"Text":").)*)"};var f15=', info_html).group(1)
    _ = re.search(r'f8_state=\{"Hidden":false,"Text":"(.*?)"', info_html)
    in_shanghai = '在上海（校内）' if _ is None or _.group(1) == '在上海' else _.group(1)
    if '在上海' in in_shanghai:
        in_school = re.search(r'f9_state=\{"Hidden":false,"SelectedValue":"(.*?)",', info_html).group(1)
    else:
        in_school = '否'
    in_home = re.search(r'f16_state=\{"Hidden":false,"SelectedValue":"(.*?)",', info_html).group(1)

    report_url = 'https://selfreport.shu.edu.cn/DayReport.aspx'
    report_html = session.get(url=report_url).text

    _ = re.search(r'ok:\'F\.f_disable\(\\\'(.*?)\\\'\);__doPostBack\(\\\'(.*?)\\\',\\\'\\\'\);\',', report_html)
    f_target = _.group(1)
    even_target = _.group(2)

    _ = re.search(r"'参考答案：(.*?)'", report_html)
    ans = None if _ is None else _.group(1)
    if ans is None:
        _ = re.search(r'正确答案为：(.*?)"', report_html)
        ans = None if _ is None else _.group(1)
    if ans is None:
        _ = re.search(r'"SelectedValueArray":\[(.*?)]', report_html)
        ans = None if _ is None else _.group(1)
        ans = ans.replace('"', '').replace(',', '')
    ans = [i for i in ans] if ans is not None else ['A']

    view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', report_html).group(1)
    view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', report_html).group(1)

    require_weekly_xing_code = True if 'f9_state={"Hidden":false' in report_html else False
    weekly_xing_code = None
    weekly_xing_img = None
    if require_weekly_xing_code:
        _ = re.search(r'f65_state=\{"Text":"(.*?)"}', report_html)
        weekly_xing_code = None if _ is None else _.group(1)
        _ = re.search(r'f66_state=\{"ImageUrl":"(.*?)"};var f66', report_html)
        weekly_xing_img = None if _ is None else _.group(1)

        if (weekly_xing_img is None or weekly_xing_img is None) and not notify_xc:
            weekly_xing_code, weekly_xing_img = getXingCodeByUpload(session, view_state, report_url, use_last)

    info = dict(vs=view_state, vsg=view_state_generator, f_target=f_target, even_target=even_target,
                province=province, city=city, county=county, address=address,
                in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                rwxc=require_weekly_xing_code, wxc=weekly_xing_code, wxi=weekly_xing_img,
                ans=ans)

    return info


def getReportForm(session, post_day, notify_xc=False):
    info = getLatestInfo(session, notify_xc)
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
    require_weekly_xing_code = info['rwxc']
    weekly_xing_code = info['wxc']
    weekly_xing_img = info['wxi']
    ans = info['ans']

    # temperature = str(round(random.uniform(36.3, 36.7), 1))

    f_state = generateFState(abs_path + '/once.json', post_day=post_day, province=province, city=city, county=county,
                             address=address, in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                             xing_img=weekly_xing_img, xing_code=weekly_xing_code, ans=ans)

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
        # 'p1$pImages$HFimgSuiSM': sui_code,
        'p1$pImages$HFimgXingCM': weekly_xing_code,
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


def reportSingle(session, post_day, notify_xc=False):
    if not session:
        return -1

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'

    form = getReportForm(session, post_day)
    if not form:
        return -2

    report_times = 0
    while True:
        report_result = session.post(url=url, data=form)
        if '提交成功' in report_result.text:
            return 1
        elif '行程码' in report_result.text:
            return -3
        else:
            print(report_result.text)
        report_times += 1
        if report_times > 10:
            return 0
        time.sleep(10)


def getUsers(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        users = yaml.load(f, Loader=yaml.FullLoader)['users']
    return users


# 上报所有用户并退出
def reportUsers(config_path, logs_path, post_day):
    users = getUsers(config_path)
    if not users:
        return False
    logs = getLogs(logs_path)
    if not logs:
        return False
    send_msg = getSendApi(config_path)
    if not send_msg:
        return False
    notify_xc = getNotifyXC(config_path)

    logs_time = getTime().strftime("%Y-%m-%d %H:%M:%S")
    read_msg_results = []
    for username in users:
        session = login(username, users[username][0])
        if session:
            read_msg_result = readUnreadMsg(session)
            read_msg_result['username'] = username
            read_msg_results.append(read_msg_result)
        report_result = reportSingle(session, post_day, notify_xc)
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
            data = {'text': title, 'desp': desp}
            text = requests.post(url, data=data).text
            result = json.loads(text)
            if result['code'] == 0:
                return True
            else:
                return False
        elif api == 2:
            url = 'http://pushplus.hxtrip.com/send'
            data = {
                "token": key,
                "title": title,
                "content": desp.replace("\n\n", "<br>")
            }
            body = json.dumps(data).encode(encoding='utf-8')
            headers = {'Content-Type': 'application/json',
                       'accept': 'application/json'}
            text = requests.post(url, data=body, headers=headers).text
            result = json.loads(text)
            if result['code'] == 200:
                return True
            else:
                return False
        elif api == 3:
            tg_bot_key, tg_chat_id = key.split('@')
            url = 'https://api.telegram.org/bot%s/sendMessage' % tg_bot_key
            data = {
                'chat_id': tg_chat_id,
                'text': title + '\n' + desp
            }
            text = requests.post(url, data=data).text
            result = json.loads(text)
            return result['ok']

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
            desp += '用户%s需要上传行程码\n\n' % username
        title += '需要行程码'
        desp += '请尽快上传行程码\n\n'

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


def checkEnv(config_path, logs_path):
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
    if not checkEnv(config_path, logs_path):
        print("请检查是否已添加用户，确保config.yaml与logs.json可读写")
        print("运行 python3 main.py add 添加用户，运行 python3 main.py send 配置消息发送API")
        return False

    post_day = getTime().strftime("%Y-%m-%d")
    report_result = reportUsers(config_path, logs_path, post_day=post_day)
    if not report_result:
        print("填报失败，请检查错误信息")
    send_result = sendLogs(logs_path, config_path)
    if not send_result:
        print("Logs 发送失败，可能未配置消息发送API")
    # print("填报成功")
    return True


# GitHub Actions
def github():
    post_day = getTime().strftime("%Y-%m-%d")
    suc_log = []
    xc_log = []
    err_log = []
    users = os.environ['users'].split(';')
    send = os.environ.get('send', '').split(',')
    notify_xc = os.environ.get('notify_xc', '')
    notify_xc = True if notify_xc == '1' else False
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
        result = reportSingle(session, post_day, notify_xc)
        if result == 1:
            suc_log.append(username)
        elif result == -3:
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
            desp += '用户%s需要上传行程码\n\n' % username
        title += '%s位需要行程码，' % len(xc_log)
        desp += '请尽快上传行程码\n\n'
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
        print('需要上传行程码用户：')
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


def getNotifyXC(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        notify_xc = yaml.load(f, Loader=yaml.FullLoader).get('notify_xc', False)
    return notify_xc


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
        form = getReportForm(session, post_day=post_day)
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
    if not checkEnv(config_path, logs_path):
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
                report_result = grabRankUsers(config_path, logs_path, post_day)
                is_reported = True
            elif is_time == 1 and len(getUsers(config_path)) > 0 and not grab_mode:
                post_day = getTime().strftime("%Y-%m-%d")
                report_result = reportUsers(config_path, logs_path, post_day=post_day)
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
