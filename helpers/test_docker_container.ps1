# Test script for containerized MCP servers
# Run: .\test_docker_container.ps1

Write-Host "Testing Containerized MCP Servers" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Test 1: Ping Server
Write-Host "`n[TEST 1] Testing Ping MCP Server" -ForegroundColor Yellow
Write-Host "Starting ping server in container..." -ForegroundColor Gray

$pingTest = docker run --rm --network host `
    -e ENABLED_SERVERS=ping `
    -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml `
    -v "$PWD/ansible_hosts.example.yml:/config/ansible_hosts.yml:ro" `
    homelab-mcp:latest 2>&1 | Select-String -Pattern "Starting|Loaded|hosts"

if ($pingTest) {
    Write-Host "✓ Ping server started successfully:" -ForegroundColor Green
    $pingTest | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
} else {
    Write-Host "✗ Ping server test failed" -ForegroundColor Red
}

# Test 2: Docker Server
Write-Host "`n[TEST 2] Testing Docker/Podman MCP Server" -ForegroundColor Yellow
Write-Host "Starting docker server in container..." -ForegroundColor Gray

$dockerTest = docker run --rm --network host `
    -e ENABLED_SERVERS=docker `
    -e ANSIBLE_INVENTORY_PATH=/config/ansible_hosts.yml `
    -v "$PWD/ansible_hosts.example.yml:/config/ansible_hosts.yml:ro" `
    homelab-mcp:latest 2>&1 | Select-String -Pattern "Starting|Loaded|Docker|Podman"

if ($dockerTest) {
    Write-Host "✓ Docker server started successfully:" -ForegroundColor Green
    $dockerTest | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
} else {
    Write-Host "✗ Docker server test failed" -ForegroundColor Red
}

# Test 3: Image Info
Write-Host "`n[TEST 3] Image Information" -ForegroundColor Yellow
$imageInfo = docker images homelab-mcp
Write-Host $imageInfo -ForegroundColor Gray

Write-Host "`n=================================" -ForegroundColor Green
Write-Host "Testing Complete!" -ForegroundColor Green
