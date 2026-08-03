@echo off
cd /d D:\Dev\repos\teleoperator-mcp
C:\Users\sandr\.local\bin\uv.exe run python -m teleoperator_mcp.server --mode dual --port 10901 >> teleop-serve.out.log 2>&1
