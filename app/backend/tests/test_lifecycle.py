import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import Mock, call

import pytest


def lifecycle_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "manage.py"
    spec = importlib.util.spec_from_file_location("compass_lifecycle_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def managed(tmp_path, monkeypatch):
    module = lifecycle_module()
    instance = module.ManagedPostgres(tmp_path / "personal-data")
    instance.process = Mock(spec=["poll", "terminate", "wait", "kill"])
    instance.process.poll.return_value = None
    instance.process.wait.return_value = 0
    instance.log = Mock(spec=["close"])
    monkeypatch.setattr(module, "pg_binary", lambda name: tmp_path / name)
    monkeypatch.setattr(module, "pg_environment", lambda: {})
    run = Mock()
    monkeypatch.setattr(module.subprocess, "run", run)
    return module, instance, run


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CalledProcessError(1, ["pg_ctl", "stop"]),
        subprocess.TimeoutExpired(["pg_ctl", "stop"], 20),
        OSError("The local stop utility is unavailable"),
    ],
)
def test_failed_pg_ctl_stops_only_the_owned_child_and_closes_log(managed, failure):
    _, instance, run = managed
    run.side_effect = failure

    instance.stop()

    command = run.call_args.args[0]
    assert command[1:] == ["-D", str(instance.cluster), "-m", "fast", "-w", "stop"]
    assert run.call_args.kwargs["check"] is True
    instance.process.terminate.assert_called_once_with()
    instance.process.wait.assert_called_once_with(timeout=10)
    instance.process.kill.assert_not_called()
    instance.log.close.assert_called_once_with()


def test_owned_child_that_ignores_termination_is_killed_and_reaped(managed):
    _, instance, run = managed
    run.side_effect = subprocess.CalledProcessError(1, ["pg_ctl", "stop"])
    instance.process.wait.side_effect = [subprocess.TimeoutExpired("owned postgres", 10), 0]

    instance.stop()

    instance.process.terminate.assert_called_once_with()
    instance.process.kill.assert_called_once_with()
    assert instance.process.wait.call_args_list == [call(timeout=10), call(timeout=5)]
    instance.log.close.assert_called_once_with()


def test_missing_stop_binary_still_cleans_up_the_owned_child(managed, monkeypatch):
    module, instance, run = managed

    def missing_binary(name):
        raise RuntimeError("PostgreSQL binaries are missing")

    monkeypatch.setattr(module, "pg_binary", missing_binary)

    instance.stop()

    run.assert_not_called()
    instance.process.terminate.assert_called_once_with()
    instance.process.wait.assert_called_once_with(timeout=10)
    instance.log.close.assert_called_once_with()


def test_reused_cluster_without_owned_process_is_never_stopped(managed):
    _, instance, run = managed
    instance.process = None

    instance.stop()

    run.assert_not_called()
    instance.log.close.assert_called_once_with()


def test_already_exited_owned_process_is_not_terminated_again(managed):
    _, instance, run = managed
    instance.process.poll.return_value = 0

    instance.stop()

    run.assert_not_called()
    instance.process.terminate.assert_not_called()
    instance.process.kill.assert_not_called()
    instance.process.wait.assert_not_called()
    instance.log.close.assert_called_once_with()
