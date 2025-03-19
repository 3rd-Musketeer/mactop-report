#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import csv
import time
import datetime
import sys
import subprocess
import signal

# 配置参数
PORT = 8888
METRICS_URL = f"http://localhost:{PORT}/metrics"  # mactop Prometheus 数据地址
CSV_FILENAME = "performance_data_coding_1.csv"
SAMPLE_INTERVAL = 0.5  # 采样间隔（秒），可根据需求调整
Mactop_CMD = ["mactop", "-p", f"{PORT}", "-i", "250"]  # 启动 mactop 的命令行参数

# 定义正则表达式，用于解析指标行
# 用于匹配格式：metric_name{labels} value 或 metric_name value
METRIC_PATTERN = re.compile(
    r'^(?P<metric_name>\w+)(?:\{(?P<labels>[^}]+)\})?\s+(?P<value>[-+]?[\d\.eE]+)$'
)

def start_mactop():
    """
    利用 subprocess 启动 mactop 程序，返回 Popen 对象。
    启动参数中：-p 指定 Prometheus 模式的端口；-i 指定更新间隔，单位毫秒。
    """
    try:
        # 启动 mactop 后台进程，并重定向其输出（可以根据需要重定向到 DEVNULL）
        proc = subprocess.Popen(Mactop_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 如果 mactop 需要一定的时间来启动，则这里可以等待数秒
        time.sleep(2)
        print("mactop 已启动，PID:", proc.pid)
        return proc
    except Exception as e:
        print("启动 mactop 出现错误:", e, file=sys.stderr)
        sys.exit(1)

def parse_metrics(text):
    """
    解析 Prometheus 格式的文本数据，返回一个包含目标字段值的字典。
    
    目标字段：
      - cpu_usage_percent
      - gpu_freq_mhz
      - gpu_usage_percent
      - memory_swap_total
      - memory_swap_used
      - memory_total
      - memory_used
      - power_cpu
      - power_gpu
      - power_total
    """
    results = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = METRIC_PATTERN.match(line)
        if match:
            metric_name = match.group("metric_name")
            labels_str = match.group("labels")
            try:
                value = float(match.group("value"))
            except ValueError:
                continue

            # 没有标签的指标
            if not labels_str:
                if metric_name == "mactop_cpu_usage_percent":
                    results["cpu_usage_percent"] = value
                elif metric_name == "mactop_gpu_freq_mhz":
                    results["gpu_freq_mhz"] = value
                elif metric_name == "mactop_gpu_usage_percent":
                    results["gpu_usage_percent"] = value
                else:
                    results[metric_name] = value
            else:
                # 解析标签，比如 'type="swap_total"' 或 'component="cpu"'
                label_parts = labels_str.split('=')
                if len(label_parts) == 2:
                    label_key = label_parts[0].strip()
                    label_value = label_parts[1].strip().strip('"')
                    if metric_name == "mactop_memory_gb" and label_key == "type":
                        if label_value == "swap_total":
                            results["memory_swap_total"] = value
                        elif label_value == "swap_used":
                            results["memory_swap_used"] = value
                        elif label_value == "total":
                            results["memory_total"] = value
                        elif label_value == "used":
                            results["memory_used"] = value
                    elif metric_name == "mactop_power_watts" and label_key == "component":
                        if label_value == "cpu":
                            results["power_cpu"] = value
                        elif label_value == "gpu":
                            results["power_gpu"] = value
                        elif label_value == "total":
                            results["power_total"] = value
                    else:
                        combined_key = f"{metric_name}_{label_key}_{label_value}"
                        results[combined_key] = value
    return results

def fetch_metrics():
    """发送 HTTP 请求获取指标数据"""
    try:
        response = requests.get(METRICS_URL, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"抓取指标数据出错: {e}", file=sys.stderr)
        return None

def write_csv_header_if_needed(filename, headers):
    """如 CSV 文件不存在，则写入表头"""
    try:
        with open(filename, "r") as f:
            pass
    except FileNotFoundError:
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

def main():
    # 自动启动 mactop
    # mactop_proc = start_mactop()

    # 定义 CSV 字段列表
    csv_fields = [
        "timestamp",
        "cpu_usage_percent",
        "gpu_freq_mhz",
        "gpu_usage_percent",
        "memory_swap_total",
        "memory_swap_used",
        "memory_total",
        "memory_used",
        "power_cpu",
        "power_gpu",
        "power_total",
    ]
    # 初始化 CSV 文件（写入表头，如不存在则创建）
    write_csv_header_if_needed(CSV_FILENAME, csv_fields)

    print("开始采集指标数据……")
    try:
        while True:
            timestamp = datetime.datetime.now().isoformat()
            content = fetch_metrics()
            if content:
                metrics = parse_metrics(content)
                # 补充时间戳字段
                metrics["timestamp"] = timestamp

                # 确保所有字段都有数据
                for field in csv_fields:
                    if field not in metrics:
                        metrics[field] = ""
                try:
                    with open(CSV_FILENAME, "a", newline="") as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
                        writer.writerow(metrics)
                        csvfile.flush()
                except Exception as e:
                    print(f"保存数据到 CSV 文件时出错: {e}", file=sys.stderr)

                print(f"采样时间 {timestamp}: {metrics}")
            else:
                print(f"采样时间 {timestamp}: 无数据可用")
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        print("检测到键盘中断，正在退出……")
    finally:
        # # 确保退出时终止 mactop 进程
        # if mactop_proc:
        #     print("终止 mactop 进程……")
        #     mactop_proc.terminate()
        #     try:
        #         mactop_proc.wait(timeout=5)
        #     except subprocess.TimeoutExpired:
        #         mactop_proc.kill()
        sys.exit(0)

if __name__ == "__main__":
    main()