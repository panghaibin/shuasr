#!/usr/bin/env bash
connect_times=0
while true; do
  openvpn --config ".github/vpn/config.ovpn" --log "vpn.log" --daemon
  connect_times=$((connect_times + 1))
  sleep 5
  test_times=0
  while true; do
    if ping -c1 xk.autoisp.shu.edu.cn; then
      echo "OpenVPN已成功连接"
      exit 0
    else
      test_times=$((test_times + 1))
      if [ $test_times -gt 15 ]; then
        echo "测试OpenVPN连接失败15次，将尝试重新连接......"
        if killall openvpn; then
          echo "已停止OpenVPN进程"
        else
          echo "停止OpenVPN进程失败"
        fi
        break
      fi
      sleep 2
    fi
  done

  if [ $connect_times -gt 3 ]; then
    echo "OpenVPN连接失败3次，将退出"
    exit 1
  fi

  if [ $connect_times -gt 1 ]; then
    sleep_time=$((RANDOM % 240 + 60))
  else
    sleep_time=$((RANDOM % 900 + 300))
  fi
  echo "开始休眠 $sleep_time 秒"
  for ((i = 0; i < sleep_time; i = i + 10)); do
    echo -ne "休眠剩余：$((sleep_time - i))         \r"
    sleep 10
  done
done
