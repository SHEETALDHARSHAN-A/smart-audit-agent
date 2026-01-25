"""
TrOCR Model Setup Script
========================
This script helps set up the TrOCR model for handwriting recognition.

HOW TO USE:
1. Download the model files manually from HuggingFace:
   https://huggingface.co/microsoft/trocr-base-handwritten/tree/main
   
   Required files to download:
   - model.safetensors (1.33 GB) - The main model
   - config.json
   - preprocessor_config.json  
   - tokenizer_config.json
   - vocab.json
   - merges.txt
   - special_tokens_map.json

2. Place all downloaded files in a folder (e.g., D:/trocr-model/)

3. Run this script:
   python setup_trocr.py D:/trocr-model/

The script will set up the model in the HuggingFace cache so hybrid_ocr.py can use it.
"""

import os
import sys
import shutil
from pathlib import Path


def get_huggingface_cache_dir():
    """Get the HuggingFace cache directory"""
    cache_dir = os.environ.get('HF_HOME') or os.environ.get('HUGGINGFACE_HUB_CACHE')
    if not cache_dir:
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
    return cache_dir


def setup_trocr_from_local(source_folder: str):
    """
    Set up TrOCR model from manually downloaded files.
    
    Args:
        source_folder: Path to folder containing the downloaded model files
    """
    print("=" * 60)
    print("TrOCR Model Setup from Local Files")
    print("=" * 60)
    
    source_path = Path(source_folder)
    
    # Required files
    required_files = [
        'model.safetensors',
        'config.json',
        'preprocessor_config.json',
    ]
    
    optional_files = [
        'tokenizer_config.json',
        'vocab.json', 
        'merges.txt',
        'special_tokens_map.json',
        'generation_config.json',
    ]
    
    # Check if source folder exists
    if not source_path.exists():
        print(f"\n✗ Error: Folder not found: {source_folder}")
        print("\nPlease download the model files from:")
        print("https://huggingface.co/microsoft/trocr-base-handwritten/tree/main")
        return False
    
    # Check for required files
    print("\n[1/3] Checking downloaded files...")
    missing_required = []
    for f in required_files:
        if not (source_path / f).exists():
            missing_required.append(f)
    
    if missing_required:
        print(f"\n✗ Missing required files: {', '.join(missing_required)}")
        print("\nPlease download these files from:")
        print("https://huggingface.co/microsoft/trocr-base-handwritten/tree/main")
        return False
    
    # List found files
    found_files = []
    for f in required_files + optional_files:
        if (source_path / f).exists():
            size_mb = (source_path / f).stat().st_size / (1024 * 1024)
            found_files.append(f"{f} ({size_mb:.1f} MB)")
    
    print(f"      Found {len(found_files)} files:")
    for f in found_files:
        print(f"        ✓ {f}")
    
    # Create cache directory structure
    print("\n[2/3] Setting up HuggingFace cache...")
    cache_dir = get_huggingface_cache_dir()
    model_cache = Path(cache_dir) / 'models--microsoft--trocr-base-handwritten'
    snapshots_dir = model_cache / 'snapshots' / 'manual_download'
    
    # Clean up any existing incomplete cache
    if model_cache.exists():
        print(f"      Removing existing cache at {model_cache}")
        shutil.rmtree(model_cache)
    
    # Create directory structure
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    (model_cache / 'refs').mkdir(exist_ok=True)
    
    # Write the ref file to point to our snapshot
    with open(model_cache / 'refs' / 'main', 'w') as f:
        f.write('manual_download')
    
    print(f"      Created cache at: {model_cache}")
    
    # Copy files to cache
    print("\n[3/3] Copying model files to cache...")
    all_files = required_files + optional_files
    copied = 0
    for f in all_files:
        src = source_path / f
        if src.exists():
            dst = snapshots_dir / f
            print(f"      Copying {f}...", end=' ', flush=True)
            shutil.copy2(src, dst)
            print("✓")
            copied += 1
    
    print(f"\n{'=' * 60}")
    print(f"✓ TrOCR model set up successfully!")
    print(f"  Copied {copied} files to cache")
    print(f"\nYou can now restart the server and TrOCR will be available.")
    print(f"{'=' * 60}")
    
    # Test loading
    print("\n[OPTIONAL] Testing model loading...")
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        
        print("      Loading processor...", end=' ', flush=True)
        processor = TrOCRProcessor.from_pretrained(
            'microsoft/trocr-base-handwritten',
            local_files_only=True
        )
        print("✓")
        
        print("      Loading model...", end=' ', flush=True)
        model = VisionEncoderDecoderModel.from_pretrained(
            'microsoft/trocr-base-handwritten',
            local_files_only=True
        )
        print("✓")
        
        print("\n✓ Model loads correctly! TrOCR is ready to use.")
        return True
        
    except Exception as e:
        print(f"\n⚠ Warning: Model test failed: {e}")
        print("  The files are copied but there may be an issue.")
        print("  Try restarting the server to see if it works.")
        return True


def download_with_retry():
    """Try to download using transformers with resume capability"""
    print("=" * 60)
    print("TrOCR Model Downloader (with resume)")
    print("=" * 60)
    print("\nAttempting to download from HuggingFace...")
    print("(This supports resume if interrupted)\n")
    
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        
        print("[1/2] Downloading TrOCR Processor...")
        processor = TrOCRProcessor.from_pretrained(
            'microsoft/trocr-base-handwritten',
            resume_download=True
        )
        print("      ✓ Processor downloaded successfully")
        
        print("\n[2/2] Downloading TrOCR Model (this may take a while)...")
        model = VisionEncoderDecoderModel.from_pretrained(
            'microsoft/trocr-base-handwritten',
            resume_download=True
        )
        print("      ✓ Model downloaded successfully")
        
        print("\n" + "=" * 60)
        print("TrOCR is ready to use! Restart the server to enable it.")
        print("=" * 60)
        return True
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted. Run again to resume.")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def print_usage():
    print(__doc__)
    print("\nUSAGE:")
    print("  python setup_trocr.py <path_to_downloaded_files>")
    print("  python setup_trocr.py --download  (to try direct download with resume)")
    print("\nEXAMPLES:")
    print("  python setup_trocr.py D:/Downloads/trocr-model/")
    print("  python setup_trocr.py C:/Users/YourName/Downloads/trocr/")
    print("  python setup_trocr.py --download")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg in ['--help', '-h']:
        print_usage()
    elif arg == '--download':
        success = download_with_retry()
        sys.exit(0 if success else 1)
    else:
        success = setup_trocr_from_local(arg)
        sys.exit(0 if success else 1)
