import logging
import sys
import os

from unittest.mock import Mock, patch
from typing import Any

from bonsai_common import SimulatorSession
from azure.core.exceptions import HttpResponseError


def test_401_error_registration(unauthorized_sim: SimulatorSession):
    try:
        unauthorized_sim.run()
    except HttpResponseError as err:
        assert err.reason == "Unauthorized"


def test_403_error_registration(forbidden_sim: SimulatorSession):
    try:
        forbidden_sim.run()
    except HttpResponseError as err:
        assert err.reason == "Forbidden"


def test_502_raises_retry_exception(bad_gateway_sim: SimulatorSession):
    try:
        bad_gateway_sim.run()
    except HttpResponseError as err:
        assert err.reason == "Bad Gateway"


def test_503_raises_retry_exception(unavailable_sim: SimulatorSession, capsys: Any):
    try:
        unavailable_sim.run()
    except HttpResponseError as err:
        assert err.reason == "Service Unavailable"


def test_504_raises_retry_exception(gateway_timeout_sim: SimulatorSession, capsys: Any):
    try:
        gateway_timeout_sim.run()
    except HttpResponseError as err:
        assert err.reason == "Gateway Timeout"


def test_training(train_sim: SimulatorSession):
    counter = 0
    while train_sim.run():
        if counter == 100:
            break
        counter += 1


@patch("time.sleep", return_value=None)
def test_flaky_sim(patched_sleep: Mock, flaky_sim: SimulatorSession, capsys: Any):
    counter = 0
    while flaky_sim.run():
        if counter == 100:
            break
        counter += 1


def test_500_err_sim(internal_server_err_sim: SimulatorSession):
    """Test that a 500 during get next event ends sim loop"""
    counter = 0
    try:
        while internal_server_err_sim.run():
            if counter == 100:
                # Avoid infinite simulation loops and fail
                assert False
            counter += 1
    except HttpResponseError as err:
        assert err.reason == "Internal Server Error"


def test_unregister_only_called_once(
    internal_server_err_sim: SimulatorSession, caplog: Any
):
    """Test to check that unregister is only called once during training"""
    counter = 0
    try:
        while internal_server_err_sim.run():
            if counter == 100:
                # Avoid infinite simulation loops and fail
                assert False
            counter += 1
    except HttpResponseError:
        pass
    assert "Attempting to unregister simulator" in caplog.text


def test_handle_unregister_event(unregister_event_sim: SimulatorSession, caplog: Any):
    """Test to check that the unregister event is handled currently in the simulation loop"""
    counter = 0
    logger = logging.getLogger("bonsai_common.simulator_session")
    logger.setLevel(logging.DEBUG)
    while unregister_event_sim.run():
        if counter == 100:
            # Avoid infinite simulation loops
            break
        counter += 1

    # Even on Unregister Events, sim was re-registered and iterated the whole time.
    # Every 25 iterations, sim gets an UnregisterEvent, and it should register again.
    assert caplog.text.count("Registering Sim") == 4
    assert counter == 100


def test_training_unregister_on_sigterm(train_sim: SimulatorSession, caplog: Any):
    if sys.platform == "win32" or sys.platform == "cygwin":
        return
    pid = os.getpid()
    counter = 0
    while train_sim.run():
        if counter == 10:
            try:
                os.kill(pid, 15)
            except SystemExit:
                pass
            break
        counter += 1
    assert "SIGTERM" in caplog.text
