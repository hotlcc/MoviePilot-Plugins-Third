from typing import Tuple, List, Dict, Any
import requests
from urllib.parse import quote
import json
from string import Template

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class HttpChannel(CustomChannel):
    """
    HTTP请求渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.http"
    # 组件名称
    comp_name: str = "HTTP请求"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 99

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "method": "get"
    }

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
                    'xxl': 2, 'xl': 2, 'lg': 2, 'md': 3, 'sm': 4, 'xs': 4
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'method',
                        'label': '请求方法',
                        'items': [
                            {'title': 'GET', 'value': 'get'},
                            {'title': 'POST', 'value': 'post'},
                            {'title': 'PUT', 'value': 'put'},
                        ],
                        'hint': '必填。http请求的方法。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 10, 'xl': 10, 'lg': 10, 'md': 9, 'sm': 8, 'xs': 8
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'url',
                        'label': '请求URL',
                        'hint': '必填。http请求url，支持模板变量替换。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextarea',
                    'props': {
                        'model': 'headers',
                        'label': '请求头',
                        'auto-grow': True,
                        'rows': 4,
                        'hint': '选填。http请求头，可填写json或者键值对；填键值对时key和value通过英文冒号:分隔，每行一个键值对；支持模板变量替换。',
                        'placeholder': 'json示例：\n'
                                       '{"key1": "value1", "key2": "value2"}\n\n'
                                       '键值对示例：\n'
                                       'key1:value1\n'
                                       'key2:value2'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextarea',
                    'props': {
                        'model': 'params',
                        'label': '请求参数',
                        'auto-grow': True,
                        'rows': 4,
                        'hint': '选填。http请求URL参数，可填写json或者键值对；填键值对时key和value通过英文冒号:分隔，每行一个键值对；支持模板变量替换。',
                        'placeholder': 'json示例：\n'
                                       '{"key1": "value1", "key2": "value2"}\n\n'
                                       '键值对示例：\n'
                                       'key1:value1\n'
                                       'key2:value2'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextarea',
                    'props': {
                        'model': 'body',
                        'label': '请求体',
                        'auto-grow': True,
                        'rows': 4,
                        'hint': '选填。http请求体；如果需要提交json、form表单等还需要配置相应的header；支持模板变量替换。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextarea',
                    'props': {
                        'model': 'template_variables',
                        'label': '自定义模板变量',
                        'auto-grow': True,
                        'rows': 4,
                        'hint': '选填。自定义模板变量，可填写json或者键值对；填键值对时key和value通过英文冒号:分隔，每行一个键值对。',
                        'placeholder': 'json示例：\n'
                                       '{"key1": "value1", "key2": "value2"}\n\n'
                                       '键值对示例：\n'
                                       'key1:value1\n'
                                       'key2:value2'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 2, 'xl': 2, 'lg': 2, 'md': 3, 'sm': 4, 'xs': 4
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'enable_proxy',
                        'label': '使用代理',
                        'hint': '发起http请求时是否使用网络代理。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 10, 'xl': 10, 'lg': 10, 'md': 9, 'sm': 8, 'xs': 8
                },
                'content': [{
                    'component': 'VAlert',
                    'props': {
                        'type': 'info',
                        'variant': 'tonal'
                    },
                    'text': '支持的模板变量见日志，使用时通过“${}”替换变量值，例如：${title}。'
                }]
            }]
        }
        row2 = self.build_notify_type_select_row_element()
        row3 = self.build_test_once_switch_row_element()
        elements = [row1, row2, row3]
        # 处理缺省配置
        self.save_default_config()
        return elements, config_suggest

    def __check_config(self) -> bool:
        """
        检查配置
        """
        if not self.get_config_item(config_key="method"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 请求方法无效")
            return False
        if not self.get_config_item(config_key="url"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 请求URL无效")
            return False
        return True

    @classmethod
    def __is_json(cls, s: str) -> bool:
        """
        判断字符串是否是json字符串
        """
        try:
            json.loads(s=s)
            return True
        except ValueError as e:
            return False

    @classmethod
    def __str_to_dict(cls, s: str) -> dict:
        """
        字符串（json或多行键值对）转字典
        """
        if not s:
            return {}
        # json
        if cls.__is_json(s=s):
            return json.loads(s=s)
        # 多行键值对
        result = {}
        for line in s.splitlines():
            if not line:
                continue
            if ":" not in line:
                continue
            key, value = line.split(":")
            if not key:
                continue
            result[key] = value
        return result

    def __get_template_variables(self, title: str, text: str, type: NotificationType, ext_info: dict) -> dict:
        """
        获取全部模板变量，包含预置的和自定义的
        """
        # 自定义的
        template_variables = self.get_config_item(config_key="template_variables")
        custom_template_variables = self.__str_to_dict(s=template_variables) or {}
        # 预置的
        preset_template_variables = ext_info.copy() if ext_info else {}
        preset_template_variables.update({
            "title": title,
            "text": text,
            "type": type.value if type else None
        })
        # 合并的
        result = custom_template_variables.copy()
        result.update(preset_template_variables)
        return result

    @classmethod
    def __parse_template_str(cls, s: str, template_variables: dict, url_encode: bool = False) -> str:
        """
        解析模板字符串
        """
        if not s or not template_variables:
            return s
        if url_encode:
            template_variables_temp = {}
            for key, value in template_variables.items():
                if not key:
                    continue
                if value != None:
                    value = quote(str(value))
                template_variables_temp[key] = value
            template_variables = template_variables_temp
        template = Template(s)
        return template.safe_substitute(template_variables)

    @classmethod
    def __get_dict_value_ignorecase(cls, data: Dict[str, any], key: str) -> any:
        """
        从词典中获取值，key大小写不敏感
        """
        if not data or not key:
            return None
        for k, v in data.items():
            if k and k.lower() == key.lower():
                return v
        return None

    def send_message(self, title: str, text: str, type: NotificationType = None, ext_info: dict = {}) -> bool:
        """
        发送消息
        """
        type_str = type.value if type else None
        enable_notify_types: List[str] = self.get_config_item("enable_notify_types")
        if (type and enable_notify_types and type.name not in enable_notify_types):
            logger.warn(f"发送消息中止: channel = {self.comp_name}, type = {type_str}, 消息类型不受支持")
            return False
        if not self.__check_config():
            return False
        # 模板变量
        template_variables = self.__get_template_variables(title=title, text=text, type=type, ext_info=ext_info)
        logger.info(f"HTTP请求 >>> 全部模板变量: {template_variables}")
        # 请求方法
        method = self.get_config_item(config_key="method")
        logger.info(f"HTTP请求 >>> 请求方法: {method}")
        # 请求URL
        url = self.get_config_item(config_key="url")
        url = self.__parse_template_str(s=url, template_variables=template_variables, url_encode=True)
        logger.info(f"HTTP请求 >>> 请求URL: {url}")
        # 请求头
        headers = self.get_config_item(config_key="headers")
        headers = self.__parse_template_str(s=headers, template_variables=template_variables)
        headers = self.__str_to_dict(s=headers)
        logger.info(f"HTTP请求 >>> 请求头: {headers}")
        # 请求参数
        params = self.get_config_item(config_key="params")
        params = self.__parse_template_str(s=params, template_variables=template_variables)
        params = self.__str_to_dict(s=params)
        logger.info(f"HTTP请求 >>> 请求参数: {params}")
        # 请求体
        body = self.get_config_item(config_key="body")
        body = self.__parse_template_str(s=body, template_variables=template_variables)
        logger.info(f"HTTP请求 >>> 请求体: {body}")
        is_json = self.__is_json(s=body)
        content_type = self.__get_dict_value_ignorecase(data=headers, key="Content-Type")
        if is_json and content_type == "application/json":
            body = json.dumps(json.loads(body))
        elif is_json and content_type == "application/x-www-form-urlencoded":
            body = json.loads(body)
        # 代理
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        # 发起请求
        res = requests.request(method=method, url=url, headers=headers, params=params, data=body, proxies=proxies)
        if res:
            if res.ok:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}, text = {res.text}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, 响应为空")
            return False
