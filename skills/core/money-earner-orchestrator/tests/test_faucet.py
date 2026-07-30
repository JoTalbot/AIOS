#!/usr/bin/env python3
"""Contract tests for faucet_collector (вектор САМООБЕСПЕЧЕНИЕ, L0).

Гарантирует: классификация кранов корректна (captcha/testnet/dead/claimable);
детекторы капчи/testnet/механизма работают на HTML-образцах; offline-safe (без сети).
Честность: testnet-краны = бесполезные монеты; captcha краны не claimable.
"""
import importlib.util
import os
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FC_PY = HERE.parent / "code" / "faucet_collector.py"


def _load_fc():
    os.environ["OCTOPUS_FAUCET_OFFLINE"] = "1"
    spec = importlib.util.spec_from_file_location("fc", FC_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE_HCAPTCHA = """
<html><body>
<div class="h-captcha" data-sitekey="xxx"></div>
<iframe src="https://newassets.hcaptcha.com/captcha/v1/abc"></iframe>
<button>GET SAT</button>
<p>LNURL-withdraw</p>
</body></html>
"""
SAMPLE_NOCAP_LNURL = """
<html><body><button>Claim</button>
<a href="lightning:LNURL...">withdraw</a></body></html>
"""
SAMPLE_TESTNET = """
<html><body>This is a TESTNET faucet. Get tBTC. No real value.</body></html>
"""
SAMPLE_CLEAN_MAINNET = """
<html><body>Get free satoshis. lightning:lnbc... withdraw now.</body></html>
"""


class DetectorTests(unittest.TestCase):
    def test_detect_captcha_widgets_hcaptcha(self):
        m = _load_fc()
        caps = m.detect_captcha_widgets(SAMPLE_HCAPTCHA)
        self.assertGreater(caps["hcaptcha"], 0)
        self.assertTrue(any(v > 0 for v in caps.values()))

    def test_detect_captcha_widgets_clean(self):
        m = _load_fc()
        caps = m.detect_captcha_widgets(SAMPLE_CLEAN_MAINNET)
        self.assertFalse(any(v > 0 for v in caps.values()))

    def test_detect_testnet(self):
        m = _load_fc()
        self.assertTrue(m.detect_testnet(SAMPLE_TESTNET))
        self.assertFalse(m.detect_testnet(SAMPLE_CLEAN_MAINNET))

    def test_detect_mechanism(self):
        m = _load_fc()
        self.assertEqual(m.detect_mechanism(SAMPLE_HCAPTCHA, "unknown"), "lnurl_withdraw")
        self.assertEqual(m.detect_mechanism(SAMPLE_CLEAN_MAINNET, "unknown"), "invoice_paste")

    def test_detect_auth_avoids_js_false_positive(self):
        m = _load_fc()
        # loginStatus:{} in JS state must NOT count as auth_required
        self.assertFalse(m.detect_auth('<script>state={loginStatus:{}}</script>'))


class ClassifyTests(unittest.TestCase):
    def test_classify_matrix(self):
        m = _load_fc()
        self.assertEqual(m.classify({"alive": False}), "dead")
        self.assertEqual(m.classify({"alive": True, "network": "testnet"}), "testnet_useless")
        self.assertEqual(m.classify({"alive": True, "network": "mainnet", "captcha": True}), "captcha_blocked")
        self.assertEqual(m.classify({"alive": True, "network": "mainnet", "captcha": False, "auth_required": True}), "auth_required")
        self.assertEqual(m.classify({"alive": True, "network": "mainnet", "captcha": False, "auth_required": False, "mechanism": "lnurl_withdraw"}), "claimable")
        self.assertEqual(m.classify({"alive": True, "network": "mainnet", "captcha": False, "auth_required": False, "mechanism": "unknown"}), "needs_investigation")


class ClaimLogicTests(unittest.TestCase):
    def test_claim_needs_lightning_address(self):
        m = _load_fc()
        res = m.claim_one({"id": "x", "name": "x", "url": "u", "claim_class": "claimable", "mechanism": "lnurl_withdraw"}, "")
        self.assertEqual(res["status"], "needs_lightning_address")

    def test_claim_skips_captcha(self):
        m = _load_fc()
        res = m.claim_one({"id": "x", "url": "u", "claim_class": "captcha_blocked"}, "name@walletofsatoshi.com")
        self.assertTrue(res["status"].startswith("skipped"))

    def test_claim_lnurl_is_manual(self):
        m = _load_fc()
        res = m.claim_one({"id": "x", "name": "x", "url": "https://ex/faucet", "claim_class": "claimable", "mechanism": "lnurl_withdraw"}, "name@walletofsatoshi.com")
        self.assertEqual(res["status"], "manual_lnurl")


class CatalogTests(unittest.TestCase):
    def test_default_catalog_nonempty_and_mainnet(self):
        m = _load_fc()
        cat = m.DEFAULT_CATALOG
        self.assertGreater(len(cat), 0)
        for f in cat:
            self.assertIn("url", f)
            self.assertIn("id", f)
        self.assertTrue(any(f.get("network") == "mainnet" for f in cat))


if __name__ == "__main__":
    unittest.main()
