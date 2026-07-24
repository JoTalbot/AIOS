# AIOS Developer SDK Quickstart

Welcome to the AIOS Developer Platform! The official `aios-client` SDK allows you to easily connect your applications to the AIOS execution engine, both via REST API and gRPC microservices.

## 📦 Installation
```bash
pip install aios-client
```

## 🚀 Basic Usage (REST API)
```python
import asyncio
from aios_sdk import AIOSClient

async def main():
    async with AIOSClient("http://localhost:8000") as client:
        # Create a new task
        task = await client.create_task(
            name="Data Processing",
            steps=[{"action": "clean_dataset", "params": {"file": "data.csv"}}]
        )
        
        # Monitor status
        status = await client.get_task_status(task["id"])
        print(f"Task Status: {status['status']}")

asyncio.run(main())
```

## ⚡ High-Performance Usage (gRPC)
For microservices requiring extreme throughput, use the new gRPC stub provided in the SDK.

```python
import grpc
from aios_core.grpc import aios_pb2, aios_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = aios_pb2_grpc.AiosCoreStub(channel)

request = aios_pb2.TaskRequest(
    name="Quantum Simulation",
    agent_id="quantum_agent",
    steps_json='[{"action": "qaoa_layer"}]'
)
response = stub.SubmitTask(request)
print(f"Dispatched gRPC Task: {response.task_id}")
```
