import sys
import os
import logging
from typing import List, Dict, Any, Tuple

from src.models import DNSRecord


def setup_logging(debug: bool = False) -> None:
    """设置日志"""
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def get_record_types() -> List[str]:
    """获取所有支持的DNS记录类型"""
    return [
        'A',
        'AAAA',
        'CNAME',
        'TXT',
        'MX',
        'NS',
        'SRV',
        'CAA',
        'PTR',
        'DNSKEY',
        'DS',
        'NAPTR',
        'SMIMEA',
        'SSHFP',
        'TLSA',
        'URI'
    ]


def format_ttl(ttl: int) -> str:
    """格式化TTL显示"""
    if ttl == 1:
        return "自动"
    elif ttl < 60:
        return f"{ttl}秒"
    elif ttl < 3600:
        minutes = ttl // 60
        return f"{minutes}分钟"
    elif ttl < 86400:
        hours = ttl // 3600
        return f"{hours}小时"
    else:
        days = ttl // 86400
        return f"{days}天"


def is_valid_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """验证记录数据的有效性"""
    required_fields = ['type', 'name', 'content']
    for field in required_fields:
        if not field in record or not record[field]:
            return False, f"缺少必填字段: {field}"
            
    record_type = record['type'].upper()
    
    # 验证记录类型
    if record_type not in get_record_types():
        return False, f"不支持的记录类型: {record_type}"
        
    # 验证特定记录类型的额外字段
    if record_type == 'MX' and not 'priority' in record:
        return False, "MX记录需要指定优先级(priority)"
        
    # 验证TTL值
    ttl = record.get('ttl', 1)
    if not isinstance(ttl, int) or ttl < 0:
        return False, "TTL必须是非负整数"
        
    return True, ""


def confirm_action(message: str) -> bool:
    """确认操作"""
    while True:
        response = input(f"{message} [y/n]: ").lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("请输入 y 或 n")


def ensure_config_dir_exists() -> str:
    """确保配置目录存在"""
    config_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config'
    )
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


