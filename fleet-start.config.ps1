# Per-repo fleet start config for teleoperator-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'teleoperator-mcp'
    BackendPort  = 10901
    FrontendPort = 10900
    HealthPath   = '/api/v1/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'teleoperator_mcp.server:app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '10901' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
