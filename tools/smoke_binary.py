#!/usr/bin/env python3
"""Smoke test for a built EYE3 Link program: start it, ask /ping, stop it.
Usage: python3 tools/smoke_binary.py "<command>" [port]      e.g. "./eye3-link-linux" 8791"""
import json, os, shlex, subprocess, sys, time, urllib.request

cmd = shlex.split(sys.argv[1], posix=(os.name != "nt"))
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8791
proc = subprocess.Popen(cmd + ["--port", str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
code = 1
try:
    for _ in range(100):
        if proc.poll() is not None:
            print("the program exited early:", (proc.stdout.read() or b"").decode("utf-8", "replace")[:300])
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/ping" % port, timeout=2) as r:
                data = json.loads(r.read())
            if data.get("name") == "EYE3 Link" and data.get("ok"):
                print("OK", data)
                code = 0
            else:
                print("unexpected answer:", data)
            break
        except Exception:
            time.sleep(0.3)
    else:
        print("the program did not answer on port", port)
finally:
    proc.kill()
sys.exit(code)
