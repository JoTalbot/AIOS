"""Tests for advanced NN architectures — Liquid, RWKV, Mamba, KAN, etc."""

from aios_core.liquid_nn import LiquidNeuralNetwork
from aios_core.rwkv import RWKVModel
from aios_core.mamba import MambaModel
from aios_core.kan import KANetwork
from aios_core.retnet import RetNet
from aios_core.moe import MixtureOfExperts


def test_liquid_nn_stats():
    s = LiquidNeuralNetwork().stats()
    assert isinstance(s, dict)


def test_rwkv_stats():
    s = RWKVModel().stats()
    assert isinstance(s, dict)


def test_mamba_stats():
    s = MambaModel().stats()
    assert isinstance(s, dict)


def test_kan_stats():
    s = KANetwork().stats()
    assert isinstance(s, dict)


def test_retnet_stats():
    s = RetNet().stats()
    assert isinstance(s, dict)


def test_moe_stats():
    s = MixtureOfExperts().stats()
    assert isinstance(s, dict)
