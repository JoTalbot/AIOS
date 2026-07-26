# A/B Testing for Templates

## Overview
Multi-Armed Bandit (Thompson Sampling) algorithm for automatic template optimization.

## API Endpoints
- `POST /api/v1/ab_testing/select?template_id=...` - Select variant using bandit
- `POST /api/v1/ab_testing/convert?variant_id=...` - Record conversion
- `GET /api/v1/ab_testing/stats` - Get statistics for all variants

## Algorithm
Thompson Sampling balances exploration vs exploitation:
- New variants get more chances initially
- Better performing variants get selected more often
- Automatically converges to optimal variant

## Usage
1. Create multiple template variants
2. On each message, call `/select` to get best variant
3. After user responds positively, call `/convert`
4. Monitor stats via `/stats`
