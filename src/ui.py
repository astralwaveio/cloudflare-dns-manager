from textual.app import App
from textual.widgets import Header, Footer, Static, Button, DataTable, Input, Checkbox, Label
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.screen import Screen
from textual.reactive import Reactive
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual import events
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.console import Console

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Tuple

from src.models import Zone, DNSRecord
from src.api import CloudflareAPI, CloudflareAPIError
from src.config import ConfigManager
from src.utils import format_ttl, get_record_types

console = Console()


class ZoneScreen(Screen):
    """域名列表页面"""
    
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("r", "refresh_zones", "刷新"),
        Binding("a", "add_zone", "添加域名", show=False),  # Cloudflare API 不支持
    ]
    
    zones = Reactive([])
    is_loading = Reactive(False)
    
    def __init__(self, api: CloudflareAPI, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = api
        
    def compose(self):
        yield Header(show_clock=True)
        yield Container(
            Static(Panel(Align("加载中...", align="center"), title="Cloudflare 域名列表"), id="loading_panel"),
            Static(id="zones_panel"),
            id="content",
        )
        yield Footer()
        
    async def on_mount(self) -> None:
        """当屏幕挂载时加载区域"""
        self.loading = self.query_one("#loading_panel")
        self.zones_panel = self.query_one("#zones_panel")
        
        await self.refresh_zones()
    
    async def refresh_zones(self) -> None:
        """刷新区域列表"""
        self.is_loading = True
        self.loading.update(Panel(Align("正在加载域名列表...", align="center"), title="Cloudflare 域名列表"))
        self.zones_panel.update("")
        
        def get_zones():
            try:
                return self.api.get_zones(), None
            except CloudflareAPIError as e:
                return None, str(e)
        
        # 在后台线程中获取区域，避免阻塞UI
        zones, error = await asyncio.to_thread(get_zones)
        
        if error:
            self.loading.update(Panel(Align(f"[red]加载失败:[/] {error}\n\n按 [bold]R[/] 刷新", align="center"), title="错误"))
        else:
            self.zones = zones
            self.loading.update("")
            
            if not zones:
                self.zones_panel.update(Panel(Align("没有找到域名。请确认您的API权限和账户中是否有域名。", align="center"), title="无域名"))
            else:
                table = DataTable()
                table.cursor_type = "row"
                table.add_column("域名", width=40)
                table.add_column("状态", width=10)
                
                for zone in zones:
                    status = "[green]活跃[/]" if zone.status == "active" and not zone.paused else "[red]暂停[/]"
                    table.add_row(zone.name, status)
                
                self.zones_panel.update(Panel(table, title=f"域名列表 ({len(zones)}个)"))
                
        self.is_loading = False
    
    async def on_data_table_row_selected(self, event):
        """当选择一个区域时"""
        if self.is_loading or not self.zones:
            return
            
        row = event.data_table.cursor_row
        if 0 <= row < len(self.zones):
            selected_zone = self.zones[row]
            await self.app.push_screen(RecordsScreen(self.api, selected_zone))
    
    async def action_quit(self) -> None:
        """退出应用"""
        self.app.exit()
        
    async def action_refresh_zones(self) -> None:
        """刷新域名列表"""
        await self.refresh_zones()


class RecordsScreen(Screen):
    """DNS记录管理页面"""
    
    BINDINGS = [
        Binding("escape", "back", "返回"),
        Binding("r", "refresh_records", "刷新"),
        Binding("a", "add_record", "添加"),
        Binding("e", "edit_record", "编辑"),
        Binding("d", "delete_record", "删除"),
        Binding("b", "batch_delete", "批量删除"),
        Binding("f", "filter_records", "筛选"),
    ]
    
    records = Reactive([])
    is_loading = Reactive(False)
    filter_text = Reactive("")
    selected_records = Reactive([])  # 批量操作选择的记录
    
    def __init__(self, api: CloudflareAPI, zone: Zone, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = api
        self.zone = zone
        self.batch_mode = False
        
    def compose(self):
        yield Header(show_clock=True)
        yield Container(
            Static(id="filter_panel"),
            Static(Panel(Align("加载中...", align="center"), title=f"域名 {self.zone.name} 的DNS记录"), id="loading_panel"),
            Static(id="records_panel"),
            id="content",
        )
        yield Footer()
        
    async def on_mount(self) -> None:
        """当屏幕挂载时加载记录"""
        self.loading = self.query_one("#loading_panel")
        self.records_panel = self.query_one("#records_panel")
        self.filter_panel = self.query_one("#filter_panel")
        
        self.update_filter_panel()
        await self.refresh_records()
    
    def update_filter_panel(self) -> None:
        """更新筛选面板"""
        if not self.filter_text:
            self.filter_panel.update("")
        else:
            self.filter_panel.update(Panel(f"当前筛选: {self.filter_text}  [按F更改]", title="筛选"))
    
    async def refresh_records(self) -> None:
        """刷新记录列表"""
        self.is_loading = True
        self.loading.update(Panel(Align("正在加载DNS记录...", align="center"), title=f"域名 {self.zone.name} 的DNS记录"))
        self.records_panel.update("")
        
        params = {}
        if self.filter_text:
            params['name'] = self.filter_text
            
        def get_records():
            try:
                return self.api.get_dns_records(self.zone.id, params), None
            except CloudflareAPIError as e:
                return None, str(e)
        
        records, error = await asyncio.to_thread(get_records)
        
        if error:
            self.loading.update(Panel(Align(f"[red]加载失败:[/] {error}\n\n按 [bold]R[/] 刷新", align="center"), title="错误"))
        else:
            self.records = records
            self.loading.update("")
            
            if not records:
                msg = "没有找到DNS记录" if not self.filter_text else f"没有找到匹配 '{self.filter_text}' 的DNS记录"
                self.records_panel.update(Panel(Align(msg, align="center"), title="无记录"))
            else:
                title = f"DNS记录列表 ({len(records)}个)"
                if self.batch_mode:
                    title = f"批量操作模式 - 已选择 {len(self.selected_records)}/{len(records)} 个记录"
                
                table = DataTable()
                table.cursor_type = "row"
                
                # 如果在批量模式下，添加选择列
                if self.batch_mode:
                    table.add_column("选择", width=4)
                
                table.add_column("类型", width=8)
                table.add_column("名称", width=30)
                table.add_column("内容", width=30)
                table.add_column("TTL", width=10)
                table.add_column("代理", width=6)
                
                for record in records:
                    # 格式化显示
                    record_type = record.type
                    name = record.name
                    content = record.content
                    ttl = format_ttl(record.ttl)
                    proxied = "[blue]是[/]" if record.proxied else "否"
                    
                    # 添加行
                    if self.batch_mode:
                        selected = "✓" if record.id in self.selected_records else ""
                        table.add_row(selected, record_type, name, content, ttl, proxied)
                    else:
                        table.add_row(record_type, name, content, ttl, proxied)
                
                self.records_panel.update(Panel(table, title=title))
                
        self.is_loading = False
    
    async def on_data_table_row_selected(self, event):
        """当选择一条记录时"""
        if self.is_loading or not self.records:
            return
            
        row = event.data_table.cursor_row
        if 0 <= row < len(self.records):
            if self.batch_mode:
                # 切换选择状态
                record_id = self.records[row].id
                if record_id in self.selected_records:
                    self.selected_records.remove(record_id)
                else:
                    self.selected_records.append(record_id)
                await self.refresh_records()
            else:
                # 正常模式下编辑记录
                await self.action_edit_record()
    
    async def action_back(self) -> None:
        """返回上一级"""
        # 如果在批量模式，先退出批量模式
        if self.batch_mode:
            self.batch_mode = False
            self.selected_records = []
            await self.refresh_records()
        else:
            self.app.pop_screen()
        
    async def action_refresh_records(self) -> None:
        """刷新记录列表"""
        await self.refresh_records()
        
    async def action_add_record(self) -> None:
        """添加记录"""
        await self.app.push_screen(RecordFormScreen(
            self.api, 
            self.zone, 
            action="add",
            on_success=self.refresh_records
        ))
        
    async def action_edit_record(self) -> None:
        """编辑当前选择的记录"""
        if self.is_loading or self.batch_mode or not self.records:
            return
            
        table = self.records_panel.query_one(DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.records):
            return
            
        record = self.records[table.cursor_row]
        await self.app.push_screen(RecordFormScreen(
            self.api, 
            self.zone, 
            action="edit",
            record=record,
            on_success=self.refresh_records
        ))
        
    async def action_delete_record(self) -> None:
        """删除当前选择的记录"""
        if self.is_loading or self.batch_mode or not self.records:
            return
            
        table = self.records_panel.query_one(DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.records):
            return
            
        record = self.records[table.cursor_row]
        await self.app.push_screen(ConfirmScreen(
            f"确定要删除记录 {record.type} {record.name} 吗？",
            on_yes=self.delete_record(record)
        ))
        
    def delete_record(self, record: DNSRecord) -> Callable:
        """返回删除记录的函数"""
        async def do_delete():
            self.is_loading = True
            
            try:
                success = await asyncio.to_thread(
                    self.api.delete_record, 
                    record.zone_id or self.zone.id, 
                    record.id
                )
                
                if success:
                    await self.refresh_records()
                else:
                    self.loading.update(Panel("[red]删除失败[/]", title="错误"))
                    await asyncio.sleep(1.5)
                    self.loading.update("")
            except CloudflareAPIError as e:
                self.loading.update(Panel(f"[red]删除失败:[/] {e}", title="错误"))
                await asyncio.sleep(1.5)
                self.loading.update("")
                
            self.is_loading = False
        
        return do_delete
        
    async def action_batch_delete(self) -> None:
        """切换到批量删除模式"""
        if self.is_loading or not self.records:
            return
            
        if not self.batch_mode:
            self.batch_mode = True
            self.selected_records = []
            await self.refresh_records()
        elif self.selected_records:
            await self.app.push_screen(ConfirmScreen(
                f"确定要删除选中的 {len(self.selected_records)} 条记录吗？",
                on_yes=self.batch_delete_records
            ))
            
    async def batch_delete_records(self) -> None:
        """执行批量删除操作"""
        if not self.selected_records:
            return
            
        self.is_loading = True
        self.loading.update(Panel(Align("正在批量删除记录...", align="center"), title="请稍候"))
        
        try:
            success_ids, failed_ids = await asyncio.to_thread(
                self.api.batch_delete_records,
                self.zone.id,
                self.selected_records
            )
            
            if failed_ids:
                msg = f"删除结果: 成功 {len(success_ids)} 条, 失败 {len(failed_ids)} 条"
                self.loading.update(Panel(msg, title="部分删除成功"))
                await asyncio.sleep(2)
            
            self.batch_mode = False
            self.selected_records = []
            await self.refresh_records()
        except CloudflareAPIError as e:
            self.loading.update(Panel(f"[red]批量删除失败:[/] {e}", title="错误"))
            await asyncio.sleep(2)
            self.loading.update("")
            
        self.is_loading = False
        
    async def action_filter_records(self) -> None:
        """筛选记录"""
        await self.app.push_screen(FilterScreen(
            current_filter=self.filter_text,
            on_filter=self.apply_filter
        ))
        
    async def apply_filter(self, filter_text: str) -> None:
        """应用筛选"""
        self.filter_text = filter_text
        self.update_filter_panel()
        await self.refresh_records()


class RecordFormScreen(Screen):
    """记录添加/编辑表单"""
    
    BINDINGS = [
        Binding("escape", "cancel", "取消"),
        Binding("f1", "submit", "保存")
    ]
    
    def __init__(
        self, 
        api: CloudflareAPI, 
        zone: Zone, 
        action: str = "add", 
        record: DNSRecord = None,
        on_success: Callable = None,
        *args, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.api = api
        self.zone = zone
        self.action = action  # "add" 或 "edit"
        self.record = record
        self.on_success = on_success
        self.config = ConfigManager()
        self.defaults = self.config.get_defaults()
        
    def compose(self):
        yield Header(show_clock=True)
        
        # 初始值设置
        record_type = self.record.type if self.record else "A"
        name = self.record.name if self.record else ""
        content = self.record.content if self.record else ""
        ttl = self.record.ttl if self.record else self.defaults.get('ttl', 1)
        proxied = self.record.proxied if self.record is not None else self.defaults.get('proxied', True)
        
        # 移除域名后缀 (仅显示用)
        domain = self.zone.name
        if name.endswith(domain):
            name = name[:-len(domain)-1] or "@"  # 如果为空，显示为@
            
        title = "添加DNS记录" if self.action == "add" else "编辑DNS记录"
        
        yield Container(
            Vertical(
                Label("记录类型:"),
                Input(placeholder="记录类型", value=record_type, id="type"),
                Label("名称:"),
                Input(placeholder="名称 (@ 代表域名本身)", value=name, id="name"),
                Label("内容:"),
                Input(placeholder="内容", value=content, id="content"),
                Label("TTL:"),
                Input(placeholder="TTL (1=自动)", value=str(ttl), id="ttl"),
                Checkbox("启用Cloudflare代理 (橙云)", value=proxied, id="proxied"),
                Horizontal(
                    Button("保存", variant="primary", id="submit"),
                    Button("取消", id="cancel"),
                    classes="buttons",
                ),
                id="form",
            ),
            id="dialog",
        )
        
        yield Footer()
        
    async def on_button_pressed(self, event: events.ButtonPressed) -> None:
        """按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "cancel":
            self.app.pop_screen()
        elif button_id == "submit":
            await self.submit_form()
            
    async def action_cancel(self) -> None:
        """取消操作"""
        self.app.pop_screen()
        
    async def action_submit(self) -> None:
        """提交表单"""
        await self.submit_form()
            
    async def submit_form(self) -> None:
        """提交表单"""
        form = self.query_one("#form")
        
        # 获取表单数据
        record_type = form.query_one("#type").value.upper()
        raw_name = form.query_one("#name").value.strip()
        content = form.query_one("#content").value.strip()
        ttl_str = form.query_one("#ttl").value.strip()
        proxied = form.query_one("#proxied").value
        
        # 表单验证
        if not record_type or record_type not in get_record_types():
            await self.app.push_screen(MessageScreen(f"无效的记录类型: {record_type}"))
            return
            
        # 处理名称 - 如果是@，转换为域名本身
        name = raw_name
        if name == "@":
            name = self.zone.name
        # 如果没有以域名结尾，添加域名
        elif not name.endswith(self.zone.name):
            if name:
                name = f"{name}.{self.zone.name}"
            else:
                name = self.zone.name
                
        # 验证TTL
        try:
            ttl = int(ttl_str)
            if ttl < 0:
                raise ValueError("TTL必须是非负整数")
        except ValueError:
            await self.app.push_screen(MessageScreen("TTL必须是有效的整数值"))
            return
            
        # 验证内容
        if not content:
            await self.app.push_screen(MessageScreen("内容不能为空"))
            return
            
        # 创建或更新记录
        record = DNSRecord(
            type=record_type,
            name=name,
            content=content,
            ttl=ttl,
            proxied=proxied,
            id=self.record.id if self.record else None,
            zone_id=self.zone.id
        )
        
        # 执行API调用
        try:
            if self.action == "add":
                await asyncio.to_thread(self.api.add_record, self.zone.id, record)
            else:
                await asyncio.to_thread(
                    self.api.update_record, 
                    self.zone.id, 
                    self.record.id, 
                    record
                )
                
            self.app.pop_screen()
            
            # 如果提供了成功回调，调用它
            if self.on_success:
                await self.on_success()
                
        except CloudflareAPIError as e:
            await self.app.push_screen(MessageScreen(f"操作失败: {e}"))


class ConfirmScreen(Screen):
    """确认对话框"""
    
    def __init__(self, message: str, on_yes: Callable = None, on_no: Callable = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no
        
    def compose(self):
        yield Static(
            Panel(
                Vertical(
                    Static(self.message),
                    Horizontal(
                        Button("是", variant="error", id="yes"),
                        Button("否", variant="primary", id="no"),
                        classes="buttons",
                    ),
                ),
                title="确认",
            )
        )
        
    async def on_button_pressed(self, event: events.ButtonPressed) -> None:
        """按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "yes" and self.on_yes:
            self.app.pop_screen()
            await self.on_yes()
        else:
            self.app.pop_screen()
            if button_id == "no" and self.on_no:
                await self.on_no()


class MessageScreen(Screen):
    """消息对话框"""
    
    def __init__(self, message: str, title: str = "消息", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.title = title
        
    def compose(self):
        yield Static(
            Panel(
                Vertical(
                    Static(self.message),
                    Button("确定", variant="primary", id="ok"),
                ),
                title=self.title,
            )
        )
        
    async def on_button_pressed(self, event: events.ButtonPressed) -> None:
        """按钮点击事件"""
        self.app.pop_screen()


class FilterScreen(Screen):
    """筛选对话框"""
    
    def __init__(
        self, 
        current_filter: str = "", 
        on_filter: Callable[[str], None] = None, 
        *args, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.current_filter = current_filter
        self.on_filter = on_filter
        
    def compose(self):
        yield Static(
            Panel(
                Vertical(
                    Label("输入筛选条件 (域名或内容)"),
                    Input(placeholder="筛选条件", value=self.current_filter, id="filter"),
                    Horizontal(
                        Button("应用", variant="primary", id="apply"),
                        Button("清除", id="clear"),
                        Button("取消", id="cancel"),
                        classes="buttons",
                    ),
                ),
                title="筛选记录",
            )
        )
        
    async def on_button_pressed(self, event: events.ButtonPressed) -> None:
        """按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "apply":
            filter_text = self.query_one("#filter").value
            self.app.pop_screen()
            if self.on_filter:
                await self.on_filter(filter_text)
        elif button_id == "clear":
            self.app.pop_screen()
            if self.on_filter:
                await self.on_filter("")
        elif button_id == "cancel":
            self.app.pop_screen()


class InitScreen(Screen):
    """初始设置界面"""
    
    def __init__(self, config: ConfigManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.credentials = self.config.get_api_credentials()
        
    def compose(self):
        yield Header(show_clock=True)
        
        yield Container(
            Vertical(
                Label("欢迎使用 Cloudflare DNS 管理工具"),
                Label("请配置您的 Cloudflare API 认证信息:"),
                Label("选项1：API 令牌 (推荐)"),
                Input(
                    placeholder="API 令牌", 
                    value=self.credentials.get('api_token', ''),
                    password=True,
                    id="api_token"
                ),
                Label("或者 选项2：API 密钥 + 邮箱"),
                Input(
                    placeholder="Global API 密钥", 
                    value=self.credentials.get('api_key', ''),
                    password=True, 
                    id="api_key"
                ),
                Input(
                    placeholder="Cloudflare 账户邮箱", 
                    value=self.credentials.get('email', ''),
                    id="email"
                ),
                Horizontal(
                    Button("保存并继续", variant="primary", id="save"),
                    Button("退出", id="exit"),
                    classes="buttons",
                ),
                id="form",
            ),
            id="dialog",
        )
        
        yield Footer()
        
    async def on_button_pressed(self, event: events.ButtonPressed) -> None:
        """按钮点击事件"""
        button_id = event.button.id
        
        if button_id == "exit":
            self.app.exit()
        elif button_id == "save":
            await self.save_credentials()
            
    async def save_credentials(self) -> None:
        """保存凭证"""
        form = self.query_one("#form")
        
        api_token = form.query_one("#api_token").value.strip()
        api_key = form.query_one("#api_key").value.strip()
        email = form.query_one("#email").value.strip()
        
        # 验证输入
        if not api_token and not (api_key and email):
            await self.app.push_screen(MessageScreen(
                "请提供API令牌或API密钥+邮箱组合以继续",
                "验证错误"
            ))
            return
            
        # 更新配置
        self.config.update_auth(api_token=api_token, api_key=api_key, email=email)
        
        # 创建API客户端并验证
        api = CloudflareAPI(api_token=api_token, api_key=api_key, email=email)
        
        try:
            valid = await asyncio.to_thread(api.verify_token)
            if valid:
                # 认证成功，启动主界面
                await self.app.switch_screen(ZoneScreen(api))
            else:
                await self.app.push_screen(MessageScreen(
                    "API 认证失败。请检查您提供的凭据。",
                    "验证错误"
                ))
        except CloudflareAPIError as e:
            await self.app.push_screen(MessageScreen(
                f"API 认证失败: {e}",
                "验证错误"
            ))


class CloudflareDNSApp(App):
    """Cloudflare DNS管理应用主类"""
    
    TITLE = "Cloudflare DNS 管理"
    CSS_PATH = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = ConfigManager()
        
    async def on_mount(self) -> None:
        """应用启动时调用"""
        # 检查是否有配置文件和有效凭据
        credentials = self.config.get_api_credentials()
        has_token = bool(credentials.get('api_token'))
        has_key_email = bool(credentials.get('api_key') and credentials.get('email'))
        
        if has_token or has_key_email:
            # 有凭据，尝试认证并启动
            api = CloudflareAPI(
                api_token=credentials.get('api_token'),
                api_key=credentials.get('api_key'),
                email=credentials.get('email')
            )
            
            try:
                valid = await asyncio.to_thread(api.verify_token)
                if valid:
                    await self.push_screen(ZoneScreen(api))
                else:
                    await self.push_screen(InitScreen(self.config))
            except CloudflareAPIError:
                await self.push_screen(InitScreen(self.config))
        else:
            # 无凭据，显示设置界面
            await self.push_screen(InitScreen(self.config))




