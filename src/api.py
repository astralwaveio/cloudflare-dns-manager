import requests
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from src.models import Zone, DNSRecord


class CloudflareAPIError(Exception):
    """Cloudflare API 错误"""
    def __init__(self, message: str, errors: List = None):
        super().__init__(message)
        self.errors = errors or []


class CloudflareAPI:
    """Cloudflare API 客户端"""
    
    def __init__(self, api_token: str = None, api_key: str = None, email: str = None):
        self.api_token = api_token
        self.api_key = api_key
        self.email = email
        self.base_url = "https://api.cloudflare.com/client/v4"
        
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        headers = {
            'Content-Type': 'application/json'
        }
        
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        elif self.api_key and self.email:
            headers['X-Auth-Key'] = self.api_key
            headers['X-Auth-Email'] = self.email
        else:
            raise ValueError("需要提供 API 令牌或者 API 密钥 + 邮箱")
            
        return headers
    
    def _request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data
            )
            
            response_data = response.json()
            
            if response.status_code >= 400 or not response_data.get('success', False):
                errors = response_data.get('errors', [])
                error_msgs = [f"{e.get('code', '未知')}：{e.get('message', '未知错误')}" for e in errors]
                error_msg = "、".join(error_msgs) if error_msgs else "API调用失败"
                raise CloudflareAPIError(error_msg, errors)
                
            return response_data.get('result', {})
            
        except requests.RequestException as e:
            raise CloudflareAPIError(f"请求错误: {str(e)}")
    
    def get_zones(self) -> List[Zone]:
        """获取所有域名(zones)"""
        data = self._request('GET', '/zones')
        zones = []
        
        for zone_data in data:
            zone = Zone(
                id=zone_data['id'],
                name=zone_data['name'],
                status=zone_data['status'],
                paused=zone_data['paused']
            )
            zones.append(zone)
            
        return zones
    
    def get_zone_by_name(self, name: str) -> Optional[Zone]:
        """通过域名获取zone信息"""
        data = self._request('GET', '/zones', params={'name': name})
        
        if not data:
            return None
            
        zone_data = data[0]
        return Zone(
            id=zone_data['id'],
            name=zone_data['name'],
            status=zone_data['status'],
            paused=zone_data['paused']
        )
        
    def get_dns_records(self, zone_id: str, params: Dict = None) -> List[DNSRecord]:
        """获取特定域名的所有DNS记录"""
        data = self._request('GET', f'/zones/{zone_id}/dns_records', params=params)
        records = []
        
        for record_data in data:
            record = DNSRecord(
                id=record_data['id'],
                zone_id=zone_id,
                type=record_data['type'],
                name=record_data['name'],
                content=record_data['content'],
                ttl=record_data['ttl'],
                proxied=record_data.get('proxied', False),
                created_on=record_data.get('created_on'),
                modified_on=record_data.get('modified_on'),
                locked=record_data.get('locked', False)
            )
            records.append(record)
            
        return records
    
    def add_record(self, zone_id: str, record: DNSRecord) -> DNSRecord:
        """添加DNS记录"""
        data = self._request('POST', f'/zones/{zone_id}/dns_records', data=record.to_dict())
        
        return DNSRecord(
            id=data['id'],
            zone_id=zone_id,
            type=data['type'],
            name=data['name'],
            content=data['content'],
            ttl=data['ttl'],
            proxied=data.get('proxied', False),
            created_on=data.get('created_on'),
            modified_on=data.get('modified_on'),
            locked=data.get('locked', False)
        )
    
    def update_record(self, zone_id: str, record_id: str, record: DNSRecord) -> DNSRecord:
        """更新DNS记录"""
        data = self._request('PUT', f'/zones/{zone_id}/dns_records/{record_id}', data=record.to_dict())
        
        return DNSRecord(
            id=data['id'],
            zone_id=zone_id,
            type=data['type'],
            name=data['name'],
            content=data['content'],
            ttl=data['ttl'],
            proxied=data.get('proxied', False),
            created_on=data.get('created_on'),
            modified_on=data.get('modified_on'),
            locked=data.get('locked', False)
        )
        
    def delete_record(self, zone_id: str, record_id: str) -> bool:
        """删除DNS记录"""
        data = self._request('DELETE', f'/zones/{zone_id}/dns_records/{record_id}')
        return data.get('id') == record_id
        
    def batch_delete_records(self, zone_id: str, record_ids: List[str]) -> Tuple[List[str], List[str]]:
        """批量删除DNS记录"""
        success_ids = []
        failed_ids = []
        
        for record_id in record_ids:
            try:
                if self.delete_record(zone_id, record_id):
                    success_ids.append(record_id)
                else:
                    failed_ids.append(record_id)
            except CloudflareAPIError:
                failed_ids.append(record_id)
                
        return success_ids, failed_ids

    def verify_token(self) -> bool:
        """验证API密钥/令牌是否有效"""
        try:
            self._request('GET', '/user/tokens/verify')
            return True
        except CloudflareAPIError:
            return False



