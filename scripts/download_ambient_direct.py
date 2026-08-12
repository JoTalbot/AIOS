#!/usr/bin/env python3
"""
AIOS Direct Ambient Recordings Downloader
"""

import os
import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AMBIENT_DIR = REPO_ROOT / "Calls" / "!voice" / "ambient_drive"

FILES_TO_DOWNLOAD = [
    ("1Z3aLBEDBtgSFev2ZRARRuEwTXVAIdvbj", "2026_05_31_20_40_22.wav"),
    ("1ieIf5PpYEb9NX5FR2Az_0uw7jSoQopv_", "2026_05_31_21_00_43.wav"),
    ("109ujuOk1ABgsW5KUF3SBdf3_veUELSA-", "2026_05_31_21_21_00.wav"),
    ("1FavxLbSLqabuAtv_M_EcKhON4TFZjpT2", "2026_05_31_21_41_00.wav"),
    ("13E2WrYQa3mGSM4YiIuZtVs-Pf_OaI0pv", "2026_05_31_22_01_01.wav"),
    ("1CicdIhO-V6Hkt96v8DrvykT44sGb5e7k", "2026_05_31_22_21_01.wav"),
    ("1W5THlJU4pJd6zEURnZlwEvEbDOye8uYc", "2026_05_31_22_41_02.wav"),
    ("1L1BsHRmsvMfTR1Zrag7ZlLJKETWtWYOB", "2026_06_01_09_23_40.wav"),
    ("1PGQ4U5L248hGXCB6Et85s6OHCaolZw2v", "2026_06_01_09_49_24.wav"),
    ("1fO7S8jg6JxOd2KKRnCSnN5ZDJljlkZWD", "2026_06_01_09_49_43.wav"),
    ("1chC_AZ-UZKf1xNHtedE53h5uNehGxsu0", "2026_06_01_12_25_26.wav"),
    ("174Unlqgb7AtusbqqwDj5DHd-asjre8hE", "2026_06_01_12_45_27.wav"),
    ("1k2lXar8rLr_qNyeeuajTtpd1XqsoZ0Z5", "2026_06_01_13_05_29.wav"),
    ("1CNoCtanG0U-XkU1FdubbqLs8TMuIgmWS", "2026_06_10_12_42_58.wav"),
    ("1Pl2kch46qxG7pSZ2oKhl7Fjd1JTyDjZS", "2026_06_10_13_02_59.wav"),
    ("1i0USadvsUuOU99Q_knOI7KS-twoJS0ae", "2026_06_10_13_23_16.wav"),
    ("1PESSrj9zBFmQnNj4eXzI2bmsdKMq8LOx", "2026_06_10_13_43_21.wav"),
    ("1BcWgVig4eMoT2gJvzuu1N6k2zo2JS6Gc", "2026_06_10_14_03_22.wav"),
    ("15bPjBKEibWGE6-6c5SkvvlwsHXuWwXSb", "2026_06_10_14_23_22.wav"),
    ("11nQcAjMYdwKW2mR9s53D5CskBcE2krZz", "2026_06_10_14_43_22.wav"),
    ("19Il5beh0vwU6QIsZu72wxb9K8O59yKPf", "2026_06_10_18_50_10.wav"),
    ("1O1_sMSGbRXRTbnabhjP1zML6b30r1B-n", "2026_06_10_19_10_25.wav"),
    ("1aazz6IRGq2nxPTNoIMVMyVL0yxLMUXqh", "2026_06_10_19_50_28.wav"),
    ("1-5v4wSZUHanFv_MzpvErMVurkvkmAB4g", "2026_06_10_20_11_58.wav"),
    ("1DMBTdIu0B8OvjkiWkY5MON7XjeARreaQ", "2026_06_10_20_31_59.wav"),
    ("16ZDaFxPaUDUyA26b-Ldyt9_SoD67qy4e", "2026_06_10_20_57_04.wav"),
    ("18xUUUJwuk8ufRlPMhJGfTFI4yVo4KmgU", "2026_06_10_21_22_31.wav"),
    ("1ABhjIw3PIwWdDWF6swPQ1jcO-x0QGBiY", "2026_06_10_21_42_32.wav"),
    ("1zu0SFTaUEhmlLrOozzzrJeWAL1vhjcYs", "2026_06_10_22_02_32.wav"),
    ("1zhdSJJ7Ulq4hDtjawBF5x9yJYpb_lODG", "2026_06_10_22_22_33.wav"),
    ("1WH4XES5QwporCC6thoqdJ6i45XXHpmj7", "2026_06_10_22_42_33.wav"),
    ("14vdTRRhLi0ZajI7SsBLFu1CM5C4Kb3XV", "2026_06_11_11_57_26.wav"),
    ("1vbbeO5bkqfw1kv_wBjz2sWk109KSDBca", "2026_06_11_12_17_54.wav"),
    ("1ECHuMq1XEC-8L5G0WnYcXtI5vuODuZhP", "2026_06_12_12_23_31.wav"),
    ("1ZzfZYTL2eeU0fWZuC1UQLJXK6pjJ_xkb", "2026_06_12_18_30_37.wav"),
    ("1mPM55h3DOjReuAfeDG5iJxFAKIy0ZuBq", "2026_06_12_18_50_53.wav"),
    ("1pCpPMM7tOevd7yon-whQRFHnP34knfwn", "2026_06_12_19_10_54.wav"),
    ("1WxCO-HPKbteymzHrDkREz6wM51_sEhmy", "2026_06_12_19_30_54.wav"),
    ("1yq29CNp7awgWF6FMOzv1VtimA076a_ak", "2026_06_12_19_57_14.wav"),
    ("1ULDLpvGM8hPylq3U7x_zHMuZIj88BSQl", "2026_06_16_21_09_50.wav"),
    ("1rfBkoYuy2yaAc36sUqvyqsdgnKd2MBfM", "2026_06_16_21_29_51.wav"),
    ("1WNhS23kbxnkmDTQT2swAly1U-qdgoGY4", "2026_06_17_11_52_26.wav"),
    ("1JvGea51q5C9FvGfwFZPaIkNW7Gy1D0mJ", "2026_06_17_12_12_27.wav"),
    ("1oNNxgoOFhLDJgF4lzActsLmiXUxoigMV", "2026_06_18_18_01_26.mp3"),
    ("14BZ-maE-UaiNm2oTfYl-6kunalxo8biJ", "2026_06_18_18_01_26.wav"),
    ("1n5thW8DelNz3pgxTvzGb1WmGS09Z0l2L", "2026_06_18_18_08_43.mp3"),
    ("1KnROEW-p5y4Z7lPMrYDvjXQ6TVjrviUH", "2026_06_18_18_08_43.wav"),
    ("12mGq9N5GOH4ceu46pUNLXbkonXAOZ8pJ", "2026_06_18_18_28_43.wav"),
    ("1YbwO6ATWnTL_ladakTbIlof3Fm_5e1e8", "2026_06_19_18_44_26.mp3"),
    ("1ISzBgVpnBNSJ3O4w9BQNF_X7q1Xuszrl", "2026_06_19_18_44_26.wav"),
    ("1hW6UkypCVAqlG79BHVH-bqabfccTfnhG", "2026_06_19_19_04_27.wav"),
    ("1Q1Nu0TYbmS0HhcKcaTzFXXMpA_8gE6VF", "2026_06_19_20_00_28.mp3"),
    ("1BIFZLo91XT6irXWCecv7a7ZKWvXUAKN5", "2026_06_19_20_00_28.wav"),
    ("1tn7jBuKDta_wIebcsw7rXOSdsIZjLhzl", "2026_06_19_22_13_24.mp3"),
    ("1YzE8BkeDHv8U75GyzFchGBKAzxNvMyf5", "2026_06_19_22_13_24.wav"),
    ("1zq4mR1U3GGBrTq0RkUTPUk_BVTF07XGQ", "2026_08_07_20_09_49.mp3"),
    ("1n1dmHF2Tx7-r4ltVklemxLzStWPykg3Y", "2026_08_07_20_29_50.wav"),
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.download_ambient")


def download_ambient_files():
    import gdown
    AMBIENT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for fid, fname in FILES_TO_DOWNLOAD[:15]:  # Batch 1
        out_path = AMBIENT_DIR / fname
        if out_path.exists():
            count += 1
            continue
        try:
            logger.info(f"📥 Скачивание фоновой записи: {fname}...")
            gdown.download(id=fid, output=str(out_path), quiet=True)
            if out_path.exists():
                count += 1
        except Exception as e:
            logger.warning(f"Ошибка {fname}: {e}")

    logger.info(f"🎉 Записей окружения готово на сервере: {count} шт.")


if __name__ == "__main__":
    download_ambient_files()
