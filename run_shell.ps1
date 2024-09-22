# Funzione per verificare se un comando è disponibile
function Test-Command($command) {
    try { Get-Command $command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Funzione per installare un pacchetto pip
function Install-PipPackage($package) {
    Write-Host "Installazione di $package via pip..." -ForegroundColor Green
    python -m pip install $package
}

# Verifica se Python è installato
if (-not (Test-Command "python")) {
    Write-Host "Python non trovato. Per favore, installa Python 3 da https://www.python.org/downloads/" -ForegroundColor Red
    exit
}

# Verifica se pip è installato
if (-not (Test-Command "pip")) {
    Write-Host "pip non trovato. Installazione in corso..." -ForegroundColor Yellow
    Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
    python get-pip.py
    Remove-Item get-pip.py
}

# Lista delle dipendenze pip
$dependencies = @("requests", "prompt_toolkit", "openai")

# Verifica e installa le dipendenze pip
foreach ($dep in $dependencies) {
    if (-not (python -m pip show $dep 2>$null)) {
        Write-Host "$dep non trovato. Installazione in corso..." -ForegroundColor Yellow
        Install-PipPackage $dep
    }
}

# Esegui lo script Python
Write-Host "Avvio di shellbrain.py..." -ForegroundColor Green
python shellbrain.py --keep
