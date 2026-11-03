# Execute no Windows do ThinkPad. Prepara a ISO oficial; NÃO apaga nenhum disco.
# A instalação e a confirmação de apagar o SSD acontecem após iniciar pelo pendrive.
param(
    [string]$Destino = (Join-Path $env:USERPROFILE 'Downloads\Debian-ThinkPad')
)

$ErrorActionPreference = 'Stop'
$Versao = '13.7.0'
$NomeIso = "debian-$Versao-amd64-netinst.iso"
$Sha512 = 'ef04d0276850d70e4aaec0b55003628660e9631b26e35215a70ab3c8c707294a4b12731bc73c75a932902f703a7c278310ca99df28d6b36fb06d5618d8d0f678'
$Url = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/$NomeIso"
$Iso = Join-Path $Destino $NomeIso

New-Item -ItemType Directory -Path $Destino -Force | Out-Null
if (-not (Test-Path -LiteralPath $Iso)) {
    Write-Host "Baixando Debian $Versao (~756 MB)..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $Iso -UseBasicParsing
}

Write-Host 'Conferindo SHA-512 da imagem...'
$HashAtual = (Get-FileHash -LiteralPath $Iso -Algorithm SHA512).Hash.ToLowerInvariant()
if ($HashAtual -ne $Sha512) {
    throw "A imagem não passou na verificação. Apague $Iso e execute novamente."
}

Write-Host "Imagem oficial verificada: $Iso"
Write-Host 'Pendrives detectados (leitura, nenhuma alteração):'
Get-Disk | Where-Object BusType -eq USB |
    Select-Object Number, FriendlyName, @{Name='TamanhoGB';Expression={[math]::Round($_.Size / 1GB, 1)}} |
    Format-Table -AutoSize

$Passos = @"
1. Faça backup dos arquivos do Windows. A instalação apagará TODOS os dados do SSD escolhido.
2. Conecte um pendrive vazio de pelo menos 2 GB. O pendrive também será apagado.
3. Baixe Rufus em https://rufus.ie/ e selecione a ISO verificada:
   $Iso
4. No Rufus, confirme cuidadosamente que o dispositivo é o PENDRIVE, nunca o SSD de 1 TB.
5. Inicie o ThinkPad pelo pendrive (menu de boot do Lenovo: normalmente F12).
6. No instalador Debian: Install; escolha idioma, teclado, rede e usuário.
7. Em particionamento, escolha 'Assistido - usar o disco inteiro'. Confirme que o disco
   escolhido é o SSD INTERNO de aproximadamente 1 TB e revise a tela que lista partições
   a apagar. A gravação só começa após sua confirmação nessa tela.
8. Instale 'SSH server' e 'standard system utilities'. Ambiente gráfico é opcional.
9. Reinicie, retire o pendrive e execute o script setup-bitcoin-node-debian.sh no Debian.

O script de preparação apenas baixa e verifica a ISO. Ele não formata discos.
"@
$ArquivoPassos = Join-Path $Destino 'PASSOS.txt'
Set-Content -LiteralPath $ArquivoPassos -Value $Passos -Encoding UTF8
Write-Host "Instruções: $ArquivoPassos"
