AIOS Core API Reference
=======================

.. automodule:: aios_core.orchestrator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.constitution_engine
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.autonomy_manager
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.formal_code_verifier
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.substrate_convergence
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.ai_advisor
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.marketplace
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.production_autopilot
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.memory
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.knowledge_graph
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.evolution
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.privacy
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.event_bus
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.planner
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: aios_core.capability
   :members:
   :undoc-members:
   :show-inheritance:

REST API Endpoints
------------------

The REST API exposes 143 routes. Key endpoints:

Health & Metrics
^^^^^^^^^^^^^^^^

.. code-block:: python

   GET  /health              # Public health check
   GET  /metrics             # Prometheus metrics
   GET  /ready               # Readiness probe

Runtime
^^^^^^^

.. code-block:: python

   GET  /api/v1/stats        # Runtime statistics
   POST /api/v1/tasks        # Create task
   GET  /api/v1/tasks/{id}   # Get task status
   POST /api/v1/evaluate     # Constitutional evaluation
   GET  /api/v1/evolution    # Evolution state
   GET  /api/v1/memory       # Memory records
   GET  /api/v1/kg           # Knowledge graph

Advisor
^^^^^^^

.. code-block:: python

   POST /api/v1/advisor/draft           # Draft reply (AI Advisor)
   GET  /api/v1/advisor/intent          # Intent classification
   GET  /api/v1/advisor/pricing         # Price advice from market samples

Marketplace
^^^^^^^^^^^

.. code-block:: python

   POST /api/v1/marketplace/publish     # Publish capability/plugin
   GET  /api/v1/marketplace/search      # Search plugins
   GET  /api/v1/marketplace/stats       # Marketplace statistics
   POST /api/v1/marketplace/install     # Install plugin

Devices & Platforms
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   POST /api/v1/devices/register        # Register device
   GET  /api/v1/devices/list            # List devices
   GET  /api/v1/dashboard               # Web dashboard (read-only)

Authentication
^^^^^^^^^^^^^^

All endpoints except ``GET /health`` require Bearer authentication:

.. code-block:: bash

   curl -H 'Authorization: Bearer YOUR_API_KEY' http://localhost:8000/api/v1/stats

API keys are configured via ``AIOS_API_KEYS`` environment variable.
