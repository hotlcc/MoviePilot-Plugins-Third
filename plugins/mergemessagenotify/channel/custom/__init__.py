from urllib.parse import quote

from app.plugins.mergemessagenotify.channel import Channel
from app.log import logger
from app.plugins.mergemessagenotify.util import TemplateUtil
from app.schemas.types import NotificationType


class CustomChannel(Channel):
    """
    自定义消息通知渠道基类
    """

    # 组件key
    comp_key: str = "custom"
    # 组件名称
    comp_name: str = ""
    # 组件顺序
    comp_order: int = 2

    def __build_test_once_switch_element(self) -> dict:
        """
        构造测试一次开关元素
        """
        return {
            'component': 'VSwitch',
            'props': {
                'model': 'test_once',
                'label': '测试一下',
                'hint': '保存后立即发送一条测试信息，仅生效一次。'
            }
        }

    def __build_test_once_switch_col_element(self) -> dict:
        """
        构造测试一次开关col元素
        """
        return {
            'component': 'VCol',
            'props': {
                'cols': 12,
                'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
            },
            'content': [self.__build_test_once_switch_element()]
        }

    def build_test_once_switch_row_element(self) -> dict:
        """
        构造测试一次开关行元素
        """
        return {
            'component': 'VRow',
            'content': [self.__build_test_once_switch_col_element()]
        }

    def __test_once(self, config: dict = None):
        """
        处理测试一次
        """
        if not self.check_stack_contain_save_config_request():
            return
        config = config or self.get_config() or {}
        if not config.get("test_once"):
            return
        try:
            self.send_message(title="测试消息", text="这是一条测试消息，您收到此消息表示您的渠道配置无误。")
            logger.info(f"测试一次消息发送完成 - {self.comp_name}")
        except Exception as e:
            logger.error(f"测试一次消息发送异常 - {self.comp_name}: {str(e)}", exc_info=True)
        finally:
            # 关闭一次性开关
            config['test_once'] = False
            self.update_config(config=config)

    def build_template_variables(self, title: str, text: str, type: NotificationType, ext_info: dict) -> dict:
        """
        构造模板变量
        """
        template_variables = ext_info.copy() if ext_info else {}
        template_variables.update({
            "title": title,
            "text": text,
            "type": type.value if type else None
        })
        return template_variables

    def __url_encode_dict_value(self, obj: dict) -> dict:
        """
        UrlEncode词典值
        """
        if not obj:
            return obj
        obj_temp = {}
        for key, value in obj.items():
            if not key:
                continue
            if value != None:
                value = quote(str(value))
            obj_temp[key] = value
        return obj_temp

    def render_template(self, text: str, variables: dict, url_encode: bool = False) -> str:
        """
        渲染模板
        """
        if url_encode:
            variables = self.__url_encode_dict_value(obj=variables)
        return TemplateUtil.render_text(text=text, variables=variables)

    def init_comp(self):
        """
        初始化组件
        """
        config = self.get_config() or {}
        # 处理测试一次
        self.__test_once(config=config)
