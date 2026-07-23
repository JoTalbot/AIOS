"""Transformer full ops."""
from aios_core.transformer import TransformerModel
def test_tf(): s=TransformerModel().stats(); assert isinstance(s,dict)
