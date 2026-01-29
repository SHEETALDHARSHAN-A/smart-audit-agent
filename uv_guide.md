# UV Setup and Usage Guide

`uv` is an extremely fast Python package installer and resolver. This guide covers how to install it, set up a virtual environment, and manage dependencies on Windows.

## 1. Install `uv`

Run the following command in PowerShell to install `uv`:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

*You may need to restart your terminal after installation for the `uv` command to be recognized.*

## 2. Set Up a Virtual Environment (Recommended)

Using a virtual environment (`venv`) keeps your project dependencies isolated from your system Python.

1.  **Navigate to your project directory**:
    ```powershell
    cd C:\path\to\your\project
    ```

2.  **Create the virtual environment**:
    ```powershell
    uv venv
    ```
    This creates a `.venv` folder in your current directory.

3.  **Activate the virtual environment**:
    ```powershell
    .\.venv\Scripts\activate
    ```
    *You will see `(.venv)` appear at the start of your command prompt line.*

## 3. Install Dependencies

Once your virtual environment is active, you can install packages into it.

-   **Install from [requirements.txt](file:///C:/sample-workspace/smart-audit-agent/Backend/requirements.txt)**:
    ```powershell
    uv pip install -r requirements.txt
    ```

-   **Install a specific package**:
    ```powershell
    uv pip install pandas numpy
    ```

-   **Upgrade packages**:
    ```powershell
    uv pip install --upgrade -r requirements.txt
    ```

## 4. Run Your Code

With the virtual environment activated, `python` will automatically use the packages installed in the `.venv`.

```powershell
python main.py
```

## Summary of Commands

| Action | Command |
| :--- | :--- |
| **Install uv** | `irm https://astral.sh/uv/install.ps1 \| iex` |
| **Create venv** | `uv venv` |
| **Activate venv** | `.\.venv\Scripts\activate` |
| **Install reqs** | `uv pip install -r requirements.txt` |
| **Add package** | `uv pip install <package_name>` |


Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "`n103.235.47.176 paddleocr.bj.bcebos.com"