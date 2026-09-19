from src.processing.article_text import (
    content_hash,
    count_chars,
    count_paragraphs,
    normalize_body,
)


def test_normalize_is_idempotent():
    messy = "\r\n第一段  \r\n\r\n\r\n\r\n第二段​\xa0內容\r\n"
    once = normalize_body(messy)
    assert once == "第一段\n\n第二段 內容"
    assert normalize_body(once) == once


def test_hash_ignores_line_ending_style_but_not_wording():
    assert content_hash("甲\r\n\r\n乙") == content_hash("甲\n\n乙")
    assert content_hash("甲\n\n乙") != content_hash("甲\n\n丙")


def test_counts_ignore_whitespace():
    body = "星河 公司\n\n宣布 新產品"
    assert count_chars(body) == 9
    assert count_paragraphs(body) == 2
