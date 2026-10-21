#!/usr/bin/env python3
"""Control del laboratorio. Python 3.9+, sin dependencias de pip."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
COMPOSE = ["docker", "compose", "--project-directory", str(ROOT), "-f", str(ROOT / "compose.yaml")]
CASES = ("attack", "below", "success", "different-ip", "different-user", "different-service", "malformed")


def call(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def compose(*args, **kwargs):
    return call(COMPOSE + list(args), **kwargs)


def inside(*args, **kwargs):
    return compose("exec", "-T", "manager", *args, **kwargs)


def init():
    for kind in ("decoders", "rules", "input", "evidence"):
        (RUNTIME / kind).mkdir(parents=True, exist_ok=True)
    (RUNTIME / "input/auth.log").touch(exist_ok=True)
    for kind, filename in (("decoders", "local_decoder.xml"), ("rules", "local_rules.xml")):
        dest = RUNTIME / kind / filename
        if not dest.exists():
            shutil.copy2(ROOT / "exercises" / kind / filename, dest)


def event(run_id, status="FAIL", ip="192.0.2.10", user="ana", service="portal"):
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return f"lab-auth: ts={timestamp} user={user} src={ip} result={status} service={service} run={run_id}"


def events(case, run_id):
    count = 4 if case == "below" else 5
    result = []
    for i in range(count):
        line = event(run_id,
                     status="SUCCESS" if case == "success" else "FAIL",
                     ip=f"192.0.2.{i + 20}" if case == "different-ip" else "192.0.2.10",
                     user=f"user{i}" if case == "different-user" else "ana",
                     service=f"app{i}" if case == "different-service" else "portal")
        if case == "malformed":
            line = line.replace("src=192.0.2.10 ", "")
        result.append(line)
    return result


def wait_ready():
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        p = compose("ps", "-q", "manager", capture_output=True)
        cid = p.stdout.strip()
        if cid:
            state = call(["docker", "inspect", "--format", "{{.State.Health.Status}}", cid], capture_output=True).stdout.strip()
            if state == "healthy":
                time.sleep(3)  # logcollector termina de abrir el archivo monitorizado
                print("Manager listo.")
                return
            if state == "unhealthy":
                break
        time.sleep(2)
    raise RuntimeError("Manager no disponible. Ejecuta: python3 scripts/lab.py logs")


def validate():
    inside("/var/ossec/bin/wazuh-analysisd", "-t")
    inside("/var/ossec/bin/wazuh-logcollector", "-t")
    print("Configuracion aceptada por Wazuh.")


def apply():
    # Copia en el contenedor, valida y restaura si hay error. El trabajo local se conserva.
    shell = '''set -eu
cp /var/ossec/etc/decoders/local_decoder.xml /tmp/lab-decoder.backup
cp /var/ossec/etc/rules/local_rules.xml /tmp/lab-rules.backup
cp /wazuh-config-mount/etc/decoders/local_decoder.xml /var/ossec/etc/decoders/local_decoder.xml
cp /wazuh-config-mount/etc/rules/local_rules.xml /var/ossec/etc/rules/local_rules.xml
if ! /var/ossec/bin/wazuh-analysisd -t; then
  cp /tmp/lab-decoder.backup /var/ossec/etc/decoders/local_decoder.xml
  cp /tmp/lab-rules.backup /var/ossec/etc/rules/local_rules.xml
  exit 1
fi
'''
    inside("bash", "-c", shell)
    compose("restart", "manager")
    wait_ready()


def solution():
    init()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = RUNTIME / "backups" / stamp
    for kind, filename in (("decoders", "local_decoder.xml"), ("rules", "local_rules.xml")):
        (backup / kind).mkdir(parents=True, exist_ok=True)
        shutil.copy2(RUNTIME / kind / filename, backup / kind / filename)
        shutil.copy2(ROOT / "solutions" / kind / filename, RUNTIME / kind / filename)
    print(f"Solucion copiada; trabajo anterior en {backup}. Ejecuta apply si el manager esta encendido.")


def logtest(lines):
    p = inside("/var/ossec/bin/wazuh-logtest", input="\n".join(lines) + "\n", capture_output=True)
    output = p.stdout + p.stderr
    if "error when connecting" in output or "ERROR:" in output:
        raise RuntimeError(output)
    return output


def test():
    validate()
    for case in CASES:
        output = logtest(events(case, uuid.uuid4().hex))
        (RUNTIME / "evidence" / f"logtest-{case}.txt").write_text(output)
        ids = re.findall(r"\bid: '([0-9]+)'", output)
        if case == "attack":
            assert ids == ["100101"] * 4 + ["100110"], f"Umbral incorrecto: {ids}"
            assert "srcip: '192.0.2.10'" in output and "dstuser: 'ana'" in output, "Campos normalizados ausentes"
        elif case == "success":
            assert ids == ["100102"] * 5, ids
        elif case == "malformed":
            assert not any(x in ("100101", "100102", "100110") for x in ids), ids
        else:
            assert ids == ["100101"] * len(events(case, "test")), ids
        print(f"PASS logtest: {case}")


def replay(case, interval):
    init()
    run_id = uuid.uuid4().hex
    lines = events(case, run_id)
    with (RUNTIME / "input/auth.log").open("a", buffering=1) as handle:
        for line in lines:
            handle.write(line + "\n")
            handle.flush()
            time.sleep(interval)
    print(f"Inyectados {len(lines)} eventos, escenario={case}, run_id={run_id}")
    return run_id, lines


def read_json(path):
    p = inside("bash", "-c", 'if [ -f "$1" ]; then cat "$1"; fi', "--", path, capture_output=True)
    rows = []
    for line in p.stdout.splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # Una ultima linea puede estar en escritura.
    return rows


def e2e():
    validate()
    report = {"tested_at": dt.datetime.now(dt.timezone.utc).isoformat(), "cases": []}
    for case in CASES:
        run_id, lines = replay(case, 0.2)
        deadline = time.monotonic() + 35
        archived, alerts = [], []
        while time.monotonic() < deadline:
            archived = [r for r in read_json("/var/ossec/logs/archives/archives.json") if f"run={run_id}" in r.get("full_log", "")]
            alerts = [r for r in read_json("/var/ossec/logs/alerts/alerts.json") if r.get("data", {}).get("run_id") == run_id]
            if len(archived) >= len(lines):
                time.sleep(1)
                alerts = [r for r in read_json("/var/ossec/logs/alerts/alerts.json") if r.get("data", {}).get("run_id") == run_id]
                break
            time.sleep(1)
        assert len(archived) == len(lines), f"{case}: ingesta incompleta {len(archived)}/{len(lines)}"
        ids = [r["rule"]["id"] for r in alerts]
        expected = (["100101"] * 4 + ["100110"] if case == "attack" else
                    ["100102"] * 5 if case == "success" else
                    [] if case == "malformed" else ["100101"] * len(lines))
        assert ids == expected, f"{case}: alertas {ids}; se esperaba {expected}"
        if case == "attack":
            assert "T1110.001" in alerts[-1]["rule"]["mitre"]["id"]
            assert alerts[-1]["data"]["srcip"] == "192.0.2.10"
        report["cases"].append({"case": case, "run_id": run_id, "ingested": len(archived), "alerts": alerts, "passed": True})
        print(f"PASS pipeline: {case}")
    (RUNTIME / "evidence/e2e.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def doctor():
    print(f"Python: {sys.version.split()[0]}; sistema: {sys.platform}")
    call(["docker", "compose", "version"])
    call(["docker", "info", "--format", "Docker: {{.OSType}}/{{.Architecture}}; RAM del motor: {{.MemTotal}} bytes"])
    free = shutil.disk_usage(ROOT).free / 1024**3
    print(f"Disco libre en el repositorio: {free:.1f} GiB")
    if sys.platform != "linux":
        print("AVISO: plataforma del taller = Linux x86_64. Este host requiere VM/emulacion.")
    if free < 50:
        print("AVISO: el anuncio pide 50 GB libres.")
    compose("config", "--quiet")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "doctor", "prepare", "up", "apply", "validate", "solution", "logtest", "test", "replay", "e2e", "alerts", "archives", "logs", "stats", "down", "export", "load"))
    parser.add_argument("--case", choices=CASES, default="attack")
    parser.add_argument("--interval", type=float, default=0.2)
    args = parser.parse_args()
    if args.interval < 0:
        parser.error("--interval debe ser >= 0")
    init()
    if args.command == "init":
        print("Ejercicios en runtime/decoders y runtime/rules; no se sobrescribe trabajo existente.")
    elif args.command == "doctor":
        doctor()
    elif args.command == "prepare":
        compose("build", "--pull")
    elif args.command == "up":
        compose("up", "-d", "--no-build", "--pull", "never")
        wait_ready()
    elif args.command == "apply":
        apply()
    elif args.command == "solution":
        solution()
    elif args.command == "validate":
        validate()
    elif args.command == "logtest":
        print(logtest(sys.stdin.read().splitlines()))
    elif args.command == "test":
        test()
    elif args.command == "replay":
        replay(args.case, args.interval)
    elif args.command == "e2e":
        e2e()
    elif args.command in ("alerts", "archives"):
        name = args.command
        inside("tail", "-n", "20", "-F", f"/var/ossec/logs/{name}/{name}.json")
    elif args.command == "logs":
        compose("logs", "--tail", "100", "manager")
    elif args.command == "stats":
        cid = compose("ps", "-q", "manager", capture_output=True).stdout.strip()
        if not cid:
            raise RuntimeError("El manager no esta ejecutandose")
        call(["docker", "stats", "--no-stream", cid])
    elif args.command == "down":
        compose("down", "--volumes")
    elif args.command == "export":
        (ROOT / "dist").mkdir(exist_ok=True)
        call(["docker", "save", "-o", str(ROOT / "dist/soc-pipeline-manager.tar"), "soc-pipeline-manager:4.14.1-lab1"])
    elif args.command == "load":
        call(["docker", "load", "-i", str(ROOT / "dist/soc-pipeline-manager.tar")])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except (subprocess.CalledProcessError, RuntimeError, AssertionError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr or "", file=sys.stderr)
        sys.exit(1)
