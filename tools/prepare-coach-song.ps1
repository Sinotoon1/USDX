param(
    [Parameter(Mandatory=$true)][string]$CoachRoot,
    [string]$Audio,
    [string]$SongId,
    [Parameter(Mandatory=$true)][string]$Title,
    [string]$Artist='Unknown',
    [string]$SongsRoot=(Join-Path $PSScriptRoot '..\game\songs'),
    [switch]$AllowUnreviewed
)
$ErrorActionPreference='Stop'
$python=Join-Path $CoachRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Coach Python environment missing' }
if ([bool]$Audio -eq [bool]$SongId) { throw 'Specify Audio or SongId, not both' }
$arguments=@((Join-Path $PSScriptRoot 'coach_bridge.py'), '--coach-root', $CoachRoot,
             '--songs-root', $SongsRoot, '--title', $Title, '--artist', $Artist)
if ($Audio) { $arguments+=@('--audio', $Audio) } else { $arguments+=@('--song-id', $SongId) }
if ($AllowUnreviewed) { $arguments+='--allow-unreviewed' }
& $python @arguments
exit $LASTEXITCODE
