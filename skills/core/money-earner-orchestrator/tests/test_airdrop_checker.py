"""Tests for airdrop_checker.py — read-only, no network required for core logic."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import airdrop_checker as ac


class AddressDetectionTests(unittest.TestCase):
    def test_evm_address(self):
        self.assertEqual(ac.detect_chain("0x937dce168f8dc93bc51f87608d4e09f592157619"), "evm")

    def test_cosmos_address(self):
        self.assertEqual(ac.detect_chain("cosmos1qpzry9x8gf2tvdw0s3jn54khce6mua7lmzmk9r"), "cosmos")

    def test_solana_address(self):
        self.assertEqual(ac.detect_chain("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"), "solana")

    def test_invalid_address(self):
        self.assertEqual(ac.detect_chain("not_an_address"), "unknown")


class BanklessNoKeyTests(unittest.TestCase):
    def test_no_api_key_returns_error(self):
        result = ac.check_bankless("0x937dce168f8dc93bc51f87608d4e09f592157619", None)
        self.assertFalse(result["ok"])
        self.assertIn("BANKLESS_API_KEY", result["error"])

    def test_no_api_key_no_unclaimed(self):
        result = ac.check_bankless("0x937dce168f8dc93bc51f87608d4e09f592157619", None)
        self.assertEqual(result["unclaimed"], [])


class ReportStructureTests(unittest.TestCase):
    def test_report_marked_read_only(self):
        rep = ac.build_report("0x937dce168f8dc93bc51f87608d4e09f592157619", None)
        self.assertTrue(rep["read_only"])
        self.assertFalse(rep["private_key_used"])
        self.assertEqual(rep["chain_detected"], "evm")
        self.assertIn("manual_links", rep)
        self.assertIn("bankless", rep)

    def test_report_contains_address(self):
        rep = ac.build_report("0x937dce168f8dc93bc51f87608d4e09f592157619", None)
        self.assertEqual(rep["address"], "0x937dce168f8dc93bc51f87608d4e09f592157619")


if __name__ == "__main__":
    unittest.main()
