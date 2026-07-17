# AIOS Knowledge Object Model

## Purpose

Define the data structures used by AIOS Immortal Memory.

AIOS memory stores structured knowledge, not only raw logs.

## Object Types

### Experience Object

Represents an observed execution event.

Contains:

- source
- action
- environment
- result
- metrics
- confidence

Example lifecycle:

```
Action
 ↓
Observation
 ↓
Metrics
 ↓
Experience Record
```

## Knowledge Object

Represents a learned pattern or fact.

Contains:

- concept
- relationships
- dependencies
- confidence
- origin

## Skill Object

Represents reusable capability learned from experience.

```
Experience
    ↓
Knowledge
    ↓
Skill
```

Contains:

- skill name
- required inputs
- execution procedure
- validation rules
- performance metrics

## Decision Object

Stores architectural and operational decisions.

Contains:

- decision
- reason
- alternatives
- evidence
- confidence

## Experiment Object

Stores controlled improvement attempts.

Contains:

- hypothesis
- change
- metrics
- result
- conclusion

## AIOS Memory Principle

Every useful action should be capable of becoming reusable intelligence.
