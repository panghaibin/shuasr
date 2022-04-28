# -*- coding: UTF-8 -*-
import hashlib
import os
import logging
from utils import abs_path, getUsers, login, html2JsLine, jsLine2Json, getSendApi, sendMsg, getTime

config = abs_path + '/pcr.yaml'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def get_last_pcr_result_md5():
    result_path = abs_path + '/pcr_result_md5.txt'
    if not os.path.exists(result_path):
        return None
    with open(result_path, 'r', encoding='utf-8') as f:
        last_pcr_result_md5 = f.read()
    return last_pcr_result_md5


def save_new_pcr_result_md5(pcr_result_md5):
    with open(abs_path + '/pcr_result_md5.txt', 'w', encoding='utf-8') as f:
        f.write(pcr_result_md5)


def check_PCR_result():
    users = getUsers(config)
    username = list(users.keys())[0]
    password = users[username][0]
    session = login(username, password)
    if not session:
        logging.info('登录失败')
        return False
    pcr_url = 'https://selfreport.shu.edu.cn/HSJC/JianKEDA.aspx'
    pcr_index = session.get(pcr_url).text
    pcr_line = html2JsLine(pcr_index)
    pcr_result = None
    for i, h in enumerate(pcr_line):
        if 'Panel1_P_HeSJCJL_HeSJCList' in h:
            pcr_result = jsLine2Json(pcr_line[i - 1])['F_Items']
            break
    if pcr_result is None:
        logging.info('获取PCR结果失败')
        return False
    last_pcr_result_md5 = get_last_pcr_result_md5()
    new_pcr_result_md5 = hashlib.md5(str(pcr_result).encode('utf-8')).hexdigest()
    if last_pcr_result_md5 == new_pcr_result_md5:
        logging.info('PCR结果未更新')
        return False
    updated_msg = 'PCR结果已更新'
    logging.info(updated_msg)
    send_api = getSendApi(config)
    now = getTime().strftime('%Y-%m-%d %H:%M:%S')
    send_result = sendMsg(updated_msg, now + '\n\n' + updated_msg, send_api['api'], send_api['key'])
    if send_result:
        logging.info('消息发送成功，更新核酸结果哈希值')
        save_new_pcr_result_md5(new_pcr_result_md5)
    else:
        logging.info('消息发送失败，未更新核酸结果哈希值')
    return True


if __name__ == '__main__':
    if check_PCR_result():
        exit(0)
    else:
        exit(1)
