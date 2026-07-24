"""gRPC Server Implementation for AIOS Core v11.0.0."""

import json
import logging
import asyncio
from concurrent import futures
import grpc
import time

from aios_core.orchestrator import Orchestrator
from aios_core.async_core import AsyncDatabase
from aios_core.grpc import aios_pb2, aios_pb2_grpc

logger = logging.getLogger(__name__)

class AiosCoreServicer(aios_pb2_grpc.AiosCoreServicer):
    """Implementation of the gRPC AIOS service."""
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    def SubmitTask(self, request, context):
        try:
            steps = json.loads(request.steps_json) if request.steps_json else []
            task = self.orchestrator.create_task(
                name=request.name,
                description=request.description,
                agent_id=request.agent_id or "grpc_agent",
                risk_level=request.risk_level or "medium",
                tenant_id=request.tenant_id if request.tenant_id else None
            )
            
            for step_data in steps:
                self.orchestrator.add_step(
                    task, 
                    step_type=step_data.get("action", "unknown"),
                    params=step_data.get("params", {})
                )
                
            # Submit to background (since gRPC is thread-pooled, we can block or run async)
            # For simplicity we execute it synchronously in this thread
            self.orchestrator.execute_task(task)
            
            return aios_pb2.TaskResponse(
                task_id=task.id,
                status=task.status.value
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return aios_pb2.TaskResponse()

    def GetTaskStatus(self, request, context):
        task = self.orchestrator._tasks.get(request.task_id)
        if not task:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Task not found")
            return aios_pb2.TaskStatusResponse()
            
        return aios_pb2.TaskStatusResponse(
            task_id=task.id,
            status=task.status.value,
            result_json=json.dumps(self.orchestrator._task_summary(task)),
            error=task.error or ""
        )

    def GetStats(self, request, context):
        stats = self.orchestrator.stats()
        return aios_pb2.StatsResponse(stats_json=json.dumps(stats))


def serve_grpc(orchestrator: Orchestrator, port: int = 50051):
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    aios_pb2_grpc.add_AiosCoreServicer_to_server(AiosCoreServicer(orchestrator), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"AIOS gRPC Server listening on port {port}")
    return server
