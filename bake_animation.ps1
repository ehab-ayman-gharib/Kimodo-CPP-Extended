param(
    [Parameter(Mandatory=$true)]
    [string]$Character,

    [Parameter(Mandatory=$true)]
    [string]$Motion,

    [Parameter(Mandatory=$false)]
    [string]$Output = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$blenderPath = "blender.exe"
if (Test-Path "E:\Program Files\Blender Foundation\Blender 5.1\blender.exe") {
    $blenderPath = "E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
} elseif (Test-Path "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe") {
    $blenderPath = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
}

if (-not $Output) {
    $charItem = Get-Item $Character
    $Output = Join-Path $charItem.DirectoryName ($charItem.BaseName + "_animated.glb")
}

Write-Host "Baking Kimodo Motion onto Character using Blender..." -ForegroundColor Cyan
Write-Host "  Character: $Character"
Write-Host "  Motion:    $Motion"
Write-Host "  Output:    $Output"

& "$blenderPath" -b -P "$scriptDir\scripts\bake_to_character.py" -- --character "$Character" --motion "$Motion" --output "$Output"
