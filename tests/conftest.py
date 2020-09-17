"""
Test fixtures
Copyright 2020 Microsoft
"""

import time
from multiprocessing import Process
from typing import Any, Dict

import pytest
from _pytest.fixtures import FixtureRequest

from bonsai_common import SimulatorSession
from microsoft_bonsai_api.simulator.client import BonsaiClientConfig
from microsoft_bonsai_api.simulator.generated.models import SimulatorInterface


from .web_server import start_app


class MinimalSim(SimulatorSession):
    def episode_start(self, config: Dict[str, Any]):
        pass

    def episode_step(self, action: Dict[str, Any]):
        pass

    def get_state(self) -> Dict[str, Any]:
        return {}

    def get_interface(self) -> SimulatorInterface:
        face = SimulatorInterface(name="minimal")
        return face

    def halted(self) -> bool:
        return False


@pytest.fixture(scope="session", autouse=True)
def start_server_process(request: FixtureRequest):

    proc = Process(target=start_app)
    proc.daemon = True
    proc.start()
    time.sleep(2)

    def fin():
        proc.terminate()

    request.addfinalizer(fin)


@pytest.fixture
def unauthorized_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "unauthorized"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def forbidden_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "forbidden"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def bad_gateway_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "badgateway"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def unavailable_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "unavailable"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def gateway_timeout_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "gatewaytimeout"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def train_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "train"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def flaky_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "flaky"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def internal_server_err_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "500"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim


@pytest.fixture
def unregister_event_sim():
    config = BonsaiClientConfig()
    config.server = "http://127.0.0.1:9000"
    config.workspace = "unregisterevent"
    config.access_key = "1111"
    sim = MinimalSim(config)
    return sim
