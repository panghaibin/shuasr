# -*- coding: UTF-8 -*-
import sys

from utils import abs_path, main, test, addUser, setSCKey


if __name__ == '__main__':
    config = abs_path + '/config.yaml'
    logs = abs_path + '/logs.json'
    if len(sys.argv) == 1:
        main(config, logs)
    elif len(sys.argv) == 2:
        if sys.argv[1] == 'test':
            test(config, logs)
        elif sys.argv[1] == 'add':
            addUser(config)
        elif sys.argv[1] == 'sckey':
            setSCKey(config)
        else:
            print('未定义的参数：%s' % sys.argv[1])
    else:
        print('未定义的参数')
