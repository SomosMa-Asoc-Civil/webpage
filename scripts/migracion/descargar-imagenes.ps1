# Descarga las imágenes del WordPress viejo a public/uploads, respetando las carpetas año/mes.
# Uso (desde la raíz del repo, en PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts/migracion/descargar-imagenes.ps1
# Se puede correr varias veces: saltea las que ya están descargadas.

$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$lista = Join-Path $PSScriptRoot "imagenes.txt"
$destinoBase = Join-Path $raiz "public\uploads"
$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

$urls = Get-Content $lista | Where-Object { $_.Trim() -ne "" }
$ok = 0; $saltadas = 0; $fallas = @()

foreach ($url in $urls) {
    $rel = ($url -replace '^https?://(www\.)?somosma\.com\.ar/wp-content/uploads/', '')
    $rel = [System.Uri]::UnescapeDataString($rel)
    $destino = Join-Path $destinoBase ($rel -replace '/', '\')
    if (Test-Path $destino) { $saltadas++; continue }
    New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
    try {
        Invoke-WebRequest -Uri $url -OutFile $destino -UserAgent $ua -UseBasicParsing
        # Si el antibot devolvió una página HTML en lugar de la imagen, la descarto
        $primeros = [System.IO.File]::ReadAllBytes($destino) | Select-Object -First 15
        if ([System.Text.Encoding]::ASCII.GetString($primeros) -match '<(!DOCTYPE|html)') {
            Remove-Item $destino
            throw "el servidor devolvió HTML (antibot)"
        }
        $ok++
        Write-Host "OK   $rel"
    } catch {
        $fallas += $url
        Write-Host "FALLA $rel -> $($_.Exception.Message)" -ForegroundColor Yellow
    }
    Start-Sleep -Milliseconds 400
}

Write-Host ""
Write-Host "Descargadas: $ok | Ya estaban: $saltadas | Fallaron: $($fallas.Count)"
if ($fallas.Count -gt 0) {
    $fallas | Set-Content (Join-Path $PSScriptRoot "imagenes-fallidas.txt")
    Write-Host "Las fallidas quedaron en scripts/migracion/imagenes-fallidas.txt (volvé a correr el script para reintentar)."
}
