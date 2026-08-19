"""PyInstaller entry point — dual transport (MCP_PORT → HTTP, fallback → stdio)."""

import os
import sys

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--mode", "http", "--host", host, "--port", str(port)]
from teleoperator_mcp.server import main

if __name__ == "__main__":
    main()
