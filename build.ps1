# Build script for FlexTime Pro

Write-Host "Building FlexTime Pro..." -ForegroundColor Cyan

# 1. Compile Tailwind CSS
Write-Host "Compiling Tailwind CSS..." -ForegroundColor Yellow
if (Test-Path ".\tailwindcss.exe") {
    .\tailwindcss.exe -i .\app\static\css\input.css -o .\app\static\css\style.css --minify
} else {
    Write-Host "Tailwind CLI not found. Please download it first." -ForegroundColor Red
}

# 2. Run Python tests (if any)
# Write-Host "Running tests..." -ForegroundColor Yellow
# pytest

Write-Host "Build complete!" -ForegroundColor Green
