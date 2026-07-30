# Bounded adaptation proposals

## external_publication_reconcile

```json
{
  "id": "external_publication_reconcile",
  "priority": "low",
  "trigger": {
    "repository": "JoTalbot/octopus",
    "canonical_issue": 12,
    "duplicates": [
      {
        "number": 14,
        "state": "CLOSED",
        "title": "Octopus: каталог SRE и automation-услуг",
        "reconciled_marker_present": true
      }
    ]
  },
  "action": "review duplicate marked issues and close/archive only after explicit approval; keep canonical OPEN issue",
  "auto_apply": false,
  "external_actions_performed": false
}
```

