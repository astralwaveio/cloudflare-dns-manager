#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from pathlib import Path
from src.ui import CloudflareDNSApp
from src.api import CloudflareAPI
from src.config import ConfigManager
from src.utils import setup_logging


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Cloudflare DNS 管理工具")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志
    setup_logging(debug=args.debug)
    
    # 处理配置文件路径
    config_path = None
    if args.config:
        config_path = args.config
        if not os.path.exists(config_path):
            logging.error(f"配置文件不存在: {config_path}")
            return 1
            
    # 启动应用
    try:
        app = CloudflareDNSApp()
        app.run()
    except Exception as e:
        logging.error(f"应用运行失败: {e}")
        if args.debug:
            raise
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())


