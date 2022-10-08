import os
import re
import yaml
import json
import base64
import random
import logging
import datetime
from time import sleep
from utils import abs_path, login, html2JsLine, jsLine2Json, sendMsg, getTime, sleepCountdown

CONFIG_PATH = os.path.join(abs_path, 'apply.yaml')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class OutSchoolApply:
    def __init__(self, username, password):
        self.username = username
        self.id_masked = username[:1] + '*****' + username[-2:]
        self.password = password
        self.session = None
        self._login()

        self.apply_list = []
        self.today_day_str = getTime().strftime('%Y-%m-%d')
        self.tomorrow_day_str = (getTime() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.last_apply_info = {}
        self.to_post_form = {}

    def _login(self):
        self.session = login(self.username, self.password)
        if not self.session:
            logging.error(f'{self.id_masked}登录失败')
            return False
        return True

    def _get_apply_list(self):
        base_url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/'
        list_url = base_url + 'XueSLXSQ_List.aspx'
        resp = self.session.get(list_url)
        if resp.status_code != 200:
            logging.error(f'获取申请列表失败，用户名：{self.id_masked}')
            return False
        html = resp.text
        js_line = html2JsLine(html)
        apply_list = []
        for i, h in enumerate(js_line):
            if 'DataList1' in h:
                apply_list = jsLine2Json(js_line[i - 1])['F_Items']
                break
        if not apply_list:
            logging.info(f'{self.id_masked}没有申请记录')
            return False
        for i in apply_list:
            day_str = re.findall(r'\d{4}-\d{2}-\d{2}', i[1])[0]
            apply_url = base_url + i[4]
            self.apply_list.append((day_str, apply_url))
        self.apply_list.sort(key=lambda x: x[0], reverse=True)
        return self.apply_list

    def _check_tomorrow_apply(self):
        if self.apply_list[0][0] == self.tomorrow_day_str:
            logging.info(f'{self.id_masked}已有明日{self.tomorrow_day_str}的外出申请')
            return False
        return True

    def _get_last_apply_info(self):
        resp = self.session.get(self.apply_list[0][1])
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}获取上次申请信息失败，状态码{resp.status_code}')
            return False
        html = resp.text
        js_line = html2JsLine(html)

        campus = None
        reason = None
        more_reason = None
        province = None
        city = None
        county = None
        address = None
        back_today = None
        for i, h in enumerate(js_line):
            if 'SuoZX' in h:
                campus = jsLine2Json(js_line[i - 1])['Text']
            elif 'YuanYin' in h:
                reason = jsLine2Json(js_line[i - 1])['Text']
            elif 'TeSYY_QiTa' in h:
                try:
                    more_reason = jsLine2Json(js_line[i - 1])['Text']
                except (KeyError, json.decoder.JSONDecodeError):
                    more_reason = ''
            elif 'ddlSheng' in h:
                province = jsLine2Json(js_line[i - 1])['Text']
            elif 'ddlShi' in h:
                city = jsLine2Json(js_line[i - 1])['Text']
            elif 'ddlXian' in h:
                county = jsLine2Json(js_line[i - 1])['Text']
            elif 'XiangXDZ' in h:
                address = jsLine2Json(js_line[i - 1])['Text']
            elif 'DangTHX' in h:
                back_today = jsLine2Json(js_line[i - 1])['Text']
        if not all([campus, reason, province, city, county, address, back_today]):
            logging.error(f'{self.id_masked}获取上次申请信息失败')
            return False
        self.last_apply_info = dict(
            campus=campus,
            reason=reason,
            more_reason=more_reason,
            province=province,
            city=city,
            county=county,
            address=address,
            back_today=back_today
        )
        return self.last_apply_info

    def _generate_fstate(self):
        fstate_path = os.path.join(abs_path, 'apply.json')
        with open(fstate_path, 'r', encoding='utf-8') as f:
            fstate = json.load(f)

        fstate['persinfo_XueGH']['Text'] = self.username
        fstate['persinfo_SuoZXQ']['SelectedValue'] = self.last_apply_info['campus']
        fstate['persinfo_ChuXRQ']['Text'] = self.tomorrow_day_str
        fstate['persinfo_YuanYin']['SelectedValue'] = self.last_apply_info['reason']
        fstate['persinfo_ddlSheng']['SelectedValueArray'][0] = self.last_apply_info['province']
        fstate['persinfo_ddlShi']['SelectedValueArray'][0] = self.last_apply_info['city']
        fstate['persinfo_ddlXian']['SelectedValueArray'][0] = self.last_apply_info['county']
        fstate['persinfo_DangTHX']['SelectedValue'] = self.last_apply_info['back_today']

        b64_fstate = base64.b64encode(json.dumps(fstate).encode('utf-8')).decode('utf-8')
        return b64_fstate

    def _generate_form(self):
        url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSLXSQ.aspx'
        resp = self.session.get(url)
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}获取表单失败，状态码{resp.status_code}')
            return False
        html = resp.text
        view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', html).group(1)
        view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', html).group(1)

        self.to_post_form = {
            '__EVENTTARGET': 'persinfo$ctl01$btnSubmit',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': view_state,
            '__VIEWSTATEGENERATOR': view_state_generator,
            'persinfo$XiZhi': 'persinfo_XiZhi',
            'persinfo$SuoZXQ': '延长校区',
            'persinfo$ChuXRQ': self.tomorrow_day_str,
            'persinfo$YuanYin': self.last_apply_info['reason'],
            'persinfo$TeSYY_QiTa': self.last_apply_info['more_reason'],
            'persinfo$ddlSheng$Value': self.last_apply_info['province'],
            'persinfo$ddlSheng': self.last_apply_info['province'],
            'persinfo$ddlShi$Value': self.last_apply_info['city'],
            'persinfo$ddlShi': self.last_apply_info['city'],
            'persinfo$ddlXian$Value': self.last_apply_info['county'],
            'persinfo$ddlXian': self.last_apply_info['county'],
            'persinfo$XiangXDZ': self.last_apply_info['address'],
            'persinfo$DangTHX': self.last_apply_info['back_today'],
            'persinfo_ctl00_Collapsed': 'false',
            'persinfo_P_HeSJC_Collapsed': 'false',
            'persinfo_HuanCQTip_Collapsed': 'false',
            'persinfo_Collapsed': 'false',
            'F_STATE': self._generate_fstate(),
            'F_TARGET': 'persinfo_ctl01_btnSubmit',
        }
        return self.to_post_form

    def _post_form(self):
        fake_ip = '59.79.' + '.'.join(str(random.randint(0, 255)) for _ in range(2))
        headers = {
            'X-Forwarded-For': fake_ip,
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102"',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/102.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'text/plain, */*; q=0.01',
            'Referer': 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSLXSQ.aspx',
            'X-Requested-With': 'XMLHttpRequest',
            'X-FineUI-Ajax': 'true',
            'sec-ch-ua-platform': '"Windows"',
        }
        url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSLXSQ.aspx'
        resp = self.session.post(url, headers=headers, data=self.to_post_form)
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}提交申请失败，状态码{resp.status_code}')
            return f'状态码 {resp.status_code}'
        if '申请已提交' not in resp.text:
            try:
                msg = re.search(r'message:\'(.*?)\'', resp.text).group(1)
                logging.error(f'{self.id_masked}提交申请失败，返回信息：{msg}')
                return msg
            except Exception as e:
                logging.exception(e)
                logging.error(f'{self.id_masked}提交申请失败，返回未知信息\n'
                              f'{base64.b64encode(resp.text.encode("utf-8")).decode("utf-8")}')
                return resp.text
        return True

    def run(self):
        if not self.session:
            return -1, 'fail', '登录失败'
        if not self._get_apply_list():
            return -2, 'fail', '获取申请列表失败'
        if not self._check_tomorrow_apply():
            return -3, 'applied', '已申请明日出校'
        if not self._get_last_apply_info():
            return -4, 'fail', '获取上次申请信息失败'
        if not self._generate_form():
            return -5, 'fail', '生成表单失败'

        post_result = self._post_form()
        if type(post_result) == str:
            return -6, 'fail', f'提交申请失败，返回报错：{post_result}'

        sleep(5)
        apply_list = self._get_apply_list()
        if self.tomorrow_day_str != apply_list[0][0]:
            return -7, 'fail', '出校申请失败，提交后未在申请列表中找到明日出校'

        return 1, 'success', '提交成功'


class Main:
    def __init__(self):
        self.users = {}
        self.global_send = {}
        self._load_config()

        self.SUCCESS = []
        self.UPLOADED = []
        self.FAIL = []
        self.status_map = {
            'success': self.SUCCESS,
            'applied': self.UPLOADED,
            'fail': self.FAIL,
        }

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                self.users = config.get('users', [])
                self.global_send = config.get('global_send', {})
                if not self.users:
                    logging.error('未配置用户信息')
                    return False
            return True
        except Exception as e:
            logging.exception(e)
            logging.error(f'读取配置文件失败，尝试从环境变量读取')

        try:
            USERS = os.environ.get('APPLY_USERS').split(';')
            SEND = os.environ.get('APPLY_SEND', '').split(',')
            if not USERS:
                print('从环境变量获取用户出错，请尝试重新设置环境变量！')
                print('确保使用的是英文逗号和分号，且用户密码中也不包含英文逗号或分号')
                return False
            for user in USERS:
                _ = user.split(',')
                if len(_) == 2:
                    self.users.update({
                        _[0]: {
                            'password': _[1],
                            'api_type': 0,
                            'api_key': '',
                        },
                    })
                elif len(_) == 4:
                    self.users.update({
                        _[0]: {
                            'password': _[1],
                            'api_type': int(_[2]),
                            'api_key': _[3],
                        },
                    })
                else:
                    print('从环境变量解析用户失败！')
                    print('确保使用的是英文逗号和分号，且用户密码中也不包含英文逗号或分号')
                    print('注意分号仅在间隔多个用户时才需要使用，USERS变量设置的内容末尾不需要带上分号')
                    continue
            if len(SEND) == 2:
                self.global_send['api_type'] = int(SEND[0])
                self.global_send['api_key'] = SEND[1]
            return True
        except Exception as e:
            logging.exception(e)
            logging.error(f'读取环境变量失败')
            return False

    def run(self):
        users = self.users
        if not users:
            print('未配置用户信息')
            return False

        for i, j in enumerate(users.keys()):
            username = j
            password = users[j].get('password')
            api_type = users[j].get('api_type', 0)
            api_key = users[j].get('api_key', '')

            _, status, desp = OutSchoolApply(username, password).run()
            desp = f'{username} {desp}'
            self.status_map[status].append(desp)

            if api_type and api_type != 0 and api_key:
                title = '成功申请' if status == 'success' else ''
                title = '申请失败' if status == 'fail' else title
                title = '已申请过' if status == 'applied' else title
                title += '明日出校'
                desp = f'用户：{username}\n\n状态：{desp}'
                send_result = sendMsg(title, f'{desp}\n\n{random.randint(1000, 9999)}', api_type, api_key)
                logging.info(f'No.{i + 1}用户消息发送成功') if send_result else logging.info(f'No.{i + 1}用户消息发送失败')

            if i < len(users) - 1:
                sleep_time = random.randint(60, 90)
                sleepCountdown(sleep_time)

        if self.global_send.get('api_type', 0) != 0 and self.global_send.get('api_key'):
            title = '离校申请'
            title += f'{len(self.SUCCESS)}个成功' if self.SUCCESS else ''
            title += f'{len(self.UPLOADED)}个已申过' if self.UPLOADED else ''
            title += f'{len(self.FAIL)}个失败' if self.FAIL else ''
            desp = '\n\n'.join(self.SUCCESS + self.UPLOADED + self.FAIL)
            sleep(10)
            send_result = sendMsg(title, f'{desp}\n\n{random.randint(1000, 9999)}', self.global_send['api_type'],
                                  self.global_send['api_key'])
            logging.info('全局消息发送成功') if send_result else logging.info('全局消息发送失败')

        if len(self.FAIL):
            return False
        return True


if __name__ == '__main__':
    Main().run()
