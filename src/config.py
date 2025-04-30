import os
import yaml
import logging
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'config.yaml'
        )
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError:
            logging.warning(f"配置文件 {self.config_path} 不存在，将使用默认配置")
            return self._create_default_config()
        except yaml.YAMLError as e:
            logging.error(f"配置文件解析错误: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        default_config = {
            'auth': {
                'api_token': '',
                'api_key': '',
                'email': ''
            },
            'defaults': {
                'ttl': 1,
                'proxied': True
            },
            'ui': {
                'theme': 'dark',
                'records_per_page': 15
            }
        }
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # 保存默认配置
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False)
        except Exception as e:
            logging.error(f"无法写入默认配置: {e}")
            
        return default_config
    
    def save(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            logging.error(f"保存配置失败: {e}")
            return False
    
    def get_auth(self) -> Dict[str, str]:
        """获取认证信息"""
        return self.config.get('auth', {})
    
    def get_api_credentials(self) -> Dict[str, Optional[str]]:
        """获取API凭证"""
        auth = self.get_auth()
        return {
            'api_token': auth.get('api_token'),
            'api_key': auth.get('api_key'),
            'email': auth.get('email')
        }
        
    def get_defaults(self) -> Dict[str, Any]:
        """获取默认设置"""
        return self.config.get('defaults', {
            'ttl': 1,
            'proxied': True
        })
        
    def get_ui_settings(self) -> Dict[str, Any]:
        """获取UI设置"""
        return self.config.get('ui', {
            'theme': 'dark',
            'records_per_page': 15
        })

    def update_auth(self, api_token: str = None, api_key: str = None, email: str = None) -> None:
        """更新认证信息"""
        if 'auth' not in self.config:
            self.config['auth'] = {}
            
        if api_token:
            self.config['auth']['api_token'] = api_token
            
        if api_key:
            self.config['auth']['api_key'] = api_key
            
        if email:
            self.config['auth']['email'] = email
            
        self.save()


