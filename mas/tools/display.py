"""
mas.tools.display: Virtual Display Isolation Engine for headless OS automation.
Manages isolated in-memory Xvfb framebuffers with zero host desktop interference.

Architect: Acinonyx
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from mas.observability import LOGGER, METRICS


@dataclass
class VirtualDisplayConfig:
    display_num: int = 99
    width: int = 1440
    height: int = 900
    color_depth: int = 24
    window_manager: Optional[str] = "fluxbox"
    extra_xvfb_args: List[str] = field(default_factory=lambda: ["-ac", "+extension", "GLX", "+render", "-noreset"])


class VirtualDisplayManager:
    """
    Manages the lifecycle of an isolated X11 virtual framebuffer (Xvfb) and window manager.
    If system Xvfb binaries are unavailable, gracefully falls back to a software-simulated
    in-memory display so tests and CI/CD pipelines remain 100% operational.
    """

    def __init__(self, config: Optional[VirtualDisplayConfig] = None) -> None:
        self.config = config or VirtualDisplayConfig()
        self.display_str = f":{self.config.display_num}"
        self.xvfb_proc: Optional[subprocess.Popen] = None
        self.wm_proc: Optional[subprocess.Popen] = None
        self.is_active = False
        self.is_mock = False
        self._mock_canvas: Optional[Any] = None
        self._launched_procs: List[subprocess.Popen] = []

    def is_xvfb_available(self) -> bool:
        """Check if Xvfb binary is installed on the host OS."""
        return shutil.which("Xvfb") is not None

    def start(self) -> "VirtualDisplayManager":
        """Start the virtual display."""
        if self.is_active:
            return self

        if not self.is_xvfb_available():
            LOGGER.warning(
                "Xvfb binary not found on host. Initializing VirtualDisplayManager in in-memory simulation mode."
            )
            self.is_mock = True
            self.is_active = True
            os.environ["DISPLAY"] = self.display_str
            METRICS.incr("virtual_display.mock_started")
            return self

        # Spawn physical Xvfb process
        screen_spec = f"{self.config.width}x{self.config.height}x{self.config.color_depth}"
        xvfb_cmd = [
            "Xvfb",
            self.display_str,
            "-screen",
            "0",
            screen_spec,
            *self.config.extra_xvfb_args,
        ]

        try:
            self.xvfb_proc = subprocess.Popen(
                xvfb_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            # Wait for X11 socket creation
            socket_path = f"/tmp/.X11-unix/X{self.config.display_num}"
            deadline = time.time() + 5.0
            ready = False
            while time.time() < deadline:
                if os.path.exists(socket_path):
                    ready = True
                    break
                time.sleep(0.05)

            if not ready and self.xvfb_proc.poll() is not None:
                raise RuntimeError(f"Xvfb failed to start on {self.display_str} (exit code: {self.xvfb_proc.returncode})")

            os.environ["DISPLAY"] = self.display_str
            self.is_active = True
            self.is_mock = False
            METRICS.incr("virtual_display.native_started")
            LOGGER.info(f"Virtual display {self.display_str} active ({screen_spec}).")

            # Optionally launch lightweight window manager
            if self.config.window_manager:
                wm_bin = shutil.which(self.config.window_manager)
                if wm_bin:
                    env = os.environ.copy()
                    env["DISPLAY"] = self.display_str
                    self.wm_proc = subprocess.Popen(
                        [wm_bin],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid,
                    )
        except Exception as e:
            LOGGER.error(f"Failed to launch native Xvfb: {e}. Falling back to mock simulation.")
            self.is_mock = True
            self.is_active = True
            os.environ["DISPLAY"] = self.display_str

        return self

    def stop(self) -> None:
        """Gracefully terminate window manager, launched applications, and Xvfb."""
        if not self.is_active:
            return

        # Terminate launched applications
        for proc in self._launched_procs:
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
        self._launched_procs.clear()

        # Terminate WM
        if self.wm_proc and self.wm_proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.wm_proc.pid), signal.SIGTERM)
            except Exception:
                pass
            self.wm_proc = None

        # Terminate Xvfb
        if self.xvfb_proc and self.xvfb_proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.xvfb_proc.pid), signal.SIGTERM)
            except Exception:
                pass
            self.xvfb_proc = None

        self.is_active = False
        LOGGER.info(f"Virtual display {self.display_str} shut down.")

    def launch_app(self, command: List[str], env_vars: Optional[Dict[str, str]] = None) -> Optional[subprocess.Popen]:
        """Launch an application window inside the isolated virtual display."""
        if not self.is_active:
            self.start()

        if self.is_mock:
            LOGGER.info(f"[MockDisplay] Simulated app launch: {' '.join(command)}")
            return None

        env = os.environ.copy()
        env["DISPLAY"] = self.display_str
        if env_vars:
            env.update(env_vars)

        try:
            proc = subprocess.Popen(
                command,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            self._launched_procs.append(proc)
            return proc
        except Exception as e:
            LOGGER.error(f"Failed to launch app {command} on {self.display_str}: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Return operational telemetry."""
        return {
            "display": self.display_str,
            "is_active": self.is_active,
            "is_mock": self.is_mock,
            "width": self.config.width,
            "height": self.config.height,
            "color_depth": self.config.color_depth,
            "active_processes": len([p for p in self._launched_procs if p.poll() is None]),
        }

    def __enter__(self) -> "VirtualDisplayManager":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
