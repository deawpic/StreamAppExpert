# PowerShell launcher for StreamAppExpert Harness with UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"
python -m harness.cli $args
