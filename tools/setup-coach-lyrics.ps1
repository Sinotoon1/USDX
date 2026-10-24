param([Parameter(Mandatory=$true)][string]$CoachRoot)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $CoachRoot).Path
$AudioPython = Join-Path $Root '.audio-venv\Scripts\python.exe'
$EnvPath = Join-Path $Root '.lyrics-venv'
if (-not (Test-Path -LiteralPath $AudioPython -PathType Leaf)) {
    throw 'Run the existing coach setup_audio.ps1 first.'
}
if (-not (Test-Path -LiteralPath "$EnvPath\Scripts\python.exe" -PathType Leaf)) {
    & $AudioPython -m venv $EnvPath
    if ($LASTEXITCODE -ne 0) { throw 'Lyrics environment creation failed' }
}
$Python = Join-Path $EnvPath 'Scripts\python.exe'
& $Python -m pip install --disable-pip-version-check -r "$PSScriptRoot\requirements-lyrics.lock.txt"
if ($LASTEXITCODE -ne 0) { throw 'Lyrics dependency installation failed' }
$Download = @'
from pathlib import Path
import json,sys
from huggingface_hub import HfApi,snapshot_download
model=Path(sys.argv[1])
repo='Systran/faster-whisper-small'
revision=HfApi().model_info(repo).sha
snapshot_download(repo,revision=revision,local_dir=model,
    allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.*'])
(model/'USDX-MODEL-ORIGIN.json').write_text(json.dumps(
    {'repo':repo,'revision':revision},indent=2),encoding='utf-8')
print('LYRICS SETUP OK: local small model; revision='+revision)
'@
& $Python -c $Download (Join-Path $Root '.models\faster-whisper-small')
if ($LASTEXITCODE -ne 0) { throw 'Lyrics model download failed' }
