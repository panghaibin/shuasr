# -*- coding: UTF-8 -*-
from utils import main, abs_path


if __name__ == '__main__':
    config = abs_path + '/config.yaml'
    logs = abs_path + '/logs.json'
    main(config, logs)
