"""
HTTP工具
"""

import urllib.parse as parse

from app.sdk.logging import logger


def improve_url(base_url: str, req_url: str) -> str:
    """
    完善URL
    """
    logger.debug(f"完善URL: 完善前的URL = {req_url}")
    base_url_parse = parse.urlparse(base_url)
    req_url_parse = parse.urlparse(req_url)
    new_url_parse = parse.ParseResult(
        scheme=base_url_parse.scheme,
        netloc=base_url_parse.netloc,
        path=base_url_parse.path + req_url_parse.path,
        params=req_url_parse.params,
        query=req_url_parse.query,
        fragment=req_url_parse.fragment
    )
    url = parse.urlunparse(new_url_parse)
    url = str(url)
    logger.debug(f"完善URL: 完善后的URL = {url}")
    return url
