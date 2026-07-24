"""Behavioral coverage for time series, simulation, spiking and streaming modules."""

import asyncio
import random

from aios_core.simulation_engine import SimulationEngine
from aios_core.spiking_nn import SpikingLayer, SpikingNetwork, SpikingNeuron, Synapse
from aios_core.time_series import TimeSeriesAnalyzer
from aios_core.webhook_manager import WebhookManager
from aios_core.webhook_metrics import get_webhook_prometheus_text, register_webhook_metrics
from aios_core.websocket import WebSocketManager
from aios_core.ws_dashboard import DashboardEventBus, WSMessage, WSMessageType


class FakeSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("disconnected")
        self.sent.append(message)

    async def send_text(self, message):
        if self.fail:
            raise RuntimeError("disconnected")
        self.sent.append(message)


def test_time_series_analysis_paths_and_retention():
    series = TimeSeriesAnalyzer(max_length=12)
    assert series.detect_trend("missing") == "insufficient_data"
    for value in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 12, 13]:
        series.add_data("x", value)
    assert len(series.series["x"]) == 12
    assert len(series.moving_average("x", 3)) == 10
    assert len(series.exponential_moving_average("x")) == 12
    assert series.detect_trend("x") == "increasing"
    assert series.detect_anomalies("x", threshold=2.0)
    assert len(series.forecast_arima("x", steps=3)) == 3
    assert len(series.autocorrelation("x", max_lag=2)) == 2
    assert series.detect_change_point("x", sensitivity=0.1)
    assert len(series.seasonal_decomposition("x", period=3)["seasonal"]) == 3
    assert series.stats()["total_points"] == 12


def test_simulation_engine_dependencies_failures_monte_carlo_and_sweeps():
    engine = SimulationEngine()
    calls = []
    engine.register_scenario("dep", lambda params: calls.append("dep") or 1)
    engine.register_scenario("main", lambda params: calls.append(params["x"]) or params["x"])
    engine.register_scenario("bad", lambda params: 1 / 0)
    engine.add_dependency("main", "dep")
    assert engine.run("none")["error"] == "Scenario not found"
    assert engine.run("main", {"x": 2})["result"] == 2
    assert calls == ["dep", 2]
    assert engine.run("bad")["status"] == "failed"
    assert engine.monte_carlo("main", runs=3, params={"x": 4})["average"] == 4.0
    assert len(engine.parameter_sweep("main", "x", [1, 2])) == 2
    assert set(engine.batch_execute(["dep", "bad"])) == {"dep", "bad"}
    assert engine.stats()["scenarios"] == 3


def test_spiking_neurons_synapses_layers_and_network():
    random.seed(4)
    neuron = SpikingNeuron(threshold=1.0)
    assert neuron.step(0.5) == 0
    assert neuron.step(1.0) == 1
    assert neuron.get_rate() > 0
    neuron.reset()
    assert neuron.stats()["total_spikes"] == 0
    synapse = Synapse(weight=0.5)
    assert synapse.transmit(1) == 0.5
    synapse.stdp_update(True, True, 0.1)
    synapse.stdp_update(False, True, 0.1)
    assert 0 <= synapse.weight <= 1
    layer = SpikingLayer(2)
    assert len(layer.forward([2.0], timesteps=2)) == 2
    network = SpikingNetwork([2, 1])
    network.connect_layers(0, 1)
    assert len(network.poisson_encode([0.0, 1.0], duration=3)) == 2
    assert len(network.forward([1.0, 0.0], timesteps=2)) == 1
    assert network.stats()["synapse_groups"] == 1


def test_webhook_metrics_and_prometheus_text():
    manager = WebhookManager()
    manager.register("ops", "https://example.test/hook", ["event"])
    register_webhook_metrics(manager)
    text = get_webhook_prometheus_text(manager)
    assert "aios_webhook_targets_total 1" in text
    assert 'target="ops"' in text
    assert "aios_webhook_targets_total" in get_webhook_prometheus_text()


def test_websocket_manager_and_dashboard_event_bus_lifecycle():
    async def run():
        manager = WebSocketManager(max_messages_per_second=2)
        healthy, broken = FakeSocket(), FakeSocket(fail=True)
        conn = await manager.connect(healthy, "one", ["events"])
        await manager.connect(broken, "two")
        assert manager.subscribe(conn, "other")
        assert await manager.send_to(conn, {"x": 1})
        assert not await manager.send_to("two", {"x": 1})
        assert "two" not in manager._connections
        assert await manager.broadcast({"event": 1}, topic="events") == 1
        assert await manager.ping_all() == {"one": True}
        manager._connections["one"].last_ping = 0
        assert await manager.cleanup_stale(timeout=1) == 1

        bus = DashboardEventBus(replay_buffer_size=1)
        client = FakeSocket()
        await bus.connect(client)
        message = WSMessage(WSMessageType.SYSTEM_STATUS, {"ok": True})
        assert await bus.broadcast(message) == 1
        assert bus.client_count == 1
        await bus.disconnect(client)
        assert bus.client_count == 0

    asyncio.run(run())
