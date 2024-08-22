from typing import Tuple, List, Dict, Any
from urllib.parse import urlencode

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.utils.http import RequestUtils


class IYUUChannel(CustomChannel):
    """
    爱语飞飞渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.iyuu"
    # 组件名称
    comp_name: str = "爱语飞飞"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 1

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {}

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取组件的配置表单
        :return: 配置表单, 建议的配置
        """
        # 建议的配置
        config_suggest = {}
        # 合并默认配置
        config_suggest.update(self.config_default)
        # elements
        row1 = {
            'component': 'VRow',
            'content': [{
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 12, 'xl': 12, 'lg': 12, 'md': 12, 'sm': 12, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'token',
                        'label': 'IYUU令牌',
                        'placeholder': 'IYUUxxx',
                        'hint': '必填。请前往爱语飞飞官网获取令牌：https://iyuu.cn'
                    }
                }]
            }]
        }
        row2 = self.build_notify_type_select_row_element()
        row3 = self.build_test_once_switch_row_element()
        elements = [row1, row2, row3]
        return elements, config_suggest

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}):
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type.value}, 消息类型不受支持")
            return
        token: str = self.get_config_item("token")
        if not token:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type.value}, 未配置Token")
            return
        query = urlencode({
            "text": title,
            "desp": text
        })
        send_url = f"https://iyuu.cn/{token}.send?{query}"
        res = RequestUtils(timeout=60).get_res(send_url)
        if res:
            if res.status_code == 200:
                res_json = res.json() or {}
                code = res_json.get("errcode")
                message = res_json.get("errmsg")
                if code == 0:
                    logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                else:
                    logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, 响应内容为空")
