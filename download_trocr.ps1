# TrOCR Model Downloader for Smart-Audit-Agent
# Downloads the TrOCR handwriting recognition model from HuggingFace
# Run this script once to download the model before deployment

$ErrorActionPreference = "Stop"

# Configuration
$MODEL_NAME = "microsoft/trocr-base-handwritten"
$BASE_URL = "https://huggingface.co/$MODEL_NAME/resolve/main"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$MODELS_DIR = Join-Path $SCRIPT_DIR "models\trocr-base-handwritten"

# Files to download
$FILES = @(
    @{name="model.safetensors"; size="1.33 GB"; required=$true},
    @{name="config.json"; size="4 KB"; required=$true},
    @{name="preprocessor_config.json"; size="224 B"; required=$true},
    @{name="tokenizer_config.json"; size="1 KB"; required=$false},
    @{name="vocab.json"; size="899 KB"; required=$false},
    @{name="merges.txt"; size="456 KB"; required=$false},
    @{name="special_tokens_map.json"; size="238 B"; required=$false},
    @{name="generation_config.json"; size="188 B"; required=$false}
)

function Write-Header {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  TrOCR Model Downloader - Smart-Audit-Agent" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Model: $MODEL_NAME"
    Write-Host "Target: $MODELS_DIR"
    Write-Host ""
}

function Test-ModelExists {
    $mainModel = Join-Path $MODELS_DIR "model.safetensors"
    $config = Join-Path $MODELS_DIR "config.json"
    return (Test-Path $mainModel) -and (Test-Path $config)
}

function Get-FileWithProgress {
    param(
        [string]$Url,
        [string]$OutFile,
        [string]$DisplayName
    )
    
    try {
        # Use BITS for better download experience with resume support
        $job = Start-BitsTransfer -Source $Url -Destination $OutFile -DisplayName $DisplayName -Asynchronous
        
        while ($job.JobState -eq "Transferring" -or $job.JobState -eq "Connecting") {
            $percent = [math]::Round(($job.BytesTransferred / $job.BytesTotal) * 100, 1)
            $transferred = [math]::Round($job.BytesTransferred / 1MB, 1)
            $total = [math]::Round($job.BytesTotal / 1MB, 1)
            Write-Progress -Activity "Downloading $DisplayName" -Status "$transferred MB / $total MB" -PercentComplete $percent
            Start-Sleep -Milliseconds 500
        }
        
        Write-Progress -Activity "Downloading $DisplayName" -Completed
        
        if ($job.JobState -eq "Transferred") {
            Complete-BitsTransfer -BitsJob $job
            return $true
        } else {
            Remove-BitsTransfer -BitsJob $job
            return $false
        }
    }
    catch {
        # Fallback to Invoke-WebRequest if BITS fails
        Write-Host "    Using alternative download method..." -ForegroundColor Yellow
        try {
            $ProgressPreference = 'Continue'
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
            return $true
        }
        catch {
            return $false
        }
    }
}

function Download-TrOCRModel {
    Write-Header
    
    # Check if model already exists
    if (Test-ModelExists) {
        Write-Host "Model already downloaded!" -ForegroundColor Green
        Write-Host "Location: $MODELS_DIR"
        Write-Host ""
        $response = Read-Host "Re-download? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Skipping download." -ForegroundColor Yellow
            return $true
        }
    }
    
    # Create models directory
    if (-not (Test-Path $MODELS_DIR)) {
        New-Item -ItemType Directory -Path $MODELS_DIR -Force | Out-Null
        Write-Host "Created directory: $MODELS_DIR" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Downloading model files..." -ForegroundColor Cyan
    Write-Host "(This may take 10-30 minutes depending on your connection)"
    Write-Host ""
    
    $success = $true
    $downloaded = 0
    $total = $FILES.Count
    
    foreach ($file in $FILES) {
        $downloaded++
        $url = "$BASE_URL/$($file.name)"
        $outPath = Join-Path $MODELS_DIR $file.name
        
        Write-Host "[$downloaded/$total] $($file.name) ($($file.size))" -NoNewline
        
        # Skip if file exists and is not the main model
        if ((Test-Path $outPath) -and $file.name -ne "model.safetensors") {
            Write-Host " - Already exists, skipping" -ForegroundColor Yellow
            continue
        }
        
        Write-Host "" 
        
        $result = Get-FileWithProgress -Url $url -OutFile $outPath -DisplayName $file.name
        
        if ($result) {
            $actualSize = (Get-Item $outPath).Length
            $sizeMB = [math]::Round($actualSize / 1MB, 2)
            Write-Host "        Downloaded: $sizeMB MB" -ForegroundColor Green
        } else {
            if ($file.required) {
                Write-Host "        FAILED - Required file!" -ForegroundColor Red
                $success = $false
            } else {
                Write-Host "        Failed (optional file)" -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host ""
    
    if ($success) {
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "  Download Complete!" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Model saved to: $MODELS_DIR"
        Write-Host ""
        Write-Host "You can now start the server - TrOCR will be available."
        Write-Host ""
    } else {
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host "  Download Failed" -ForegroundColor Red  
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Some required files failed to download."
        Write-Host "Please check your internet connection and try again."
        Write-Host ""
    }
    
    return $success
}

# Run the download
$result = Download-TrOCRModel
if (-not $result) {
    exit 1
}
