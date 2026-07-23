"""M8 Test Generator tests"""

from aios_core.android_test_generator import AndroidTestGenerator


def test_from_user_flow():
    gen = AndroidTestGenerator(output_dir="/tmp/tests_gen")
    test = gen.from_user_flow(
        flow=["Tap search_field", "Type: iPhone 13", "Tap search_button"],
        platform="ua.slando",
        name="test_search_flow",
        description="Search flow",
    )
    assert test.platform == "ua.slando"
    assert len(test.steps) == 3
    assert "search_field" in test.steps[0].target


def test_to_pytest():
    gen = AndroidTestGenerator(output_dir="/tmp/tests_gen")
    test = gen.from_user_flow(
        flow=["Tap login_button", "Type: test@example.com"],
        platform="ua.slando",
        name="test_login",
        description="Login",
    )
    py_code = test.to_pytest()
    assert "def test_login" in py_code
    assert "android_driver" in py_code


def test_to_json():
    gen = AndroidTestGenerator(output_dir="/tmp/tests_gen")
    test = gen.from_user_flow(
        flow=["Wait search_results", "Assert iPhone"],
        platform="ua.slando",
        name="test_assert",
        description="Assert",
    )
    js = test.to_json()
    assert js["name"] == "test_assert"
    assert len(js["steps"]) == 2


def test_generate_suite():
    gen = AndroidTestGenerator(output_dir="/tmp/tests_gen")
    suite = gen.generate_suite("ua.slando")
    assert suite["total_generated"] == 4
    assert suite["platform"] == "ua.slando"


def test_from_recording_missing_file():
    gen = AndroidTestGenerator(output_dir="/tmp/tests_gen")
    test = gen.from_recording("/nonexistent.json", "ua.slando", "recorded_test")
    assert len(test.steps) >= 1
