$tokens = $null
$errs = $null
[System.Management.Automation.Language.Parser]::ParseFile('C:\Users\Clamps\.openclaw\workspace\scripts\automation\bundle-run-log.ps1', [ref]$tokens, [ref]$errs) | Out-Null
$errs | ForEach-Object {
  "{0}:{1} {2}" -f $_.Extent.StartLineNumber, $_.Extent.StartColumnNumber, $_.Message
}
