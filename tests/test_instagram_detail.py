"""Tests for Instagram detail parser and post composer."""

from aios_core.modules.instagram.detail import InstagramDetailParser
from aios_core.modules.instagram.posts import PostComposer


def test_detail_parser_init():
    p = InstagramDetailParser()
    assert p is not None


def test_post_composer_init():
    pc = PostComposer()
    assert pc is not None
