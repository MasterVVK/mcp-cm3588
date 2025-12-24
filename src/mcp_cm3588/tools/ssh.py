"""SSH tools for CM3588 remote operations."""

import os
from pathlib import Path
from typing import Any

import paramiko
from pydantic import BaseModel, Field

from ..config import config


class SSHResult(BaseModel):
    """Result of an SSH command execution."""

    stdout: str
    stderr: str
    exit_code: int
    success: bool = Field(default=True)


class SSHClient:
    """SSH client for CM3588 operations."""

    def __init__(self):
        self._client: paramiko.SSHClient | None = None

    def _get_client(self) -> paramiko.SSHClient:
        """Get or create SSH client connection."""
        if self._client is None or not self._client.get_transport():
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs: dict[str, Any] = {
                "hostname": config.ssh.host,
                "username": config.ssh.user,
                "port": config.ssh.port,
            }

            if config.ssh.ssh_key:
                key_path = os.path.expanduser(config.ssh.ssh_key)
                if Path(key_path).exists():
                    connect_kwargs["key_filename"] = key_path
            elif config.ssh.password:
                connect_kwargs["password"] = config.ssh.password

            self._client.connect(**connect_kwargs)

        return self._client

    def execute(self, command: str, timeout: int = 30) -> SSHResult:
        """Execute a command on CM3588."""
        try:
            client = self._get_client()
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")

            return SSHResult(
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=exit_code,
                success=exit_code == 0,
            )
        except Exception as e:
            return SSHResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
            )

    def read_file(self, remote_path: str) -> str:
        """Read a file from CM3588."""
        result = self.execute(f"cat {remote_path}")
        if result.success:
            return result.stdout
        raise FileNotFoundError(f"Cannot read {remote_path}: {result.stderr}")

    def write_file(self, remote_path: str, content: str) -> bool:
        """Write content to a file on CM3588."""
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
            return True
        finally:
            sftp.close()

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on CM3588."""
        result = self.execute(f"test -e {remote_path} && echo 'exists'")
        return "exists" in result.stdout

    def get_system_info(self) -> dict[str, Any]:
        """Get system information from CM3588."""
        info = {}

        # CPU info
        result = self.execute("cat /proc/cpuinfo | grep 'model name' | head -1")
        if result.success:
            info["cpu"] = result.stdout.split(":")[-1].strip() if ":" in result.stdout else "RK3588"

        # Memory
        result = self.execute("free -h | grep Mem")
        if result.success:
            parts = result.stdout.split()
            if len(parts) >= 2:
                info["memory_total"] = parts[1]
                info["memory_used"] = parts[2] if len(parts) > 2 else "N/A"

        # Disk
        result = self.execute("df -h / | tail -1")
        if result.success:
            parts = result.stdout.split()
            if len(parts) >= 4:
                info["disk_total"] = parts[1]
                info["disk_used"] = parts[2]
                info["disk_percent"] = parts[4]

        # NPU status
        result = self.execute("cat /sys/kernel/debug/rknpu/version 2>/dev/null || echo 'N/A'")
        info["npu_driver"] = result.stdout.strip()

        # Temperature
        result = self.execute(
            "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo '0'"
        )
        try:
            temp = int(result.stdout.strip()) / 1000
            info["cpu_temp"] = f"{temp:.1f}C"
        except ValueError:
            info["cpu_temp"] = "N/A"

        # Uptime
        result = self.execute("uptime -p")
        info["uptime"] = result.stdout.strip()

        return info

    def get_service_status(self, service_name: str) -> dict[str, Any]:
        """Get status of a systemd service."""
        result = self.execute(f"systemctl is-active {service_name}")
        is_active = result.stdout.strip() == "active"

        result = self.execute(f"systemctl status {service_name} --no-pager -l")

        return {
            "name": service_name,
            "active": is_active,
            "status": result.stdout if result.success else result.stderr,
        }

    def check_port(self, port: int) -> bool:
        """Check if a port is listening."""
        result = self.execute(f"ss -tlnp | grep :{port}")
        return bool(result.stdout.strip())

    def close(self) -> None:
        """Close SSH connection."""
        if self._client:
            self._client.close()
            self._client = None


# Global SSH client instance
ssh_client = SSHClient()
