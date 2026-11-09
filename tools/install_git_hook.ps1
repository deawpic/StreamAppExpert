# Install pre-commit hook in Git
$hookDir = Join-Path $PSScriptRoot "..\.git\hooks"

if (-not (Test-Path $hookDir)) {
    Write-Error ".git/hooks directory not found. Please run git init first."
    exit 1
}

$hookPath = Join-Path $hookDir "pre-commit"
$hookContent = @"
#!/bin/sh
echo "🔍 Running StreamAppExpert streaming compliance pre-commit hook..."
python -m harness.cli streaming-lint
if [ `$? -ne 0 ]; then
    echo "❌ Commit rejected by StreamAppExpert: Streaming anti-patterns detected!"
    exit 1
fi
"@

Set-Content -Path $hookPath -Value $hookContent -NoNewline
Write-Output "✅ Git pre-commit hook installed successfully at $hookPath"
