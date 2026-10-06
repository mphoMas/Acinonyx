"""
mas.organization.executive: Executive-tier agents for ACG.

CIOAgent — Chief Information Officer.
Responsibility: Infrastructure observability, technology inventory,
capacity planning, and internal audit governance.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import platform
import os
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from mas.core.agent import BaseAgent
from mas.core.message import Role
from mas.mcp.transport import MCPClient


# ---------------------------------------------------------------------------
# Audit Data-Model
# ---------------------------------------------------------------------------

@dataclass
class HardwareProfile:
    os_name: str
    os_release: str
    os_version: str
    machine: str
    processor: str
    hostname: str
    cpu_count_logical: int
    cpu_count_physical: Optional[int]
    total_ram_gb: float
    available_ram_gb: float
    swap_total_gb: float
    swap_free_gb: float
    disk_partitions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SoftwareProfile:
    python_version: str
    python_executable: str
    python_path: str
    installed_binaries: Dict[str, str] = field(default_factory=dict)   # binary → path or "not found"
    pip_packages: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkspaceProfile:
    root_path: str
    total_files: int
    total_dirs: int
    total_size_mb: float
    top_level_dirs: List[str] = field(default_factory=list)
    python_modules: List[str] = field(default_factory=list)


@dataclass
class InfrastructureAuditReport:
    audit_timestamp: str
    auditor: str
    company: str
    hardware: HardwareProfile
    software: SoftwareProfile
    workspace: WorkspaceProfile
    recommendations: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        hw = self.hardware
        sw = self.software
        ws = self.workspace
        lines = [
            "# 🖥️  CIO Infrastructure Audit Report",
            f"**Company:** {self.company}",
            f"**Auditor:** {self.auditor}",
            f"**Timestamp:** {self.audit_timestamp}",
            "",
            "---",
            "",
            "## 1. Hardware Profile",
            "| Field | Value |",
            "|---|---|",
            f"| OS | {hw.os_name} {hw.os_release} |",
            f"| Kernel | {hw.os_version} |",
            f"| Architecture | {hw.machine} |",
            f"| Processor | {hw.processor or 'N/A'} |",
            f"| Hostname | {hw.hostname} |",
            f"| CPU (Logical) | {hw.cpu_count_logical} cores |",
            f"| CPU (Physical) | {hw.cpu_count_physical or 'N/A'} cores |",
            f"| RAM Total | {hw.total_ram_gb:.2f} GB |",
            f"| RAM Available | {hw.available_ram_gb:.2f} GB |",
            f"| Swap Total | {hw.swap_total_gb:.2f} GB |",
            f"| Swap Free | {hw.swap_free_gb:.2f} GB |",
            "",
            "### Disk Partitions",
            "| Mount | Total (GB) | Used (GB) | Free (GB) | Usage% |",
            "|---|---|---|---|---|",
        ]
        for p in hw.disk_partitions:
            lines.append(
                f"| {p.get('mountpoint', '?')} | {p.get('total_gb', '?')} "
                f"| {p.get('used_gb', '?')} | {p.get('free_gb', '?')} "
                f"| {p.get('percent', '?')}% |"
            )
        lines += [
            "",
            "---",
            "",
            "## 2. Software Profile",
            "| Field | Value |",
            "|---|---|",
            f"| Python Version | {sw.python_version} |",
            f"| Python Executable | {sw.python_executable} |",
            f"| Python Path | {sw.python_path} |",
        ]

        available_binaries = {k: v for k, v in sw.installed_binaries.items() if v != "not found"}
        lines += [
            "",
            f"### 🟢 Operational Binary Tooling ({len(available_binaries)} Installed)",
            "| Tool | Path |",
            "|---|---|",
        ]
        for binary, path in sorted(available_binaries.items()):
            lines.append(f"| `{binary}` | `{path}` |")

        # Focus on architecture gaps only
        key_missing = [b for b in ("podman", "sqlite3", "kubectl") if sw.installed_binaries.get(b) == "not found"]
        if key_missing:
            lines += [
                "",
                "### ⚠️ Optional Architecture Absences",
                f"*{', '.join(f'`{b}`' for b in key_missing)}*",
            ]
        if sw.pip_packages:
            lines += [
                "",
                "### Installed Packages (pip list)",
                "```",
            ] + sw.pip_packages[:50] + ["```"]
        if sw.environment_variables:
            lines += [
                "",
                "### Key Environment Variables",
                "| Variable | Value |",
                "|---|---|",
            ]
            for k, v in sw.environment_variables.items():
                lines.append(f"| `{k}` | `{v}` |")
        lines += [
            "",
            "---",
            "",
            "## 3. Workspace Profile",
            "| Field | Value |",
            "|---|---|",
            f"| Root | {ws.root_path} |",
            f"| Total Files | {ws.total_files} |",
            f"| Total Directories | {ws.total_dirs} |",
            f"| Total Size | {ws.total_size_mb:.2f} MB |",
            "",
            "**Top-Level Directories:**",
        ]
        for d in ws.top_level_dirs:
            lines.append(f"- `{d}`")
        lines += [
            "",
            "**Python Module Packages:**",
        ]
        for m in ws.python_modules:
            lines.append(f"- `{m}`")
        lines += [
            "",
            "---",
            "",
            "## 4. Risk Flags 🚨",
        ]
        if self.risk_flags:
            for r in self.risk_flags:
                lines.append(f"- ⚠️  {r}")
        else:
            lines.append("_No critical risks identified._")
        lines += [
            "",
            "## 5. Recommendations 📋",
        ]
        if self.recommendations:
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
        lines += [
            "",
            "## 6. Opportunities 🚀",
        ]
        if self.opportunities:
            for op in self.opportunities:
                lines.append(f"- ✅ {op}")
        lines += ["", "---", "_End of CIO Infrastructure Audit Report_"]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CIO Agent
# ---------------------------------------------------------------------------

class CIOAgent(BaseAgent):
    """
    Chief Information Officer — responsible for infrastructure visibility,
    technology strategy, and internal audit governance at ACG.

    On demand, the CIO performs a full infrastructure audit of the local
    machine and workspace, returning a structured `InfrastructureAuditReport`.
    """

    BINARIES_TO_CHECK = [
        "python3", "python", "pip", "pip3", "uv",
        "git", "git-lfs",
        "node", "npm", "npx",
        "docker", "docker-compose", "podman", "bwrap",
        "kubectl", "helm", "terraform", "ansible",
        "curl", "wget", "ssh", "scp", "rsync",
        "make", "gcc", "g++", "clang",
        "sqlite3", "psql", "mysql",
        "java", "javac", "mvn", "gradle",
        "go", "cargo", "rustc",
        "ffmpeg", "convert",  # ImageMagick
        "htop", "top", "vmstat", "lscpu", "lsblk", "df",
        "systemctl", "journalctl",
        "jq", "yq",
    ]

    IMPORTANT_ENV_VARS = [
        "HOME", "USER", "SHELL", "PATH", "LANG", "LC_ALL",
        "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
        "PYTHONPATH", "PYTHONUSERBASE",
        "XDG_DATA_HOME", "XDG_CONFIG_HOME",
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy",
        "DISPLAY", "WAYLAND_DISPLAY",
        "TERM", "COLORTERM",
        "GPU_DEVICE_ORDINAL", "CUDA_VISIBLE_DEVICES",
    ]

    def __init__(self, mcp_client: Optional[MCPClient] = None) -> None:
        super().__init__(
            name="CIOAgent",
            role=Role.SUPERVISOR,
            system_prompt=(
                "You are the Chief Information Officer (CIO) of Acinonyx Consulting Group. "
                "Your mandate is to maintain complete visibility over infrastructure, "
                "software tooling, and technical capacity. You conduct rigorous audits, "
                "identify risks, and produce strategic recommendations to ensure ACG "
                "operates on a robust, secure, and scalable technology foundation."
            ),
            mcp_client=mcp_client,
        )
        self._last_audit: Optional[InfrastructureAuditReport] = None

    # -----------------------------------------------------------------------
    # Internal Probe Helpers
    # -----------------------------------------------------------------------

    def _probe_hardware(self) -> HardwareProfile:
        uname = platform.uname()

        # --- RAM via /proc/meminfo ---
        total_ram_kb = 0
        available_ram_kb = 0
        swap_total_kb = 0
        swap_free_kb = 0
        try:
            with open("/proc/meminfo") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) >= 2:
                        key, val = parts[0].rstrip(":"), parts[1]
                        if key == "MemTotal":
                            total_ram_kb = int(val)
                        elif key == "MemAvailable":
                            available_ram_kb = int(val)
                        elif key == "SwapTotal":
                            swap_total_kb = int(val)
                        elif key == "SwapFree":
                            swap_free_kb = int(val)
        except OSError:
            pass

        # --- CPU physical count via /proc/cpuinfo ---
        cpu_physical: Optional[int] = None
        try:
            ids: set = set()
            with open("/proc/cpuinfo") as fh:
                for line in fh:
                    if line.startswith("physical id"):
                        ids.add(line.split(":")[1].strip())
            if ids:
                cpu_physical = len(ids)
        except OSError:
            pass

        # --- Disk partitions ---
        partitions = []
        try:
            result = subprocess.run(
                ["df", "-P", "--block-size=1"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        total_bytes = int(parts[1])
                        used_bytes = int(parts[2])
                        free_bytes = int(parts[3])
                        pct = parts[4].rstrip("%")
                        mount = parts[5]
                        # Filter pseudo/overlay/tmpfs to avoid noise
                        if mount.startswith("/") and total_bytes > 0:
                            partitions.append({
                                "mountpoint": mount,
                                "total_gb": round(total_bytes / 1e9, 2),
                                "used_gb": round(used_bytes / 1e9, 2),
                                "free_gb": round(free_bytes / 1e9, 2),
                                "percent": pct,
                            })
                    except ValueError:
                        continue
        except Exception:
            # Fallback to shutil
            du = shutil.disk_usage("/")
            partitions = [{
                "mountpoint": "/",
                "total_gb": round(du.total / 1e9, 2),
                "used_gb": round(du.used / 1e9, 2),
                "free_gb": round(du.free / 1e9, 2),
                "percent": round(du.used / du.total * 100, 1),
            }]

        return HardwareProfile(
            os_name=uname.system,
            os_release=uname.release,
            os_version=uname.version,
            machine=uname.machine,
            processor=uname.processor,
            hostname=uname.node,
            cpu_count_logical=os.cpu_count() or 0,
            cpu_count_physical=cpu_physical,
            total_ram_gb=round(total_ram_kb / 1e6, 2),
            available_ram_gb=round(available_ram_kb / 1e6, 2),
            swap_total_gb=round(swap_total_kb / 1e6, 2),
            swap_free_gb=round(swap_free_kb / 1e6, 2),
            disk_partitions=partitions,
        )

    def _probe_software(self) -> SoftwareProfile:
        import sys

        # --- Binary scan ---
        binaries: Dict[str, str] = {}
        probe_env = {
            **os.environ,
            "PATH": f"/home/acinonyx/Desktop/MAS/bin:{os.environ.get('PATH', '')}",
        }
        for binary in self.BINARIES_TO_CHECK:
            try:
                result = subprocess.run(
                    ["which", binary],
                    env=probe_env,
                    capture_output=True, text=True, timeout=3
                )
                path = result.stdout.strip()
                binaries[binary] = path if path else "not found"
            except Exception:
                binaries[binary] = "not found"

        # --- pip packages ---
        pip_packages: List[str] = []
        for pip_cmd in ("pip3", "pip"):
            try:
                result = subprocess.run(
                    [pip_cmd, "list", "--format=columns"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    pip_packages = result.stdout.strip().splitlines()
                    break
            except Exception:
                continue

        # --- Env vars ---
        env_vars = {
            k: os.environ.get(k, "<not set>")
            for k in self.IMPORTANT_ENV_VARS
        }

        return SoftwareProfile(
            python_version=platform.python_version(),
            python_executable=sys.executable,
            python_path=":".join(sys.path),
            installed_binaries=binaries,
            pip_packages=pip_packages,
            environment_variables=env_vars,
        )

    def _probe_workspace(self, workspace_root: str) -> WorkspaceProfile:
        total_files = 0
        total_dirs = 0
        total_size_bytes = 0
        python_modules: List[str] = []

        try:
            for dirpath, dirnames, filenames in os.walk(workspace_root):
                # Exclude pycache dirs
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                total_dirs += len(dirnames)
                for fname in filenames:
                    total_files += 1
                    try:
                        fpath = os.path.join(dirpath, fname)
                        total_size_bytes += os.path.getsize(fpath)
                    except OSError:
                        pass
        except OSError:
            pass

        top_level = []
        try:
            entries = sorted(os.listdir(workspace_root))
            top_level = entries
        except OSError:
            pass

        # Find Python packages (dirs with __init__.py)
        try:
            for dirpath, dirnames, filenames in os.walk(workspace_root):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                if "__init__.py" in filenames:
                    rel = os.path.relpath(dirpath, workspace_root)
                    python_modules.append(rel)
        except OSError:
            pass

        return WorkspaceProfile(
            root_path=workspace_root,
            total_files=total_files,
            total_dirs=total_dirs,
            total_size_mb=round(total_size_bytes / 1e6, 2),
            top_level_dirs=top_level,
            python_modules=sorted(python_modules),
        )

    def _generate_intelligence(
        self,
        hw: HardwareProfile,
        sw: SoftwareProfile,
        ws: WorkspaceProfile,
    ) -> tuple[list, list, list]:
        """Derive strategic risk flags, recommendations, and opportunities."""
        risks: List[str] = []
        recs: List[str] = []
        opps: List[str] = []

        # RAM assessment
        if hw.total_ram_gb < 4:
            risks.append(f"LOW MEMORY: Only {hw.total_ram_gb:.1f} GB RAM. Multi-agent parallelism will be constrained.")
            recs.append("Upgrade RAM to minimum 16 GB for stable multi-agent orchestration.")
        elif hw.total_ram_gb < 8:
            recs.append(f"RAM is {hw.total_ram_gb:.1f} GB. Consider increasing to 16 GB+ for production LLM inference.")
        else:
            opps.append(f"Adequate RAM ({hw.total_ram_gb:.1f} GB) supports concurrent multi-agent execution.")

        # CPU
        if hw.cpu_count_logical >= 8:
            opps.append(f"{hw.cpu_count_logical} logical CPU cores enable high-concurrency async agent pipelines.")
        else:
            recs.append(f"Only {hw.cpu_count_logical} logical CPUs. Limit parallel agent fan-out to avoid contention.")

        # Disk
        for part in hw.disk_partitions:
            try:
                pct = float(part.get("percent", 0))
                if pct > 90:
                    risks.append(f"DISK CRITICAL: {part['mountpoint']} at {pct}% capacity ({part['free_gb']} GB free).")
                elif pct > 75:
                    recs.append(f"Disk {part['mountpoint']} at {pct}% — monitor closely. Free: {part['free_gb']} GB.")
            except (ValueError, TypeError):
                pass

        # Git
        if sw.installed_binaries.get("git", "not found") == "not found":
            risks.append("git is not available. Version control and remote collaboration are blocked.")
            recs.append("Install git (apt install git) immediately to enable version control.")
        else:
            opps.append("git is available — version control workflows can be activated.")

        # pip / package manager
        if sw.installed_binaries.get("pip3", "not found") == "not found" and \
           sw.installed_binaries.get("pip", "not found") == "not found":
            risks.append("pip is unavailable. Dependency management requires manual binary placement.")
            recs.append("Install pip via 'curl https://bootstrap.pypa.io/get-pip.py | python3' or use uv.")

        if sw.installed_binaries.get("uv", "not found") != "not found":
            opps.append("uv package manager detected — fast dependency resolution available.")

        # Docker
        if sw.installed_binaries.get("docker", "not found") != "not found":
            opps.append("Docker available — containerized agent deployments and sandboxing enabled.")
        else:
            recs.append("Install Docker to enable container-based agent sandboxing and deployment.")

        # curl
        if sw.installed_binaries.get("curl", "not found") != "not found":
            opps.append("curl available — HTTP provider integrations (OpenAI, Ollama) can be activated.")

        # Python version
        py_parts = sw.python_version.split(".")
        if len(py_parts) >= 2:
            major, minor = int(py_parts[0]), int(py_parts[1])
            if major == 3 and minor >= 11:
                opps.append(f"Python {sw.python_version} — asyncio task groups, exception groups, and tomllib available.")
            elif major == 3 and minor < 10:
                risks.append(f"Python {sw.python_version} is below 3.10 — structural pattern matching and modern type hints unavailable.")

        # Workspace size
        if ws.total_size_mb > 500:
            recs.append(f"Workspace is large ({ws.total_size_mb:.0f} MB). Consider archiving old artifacts.")
        opps.append(f"Workspace has {ws.total_files} files across {ws.total_dirs} directories — {len(ws.python_modules)} Python packages registered.")

        # HTTP proxy
        proxy = sw.environment_variables.get("http_proxy") or sw.environment_variables.get("HTTP_PROXY")
        if proxy and proxy != "<not set>":
            risks.append(f"HTTP proxy active ({proxy}). All outbound urllib calls must use ProxyHandler bypass for localhost.")
            recs.append("Ensure all internal test HTTP calls use urllib.request.ProxyHandler({}) to bypass the corporate proxy.")

        # Node.js / frontend
        if sw.installed_binaries.get("node", "not found") != "not found":
            opps.append("Node.js available — React/Next.js frontend tooling can be scaffolded.")

        # SQLite
        if sw.installed_binaries.get("sqlite3", "not found") != "not found":
            opps.append("SQLite3 available — lightweight embedded persistence for agent memory and episodic storage.")

        return risks, recs, opps

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def run_infrastructure_audit(
        self,
        workspace_root: str = "/home/acinonyx/Desktop/MAS",
    ) -> InfrastructureAuditReport:
        """
        Execute a full infrastructure audit. Returns a structured report.
        Synchronous probes are run in a thread executor to not block the event loop.
        """
        import datetime

        loop = asyncio.get_event_loop()

        hw, sw, ws = await asyncio.gather(
            loop.run_in_executor(None, self._probe_hardware),
            loop.run_in_executor(None, self._probe_software),
            loop.run_in_executor(None, self._probe_workspace, workspace_root),
        )

        risks, recs, opps = self._generate_intelligence(hw, sw, ws)

        report = InfrastructureAuditReport(
            audit_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            auditor=self.name,
            company="Acinonyx Consulting Group (ACG)",
            hardware=hw,
            software=sw,
            workspace=ws,
            risk_flags=risks,
            recommendations=recs,
            opportunities=opps,
        )

        self._last_audit = report
        return report

    @property
    def last_audit(self) -> Optional[InfrastructureAuditReport]:
        return self._last_audit
