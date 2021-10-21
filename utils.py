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

abs_path = os.path.split(os.path.realpath(__file__))[0]

GRAB_LOGS = {'success': [], 'fail': []}


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
                                            'KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36 '
            session.trust_env = False
            session.keep_alive = False
            sso = session.get(url=index_url)
            index = session.post(url=sso.url, data=form_data, allow_redirects=False)
            # 一个非常奇怪的bug，URL编码本应是不区分大小写的，但访问302返回的URL就会出问题，需要将URL中的替换成252f
            # index = session.get(url=index.history[-1].url.replace("252F", "252f"))
            # index = session.get(url=index.next.url.replace("252F", "252f"))
            index = session.get(url='https://newsso.shu.edu.cn/oauth/authorize?client_id=WUHWfrntnWYHZfzQ5QvXUCVy'
                                    '&response_type=code&scope=1&redirect_uri=https%3A%2F%2Fselfreport.shu.edu.cn'
                                    '%2FLoginSSO.aspx%3FReturnUrl%3D%252fDefault.aspx&state=')
            if index.url == index_url and index.status_code == 200:
                return session
            else:
                # debug
                print(index.history)
        except Exception as e:
            print(e)
            traceback.print_exc()

        if try_once:
            return False
        login_times += 1
        if login_times > 10:
            print('尝试登录次数过多')
            return False
        time.sleep(60)


def generateFState(json_file, post_day=None, province=None, city=None, county=None, address=None, in_shanghai=None,
                   in_school=None, in_home=None, sui_img=None, sui_code=None, xing_img=None, xing_code=None):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        print(e)
        print('json文件出错')
        return False

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

    fstate = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    return fstate


# 获取用户上报页面的最新上报成功的信息
def getLatestInfo(session):
    url = 'https://selfreport.shu.edu.cn/ReportHistory.aspx'
    index = session.get(url=url).text
    js_str = re.search('f2_state=(.*?);', index).group(1)
    items = json.loads(js_str)['F_Items']
    info_url = 'https://selfreport.shu.edu.cn'
    for i in items:
        if '已按时填报' in i[1] or '已补报' in i[1]:
            info_url += i[4]
            break

    # return info_url
    html = session.get(url=info_url).text
    province = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f12=', html).group(1)
    city = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f13=', html).group(1)
    county = re.search(r'"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f14=', html).group(1)
    address = re.search(r'"Text":"(((?!"Text":").)*)"};var f15=', html).group(1)
    in_shanghai = re.search(r'f8_state=\{"Hidden":false,"SelectedValue":"(.*?)",', html).group(1)
    if in_shanghai == '是':
        in_school = re.search(r'f9_state=\{"Hidden":false,"SelectedValue":"(.*?)",', html).group(1)
    else:
        in_school = '否'
    in_home = re.search(r'f16_state=\{"Hidden":false,"SelectedValue":"(.*?)",', html).group(1)
    _ = re.search(r'f47_state=\{"ImageUrl":"(.*?)"}', html)
    sui_img = None if _ is None else _.group(1)
    _ = re.search(r'f48_state=\{"ImageUrl":"(.*?)"}', html)
    xing_img = None if _ is None else _.group(1)

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'
    html = session.get(url=url).text
    _ = re.search(r'f64_state=\{"Text":"(.*?)"}', html)
    sui_code = None if _ is None else _.group(1)
    _ = re.search(r'f67_state=\{"Text":"(.*?)"}', html)
    xing_code = None if _ is None else _.group(1)
    _ = re.search(r'ok:\'F\.f_disable\(\\\'(.*?)\\\'\);__doPostBack\(\\\'(.*?)\\\',\\\'\\\'\);\',', html)
    f_target = _.group(1)
    even_target = _.group(2)

    info = dict(f_target=f_target, even_target=even_target,
                province=province, city=city, county=county, address=address,
                in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                sui_img=sui_img, xing_img=xing_img, sui_code=sui_code, xing_code=xing_code)

    return info


def getReportForm(session, url, post_day):
    get_times = 0
    while True:
        try:
            index = session.get(url=url)
            if index.status_code == 200:
                break
        except Exception as e:
            print('view state 获取出错')
            print(e)
        get_times += 1
        if get_times > 10:
            print('view state 获取超时')
            return False
        time.sleep(10)
    html = index.text

    view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', html).group(1)
    view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', html).group(1)
    # post_day = re.search('f4_state={"Text":"(.*?)"}', html).group(1)

    info = getLatestInfo(session)
    province = info['province']
    city = info['city']
    county = info['county']
    address = info['address']
    in_shanghai = info['in_shanghai']
    in_school = info['in_school']
    in_home = info['in_home']
    sui_img = info['sui_img']
    sui_code = info['sui_code']
    xing_img = info['xing_img']
    xing_code = info['xing_code']
    f_target = info['f_target']
    even_target = info['even_target']

    # temperature = str(round(random.uniform(36.3, 36.7), 1))

    f_state = generateFState(abs_path + '/once.json', post_day=post_day, province=province, city=city, county=county,
                             address=address, in_shanghai=in_shanghai, in_school=in_school, in_home=in_home,
                             sui_img=sui_img, sui_code=sui_code, xing_img=xing_img, xing_code=xing_code)

    report_form = {
        '__EVENTTARGET': even_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        'p1$ChengNuo': 'p1_ChengNuo',
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


def reportSingle(username, password, post_day):
    session = login(username, password)
    if not session:
        return False

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'

    form = getReportForm(session, url, post_day)
    if not form:
        return False

    report_times = 0
    while True:
        report_result = session.post(url=url, data=form)
        if '提交成功' in report_result.text:
            return True
        else:
            print(report_result.text)
        report_times += 1
        if report_times > 10:
            return False
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

    logs_time = getTime().strftime("%Y-%m-%d %H:%M:%S")
    for username in users:
        report_result = reportSingle(username, users[username][0], post_day)
        logs = updateLogs(logs, logs_time, username, report_result)
        time.sleep(60)
    saveLogs(logs_path, logs)
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

    success = logs[logs_time]['success']
    fail = logs[logs_time]['fail']

    if status and username not in success:
        success.append(username)
    elif not status and username not in fail:
        fail.append(username)

    logs[logs_time]['success'] = success
    logs[logs_time]['fail'] = fail

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

    if len(success):
        for username in success:
            title += username[4:] + '.'
            desp += '用户%s填报成功\n\n' % username
        title += '成功'

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
                    '推送加 https://pushplus.hxtrip.com/']
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
    err_log = []
    users = os.environ['users'].split(';')
    send = os.environ.get('send', '').split(',')
    for user_info in users:
        username, password = user_info.split(',')
        result = reportSingle(username, password, post_day)
        if result:
            suc_log.append(username)
        else:
            err_log.append(username)
        time.sleep(60)

    if not err_log:
        title = '每日一报%s位成功，共%s位' % (len(suc_log), len(users))
    elif not suc_log:
        title = '每日一报%s位失败，共%s位' % (len(err_log), len(users))
    else:
        title = '每日一报%s位成功，%s位失败，共%s位' % (len(suc_log), len(err_log), len(users))
    if len(send) == 2:
        send_api = int(send[0])
        send_key = send[1]
        desp = ''
        for log in suc_log:
            desp += "%s填报成功\n\n" % log
        for log in err_log:
            desp += "%s填报失败\n\n" % log
        send_result = sendMsg(title, desp, send_api, send_key)
        print('消息发送结果：%s' % send_result)

    print(title)
    if err_log:
        print('填报失败用户：')
    for log in err_log:
        print('%s****%s' % (log[0:2], log[-2]))


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

    url = 'https://selfreport.shu.edu.cn/DayReport.aspx'

    try_times = 0
    while True:
        form = getReportForm(session, url=url, post_day=post_day)
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

    global GRAB_LOGS
    GRAB_LOGS = {'success': [], 'fail': []}

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
