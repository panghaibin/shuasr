import os
import re
import yaml
import json
import base64
import random
import logging
import requests
import datetime
from time import sleep
from utils import abs_path, login, html2JsLine, jsLine2Json, sendMsg, getTime, sleepCountdown, generateXingImage, \
    convertAddress

CONFIG_PATH = os.path.join(abs_path, 'apply.yaml')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class OutSchoolApply:
    def __init__(self, session: requests.Session, username: str):
        self.username = username
        self.id_masked = username[:1] + '*****' + username[-2:]
        self.session = session

        self.apply_list = []
        self.today_day_str = getTime().strftime('%Y-%m-%d')
        self.tomorrow_day_str = (getTime() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.last_apply_info = {}
        self.to_post_form = {}

    def _get_apply_list(self):
        base_url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/'
        list_url = base_url + 'XueSLXSQ_List.aspx'
        resp = self.session.get(list_url)
        if resp.status_code != 200:
            logging.error(f'获取进校申请列表失败，用户名：{self.id_masked}')
            return False
        html = resp.text
        js_line = html2JsLine(html)
        apply_list = []
        for i, h in enumerate(js_line):
            if 'DataList1' in h:
                apply_list = jsLine2Json(js_line[i - 1])['F_Items']
                break
        if not apply_list:
            logging.info(f'{self.id_masked}没有离校申请记录')
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
            logging.error(f'{self.id_masked}获取上次离校申请信息失败，状态码{resp.status_code}')
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
            logging.error(f'{self.id_masked}获取上次离校申请信息失败')
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
        fstate_path = os.path.join(abs_path, 'out_apply.json')
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
            'persinfo$SuoZXQ': self.last_apply_info['campus'],
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
            logging.error(f'{self.id_masked}提交离校申请失败，状态码{resp.status_code}')
            return f'状态码 {resp.status_code}'
        if '申请已提交' not in resp.text:
            try:
                msg = re.search(r'message:\'(.*?)\'', resp.text).group(1)
                logging.error(f'{self.id_masked}提交离校申请失败，返回信息：{msg}')
                return msg
            except Exception as e:
                logging.exception(e)
                logging.error(f'{self.id_masked}提交离校申请失败，返回未知信息\n'
                              f'{base64.b64encode(resp.text.encode("utf-8")).decode("utf-8")}')
                return resp.text
        return True

    def run(self):
        if not self.session:
            return -1, 'fail', '登录失败'
        if not self._get_apply_list():
            return -2, 'fail', '获取离校申请列表失败'
        if not self._check_tomorrow_apply():
            return -3, 'applied', '已申请明日出校'
        if not self._get_last_apply_info():
            return -4, 'fail', '获取上次离校申请信息失败'
        if not self._generate_form():
            return -5, 'fail', '生成表单失败'

        post_result = self._post_form()
        if type(post_result) == str:
            return -6, 'fail', f'提交离校申请失败，返回报错：{post_result}'

        sleep(5)
        apply_list = self._get_apply_list()
        if self.tomorrow_day_str != apply_list[0][0]:
            return -7, 'fail', '出校申请失败，提交后未在申请列表中找到明日出校'

        return 1, 'success', '离校提交成功'


class InSchoolApply:
    def __init__(self, session: requests.Session, username: str):
        self.username = username
        self.id_masked = username[:1] + '*****' + username[-2:]
        self.session = session

        self.apply_list = []
        self.today_day_str = getTime().strftime('%Y-%m-%d')
        self.tomorrow_day_str = (getTime() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.last_apply_info = {}
        self.to_post_form = {}

    def _get_apply_list(self):
        base_url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/'
        list_url = base_url + 'XueSJXSQ_List.aspx'
        resp = self.session.get(list_url)
        if resp.status_code != 200:
            logging.error(f'获取进校申请列表失败，用户名：{self.id_masked}')
            return False
        html = resp.text
        js_line = html2JsLine(html)
        apply_list = []
        for i, h in enumerate(js_line):
            if 'DataList1' in h:
                apply_list = jsLine2Json(js_line[i - 1])['F_Items']
                break
        if not apply_list:
            logging.info(f'{self.id_masked}没有进校申请记录')
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

    def update_view_state(self):
        url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSJXSQ.aspx'
        resp = self.session.get(url)
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}获取VS失败，状态码{resp.status_code}')
            return False
        html = resp.text
        view_state = re.search(r'id="__VIEWSTATE" value="(.*?)" /', html).group(1)
        view_state_generator = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)" /', html).group(1)
        self.to_post_form.update({
            '__VIEWSTATE': view_state,
            '__VIEWSTATEGENERATOR': view_state_generator,
        })
        return view_state, view_state_generator

    def _get_last_apply_info(self):
        resp = self.session.get(self.apply_list[0][1])
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}获取上次进校申请信息失败，状态码{resp.status_code}')
            return False
        html = resp.text
        js_line = html2JsLine(html)

        campus = None
        reason = None
        more_reason = None
        province = None
        city = None
        county = None
        street = None
        address = None
        for i, h in enumerate(js_line):
            if 'JinXXQ' in h:
                campus = jsLine2Json(js_line[i - 1])['Text']
            elif 'YuanYin' in h and 'QiTa' not in h:
                reason = jsLine2Json(js_line[i - 1])['Text']
            elif 'YuanYin_QiTa' in h:
                try:
                    more_reason = jsLine2Json(js_line[i - 1])['Text']
                except (KeyError, json.decoder.JSONDecodeError):
                    more_reason = ''
            elif 'Sheng' in h:
                province = jsLine2Json(js_line[i - 1])['Text']
            elif 'Shi' in h:
                city = jsLine2Json(js_line[i - 1])['Text']
            elif 'Xian' in h and 'XiangXDZ' not in h:
                county = jsLine2Json(js_line[i - 1])['Text']
            elif 'JieDao' in h:
                street = jsLine2Json(js_line[i - 1])['Text']
            elif 'XiangXDZ' in h:
                address = jsLine2Json(js_line[i - 1])['Text']
        if not all([campus, reason, province, city, county, street, address]):
            logging.error(f'{self.id_masked}获取上次进校申请信息失败')
            return False
        self.last_apply_info.update({
            'campus': campus,
            'reason': reason,
            'more_reason': more_reason,
            'province': province,
            'city': city,
            'county': county,
            'street': street,
            'address': address
        })
        self._get_campus_district()
        return self.last_apply_info

    def _get_campus_district(self):
        # 申请历史里不能查看上次选择的进校片区，默认选最后一个
        if self.last_apply_info['campus'] == '宝山校区':
            district_list = [["东区", "东区", 1], ["南区", "南区", 1], ["新世纪", "新世纪", 1], ["校内", "校内", 1]]
        elif self.last_apply_info['campus'] == '嘉定校区':
            district_list = [["校内", "校内", 1]]
        elif self.last_apply_info['campus'] == '延长校区':
            district_list = [["东部", "东部", 1], ["西部", "西部", 1], ["北部", "北部", 1]]
        else:
            return
        self.last_apply_info.update({
            'district': district_list[-1][0],
            'district_list': district_list
        })

    def _upload_xing_img(self):
        p_info_url = 'https://selfreport.shu.edu.cn/PersonInfo.aspx'
        p_info_html = self.session.get(url=p_info_url).text
        p_info_line = html2JsLine(p_info_html)

        phone_number = '13888885174'
        for i, h in enumerate(p_info_line):
            if 'ShouJHM' in h:
                phone_number = jsLine2Json(p_info_line[i - 1])['Text']
                break

        view_state, view_state_generator = self.update_view_state()
        url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSJXSQ.aspx'

        position = convertAddress(self.last_apply_info['province'], self.last_apply_info['city'])
        xing_img_path = generateXingImage(phone_number, position)
        img_upload = open(xing_img_path, 'rb')
        data = {
            'p1$BaoSRQ': getTime().strftime("%Y-%m-%d"),
            "__EVENTTARGET": "persinfo$Panel2$fileXingCM",
            '__VIEWSTATE': view_state,
            "__VIEWSTATEGENERATOR": view_state_generator,
            "persinfo$Panel1$HFimgHeSJC1_BG": "",
            "persinfo$Panel2$HFimgXingCM": "",
            "persinfo_ctl00_Collapsed": "false",
            "persinfo_ctl01_Collapsed": "false",
            "persinfo_P_HeSJC_Collapsed": "false",
            "persinfo_P_ChuFD_Collapsed": "false",
            "persinfo_Panel1_Collapsed": "false",
            "persinfo_Panel2_Collapsed": "false",
            "persinfo_Collapsed": "false",
            'X-FineUI-Ajax': 'true',
        }
        file = {
            'persinfo$Panel2$fileXingCM': img_upload,
        }
        upload_result = self.session.post(url=url, data=data, files=file).text
        img_upload.close()

        _ = re.search(r'Text&quot;:&quot;(.*?)&quot;}\)', upload_result)
        xing_code = None if _ is None else _.group(1)
        _ = re.search(r'ImageUrl&quot;:&quot;(.*?)&quot;}\)', upload_result)
        xing_img = None if _ is None else _.group(1)
        if xing_code is None or xing_img is None:
            logging.error('上传XC码失败')

        os.remove(xing_img_path)
        self.last_apply_info.update({
            'xing_code': xing_code,
            'xing_img': xing_img
        })
        return self.last_apply_info

    def _generate_fstate(self):
        fstate_path = os.path.join(abs_path, 'in_apply.json')
        with open(fstate_path, 'r', encoding='utf-8') as f:
            fstate = json.load(f)

        fstate['persinfo_XueGH']['Text'] = self.username
        fstate['persinfo_ChuFRQ']['Text'] = self.tomorrow_day_str
        fstate['persinfo_JinXRQ']['Text'] = self.tomorrow_day_str
        fstate['persinfo_JinXXQ']['SelectedValue'] = self.last_apply_info['campus']
        fstate['persinfo_PianQu']['F_Items'] = self.last_apply_info['district_list']
        fstate['persinfo_PianQu']['SelectedValue'] = self.last_apply_info['district']

        fstate['persinfo_YuanYin']['SelectedValue'] = self.last_apply_info['reason']
        fstate['persinfo_YuanYin_QiTa']['Text'] = self.last_apply_info['more_reason']

        fstate['persinfo_P_ChuFD_DangQSZD_Sheng']['SelectedValueArray'][0] = self.last_apply_info['province']
        fstate['persinfo_P_ChuFD_DangQSZD_Shi']['SelectedValueArray'][0] = self.last_apply_info['city']
        fstate['persinfo_P_ChuFD_DangQSZD_Xian']['SelectedValueArray'][0] = self.last_apply_info['county']
        fstate['persinfo_P_ChuFD_DangQSZD_JieDao']['SelectedValueArray'][0] = self.last_apply_info['street']
        fstate['persinfo_P_ChuFD_DangQSZD_JieDao']['F_Items'][1][0] = self.last_apply_info['street']
        fstate['persinfo_P_ChuFD_DangQSZD_JieDao']['F_Items'][1][1] = self.last_apply_info['street']
        fstate['persinfo_P_ChuFD_DangQSZD_JieDao']['F_Items'][1][3] = self.last_apply_info['street']
        fstate['persinfo_P_ChuFD_DangQSZD_XiangXDZ']['Text'] = self.last_apply_info['address']

        fstate['persinfo_Panel2_HFimgXingCM']['Text'] = self.last_apply_info['xing_code']
        fstate['persinfo_Panel2_imgXingCM']['ImageUrl'] = self.last_apply_info['xing_img']

        b64_fstate = base64.b64encode(json.dumps(fstate).encode('utf-8')).decode('utf-8')
        return b64_fstate

    def _generate_form(self):
        view_state, view_state_generator = self.update_view_state()

        self.to_post_form = {
            "__EVENTTARGET": "persinfo$ctl02$btnSubmit",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": view_state,
            "__VIEWSTATEGENERATOR": view_state_generator,
            "persinfo$XiZhi": "persinfo_XiZhi",
            "persinfo$ChuFRQ": self.tomorrow_day_str,
            "persinfo$JinXRQ": self.tomorrow_day_str,
            "persinfo$YiLCS": "否",
            "persinfo$QianYTZXW": "否",
            "persinfo$JinXXQ": self.last_apply_info['campus'],
            "persinfo$PianQu": self.last_apply_info['district'],
            "persinfo$YuanYin": self.last_apply_info['reason'],
            "persinfo$YuanYin_QiTa": self.last_apply_info['more_reason'],
            "persinfo$DangTLX": "否",
            "persinfo$GeLD": "否",
            "persinfo$P_ChuFD$DangQSZD_Sheng$Value": self.last_apply_info['province'],
            "persinfo$P_ChuFD$DangQSZD_Sheng": self.last_apply_info['province'],
            "persinfo$P_ChuFD$DangQSZD_Shi$Value": self.last_apply_info['city'],
            "persinfo$P_ChuFD$DangQSZD_Shi": self.last_apply_info['city'],
            "persinfo$P_ChuFD$DangQSZD_Xian$Value": self.last_apply_info['county'],
            "persinfo$P_ChuFD$DangQSZD_Xian": self.last_apply_info['county'],
            "persinfo$P_ChuFD$DangQSZD_JieDao$Value": self.last_apply_info['street'],
            "persinfo$P_ChuFD$DangQSZD_JieDao": self.last_apply_info['street'],
            "persinfo$P_ChuFD$DangQSZD_XiangXDZ": self.last_apply_info['address'],
            "persinfo$Panel1$HFimgHeSJC1_BG": "",
            "persinfo$Panel2$HFimgXingCM": self.last_apply_info['xing_code'],
            "persinfo_ctl00_Collapsed": "false",
            "persinfo_ctl01_Collapsed": "false",
            "persinfo_P_HeSJC_Collapsed": "false",
            "persinfo_P_ChuFD_Collapsed": "false",
            "persinfo_Panel1_Collapsed": "false",
            "persinfo_Panel2_Collapsed": "false",
            "persinfo_Collapsed": "false",
            "F_STATE": self._generate_fstate(),
            "F_TARGET": "persinfo_ctl02_btnSubmit",
            "X-FineUI-Ajax": "true",
        }
        return self.to_post_form

    def _post_form(self):
        fake_ip = '59.79.' + '.'.join(str(random.randint(0, 255)) for _ in range(2))
        headers = {
            'X-Forwarded-For': fake_ip,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,und;q=0.7,ja;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': 'https://selfreport.shu.edu.cn',
            'Pragma': 'no-cache',
            'Referer': 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSJXSQ.aspx',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/102.0.0.0 Safari/537.36',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        url = 'https://selfreport.shu.edu.cn/XiaoYJC202207/XueSJXSQ.aspx'
        resp = self.session.post(url, headers=headers, data=self.to_post_form)
        if resp.status_code != 200:
            logging.error(f'{self.id_masked}提交进校申请失败，状态码{resp.status_code}')
            return f'状态码 {resp.status_code}'
        if '有点忙' in resp.text:
            for i in range(3):
                print(f'{self.id_masked}提交进校申请失败，有点忙，正在重试第{i + 1}次')
                sleep(5)
                self.update_view_state()
                resp = self.session.post(url, headers=headers, data=self.to_post_form)
                if '有点忙' not in resp.text:
                    break
        if '申请已提交' not in resp.text:
            try:
                msg = re.search(r'message:\'(.*?)\'', resp.text).group(1)
                logging.error(f'{self.id_masked}提交进校申请失败，返回信息：{msg}')
                return msg
            except Exception as e:
                logging.exception(e)
                logging.error(f'{self.id_masked}提交进校申请失败，返回未知信息\n'
                              f'{base64.b64encode(resp.text.encode("utf-8")).decode("utf-8")}')
                return resp.text
        return True

    def run(self):
        if not self.session:
            return -1, 'fail', '登录失败'
        if not self._get_apply_list():
            return -2, 'fail', '获取进校申请列表失败'
        if not self._check_tomorrow_apply():
            return -3, 'applied', '已申请明日进校'
        if not self._get_last_apply_info():
            return -4, 'fail', '获取上次进校申请信息失败'
        if not self._upload_xing_img():
            return -5, 'fail', '上传XC码失败'
        if not self._generate_form():
            return -6, 'fail', '生成表单失败'

        sleep(5)
        post_result = self._post_form()
        if type(post_result) == str:
            return -7, 'fail', f'提交进校申请失败，返回报错：{post_result}'

        sleep(5)
        apply_list = self._get_apply_list()
        if self.tomorrow_day_str != apply_list[0][0]:
            return -8, 'fail', '进校申请失败，提交后未在申请列表中找到明日进校'

        return 1, 'success', '进校提交成功'


class InOutSchoolApply:
    def __init__(self, username: str, password: str):
        self.username = username
        self.id_masked = username[:1] + '*****' + username[-2:]
        self.password = password
        self.session = None
        self._login()

    def _login(self):
        self.session = login(self.username, self.password)
        if not self.session:
            logging.error(f'{self.id_masked}登录失败')
            return False
        return True

    def run_out(self):
        out = OutSchoolApply(self.session, self.username)
        return out.run()

    def run_in(self):
        in_ = InSchoolApply(self.session, self.username)
        return in_.run()


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
                if _[2] == 'in':
                    apply_in = True
                    apply_out = False
                elif _[2] == 'out':
                    apply_in = False
                    apply_out = True
                elif _[2] == 'all':
                    apply_in = True
                    apply_out = True
                else:
                    print('未知的进出校申请类型')
                    continue
                if len(_) == 3:
                    self.users.update({
                        _[0]: {
                            'password': _[1],
                            'apply_in': apply_in,
                            'apply_out': apply_out,
                            'api_type': 0,
                            'api_key': '',
                        },
                    })
                elif len(_) == 5:
                    self.users.update({
                        _[0]: {
                            'password': _[1],
                            'apply_in': apply_in,
                            'apply_out': apply_out,
                            'api_type': int(_[3]),
                            'api_key': _[4],
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
            apply_in = users[j].get('apply_in', False)
            apply_out = users[j].get('apply_out', False)
            if not apply_in and not apply_out:
                logging.info(f'有用户未配置进出校申请类型')
                continue

            if apply_in:
                _, status_in, desp_in = InOutSchoolApply(username, password).run_in()
                self.status_map[status_in].append(f'{username} {desp_in}')
            else:
                status_in = 'skip'
                desp_in = '未申请进校'
            if apply_out:
                _, status_out, desp_out = InOutSchoolApply(username, password).run_out()
                self.status_map[status_out].append(f'{username} {desp_out}')
            else:
                status_out = 'skip'
                desp_out = '未申请出校'

            if api_type and api_type != 0 and api_key:
                title = ''
                if apply_in:
                    title = '成功申请' if status_in == 'success' else title
                    title = '申请失败' if status_in == 'fail' else title
                    title = '已申请过' if status_in == 'applied' else title
                    title += '明日进校'
                if apply_out:
                    title = '成功申请' if status_out == 'success' else title
                    title = '申请失败' if status_out == 'fail' else title
                    title = '已申请过' if status_out == 'applied' else title
                    title += '明日出校'
                desp = f'用户：{username}\n\n状态：{desp_in}\n\n{desp_out}'
                send_result = sendMsg(title, f'{desp}\n\n{random.randint(1000, 9999)}', api_type, api_key)
                logging.info(f'No.{i + 1}用户消息发送成功') if send_result else logging.info(f'No.{i + 1}用户消息发送失败')

            if i < len(users) - 1:
                sleep_time = random.randint(60, 90)
                sleepCountdown(sleep_time)

        if self.global_send.get('api_type', 0) != 0 and self.global_send.get('api_key'):
            title = '进出校申请'
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
