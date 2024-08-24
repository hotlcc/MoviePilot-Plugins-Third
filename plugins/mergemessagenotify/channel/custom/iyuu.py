from typing import Tuple, List, Dict, Any
import requests

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger


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

    def __check_config(self) -> bool:
        """
        检查配置
        """
        if not self.get_config_item(config_key="token"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, IYUU令牌无效")
            return False
        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        token = self.get_config_item(config_key="token")
        return f"https://iyuu.cn/{token}.send"

    def __build_params(self, title: str, text: str) -> dict:
        """
        构造请求参数
        """
        # params
        params = {
            "text": title
        }
        # desp
        desp = text or title
        params["desp"] = desp
        return params

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}) -> bool:
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息类型不受支持")
            return False
        if not title:
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息标题为空")
            return False
        if not self.__check_config():
            return False
        send_url = self.__build_url()
        params = self.__build_params(title=title, text=text)
        res = requests.post(url=send_url, params=params)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("errcode")
            message = res_json.get("errmsg")
            if code == 0:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
