import unittest
import tempfile
from unittest.mock import MagicMock, patch

from monitor import docker_events_poller, docker_socket_access


class DockerProxyEndpointTests(unittest.TestCase):
    def test_event_client_uses_private_tcp_proxy_without_unix_prefix(self):
        self.assertEqual(
            docker_events_poller._docker_base_url("tcp://docker-events-proxy:2375"),
            "tcp://docker-events-proxy:2375",
        )
        self.assertEqual(
            docker_events_poller._docker_base_url("/var/run/docker.sock"),
            "unix:///var/run/docker.sock",
        )

    def test_proxy_ping_succeeds_without_host_socket(self):
        client = MagicMock()
        sdk = MagicMock()
        sdk.DockerClient.return_value = client
        with patch.object(docker_socket_access, "docker_sdk", sdk), \
             patch.object(docker_socket_access.os, "stat", side_effect=AssertionError("must not stat host socket")):
            issue = docker_socket_access.check_docker_socket_access("tcp://docker-events-proxy:2375")
        self.assertIsNone(issue)
        sdk.DockerClient.assert_called_once_with(base_url="tcp://docker-events-proxy:2375", timeout=3)
        client.ping.assert_called_once_with()
        client.close.assert_called_once_with()

    def test_proxy_diagnostic_rejects_credentials(self):
        issue = docker_socket_access.check_docker_socket_access("tcp://user:pass@docker-events-proxy:2375")
        self.assertIn("格式无效", issue)

    def test_event_poller_starts_with_tcp_proxy_without_socket_file(self):
        with tempfile.TemporaryDirectory() as cursor_dir:
            poller = docker_events_poller.DockerEventsPoller(
                "tcp://docker-events-proxy:2375", cursor_dir, ["DOCKER_CONTAINER_DIE"])
            with patch.object(docker_events_poller, "docker", MagicMock()), \
                 patch.object(poller, "_align_since_cursor_to_start_time"), \
                 patch.object(docker_events_poller.threading, "Thread") as thread:
                poller.start()
            self.assertTrue(poller.running)
            thread.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
