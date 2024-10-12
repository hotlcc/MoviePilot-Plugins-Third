from mako.template import Template

from app.log import logger


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
