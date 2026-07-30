# Bounded adaptation proposals

## merge_duplicate_skill-marketplace-sync

```json
{
  "id": "merge_duplicate_skill-marketplace-sync",
  "priority": "low",
  "trigger": "duplicate_skill_name",
  "canonical_candidate": "meta/skill-marketplace-sync",
  "duplicates": [
    "core/skill-marketplace-sync",
    "meta/skill-marketplace-sync"
  ],
  "action": "compare code/tests/references, merge unique content into canonical candidate, archive duplicate after explicit validation",
  "auto_apply": false,
  "destructive_action_performed": false
}
```

