#!/usr/bin/env python3
"""Blender MCP Python Client to execute scripts directly inside running Blender."""

import json
import socket
import sys

def exec_blender_code(code: str, host: str = "127.0.0.1", port: int = 9876, strict_json: bool = False) -> dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    req = {
        "type": "execute",
        "code": code,
        "strict_json": strict_json
    }
    
    payload = json.dumps(req).encode("utf-8") + b"\x00"
    sock.sendall(payload)
    
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf.extend(chunk)
        if b"\x00" in buf:
            break
            
    sock.close()
    raw = buf.decode("utf-8").rstrip("\x00")
    return json.loads(raw)

if __name__ == "__main__":
    test_code = """
import bpy
result = {
    "blender_version": list(bpy.app.version),
    "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
    "objects": [o.name for o in bpy.data.objects]
}
"""
    res = exec_blender_code(test_code)
    print("=== CONNECTED TO BLENDER MCP SERVER ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
