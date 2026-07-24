"""Product image comparison — perceptual hashing for visual similarity.

Provides three perceptual hash algorithms:
- Average Hash (aHash): fastest, coarse similarity
- Difference Hash (dHash): better gradient detection
- Perceptual Hash (pHash): DCT-based, best accuracy

Also includes:
- Color histogram comparison for product images
- Composite similarity scoring (hash + color + metadata)
- Duplicate detection across platforms

Pure Python — no external image libraries required.
Works with raw pixel data (list[int]) or simulated test grids.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HashAlgorithm(Enum):
    """Supported perceptual hash algorithms."""

    AHASH = "ahash"
    DHASH = "dhash"
    PHASH = "phash"


@dataclass
class ImageHash:
    """Perceptual hash result with algorithm metadata."""

    hash_value: int  # 64-bit hash as integer
    algorithm: HashAlgorithm
    width: int = 8  # Source grid width
    height: int = 8  # Source grid height
    bit_string: str = ""  # Binary representation for debugging

    def __post_init__(self) -> None:
        """Compute bit_string from hash_value."""
        if not self.bit_string:
            self.bit_string = format(self.hash_value, "064b")

    def distance(self, other: ImageHash) -> int:
        """Hamming distance between two hashes.

        Args:
            other: Another ImageHash to compare.

        Returns:
            Number of differing bits (0 = identical, 64 = completely different).
        """
        return (self.hash_value ^ other.hash_value).bit_count()

    def similarity(self, other: ImageHash) -> float:
        """Similarity score (0.0 to 1.0) based on Hamming distance.

        Args:
            other: Another ImageHash to compare.

        Returns:
            1.0 = identical, 0.0 = completely different.
        """
        dist = self.distance(other)
        return 1.0 - dist / 64.0


@dataclass
class ColorHistogram:
    """RGB color histogram for image comparison."""

    red: list[int] = field(default_factory=lambda: [0] * 8)
    green: list[int] = field(default_factory=lambda: [0] * 8)
    blue: list[int] = field(default_factory=lambda: [0] * 8)
    bins: int = 8

    def similarity(self, other: ColorHistogram) -> float:
        """Compute histogram intersection similarity.

        Args:
            other: Another ColorHistogram to compare.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        total_intersect = 0
        total_sum = 0

        for ch_name in ("red", "green", "blue"):
            self_ch = getattr(self, ch_name)
            other_ch = getattr(other, ch_name)
            s = sum(self_ch) + sum(other_ch)
            if s == 0:
                continue
            intersect = sum(min(a, b) for a, b in zip(self_ch, other_ch, strict=False))
            total_intersect += intersect
            total_sum += s / 2

        return total_intersect / total_sum if total_sum > 0 else 0.0


@dataclass
class ComparisonResult:
    """Result of comparing two product images."""

    source_fingerprint: str
    target_fingerprint: str
    hash_similarity: float  # 0.0 to 1.0
    color_similarity: float  # 0.0 to 1.0
    composite_similarity: float  # Weighted combination
    is_duplicate: bool  # True if similarity >= threshold
    hash_distance: int  # Hamming distance
    algorithm: HashAlgorithm
    metadata: dict[str, Any] = field(default_factory=dict)


def _pixels_to_grid(
    pixels: list[int], width: int, height: int, target_w: int = 8, target_h: int = 8
) -> list[list[int]]:
    """Resample pixel array to target grid size using averaging.

    Args:
        pixels: Flat list of grayscale pixel values (0-255).
        width: Original image width.
        height: Original image height.
        target_w: Target grid width.
        target_h: Target grid height.

    Returns:
        2D grid of averaged pixel values (target_h × target_w).
    """
    if width == target_w and height == target_h:
        grid = []
        for y in range(target_h):
            row = []
            for x in range(target_w):
                idx = y * width + x
                row.append(pixels[idx] if idx < len(pixels) else 0)
            grid.append(row)
        return grid

    # Block averaging
    block_w = width / target_w
    block_h = height / target_h
    grid = []

    for ty in range(target_h):
        row = []
        for tx in range(target_w):
            start_x = int(tx * block_w)
            end_x = int((tx + 1) * block_w)
            start_y = int(ty * block_h)
            end_y = int((ty + 1) * block_h)

            total = 0
            count = 0
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    idx = y * width + x
                    if idx < len(pixels):
                        total += pixels[idx]
                        count += 1

            row.append(total // count if count > 0 else 0)
        grid.append(row)

    return grid


def average_hash(pixels: list[int], width: int = 8, height: int = 8) -> ImageHash:
    """Compute Average Hash (aHash).

    1. Reduce image to 8×8 grayscale grid.
    2. Compute mean pixel value.
    3. Each pixel > mean → 1, else → 0.
    4. Pack 64 bits into integer.

    Args:
        pixels: Flat grayscale pixel list (0-255).
        width: Original width (or 8 if already reduced).
        height: Original height (or 8 if already reduced).

    Returns:
        ImageHash with aHash result.
    """
    grid = _pixels_to_grid(pixels, width, height, 8, 8)

    flat = [grid[y][x] for y in range(8) for x in range(8)]
    mean_val = sum(flat) / len(flat) if flat else 0

    hash_bits = 0
    for i, val in enumerate(flat):
        if val >= mean_val:
            hash_bits |= 1 << (63 - i)

    return ImageHash(
        hash_value=hash_bits,
        algorithm=HashAlgorithm.AHASH,
        width=width,
        height=height,
    )


def difference_hash(pixels: list[int], width: int = 9, height: int = 8) -> ImageHash:
    """Compute Difference Hash (dHash).

    1. Reduce image to 9×8 grayscale grid.
    2. Compare adjacent pixels: left < right → 1, else → 0.
    3. 8×8 = 64 bits.

    Args:
        pixels: Flat grayscale pixel list (0-255).
        width: Original width (default 9 for 9×8 grid).
        height: Original height (default 8).

    Returns:
        ImageHash with dHash result.
    """
    grid = _pixels_to_grid(pixels, width, height, 9, 8)

    hash_bits = 0
    bit_idx = 0
    for y in range(8):
        for x in range(8):
            left = grid[y][x]
            right = grid[y][x + 1] if x + 1 < 9 else grid[y][x]
            if left < right:
                hash_bits |= 1 << (63 - bit_idx)
            bit_idx += 1

    return ImageHash(
        hash_value=hash_bits,
        algorithm=HashAlgorithm.DHASH,
        width=width,
        height=height,
    )


def _dct_1d(vec: list[float]) -> list[float]:
    """Compute 1D Discrete Cosine Transform (Type II).

    Args:
        vec: Input vector of length N.

    Returns:
        DCT coefficients of length N.
    """
    N = len(vec)
    result = []
    for k in range(N):
        s = 0.0
        for n in range(N):
            s += vec[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
        result.append(s * math.sqrt(2.0 / N) if k > 0 else s * math.sqrt(1.0 / N))
    return result


def _dct_2d(grid: list[list[float]]) -> list[list[float]]:
    """Compute 2D DCT by applying 1D DCT to rows then columns.

    Args:
        grid: 2D input matrix (N×N).

    Returns:
        2D DCT coefficients.
    """
    # DCT on rows
    row_dct = [_dct_1d(row) for row in grid]

    # DCT on columns
    N = len(grid)
    col_dct: list[list[float]] = [[0.0] * N for _ in range(N)]
    for x in range(N):
        column = [row_dct[y][x] for y in range(N)]
        dct_col = _dct_1d(column)
        for y in range(N):
            col_dct[y][x] = dct_col[y]

    return col_dct


def perceptual_hash(pixels: list[int], width: int = 32, height: int = 32) -> ImageHash:
    """Compute Perceptual Hash (pHash) using DCT.

    1. Reduce image to 32×32 grayscale.
    2. Apply 2D DCT.
    3. Keep top-left 8×8 low-frequency coefficients.
    4. Compute median of those 64 coefficients.
    5. Each coeff > median → 1, else → 0.
    6. Pack 64 bits into integer.

    Args:
        pixels: Flat grayscale pixel list (0-255).
        width: Original width.
        height: Original height.

    Returns:
        ImageHash with pHash result.
    """
    # Reduce to 32×32
    grid = _pixels_to_grid(pixels, width, height, 32, 32)

    # Convert to float
    float_grid = [[float(grid[y][x]) for x in range(32)] for y in range(32)]

    # Apply DCT
    dct = _dct_2d(float_grid)

    # Take top-left 8×8 (low-frequency)
    low_freq = []
    for y in range(8):
        for x in range(8):
            # Skip DC coefficient (0,0) for better hashing
            if y == 0 and x == 0:
                continue
            low_freq.append(dct[y][x])

    # Compute median
    sorted_freq = sorted(low_freq)
    median = sorted_freq[len(sorted_freq) // 2]

    # Build hash (63 bits, since we skip DC)
    # We add back one bit for DC: >0 → 1
    hash_bits = 0
    bit_idx = 0

    # DC coefficient
    dc = dct[0][0]
    if dc > 0:
        hash_bits |= 1 << (63 - bit_idx)
    bit_idx += 1

    # Low-frequency coefficients
    for val in low_freq:
        if val > median:
            hash_bits |= 1 << (63 - bit_idx)
        bit_idx += 1

    return ImageHash(
        hash_value=hash_bits,
        algorithm=HashAlgorithm.PHASH,
        width=width,
        height=height,
    )


def compute_color_histogram(
    pixels_rgb: list[tuple[int, int, int]],
    bins: int = 8,
) -> ColorHistogram:
    """Compute RGB color histogram from pixel data.

    Args:
        pixels_rgb: List of (R, G, B) tuples (0-255 each).
        bins: Number of bins per channel (default 8 → 32 values per bin).

    Returns:
        ColorHistogram with bin counts.
    """
    bin_size = 256 // bins
    hist = ColorHistogram(bins=bins)

    for r, g, b in pixels_rgb:
        r_bin = min(r // bin_size, bins - 1)
        g_bin = min(g // bin_size, bins - 1)
        b_bin = min(b // bin_size, bins - 1)
        hist.red[r_bin] += 1
        hist.green[g_bin] += 1
        hist.blue[b_bin] += 1

    return hist


class ImageComparisonEngine:
    """Product image comparison engine combining hash and color similarity.

    Provides:
    - compare() — compare two images with composite scoring
    - find_duplicates() — scan product images for near-duplicates
    - best_match() — find best matching image in a catalog
    """

    def __init__(
        self,
        hash_algorithm: HashAlgorithm = HashAlgorithm.PHASH,
        duplicate_threshold: float = 0.85,
        hash_weight: float = 0.6,
        color_weight: float = 0.4,
    ) -> None:
        """Initialize ImageComparisonEngine.

        Args:
            hash_algorithm: Default hash algorithm for comparisons.
            duplicate_threshold: Minimum similarity to flag as duplicate.
            hash_weight: Weight for hash similarity in composite score.
            color_weight: Weight for color similarity in composite score.
        """
        self.hash_algorithm = hash_algorithm
        self.duplicate_threshold = duplicate_threshold
        self.hash_weight = hash_weight
        self.color_weight = color_weight

    def _compute_hash(
        self,
        pixels: list[int],
        width: int,
        height: int,
        algorithm: HashAlgorithm | None = None,
    ) -> ImageHash:
        """Compute perceptual hash using specified algorithm.

        Args:
            pixels: Grayscale pixel data.
            width: Image width.
            height: Image height.
            algorithm: Hash algorithm (default: self.hash_algorithm).

        Returns:
            ImageHash result.
        """
        algo = algorithm or self.hash_algorithm
        if algo == HashAlgorithm.AHASH:
            return average_hash(pixels, width, height)
        elif algo == HashAlgorithm.DHASH:
            return difference_hash(pixels, width, height)
        else:
            return perceptual_hash(pixels, width, height)

    def compare(
        self,
        source_pixels: list[int],
        source_w: int,
        source_h: int,
        target_pixels: list[int],
        target_w: int,
        target_h: int,
        source_rgb: list[tuple[int, int, int]] | None = None,
        target_rgb: list[tuple[int, int, int]] | None = None,
        source_fingerprint: str = "",
        target_fingerprint: str = "",
        algorithm: HashAlgorithm | None = None,
    ) -> ComparisonResult:
        """Compare two product images.

        Args:
            source_pixels: Grayscale pixels of source image.
            source_w: Source width.
            source_h: Source height.
            target_pixels: Grayscale pixels of target image.
            target_w: Target width.
            target_h: Target height.
            source_rgb: Optional RGB pixels for color histogram.
            target_rgb: Optional RGB pixels for color histogram.
            source_fingerprint: Source product fingerprint.
            target_fingerprint: Target product fingerprint.
            algorithm: Hash algorithm override.

        Returns:
            ComparisonResult with all similarity metrics.
        """
        src_hash = self._compute_hash(source_pixels, source_w, source_h, algorithm)
        tgt_hash = self._compute_hash(target_pixels, target_w, target_h, algorithm)

        hash_sim = src_hash.similarity(tgt_hash)
        hash_dist = src_hash.distance(tgt_hash)

        # Color similarity
        color_sim = 0.0
        if source_rgb and target_rgb:
            src_hist = compute_color_histogram(source_rgb)
            tgt_hist = compute_color_histogram(target_rgb)
            color_sim = src_hist.similarity(tgt_hist)

        # Composite similarity
        if source_rgb and target_rgb:
            composite = hash_sim * self.hash_weight + color_sim * self.color_weight
        else:
            composite = hash_sim  # Only hash available

        is_dup = composite >= self.duplicate_threshold

        return ComparisonResult(
            source_fingerprint=source_fingerprint,
            target_fingerprint=target_fingerprint,
            hash_similarity=round(hash_sim, 4),
            color_similarity=round(color_sim, 4),
            composite_similarity=round(composite, 4),
            is_duplicate=is_dup,
            hash_distance=hash_dist,
            algorithm=src_hash.algorithm,
        )

    def find_duplicates(
        self,
        image_catalog: dict[str, tuple[list[int], int, int]],
        threshold: float | None = None,
        algorithm: HashAlgorithm | None = None,
    ) -> list[ComparisonResult]:
        """Find duplicate images in a catalog.

        Args:
            image_catalog: Dict of fingerprint → (pixels, width, height).
            threshold: Duplicate threshold override.
            algorithm: Hash algorithm override.

        Returns:
            List of ComparisonResult for pairs exceeding threshold.
        """
        dup_threshold = threshold or self.duplicate_threshold
        fingerprints = list(image_catalog.keys())
        hashes: dict[str, ImageHash] = {}

        # Compute hashes for all images
        for fp, (pixels, w, h) in image_catalog.items():
            hashes[fp] = self._compute_hash(pixels, w, h, algorithm)

        # Compare all pairs
        duplicates = []
        for i in range(len(fingerprints)):
            for j in range(i + 1, len(fingerprints)):
                fp1 = fingerprints[i]
                fp2 = fingerprints[j]
                sim = hashes[fp1].similarity(hashes[fp2])
                if sim >= dup_threshold:
                    duplicates.append(
                        ComparisonResult(
                            source_fingerprint=fp1,
                            target_fingerprint=fp2,
                            hash_similarity=round(sim, 4),
                            color_similarity=0.0,
                            composite_similarity=round(sim, 4),
                            is_duplicate=True,
                            hash_distance=hashes[fp1].distance(hashes[fp2]),
                            algorithm=hashes[fp1].algorithm,
                        )
                    )

        return duplicates

    def best_match(
        self,
        query_pixels: list[int],
        query_w: int,
        query_h: int,
        catalog: dict[str, tuple[list[int], int, int]],
        algorithm: HashAlgorithm | None = None,
    ) -> tuple[str, float] | None:
        """Find the best matching image in a catalog.

        Args:
            query_pixels: Query image grayscale pixels.
            query_w: Query width.
            query_h: Query height.
            catalog: Dict of fingerprint → (pixels, width, height).
            algorithm: Hash algorithm override.

        Returns:
            (fingerprint, similarity) of best match, or None if catalog empty.
        """
        if not catalog:
            return None

        query_hash = self._compute_hash(query_pixels, query_w, query_h, algorithm)

        best_fp = ""
        best_sim = 0.0

        for fp, (pixels, w, h) in catalog.items():
            cat_hash = self._compute_hash(pixels, w, h, algorithm)
            sim = query_hash.similarity(cat_hash)
            if sim > best_sim:
                best_sim = sim
                best_fp = fp

        if best_sim > 0.0:
            return (best_fp, round(best_sim, 4))
        return None
