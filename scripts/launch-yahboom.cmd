@echo off
cd /d D:\Dev\repos\yahboom-mcp
C:\Users\sandr\.local\bin\uv.exe run python -m yahboom_mcp.server --mode dual --port 10892 >> yahboom-serve.out.log 2>&1
