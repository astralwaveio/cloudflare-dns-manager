from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class DNSRecord:
    """DNS 记录数据结构"""
    type: str
    name: str
    content: str
    ttl: int
    proxied: bool
    id: Optional[str] = None
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    created_on: Optional[str] = None
    modified_on: Optional[str] = None
    locked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """将记录转换为API需要的字典格式"""
        record_dict = {
            "type": self.type,
            "name": self.name,
            "content": self.content,
            "ttl": self.ttl,
            "proxied": self.proxied
        }
        return record_dict


@dataclass
class Zone:
    """Cloudflare 域名区域数据结构"""
    id: str
    name: str
    status: str
    paused: bool
    records: List[DNSRecord] = field(default_factory=list)


