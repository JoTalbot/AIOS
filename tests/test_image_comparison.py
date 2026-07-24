"""Tests for image_comparison module — perceptual hashing and product image comparison."""

from __future__ import annotations

import pytest

from aios_core.image_comparison import (
    ColorHistogram,
    ComparisonResult,
    HashAlgorithm,
    ImageComparisonEngine,
    ImageHash,
    average_hash,
    compute_color_histogram,
    difference_hash,
    perceptual_hash,
)


# ─── Test helpers ───

def _uniform_pixels(value: int, size: int = 64) -> list[int]:
    """Create flat pixel array of uniform value."""
    return [value] * size


def _gradient_pixels(size: int = 64) -> list[int]:
    """Create flat pixel array with linear gradient 0→255."""
    return [int(255 * i / size) for i in range(size)]


def _checker_pixels(size: int = 64) -> list[int]:
    """Create checkerboard pattern pixels."""
    pixels = []
    for i in range(size):
        row = i // 8
        col = i % 8
        pixels.append(255 if (row + col) % 2 == 0 else 0)
    return pixels


def _checker_pixels_9x8() -> list[int]:
    """Create 9×8 checkerboard pattern for dHash."""
    pixels = []
    for row in range(8):
        for col in range(9):
            pixels.append(255 if (row + col) % 2 == 0 else 0)
    return pixels


# ─── ImageHash ───

class TestImageHash:
    """Tests for ImageHash dataclass."""

    def test_hash_creation(self) -> None:
        """Create ImageHash from integer."""
        h = ImageHash(hash_value=12345, algorithm=HashAlgorithm.AHASH)
        assert h.hash_value == 12345
        assert h.algorithm == HashAlgorithm.AHASH
        assert len(h.bit_string) == 64

    def test_bit_string_generated(self) -> None:
        """bit_string auto-generated from hash_value."""
        h = ImageHash(hash_value=0, algorithm=HashAlgorithm.AHASH)
        assert h.bit_string == "0" * 64

    def test_custom_bit_string(self) -> None:
        """Custom bit_string preserved."""
        h = ImageHash(
            hash_value=1, algorithm=HashAlgorithm.AHASH,
            bit_string="0001"
        )
        assert h.bit_string == "0001"

    def test_identical_hashes_distance_zero(self) -> None:
        """Same hash → distance 0."""
        h = ImageHash(hash_value=42, algorithm=HashAlgorithm.AHASH)
        assert h.distance(h) == 0

    def test_distance_different_hashes(self) -> None:
        """Different hashes → nonzero distance."""
        h1 = ImageHash(hash_value=0, algorithm=HashAlgorithm.AHASH)
        h2 = ImageHash(hash_value=1, algorithm=HashAlgorithm.AHASH)
        # Only 1 bit differs
        assert h1.distance(h2) == 1

    def test_similarity_identical(self) -> None:
        """Same hash → similarity 1.0."""
        h = ImageHash(hash_value=42, algorithm=HashAlgorithm.AHASH)
        assert h.similarity(h) == 1.0

    def test_similarity_opposite(self) -> None:
        """Completely different → low similarity."""
        h1 = ImageHash(hash_value=0, algorithm=HashAlgorithm.AHASH)
        h2 = ImageHash(hash_value=(1 << 64) - 1, algorithm=HashAlgorithm.AHASH)
        # All 64 bits differ
        assert h1.similarity(h2) == 0.0

    def test_similarity_partial(self) -> None:
        """1 bit differ → 63/64 similarity."""
        h1 = ImageHash(hash_value=0, algorithm=HashAlgorithm.AHASH)
        h2 = ImageHash(hash_value=1, algorithm=HashAlgorithm.AHASH)
        assert abs(h1.similarity(h2) - (63 / 64)) < 0.01


# ─── Average Hash ───

class TestAverageHash:
    """Tests for average_hash function."""

    def test_uniform_image(self) -> None:
        """All same pixels → hash should be all-ones or all-zeros."""
        pixels = _uniform_pixels(128, 64)
        h = average_hash(pixels, 8, 8)
        # Uniform: all pixels == mean → all >= mean → all bits = 1
        assert h.algorithm == HashAlgorithm.AHASH
        assert h.hash_value == (1 << 64) - 1

    def test_gradient_image(self) -> None:
        """Gradient image → non-trivial hash."""
        pixels = _gradient_pixels(64)
        h = average_hash(pixels, 8, 8)
        assert h.algorithm == HashAlgorithm.AHASH
        # Should have both 0 and 1 bits
        assert h.bit_string != "0" * 64
        assert h.bit_string != "1" * 64

    def test_same_image_same_hash(self) -> None:
        """Same pixels → same aHash."""
        pixels = _gradient_pixels(64)
        h1 = average_hash(pixels, 8, 8)
        h2 = average_hash(pixels, 8, 8)
        assert h1.distance(h2) == 0

    def test_different_images_different_hash(self) -> None:
        """Different patterns → different aHash."""
        h1 = average_hash(_uniform_pixels(50, 64), 8, 8)
        h2 = average_hash(_gradient_pixels(64), 8, 8)
        assert h1.distance(h2) > 0


# ─── Difference Hash ───

class TestDifferenceHash:
    """Tests for difference_hash function."""

    def test_gradient_dhash(self) -> None:
        """Gradient image → dHash detects horizontal differences."""
        # 9×8 gradient
        pixels = []
        for row in range(8):
            for col in range(9):
                pixels.append(col * 28)  # 0, 28, 56, ... across each row
        h = difference_hash(pixels, 9, 8)
        assert h.algorithm == HashAlgorithm.DHASH
        # All left < right → all bits set to 1
        assert h.hash_value > 0

    def test_flat_dhash(self) -> None:
        """Flat image → dHash all zeros (no differences)."""
        pixels = _uniform_pixels(128, 72)  # 9×8 = 72
        h = difference_hash(pixels, 9, 8)
        # left == right → no bits set
        assert h.hash_value == 0

    def test_same_image_same_dhash(self) -> None:
        """Same pixels → same dHash."""
        pixels = _gradient_pixels(72)
        h1 = difference_hash(pixels, 9, 8)
        h2 = difference_hash(pixels, 9, 8)
        assert h1.distance(h2) == 0


# ─── Perceptual Hash ───

class TestPerceptualHash:
    """Tests for perceptual_hash function."""

    def test_phash_computable(self) -> None:
        """pHash produces a valid hash."""
        # 32×32 = 1024 pixels
        pixels = _gradient_pixels(1024)
        h = perceptual_hash(pixels, 32, 32)
        assert h.algorithm == HashAlgorithm.PHASH
        assert h.bit_string != ""

    def test_phash_same_image(self) -> None:
        """Same image → same pHash."""
        pixels = _gradient_pixels(1024)
        h1 = perceptual_hash(pixels, 32, 32)
        h2 = perceptual_hash(pixels, 32, 32)
        assert h1.distance(h2) == 0

    def test_phash_different_images(self) -> None:
        """Different images → different pHash."""
        pixels1 = _gradient_pixels(1024)
        pixels2 = _uniform_pixels(128, 1024)
        h1 = perceptual_hash(pixels1, 32, 32)
        h2 = perceptual_hash(pixels2, 32, 32)
        assert h1.distance(h2) > 10  # Should differ significantly


# ─── Color Histogram ───

class TestColorHistogram:
    """Tests for ColorHistogram and compute_color_histogram."""

    def test_empty_histogram_similarity(self) -> None:
        """Two empty histograms → similarity 0."""
        h1 = ColorHistogram()
        h2 = ColorHistogram()
        assert h1.similarity(h2) == 0.0

    def test_identical_histograms(self) -> None:
        """Same histogram → similarity 1.0."""
        h = ColorHistogram(red=[10] * 8, green=[10] * 8, blue=[10] * 8)
        assert h.similarity(h) == 1.0

    def test_different_histograms(self) -> None:
        """Completely different → low similarity."""
        h1 = ColorHistogram(red=[100, 0, 0, 0, 0, 0, 0, 0], green=[0] * 8, blue=[0] * 8)
        h2 = ColorHistogram(red=[0, 0, 0, 0, 0, 0, 0, 100], green=[0] * 8, blue=[0] * 8)
        # No overlap → similarity 0
        assert h1.similarity(h2) == 0.0

    def test_compute_color_histogram(self) -> None:
        """compute_color_histogram produces correct bins."""
        # 4 pixels: (0,0,0), (255,255,255), (128,128,128), (64,64,64)
        rgb = [(0, 0, 0), (255, 255, 255), (128, 128, 128), (64, 64, 64)]
        hist = compute_color_histogram(rgb, bins=8)
        # bin_size = 256/8 = 32
        assert hist.red[0] == 1   # (0) → bin 0
        assert hist.red[7] == 1   # (255) → bin 7
        assert hist.red[4] == 1   # (128) → bin 4
        assert hist.red[2] == 1   # (64) → bin 2

    def test_partial_overlap_histogram(self) -> None:
        """Partial overlap → partial similarity."""
        h1 = ColorHistogram(red=[50, 50, 0, 0, 0, 0, 0, 0], green=[0] * 8, blue=[0] * 8)
        h2 = ColorHistogram(red=[30, 30, 0, 0, 0, 0, 0, 0], green=[0] * 8, blue=[0] * 8)
        sim = h1.similarity(h2)
        assert 0.5 < sim < 1.0  # Partial overlap


# ─── ImageComparisonEngine ───

class TestImageComparisonEngine:
    """Tests for ImageComparisonEngine."""

    def test_compare_same_image(self) -> None:
        """Same image → high similarity, flagged as duplicate."""
        engine = ImageComparisonEngine(duplicate_threshold=0.8)
        pixels = _gradient_pixels(64)
        result = engine.compare(
            pixels, 8, 8, pixels, 8, 8,
            source_fingerprint="fp1",
            target_fingerprint="fp1_copy",
        )
        assert result.hash_similarity == 1.0
        assert result.composite_similarity >= 0.8
        assert result.is_duplicate

    def test_compare_different_images(self) -> None:
        """Different images → low similarity, not duplicate."""
        engine = ImageComparisonEngine(
            duplicate_threshold=0.9, hash_algorithm=HashAlgorithm.AHASH
        )
        pixels1 = _uniform_pixels(50, 64)
        pixels2 = _checker_pixels()
        result = engine.compare(
            pixels1, 8, 8, pixels2, 8, 8,
            source_fingerprint="fp_flat",
            target_fingerprint="fp_checker",
            algorithm=HashAlgorithm.AHASH,
        )
        assert result.hash_similarity < 0.95
        assert not result.is_duplicate

    def test_compare_with_color_histograms(self) -> None:
        """RGB histograms enhance composite similarity."""
        engine = ImageComparisonEngine(
            hash_weight=0.5, color_weight=0.5
        )
        pixels = _gradient_pixels(64)
        rgb1 = [(128, 128, 128)] * 64
        rgb2 = [(128, 128, 128)] * 64
        result = engine.compare(
            pixels, 8, 8, pixels, 8, 8,
            source_rgb=rgb1, target_rgb=rgb2,
            source_fingerprint="fp_rgb1",
            target_fingerprint="fp_rgb2",
        )
        assert result.color_similarity == 1.0
        assert result.composite_similarity == 1.0

    def test_different_hash_algorithms(self) -> None:
        """Compare using different hash algorithms."""
        engine = ImageComparisonEngine(hash_algorithm=HashAlgorithm.AHASH)
        pixels = _gradient_pixels(64)
        r_ahash = engine.compare(
            pixels, 8, 8, pixels, 8, 8,
            algorithm=HashAlgorithm.AHASH,
        )
        r_phash = engine.compare(
            pixels, 32, 32, pixels, 32, 32,
            algorithm=HashAlgorithm.PHASH,
        )
        # Same image → both should show similarity
        assert r_ahash.hash_similarity == 1.0
        assert r_phash.hash_similarity == 1.0

    def test_find_duplicates(self) -> None:
        """Find duplicates in a catalog of images."""
        engine = ImageComparisonEngine(duplicate_threshold=0.9)
        grad = _gradient_pixels(64)
        flat = _uniform_pixels(128, 64)
        checker = _checker_pixels()

        catalog = {
            "fp_grad": (grad, 8, 8),
            "fp_grad_copy": (grad, 8, 8),  # Exact duplicate
            "fp_flat": (flat, 8, 8),
        }
        duplicates = engine.find_duplicates(catalog)
        # Should find grad ↔ grad_copy as duplicate
        assert len(duplicates) >= 1
        dup_fps = {(d.source_fingerprint, d.target_fingerprint) for d in duplicates}
        assert ("fp_grad", "fp_grad_copy") in dup_fps

    def test_find_duplicates_empty_catalog(self) -> None:
        """Empty catalog → no duplicates."""
        engine = ImageComparisonEngine()
        duplicates = engine.find_duplicates({})
        assert duplicates == []

    def test_best_match(self) -> None:
        """Find best matching image in catalog."""
        engine = ImageComparisonEngine()
        grad = _gradient_pixels(64)
        flat = _uniform_pixels(128, 64)

        catalog = {
            "fp_grad": (grad, 8, 8),
            "fp_flat": (flat, 8, 8),
        }
        # Query with gradient → should match fp_grad
        result = engine.best_match(grad, 8, 8, catalog)
        assert result is not None
        assert result[0] == "fp_grad"

    def test_best_match_empty_catalog(self) -> None:
        """Empty catalog → None."""
        engine = ImageComparisonEngine()
        result = engine.best_match(_gradient_pixels(64), 8, 8, {})
        assert result is None

    def test_best_match_no_similarity(self) -> None:
        """Completely different → best match with low similarity."""
        engine = ImageComparisonEngine()
        grad = _gradient_pixels(64)
        flat = _uniform_pixels(0, 64)  # All black

        catalog = {"fp_flat": (flat, 8, 8)}
        result = engine.best_match(grad, 8, 8, catalog)
        # Still returns best (even if low) since there's only one option
        assert result is not None
