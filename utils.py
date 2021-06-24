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


# 一报：0 两报上午：1 两报下午：2
def getReportType(session):
    index = session.get(url='https://selfreport.shu.edu.cn/')
    if '每日一报' in index.text:
        return 0
    elif '每日两报' in index.text:
        report_type = 1 if getTime().hour < 20 else 2
        return report_type
    else:
        print(index.text)
        print('判断一报/两报失败')
        return False


def getReportUrl(report_type):
    if report_type == 0:
        return 'https://selfreport.shu.edu.cn/DayReport.aspx'
    elif report_type == 1 or report_type == 2:
        return f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?t={report_type}'
    else:
        print('错误的report_type')
        return False


def generateFState(origin_json, post_day=None, province=None, city=None, county=None, address=None, is_in_shanghai=None,
                   temperature=None, campus=None):
    try:
        with open(origin_json, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        print(e)
        print('json文件出错')
        return False

    if campus is None:
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
        json_data['p1_ShiFSH']['SelectedValue'] = is_in_shanghai

        fstate = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    else:
        json_data['p1_BaoSRQ']['Text'] = post_day
        json_data['p1_TiWen']['Text'] = temperature
        json_data['p1_ZaiXiao']['SelectedValue'] = campus
        json_data['p1_ddlXian']['SelectedValueArray'][0] = county
        json_data['p1_XiangXDZ']['Text'] = address

        fstate = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    return fstate


def getReportForm(session, report_type, url, post_day, campus_id):
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

    view_state = re.search('id="__VIEWSTATE" value="(.*?)" /', html).group(1)
    view_state_generator = re.search('id="__VIEWSTATEGENERATOR" value="(.*?)" /', html).group(1)
    # post_day = re.search('f4_state={"Text":"(.*?)"}', html).group(1)

    if report_type == 0 and campus_id == 0:
        province = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f24=', html).group(1)
        city = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f25=', html).group(1)
        county = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f26=', html).group(1)
        address = re.search('"Text":"(((?!"Text":").)*)"};var f27=', html).group(1)
        is_in_shanghai = '是' if province == '上海' else '否'
        # temperature = str(round(random.uniform(36.3, 36.7), 1))

        fstate = generateFState(abs_path + '/once.json', post_day=post_day, province=province, city=city,
                                county=county, address=address, is_in_shanghai=is_in_shanghai)

        report_form = {
            '__EVENTTARGET': 'p1$ctl01$btnSubmit',
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
            'p1$ShiFSH': is_in_shanghai,
            'p1$ShiFZX': '是',
            'p1$ddlSheng$Value': province,
            'p1$ddlSheng': province,
            'p1$ddlShi$Value': city,
            'p1$ddlShi': city,
            'p1$ddlXian$Value': county,
            'p1$ddlXian': county,
            'p1$XiangXDZ': address,
            'p1$ShiFZJ': '否',
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
            'F_TARGET': 'p1_ctl00_btnSubmit',
            'p1_ContentPanel1_Collapsed': 'true',
            'p1_GeLSM_Collapsed': 'false',
            'p1_Collapsed': 'false',
            'F_STATE': fstate,
        }
        return report_form

    if report_type in [1, 2] and campus_id in [1, 2, 3]:
        campus_info = [{'campus': '宝山', 'county': '宝山区', 'address': '上海大学宝山校区'},
                       {'campus': '嘉定', 'county': '嘉定区', 'address': '上海大学嘉定校区'},
                       {'campus': '延长', 'county': '静安区', 'address': '上海大学延长校区'}]
        temperature = str(round(random.uniform(36.3, 36.7), 1))
        campus = campus_info[campus_id - 1]['campus']
        county = campus_info[campus_id - 1]['county']
        address = campus_info[campus_id - 1]['address']

        fstate = generateFState(abs_path + '/twice.json', post_day=post_day, temperature=temperature, campus=campus,
                                county=county, address=address)

        report_form = {
            '__EVENTTARGET': 'p1$ctl00$btnSubmit',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': view_state,
            '__VIEWSTATEGENERATOR': view_state_generator,
            'p1$ChengNuo': 'p1_ChengNuo',
            'p1$BaoSRQ': post_day,
            'p1$DangQSTZK': '良好',
            'p1$TiWen': temperature,
            'p1$ZaiXiao': campus,
            'p1$ddlSheng$Value': '上海',
            'p1$ddlSheng': '上海',
            'p1$ddlShi$Value': '上海市',
            'p1$ddlShi': '上海市',
            'p1$ddlXian$Value': county,
            'p1$ddlXian': county,
            'p1$FengXDQDL': '否',
            'p1$TongZWDLH': '否',
            'p1$XiangXDZ': address,
            'p1$QueZHZJC$Value': '否',
            'p1$QueZHZJC': '否',
            'p1$DangRGL': '否',
            'p1$GeLDZ': '',
            'p1$CengFWH': '否',
            'p1$CengFWH_RiQi': '',
            'p1$CengFWH_BeiZhu': '',
            'p1$JieChu': '否',
            'p1$JieChu_RiQi': '',
            'p1$JieChu_BeiZhu': '',
            'p1$TuJWH': '否',
            'p1$TuJWH_RiQi': '',
            'p1$TuJWH_BeiZhu': '',
            'p1$JiaRen_BeiZhu': '',
            'p1$SuiSM': '绿色',
            'p1$LvMa14Days': '是',
            # 'p1$ShiFJC': ['早餐', '午餐', '晚餐'],
            'p1$Address2': '',
            'F_TARGET': 'p1_ctl00_btnSubmit',
            'p1_GeLSM_Collapsed': 'false',
            'p1_Collapsed': 'false',
            'F_STATE': fstate
        }
        return report_form

    print('传入参数有误')
    return False


def reportSingle(username, password, post_day, campus_id):
    session = login(username, password)
    if not session:
        return False

    report_type = getReportType(session)
    if report_type not in [0, 1, 2]:
        return False

    url = getReportUrl(report_type)
    if not url:
        return False

    form = getReportForm(session, report_type, url, post_day, campus_id)
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


# is_in_school: 获取所有(None)/不在校(0)/在校(1)用户
def getUsers(config_path, is_in_school):
    with open(config_path, 'r', encoding='utf-8') as f:
        users = yaml.load(f, Loader=yaml.FullLoader)['users']
    if is_in_school is None:
        return users
    elif is_in_school == 0:
        filter_users = {}
        for username in users:
            if users[username][1] == 0:
                filter_users.update({username: users[username]})
        return filter_users
    elif is_in_school == 1:
        filter_users = {}
        for username in users:
            if users[username][1] in [1, 2, 3]:
                filter_users.update({username: users[username]})
        return filter_users
    print(f'错误的report_type: {is_in_school}')
    return False


# 上报所有指定 is_in_school 的用户并退出
def reportUsers(config_path, logs_path, is_in_school, post_day):
    if is_in_school is not None and is_in_school not in [0, 1]:
        return False
    users = getUsers(config_path, is_in_school)
    if not users:
        return False
    logs = getLogs(logs_path)
    if not logs:
        return False

    logs_time = getTime().strftime("%Y-%m-%d %H:%M:%S")
    for username in users:
        report_result = reportSingle(username, users[username][0], post_day, users[username][1])
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
            url = "http://sc.ftqq.com/%s.send" % key
            data = {'text': title, 'desp': desp}
            text = requests.post(url, data=data).text
            result = json.loads(text)
            if result['data'] == '发送消息成功':
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
            headers = {'Content-Type': 'application/json'}
            text = requests.post(url, data=body, headers=headers).text
            result = json.loads(text)
            if result['errmsg'] == 'success':
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
        send_msg = sendMsg(title, desp, send_msg['api'], send_msg['key'])
        if send_msg != False and send_msg == True:
            return True
        send_times += 1
        if send_times > 10:
            return False


def checkEnv(config_path, logs_path):
    try:
        users = getUsers(config_path, None)
        if len(users) == 0:
            print('未配置用户，请执行 python3 main.py add 添加用户')
            return False

        for username in users:
            if len(username) != 8:
                print(f'学号{username}有误')
                return False
            if users[username][1] not in [0, 1, 2, 3]:
                print(f'学号{username}校区设置错误')
                return False

        logs = getLogs(logs_path)
        if not logs:
            print('logs.json文件出错')
            return False
        saveLogs(logs_path, logs)
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
    print('当前消息发送平台设置为：%s' % send_msg_api[config['send_api']])
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

    print('当前Token为: %s' % config['send_key'])
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

    if False:
        while True:
            campus = input('输入校区，宝山1/嘉定2/延长3/不在校0：')
            try:
                campus = int(campus)
            except Exception as e:
                print(e)
                print('输入有误，请重新输入')
                continue
            if campus not in [0, 1, 2, 3]:
                print('输入有误，请重新输入')
            else:
                break
    else:
        campus = 0
    new_user = {username: [password, campus]}

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
    report_result = reportUsers(config_path, logs_path, is_in_school=None, post_day=post_day)
    if not report_result:
        print("填报失败，请检查错误信息")
    send_result = sendLogs(logs_path, config_path)
    if not send_result:
        print("Logs 发送失败，可能未配置消息发送API")
    # print("填报成功")
    return True


def isTimeToReport():
    now = getTime()
    if now.hour == 23 and now.minute >= 30:
        return 0
    elif now.hour == 0:
        return 3
    elif 7 <= now.hour <= 8:
        return 1
    elif 20 <= now.hour <= 21:
        return 2
    return -1


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
        form = getReportForm(session, report_type=0, url=url, post_day=post_day, campus_id=0)
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
    sleep_time = 60 * (57 - now.minute)
    sleep_time = sleep_time if sleep_time > 0 and now.hour == 23 else 0
    time.sleep(sleep_time)

    while True:
        now = getTime()
        if (now.hour == 23 and now.minute == 59 and now.second >= 55) or now.hour != 23:
            try_times = 0
            while True:
                report_result = session.post(url=url, data=form)
                if '提交成功' in report_result.text:
                    GRAB_LOGS['success'].append(username)
                    return True
                # else:
                #     print(report_result.text)
                try_times += 1
                if try_times > 500:
                    print(report_result.text)
                    GRAB_LOGS['fail'].append(username)
                    return False
        time.sleep(0.5)


def grabRankUsers(config_path, logs_path, post_day):
    users = getUsers(config_path, is_in_school=0)
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


def main(config_path, logs_path, grab_mode):
    if not checkEnv(config_path, logs_path):
        print("请检查是否已添加用户，确保config.yaml与logs.json可读写")
        print("运行 python3 main.py add 添加用户，运行 python3 main.py send 配置消息发送API")
        return False

    report_result = False
    while True:
        if not report_result:
            is_reported = False
            is_time = isTimeToReport()
            if (is_time == 0 or is_time == 3) and grab_mode and len(getUsers(config_path, 0)) > 0:
                post_day = (getTime() + datetime.timedelta(days=1)).strftime(
                    "%Y-%m-%d") if is_time == 0 else getTime().strftime("%Y-%m-%d")
                report_result = grabRankUsers(config_path, logs_path, post_day)
                is_reported = True
            elif is_time == 1 and len(getUsers(config_path, 0)) > 0:
                post_day = getTime().strftime("%Y-%m-%d")
                if not grab_mode:
                    report_result = reportUsers(config_path, logs_path, is_in_school=None, post_day=post_day)
                    is_reported = True
                elif len(getUsers(config_path, 1)) > 0:
                    report_result = reportUsers(config_path, logs_path, is_in_school=1, post_day=post_day)
                    is_reported = True
            elif is_time == 2 and len(getUsers(config_path, 1)) > 0:
                post_day = getTime().strftime("%Y-%m-%d")
                report_result = reportUsers(config_path, logs_path, is_in_school=1, post_day=post_day)
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
