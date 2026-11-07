param([Parameter(Mandatory = $true)][string]$Pasta)

$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
try {
    $word.Visible = $false
    $word.DisplayAlerts = 0
    foreach ($arquivo in Get-ChildItem -LiteralPath $Pasta -Filter '*.docx') {
        $doc = $word.Documents.Open($arquivo.FullName, $false, $true)
        try {
            $doc.SaveAs2([IO.Path]::ChangeExtension($arquivo.FullName, '.pdf'), 17)
        }
        finally {
            $doc.Close(0)
        }
    }
}
finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
