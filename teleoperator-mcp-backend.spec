# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — produce teleoperator-mcp-backend.exe for Tauri NSIS embedding.
# Fleet standard: strip=False, upx=False, noarchive=True (see tauri_nsis_building.md).
# Usage (from repo root):
#   uv run pyinstaller teleoperator-mcp-backend.spec --distpath dist --clean --noconfirm

block_cipher = None

a = Analysis(
    ["src/teleoperator_mcp/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[("src/teleoperator_mcp", "teleoperator_mcp")],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "h11",
        "beartype",
        "websockets",
        "sqlite3",
        "_strptime",
        "_datetime",
        "cachetools",
        "pytz",
        "jsonschema",
        "joserfc",
        "joserfc.jwk",
        "joserfc.jwt",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "setuptools", "pip", "wheel", "test", "tests", "unittest", "_distutils_hack"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,
)
# Strip .dist-info but preserve metadata for packages that need it at runtime
_keep_dist = ["fastmcp-", "fastmcp_slim-", "mcp-", "prefab_ui-", "opentelemetry", "email_validator-"]
_saved = [
    e
    for e in a.datas
    if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and ".dist-info" in str(e[0])
]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and ".dist-info" in str(e[0]))]
a.datas.extend(_saved)
SKIP = [
    "torch",
    "playwright",
    "bitsandbytes",
    "llvmlite",
    "pyarrow",
    "pymupdf",
    "grpc",
    "numba",
    "Cython",
    "google",
    "azure",
    "boto3",
    "botocore",
    "matplotlib",
    # NOTE: "PIL" intentionally NOT in SKIP - teleoperator_mcp.livekit.mjpeg
    # imports PIL.Image for MJPEG decoding; stripping it breaks the frozen
    # backend at import time (ImportError: cannot import name '_imaging').
    "pandas",
    "scipy",
    "sklearn",
    "onnxruntime",
]
def _skip_binary(dest_path: str) -> bool:
    low = dest_path.lower().replace("/", "\\")
    # "scipy" as a bare substring also matches numpy's own vendored BLAS lib
    # (numpy.libs\libscipy_openblas64_-*.dll) - only skip real scipy package
    # files, identified by "scipy" as a path segment, not a substring.
    if low.startswith("scipy\\") or low.startswith("scipy-") or "\\scipy\\" in low:
        return True
    return any(s for s in SKIP if s != "scipy" and s.lower() in low)


a.binaries = [b for b in a.binaries if not _skip_binary(b[0])]
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="teleoperator-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
