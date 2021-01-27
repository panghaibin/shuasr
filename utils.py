# -*- coding: UTF-8 -*-
import random
import json
import base64
import re
import time
import requests
import yaml
import datetime
import os

abs_path = os.path.split(os.path.realpath(__file__))[0]


def getTime():
    t = datetime.datetime.utcnow()
    t += datetime.timedelta(hours=8)
    return t


def login(username, password):
    index_url = "https://selfreport.shu.edu.cn/Default.aspx"
    form_data = {
        'username': username,
        'password': password,
        'login_submit': None,
    }
    login_times = 0
    while True:
        try:
            session = requests.Session()
            session.keep_alive = False
            sso = session.get(url=index_url)
            index = session.post(url=sso.url, data=form_data)
            # 一个非常奇怪的bug，URL编码本应是不区分大小写的，但访问302返回的URL就会出问题，需要将URL中的替换成252f
            index = session.get(url=index.history[-1].url.replace("252F", "252f"))
            if index.url == index_url and index.status_code == 200:
                return session
        except Exception as e:
            print(e)

        login_times += 1
        if login_times > 10:
            print('尝试登录次数过多')
            return False
        time.sleep(60)


def getReportType(session):
    index = session.get(url='https://selfreport.shu.edu.cn/')
    if '每日一报' in index.text:
        return 0
    elif '每日两报' in index.text:
        report_type = 1 if getTime().hour < 20 else 2
        return report_type
    else:
        print(index.text)
        return False


def getReportUrl(report_type):
    if report_type == 0:
        return 'https://selfreport.shu.edu.cn/DayReport.aspx'
    elif report_type == 1 or report_type == 2:
        return f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?t={report_type}'
    else:
        return False


def generateFState(origin_json, post_day, province, city, county, address, is_in_shanghai):
    try:
        with open(origin_json, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        print(e)
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
    json_data['p1_ShiFSH']['SelectedValue'] = is_in_shanghai

    fstate = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    return fstate


def getDailyReportForm(session, url):
    get_times = 0
    while True:
        try:
            index = session.get(url=url)
            if index.status_code == 200:
                break
        except Exception as e:
            print(e)
        get_times += 1
        if get_times > 10:
            return False
        time.sleep(60)
    html = index.text

    view_state = re.search('id="__VIEWSTATE" value="(.*?)" /', html).group(1)
    view_state_generator = re.search('id="__VIEWSTATEGENERATOR" value="(.*?)" /', html).group(1)
    post_day = re.search('f4_state={"Text":"(.*?)"}', html).group(1)
    province = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f23=', html).group(1)
    city = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f24=', html).group(1)
    county = re.search('"SelectedValueArray":\["(((?!"SelectedValueArray":\[").)*)"]};var f25=', html).group(1)
    address = re.search('"Text":"(((?!"Text":").)*)"};var f26=', html).group(1)
    is_in_shanghai = '是' if province == '上海' else '否'
    # temperature = str(round(random.uniform(36.3, 36.7), 1))

    fstate = generateFState(abs_path + '/daily.json', post_day, province, city, county, address, is_in_shanghai)

    daily_post = {
        '__EVENTTARGET': 'p1$ctl00$btnSubmit',
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
        'p1$ShiFZX': '否',
        'p1$ddlSheng$Value': province,
        'p1$ddlSheng': province,
        'p1$ddlShi$Value': city,
        'p1$ddlShi': city,
        'p1$ddlXian$Value': county,
        'p1$ddlXian': county,
        'p1$XiangXDZ': address,
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

    return daily_post


def reportSingle(username, password):
    session = login(username, password)
    if not session:
        return False

    report_type = getReportType(session)
    if report_type != 0 != 1 != 2:
        return False

    url = getReportUrl(report_type)
    if not url:
        return False

    form = getDailyReportForm(session, url)
    if not form:
        return False

    report_result = session.post(url=url, data=form)
    if '提交成功' in report_result.text:
        return True
    else:
        print(report_result.text)
        return False


def getUsers(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.load(f, Loader=yaml.FullLoader)['users']


def scSend(title, desp, key):
    url = "http://sc.ftqq.com/%s.send" % key
    data = {'text': title, 'desp': desp}
    return json.loads(requests.post(url, data=data).text)


def getLogs(logs_path, newest=False):
    with open(logs_path, 'r', encoding='utf-8') as f:
        logs = json.load(f)
    if not newest:
        return logs
    else:
        report_time = max(logs.keys())
        return {report_time: logs[report_time]}


def updateLogs(logs, report_time, username, status):
    if report_time not in logs:
        logs.update({report_time: {}})
        if 'success' not in logs.get(report_time, {}):
            logs[report_time].update({'success': []})
        if 'fail' not in logs.get(report_time, {}):
            logs[report_time].update({'fail': []})

    success = logs[report_time]['success']
    fail = logs[report_time]['fail']

    if status and username not in success:
        success.append(username)
    elif not status and username not in fail:
        fail.append(username)

    logs[report_time]['success'] = success
    logs[report_time]['fail'] = fail

    return logs


def saveLogs(logs_path, logs):
    with open(logs_path, 'w') as f:
        json.dump(logs, f)


def sendLogs(logs_path, config_path):
    config = open(config_path, encoding='utf-8').read()
    sckey = yaml.load(config, Loader=yaml.FullLoader).get('sckey', None)
    if sckey is None:
        print("未配置sckey")
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

    sc_msg = scSend(title, desp, sckey)
    if sc_msg['errmsg'] != 'success':
        return False
    return True


def reportUsers(config_path, logs_path):
    users = getUsers(config_path)
    if not users:
        return False

    logs = getLogs(logs_path)
    report_time = getTime().strftime("%Y-%m-%d %H:%M:%S")

    for username in users:
        report_result = reportSingle(username, users[username][0])
        logs = updateLogs(logs, report_time, username, report_result)
        time.sleep(60)

    saveLogs(logs_path, logs)

    return True


def check_env(config_path, logs_path):
    try:
        users = getUsers(config_path)
        for username in users:
            int(username)
        logs = getLogs(logs_path)
        saveLogs(logs_path, logs)
    except Exception as e:
        print(e)
        return False
    return True


def main(config_path, logs_path):
    if not check_env(config_path, logs_path):
        print("请检查是否已正确修改配置文件，确保config.yaml与logs.json可读写")
        return False
    report_result = reportUsers(config_path, logs_path)
    if not report_result:
        print("填报失败，尝试重试")
    send_result = sendLogs(logs_path, config_path)
    if not send_result:
        print("Logs 发送失败，可能未配置key")
    print("填报成功")
