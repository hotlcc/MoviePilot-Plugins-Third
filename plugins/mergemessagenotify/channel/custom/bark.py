import base64
from typing import Tuple, List, Dict, Any
from enum import Enum
import requests
import json as lib_json

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as lib_padding
from cryptography.exceptions import InvalidTag

from app.plugins.mergemessagenotify.channel.custom import CustomChannel
from app.schemas.types import NotificationType
from app.log import logger
from app.core.config import settings


class Sound(Enum):
    """
    铃声枚举
    """

    alarm = (2)
    anticipate = (4.5)
    bell = (1.4)
    birdsong = (0.67)
    bloom = (1.6)
    calypso = (0.9)
    chime = (4.5)
    choo = (2.2)
    descent = (1.9)
    electronic = (1.5)
    fanfare = (1.5)
    glass = (1.7)
    gotosleep = (3)
    healthnotification = (1.8)
    horn = (1.5)
    ladder = (1.3)
    mailsent = (1.5)
    minuet = (7)
    multiwayinvitation = (2.2)
    newmail = (1.5)
    newsflash = (2.9)
    noir = (1.9)
    paymentsuccess = (1.4)
    shake = (0.6)
    sherwoodforest = (4.7)
    silence = (0.5)
    spell = (2.9)
    suspense = (4.2)
    telegraph = (1.2)
    tiptoes = (1.5)
    typewriters = (2.6)
    update = (4.5)

    def __init__(self, second: float):
        """
        :param second: 时长
        """
        self.second = second


class BarkChannel(CustomChannel):
    """
    Bark渠道
    """

    # 组件key
    comp_key: str = f"{CustomChannel.comp_key}.bark"
    # 组件名称
    comp_name: str = "Bark"
    # 组件顺序
    comp_order: int = CustomChannel.comp_order * 100 + 2

    # 支持的加密算法
    support_cipher_algorithms = ["AES128", "AES192", "AES256"]
    # 支持的加密模式
    support_cipher_modes = ["CBC", "ECB", "GCM"]
    # 支持的加密填充
    support_cipher_paddings = ["noPadding", "pkcs7"]

    # 配置相关
    # 组件缺省配置
    config_default: Dict[str, Any] = {
        "server_url": "https://api.day.app",

        "cipher_algorithm": "AES256",
        "cipher_mode": "GCM",
        "cipher_padding": "noPadding",

        "group": "MoviePilot",
        "level": "active",
        "isArchive": True,
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
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'server_url',
                        'label': '服务器地址',
                        'placeholder': 'https://api.day.app',
                        'hint': '必填。缺省时为官方地址：https://api.day.app'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'push_key',
                        'label': '推送密钥',
                        'hint': '必填。推送密钥'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': '_config_cipher_dialog_closed',
                        'label': '配置推送加密',
                        'hint': '点击展开推送加密配置窗口。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VTextField',
                    'props': {
                        'model': 'group',
                        'label': '消息分组',
                        'hint': '选填。对消息进行分组，推送将按分组显示在通知中心中。也可在历史消息列表中选择查看不同的分组。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'sound',
                        'label': '推送铃声',
                        'clearable': True,
                        'items': [{
                            "title": f"{sound.name} ({sound.second}秒)",
                            "value": sound.name
                        } for sound in Sound if sound],
                        'hint': '选填。可以为推送设置不同的铃声。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSelect',
                    'props': {
                        'model': 'level',
                        'label': '通知级别',
                        'clearable': True,
                        'items': [
                            {"title": "立即亮屏显示通知", "value": "active"},
                            {"title": "时效性通知，可在专注状态显示", "value": "timeSensitive"},
                            {"title": "仅添加到通知列表而不亮屏提醒", "value": "passive"},
                        ],
                        'hint': '选填。可以为推送设置不同的铃声。缺省时为“立即亮屏显示通知”。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'isArchive',
                        'label': '自动保存',
                        'hint': '是否自动保存推送消息。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'autoCopy',
                        'label': '自动拷贝',
                        'hint': '是否自动拷贝消息内容到剪贴板。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': '_config_more_dialog_closed',
                        'label': '配置更多参数',
                        'hint': '点击展开更多参数配置窗口。'
                    }
                }]
            }, {
                'component': 'VCol',
                'props': {
                    'cols': 12,
                    'xxl': 4, 'xl': 4, 'lg': 4, 'md': 4, 'sm': 6, 'xs': 12
                },
                'content': [{
                    'component': 'VSwitch',
                    'props': {
                        'model': 'enable_proxy',
                        'label': '使用代理',
                        'hint': '推送消息时是否使用网络代理。'
                    }
                }]
            }]
        }
        dialogs = [{
            'component': 'VDialog',
            'props': {
                'model': '_config_cipher_dialog_closed',
                'max-width': '40rem'
            },
            'content': [{
                'component': 'VCard',
                'props': {
                    'title': '配置推送加密',
                    'style': {
                        'padding': '0 20px 20px 20px'
                    }
                },
                'content': [{
                    'component': 'VDialogCloseBtn',
                    'props': {
                        'model': '_config_cipher_dialog_closed'
                    }
                }, {
                    'component': 'VRow',
                    'content': [{
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VSwitch',
                            'props': {
                                'model': 'cipher_enable',
                                'label': '开关',
                                'hint': '是否启用推送加密。'
                            }
                        }]
                    }, {
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VSelect',
                            'props': {
                                'model': 'cipher_algorithm',
                                'label': '算法',
                                'items': [{
                                    "title": item,
                                    "value": item
                                } for item in self.support_cipher_algorithms if item],
                                'hint': '推送加密算法。'
                            }
                        }]
                    }, {
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VSelect',
                            'props': {
                                'model': 'cipher_mode',
                                'label': '模式',
                                'items': [{
                                    "title": item,
                                    "value": item
                                } for item in self.support_cipher_modes if item],
                                'hint': '推送加密模式。'
                            }
                        }]
                    }, {
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VSelect',
                            'props': {
                                'model': 'cipher_padding',
                                'label': '填充（Padding）',
                                'items': [{
                                    "title": item,
                                    "value": item
                                } for item in self.support_cipher_paddings if item],
                                'hint': '推送加密Padding。'
                            }
                        }]
                    }, {
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VTextField',
                            'props': {
                                'model': 'cipher_key',
                                'label': '密钥（Key）',
                                'hint': '必填。密钥（Key）。'
                            }
                        }]
                    }, {
                        'component': 'VCol',
                        'props': {
                            'cols': 12,
                            'xxl': 6, 'xl': 6, 'lg': 6, 'md': 6, 'sm': 6, 'xs': 12
                        },
                        'content': [{
                            'component': 'VTextField',
                            'props': {
                                'model': 'cipher_iv',
                                'label': '初始向量（Iv）',
                                'hint': '初始向量（Iv）。'
                            }
                        }]
                    }]
                }]
            }]
        }, {
            'component': 'VDialog',
            'props': {
                'model': '_config_more_dialog_closed',
                'max-width': '40rem'
            },
            'content': [{
                'component': 'VCard',
                'props': {
                    'title': '配置更多参数',
                    'style': {
                        'padding': '0 20px 20px 20px'
                    }
                },
                'content': [{
                    'component': 'VDialogCloseBtn',
                    'props': {
                        'model': '_config_more_dialog_closed'
                    }
                }, {
                    'component': 'VRow',
                    'content': [{
                        'component': 'VCol',
                        'props': {
                            'cols': 12
                        },
                        'content': [{
                            'component': 'VTextarea',
                            'props': {
                                'model': 'more_json',
                                'label': '更多参数',
                                'placeholder': '1、格式：json；\n'
                                               '2、会覆盖前面的标准配置，更多参数优先级更高；\n'
                                               '3、参考官方文档：https://bark.day.app/#/tutorial?id=请求参数',
                                'hint': '更多参数。格式：json；会覆盖前面的标准配置，更多参数优先级更高；参考官方文档：https://bark.day.app/#/tutorial?id=请求参数'
                            }
                        }]
                    }]
                }]
            }]
        }]
        row2 = self.build_notify_type_select_row_element()
        row3 = self.build_test_once_switch_row_element()
        elements = [row1]
        elements.extend(dialogs)
        elements.append(row2)
        elements.append(row3)
        # 处理缺省配置
        self.save_default_config()
        return elements, config_suggest

    def __check_config(self) -> bool:
        """
        检查配置
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/") if server_url else None
        if not server_url:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 服务器地址无效")
            return False
        if not self.get_config_item(config_key="push_key"):
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 推送密钥无效")
            return False
        return self.__check_cipher_config()

    def __check_cipher_config(self) -> bool:
        """
        检查加密配置
        """
        if not self.get_config_item(config_key="cipher_enable"):
            return True

        # 算法
        cipher_algorithm: str = self.get_config_item(config_key="cipher_algorithm")
        if not cipher_algorithm or cipher_algorithm not in self.support_cipher_algorithms:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密算法无效: {cipher_algorithm}")
            return False

        # 模式
        cipher_mode: str = self.get_config_item(config_key="cipher_mode")
        if not cipher_mode or cipher_mode not in self.support_cipher_modes:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密模式无效: {cipher_mode}")
            return False

        # 填充
        cipher_padding: str = self.get_config_item(config_key="cipher_padding")
        if not cipher_padding or cipher_padding not in self.support_cipher_paddings:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密填充无效: {cipher_padding}")
            return False

        # Key
        cipher_key: str = self.get_config_item(config_key="cipher_key")
        if not cipher_key:
            logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密密钥（Key）无效: {cipher_key}")
            return False
        cipher_key_bytes = cipher_key.encode("utf-8")
        cipher_key_bytes_len = len(cipher_key_bytes)
        if cipher_algorithm == "AES128":
            if cipher_key_bytes_len != 16:
                logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密密钥（Key）不是16位")
                return False
        elif cipher_algorithm == "AES192":
            if cipher_key_bytes_len != 24:
                logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密密钥（Key）不是24位")
                return False
        elif cipher_algorithm == "AES256":
            if cipher_key_bytes_len != 32:
                logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密密钥（Key）不是32位")
                return False

        # Iv
        cipher_iv: str = self.get_config_item(config_key="cipher_iv") or ""
        cipher_iv_bytes = cipher_iv.encode("utf-8")
        cipher_iv_bytes_len = len(cipher_iv_bytes)
        if cipher_mode == "CBC" or cipher_mode == "GCM":
            if not cipher_iv:
                logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密初始向量（Iv）无效: {cipher_iv}")
                return False
            if cipher_mode == "CBC":
                if cipher_iv_bytes_len != 16:
                    logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密初始向量（Iv）不是16位")
                    return False
            elif cipher_mode == "GCM":
                if cipher_iv_bytes_len != 12:
                    logger.warn(f"配置检查不通过: channel = {self.comp_name}, 加密初始向量（Iv）不是12位")
                    return False

        return True

    def __build_url(self) -> str:
        """
        构造url
        """
        server_url: str = self.get_config_item(config_key="server_url")
        server_url = server_url.rstrip("/")
        push_key = self.get_config_item(config_key="push_key")
        return f"{server_url}/{push_key}"

    def __build_json(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        构造请求json
        """
        ext_info = ext_info or {}

        # json
        # 标题和内容
        json = {
            "title": title,
            "body": text or title
        }
        # sound
        sound = self.get_config_item(config_key="sound")
        if sound:
            json["sound"] = sound
        # icon
        image = ext_info.get("image")
        if image:
            json["icon"] = image
        # group
        group = self.get_config_item(config_key="group")
        if group:
            json["group"] = group
        # url
        link = ext_info.get("link")
        if link:
            json["url"] = link
        # level
        level = self.get_config_item(config_key="level")
        if level:
            json["level"] = level
        # isArchive
        isArchive = self.get_config_item(config_key="isArchive")
        if isArchive:
            json["isArchive"] = 1
        # autoCopy
        autoCopy = self.get_config_item(config_key="autoCopy")
        if autoCopy:
            json["autoCopy"] = 1

        # 更多参数
        more_json: str = self.get_config_item(config_key="more_json")
        if more_json:
            try:
                more_json_obj = lib_json.loads(more_json)
                json.update(more_json_obj)
            except Exception as e:
                logger.error(f"更多参数解析异常: {str(e)}", exc_info=True)

        return json

    def __cipher_text(self, plaintext: str,
                      algorithm: str, mode: str, padding: str, key: str, iv: str) -> tuple[str, str]:
        """
        加密文本
        """
        plaintext = plaintext or ""
        plaintext_bytes = plaintext.encode("utf-8")
        key = key or ""
        key_bytes = key.encode("utf-8")
        iv = iv or ""
        iv_bytes = iv.encode("utf-8")

        if mode in ["CBC", "ECB"]:
            padder = lib_padding.PKCS7(128).padder()
            padded_plaintext_bytes = padder.update(plaintext_bytes) + padder.finalize()
        else:
            padded_plaintext_bytes = plaintext_bytes

        backend = default_backend()

        try:
            if mode == "ECB":
                cipher = Cipher(algorithm=algorithms.AES(key_bytes), mode=modes.ECB(), backend=backend)
                encryptor = cipher.encryptor()
                ciphertext_bytes = encryptor.update(padded_plaintext_bytes) + encryptor.finalize()
                ciphertext = base64.b64encode(ciphertext_bytes).decode("utf-8")
                return ciphertext, None
            elif mode == "CBC":
                cipher = Cipher(algorithm=algorithms.AES(key_bytes), mode=modes.CBC(iv_bytes), backend=backend)
                encryptor = cipher.encryptor()
                ciphertext_bytes = encryptor.update(padded_plaintext_bytes) + encryptor.finalize()
                ciphertext = base64.b64encode(ciphertext_bytes).decode("utf-8")
                return ciphertext, iv
            elif mode == "GCM":
                cipher = Cipher(algorithm=algorithms.AES(key_bytes), mode=modes.GCM(iv_bytes), backend=backend)
                encryptor = cipher.encryptor()
                ciphertext_bytes = encryptor.update(padded_plaintext_bytes) + encryptor.finalize() + encryptor.tag
                ciphertext = base64.b64encode(ciphertext_bytes).decode("utf-8")
                return ciphertext, iv
            else:
                return None, None
        except InvalidTag:
            raise InvalidTag("GCM模式加密失败: 认证标签生成异常")
        except Exception as e:
            raise ValueError(f"AES加密失败: {str(e)}")

    def __cipher_json(self, json: dict) -> tuple[str, str]:
        """
        加密json
        """
        if not self.__check_cipher_config():
            raise ValueError("加密配置有误")

        return self.__cipher_text(
            plaintext=lib_json.dumps(json or {}),
            algorithm=self.get_config_item(config_key="cipher_algorithm"),
            mode=self.get_config_item(config_key="cipher_mode"),
            padding=self.get_config_item(config_key="cipher_padding"),
            key=self.get_config_item(config_key="cipher_key"),
            iv=self.get_config_item(config_key="cipher_iv")
        )

    def __build_req_data(self, title: str, text: str, ext_info: dict = {}) -> dict:
        """
        生成请求数据
        """
        json = self.__build_json(title=title, text=text, ext_info=ext_info)
        if not self.get_config_item(config_key="cipher_enable"):
            return json
        else:
            try:
                ciphertext, iv = self.__cipher_json(json)
                return {
                    "ciphertext": ciphertext,
                    "iv": iv
                }
            except Exception as e:
                logger.error(f"加密异常，已降级为非加密方式: {str(e)}", exc_info=True)
                return json

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
        send_url = self.__build_url()
        json = self.__build_req_data(title=title, text=text, ext_info=ext_info)
        proxies = settings.PROXY if self.get_config_item(config_key="enable_proxy") else None
        res = requests.post(url=send_url, json=json, proxies=proxies)
        res_json = res.json() or {}
        if res.ok or res_json:
            code = res_json.get("code")
            message = res_json.get("message")
            if code == 200:
                logger.info(f"发送消息成功: channel = {self.comp_name}, type = {type_str}")
                return True
            else:
                logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, code = {code}, message = {message}")
                return False
        else:
            logger.warn(f"发送消息失败: channel = {self.comp_name}, type = {type_str}, status_code = {res.status_code}, reason = {res.reason}")
            return False
