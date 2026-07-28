# teleoperator-mcp (MCPB Bundle)

WebXR teleoperation gateway — VR pose streaming to fleet robots via MCP + WebSocket

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "teleoperator-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "teleoperator_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **teleop_status**: teleop_status

## Requirements

- Python 3.12+
- uv
