# Usa el zip de Simply Static para:
#   1) copiar a public/uploads SOLO las imágenes que usa el sitio (las de imagenes.txt)
#   2) armar un zip chico con el HTML y CSS de las páginas, como referencia de diseño
#
# Uso (desde la raíz del repo, en PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts/migracion/preparar-desde-simply-static.ps1 -Zip "C:\Users\ponce\Downloads\simply-static-1-1793729312.zip"

param(
    [Parameter(Mandatory = $true)][string]$Zip
)

$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tmp = Join-Path $env:TEMP "somosma-static"

Write-Host "Descomprimiendo (puede tardar un poco)..."
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive -Path $Zip -DestinationPath $tmp

# Simply Static a veces mete todo dentro de una carpeta: buscamos dónde está wp-content
$wp = Get-ChildItem $tmp -Directory -Recurse -Filter "wp-content" | Select-Object -First 1
if (-not $wp) { throw "No encontré la carpeta wp-content dentro del zip." }
$base = Split-Path $wp.FullName
$uploads = Join-Path $wp.FullName "uploads"

# 1) Imágenes
$destinoBase = Join-Path $raiz "public\uploads"
$ok = 0; $faltan = @()
foreach ($url in Get-Content (Join-Path $PSScriptRoot "imagenes.txt")) {
    if (-not $url.Trim()) { continue }
    $rel = [System.Uri]::UnescapeDataString(($url -replace '^https?://(www\.)?somosma\.com\.ar/wp-content/uploads/', '')) -replace '/', '\'
    $origen = Join-Path $uploads $rel
    $destino = Join-Path $destinoBase $rel
    if (Test-Path $origen) {
        New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
        Copy-Item $origen $destino -Force
        $ok++
    } else { $faltan += $url }
}
Write-Host "Imágenes copiadas: $ok | No estaban en el zip: $($faltan.Count)"
if ($faltan.Count) {
    $faltan | Set-Content (Join-Path $PSScriptRoot "imagenes-fallidas.txt")
    Write-Host "Las que faltan quedaron en scripts/migracion/imagenes-fallidas.txt (bajalas con descargar-imagenes.ps1)."
}

# 2) Referencia de diseño: HTML de las páginas principales + CSS
$ref = Join-Path $env:TEMP "somosma-referencia"
if (Test-Path $ref) { Remove-Item $ref -Recurse -Force }
New-Item -ItemType Directory -Path $ref | Out-Null
$paginas = @("", "nosotras", "que-hacemos", "noticias-2", "sumate", "contacto", "dia-del-padre-mundial-y-deuda-alimentaria")
foreach ($p in $paginas) {
    $html = if ($p) { Join-Path $base "$p\index.html" } else { Join-Path $base "index.html" }
    if (Test-Path $html) {
        $nombre = if ($p) { "$p.html" } else { "inicio.html" }
        Copy-Item $html (Join-Path $ref $nombre)
    }
}
$css = Join-Path $ref "css"
New-Item -ItemType Directory -Path $css | Out-Null
Get-ChildItem $base -Recurse -Include *.css | Where-Object { $_.FullName -match 'kubio|themes|uploads' -and $_.Length -lt 2MB } |
    ForEach-Object { Copy-Item $_.FullName (Join-Path $css (($_.FullName.Substring($base.Length + 1)) -replace '[\\/]', '__')) }

$salida = Join-Path $raiz "referencia-diseno.zip"
if (Test-Path $salida) { Remove-Item $salida }
Compress-Archive -Path (Join-Path $ref "*") -DestinationPath $salida
$mb = [math]::Round((Get-Item $salida).Length / 1MB, 2)
Write-Host "Listo: referencia-diseno.zip ($mb MB) en la raíz del repo. Ese es el que hay que enviar (no lo subas al repo)."

Remove-Item $tmp -Recurse -Force
Remove-Item $ref -Recurse -Force
