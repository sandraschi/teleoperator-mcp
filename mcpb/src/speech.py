"""Spoken warnings via speech-mcp REST, with Windows SAPI fallback."""

from __future__ import annotations

import asyncio
import logging

import httpx

from .config import settings

logger = logging.getLogger("teleoperator_mcp.speech")


async def speak_warning(text: str, *, provider: str | None = None) -> dict:
    """Play a short warning on the workstation speaker."""
    if not settings.speech_enabled:
        logger.info("speech disabled, would say: %s", text)
        return {"success": True, "spoken": False, "reason": "speech_disabled"}

    prov = provider or settings.speech_provider
    url = f"{settings.speech_mcp_url.rstrip('/')}/api/v1/tts"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"text": text, "provider": prov})
            if resp.status_code == 200:
                body = resp.json()
                logger.info("speech-mcp: %s", text[:80])
                return {"success": True, "spoken": True, "provider": body.get("provider", prov)}
    except Exception as exc:
        logger.warning("speech-mcp failed (%s), falling back to SAPI", exc)

    ok = await _windows_sapi(text)
    return {"success": ok, "spoken": ok, "provider": "windows_sapi"}


async def _windows_sapi(text: str) -> bool:
    safe = text.replace('"', "'").replace("`", "'")
    cmd = (
        "Add-Type -AssemblyName System.Speech; "
        f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\"{safe}\")"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-Command",
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=45.0)
        return proc.returncode == 0
    except Exception as exc:
        logger.error("SAPI fallback failed: %s", exc)
        return False
