$ErrorActionPreference = "Stop"
& wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant && ./scripts/stop-services.sh'
if ($LASTEXITCODE -ne 0) {
    throw "Az AI Assistant leallitasa sikertelen."
}