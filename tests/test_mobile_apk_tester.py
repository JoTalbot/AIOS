"""Tests for Mobile APK Testing Tool."""

import zipfile

from tools.mobile_apk_tester import APKManifestAnalyzer


def test_apk_manifest_analyzer(tmp_path):
    # Create a mock APK zip file
    mock_apk = tmp_path / "test_app.apk"
    with zipfile.ZipFile(mock_apk, "w") as zf:
        zf.writestr("AndroidManifest.xml", "<manifest></manifest>")
        zf.writestr("classes.dex", "mock_dex_bytes")
        zf.writestr("lib/arm64-v8a/libnative.so", "mock_so_bytes")

    analyzer = APKManifestAnalyzer(str(mock_apk))
    struct = analyzer.inspect_apk_structure()

    assert struct["apk_name"] == "test_app.apk"
    assert struct["dex_classes_count"] == 1
    assert struct["has_native_c_libraries"] is True

    security = analyzer.analyze_security_permissions(["android.permission.INTERNET"])
    assert security["constitutional_safety_approved"] is True
    assert security["risk_score"] == 1.0
