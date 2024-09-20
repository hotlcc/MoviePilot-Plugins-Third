import threading
from mako.template import Template

from app.log import logger


class ThreadLocalUtil():
    """
    线程本地变量工具
    """

    __local = threading.local()

    @staticmethod
    def set(key: str, value: any):
        """
        设置本地变量
        """
        setattr(ThreadLocalUtil.__local, key, value)

    @staticmethod
    def get(key: str, default_value: any = None) -> any:
        """
        获取本地变量
        """
        return getattr(ThreadLocalUtil.__local, key, default_value)

    @staticmethod
    def exist(key: str) -> bool:
        """
        判断本地变量是否存在
        """
        return hasattr(ThreadLocalUtil.__local, key)

    @staticmethod
    def delete(key: str):
        """
        删除本地变量
        """
        try:
            delattr(ThreadLocalUtil.__local, key)
        except AttributeError:
            pass

    @staticmethod
    def delete_batch(keys: list[str]):
        """
        删除多个本地变量
        """
        if not keys:
            return
        for key in keys:
            ThreadLocalUtil.delete(key=key)

    @staticmethod
    def get_set(key: str, value: any) -> any:
        """
        获取并设置本地变量
        """
        old_value = ThreadLocalUtil.get(key=key)
        ThreadLocalUtil.set(key=key, value=value)
        return old_value

    @staticmethod
    def get_delete(key: str) -> any:
        """
        获取并删除本地变量
        """
        old_value = ThreadLocalUtil.get(key=key)
        ThreadLocalUtil.delete(key=key)
        return old_value

    @staticmethod
    def auto_delete(keys: list[str]):
        """
        函数执行结束后自动删除多个本地变量的装饰器
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                finally:
                    try:
                        ThreadLocalUtil.delete_batch(keys=keys)
                    except Exception:
                        pass
            return wrapper
        return decorator


class TemplateUtil():
    """
    模板工具
    """

    @staticmethod
    def render_text(text: str, variables: dict) -> str:
        """
        渲染文本
        :param text: 模板文本
        :param variables: 模板变量（词典）
        """
        if not text or not variables:
            return text
        try:
            template = Template(text=text)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"渲染文本异常: text = {text}, variables = {str(variables)}, {str(e)}", exc_info=True)
            return text
