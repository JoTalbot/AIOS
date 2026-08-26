# Global Task Graph

Federated task orchestration across AIOS clusters.

Nodes represent executable units.
Edges represent dependencies.

```
User Goal
 |
 Global Planner
 |
 +--- Cluster Task A
 +--- Cluster Task B
 +--- Cluster Task C
```

The graph is governed by policy, capability and trust layers.
