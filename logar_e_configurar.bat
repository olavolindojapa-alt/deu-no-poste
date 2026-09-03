@echo off
chcp 65001 >nul
cd /d "%~dp0"
title BOT - LOGIN WHATSAPP + CONFIGURAR GITHUB
color 0A
setlocal EnableDelayedExpansion

REM Garantir que go e gh estejam no PATH (independente de sessao antiga)
if exist "C:\Program Files\Go\bin\go.exe" set "PATH=C:\Program Files\Go\bin;%PATH%"
if exist "%ProgramFiles%\GitHub CLI\gh.exe" set "PATH=%ProgramFiles%\GitHub CLI;%PATH%"
where gh >nul 2>nul || (for /f "delims=" %%i in ('dir /b /s "C:\Program Files\GitHub CLI\gh.exe" 2^>nul ^| findstr /i gh.exe') do set "PATH=%%~dpi;%PATH%")

echo ================================================================
echo   BOT JOGO DO BICHO - LOGIN + CONFIGURAO AUTOMATICA DO GITHUB
echo ================================================================
echo.
echo Este script vai:
echo   1. Fazer login no GitHub (sua conta japinhadouglas) - 1 vez
echo   2. Mostrar o QR para voce escanear no celular - com calma
echo   3. Separar a sessao em 2 arquivos
echo   4. Enviar os 2 arquivos para o GitHub (SEM copiar/colar)
echo.
echo -----------------------------------------------------------------
echo.

REM ---------- 0) Verificar se o GitHub CLI (gh) esta instalado ----------
where gh >nul 2>nul
if errorlevel 1 (
    echo [ERRO] GitHub CLI nao encontrado.
    echo Instale rodando:  winget install --id GitHub.cli
    pause
    exit /b 1
)

REM ---------- 0.1) Verificar se Go esta instalado ----------
where go >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Go nao encontrado.
    echo Instale em:  https://go.dev/dl/   (Windows, go1.25* windows-amd64.msi)
    pause
    exit /b 1
)

REM ---------- 1) Login no GitHub (so se ainda nao estiver logado) ----------
echo [1/4] Verificando login no GitHub...
gh auth status >nul 2>nul
if errorlevel 1 (
    echo.
    echo Preciso que voce faca login no GitHub UMA vez.
    echo Escolha:  GitHub.com  ^>  HTTPS  ^>  Login with a web browser
    echo Depois digite o codigo que aparecer e confirme no navegador.
    echo.
    gh auth login --hostname github.com --git-protocol https --web
    if errorlevel 1 (
        echo [ERRO] Falha no login do GitHub.
        pause
        exit /b 1
    )
    echo Login OK!
) else (
    echo   Ja esta logado no GitHub. Continuando...
)
echo Done.
echo.

REM ---------- 2) Gerar sessao do WhatsApp (QR em imagem) ----------
echo [2/4] Gerando sessao do WhatsApp...
echo.
echo   Vai ser criada a imagem qr_login.png na pasta.
echo   No celular:  WhatsApp ^> Aparelhos conectados ^> Conectar um aparelho
echo   Escaneie o QR que abrir na tela (ou abra qr_login.png).
echo   Deixe esta janela aberta ate aparecer "Sessao salva".
echo.
if exist qr_login.png del qr_login.png
go build -o login.exe login.go
if errorlevel 1 (
    echo [ERRO] Falha ao compilar o login.
    pause
    exit /b 1
)
start "login-whatsapp" /min cmd /c "login.exe 2>login.log"
echo   Aguardando o QR ser gerado...
:waitqr
if not exist qr_login.png (
    timeout /t 2 >nul
    goto waitqr
)
echo   QR gerado! Abrindo a imagem para voce escanear...
start qr_login.png
echo.
echo   >>> Escaneie o QR no celular. Deixe esta janela aberta. <<<
echo   >>> Quando conectar, o login salva a sessao e a janela fecha sozinha. <<<
echo.
:waitsessao
tasklist /fi "IMAGENAME eq login.exe" | find "login.exe" >nul
if errorlevel 1 (
    goto done_wait
)
timeout /t 1 >nul
goto waitsessao
:done_wait
echo   Login encerrou. Continuando...
echo Done.
echo.

REM ---------- 3) Separar a sessao em 2 arquivos ----------
echo [3/4] Separando a sessao em 2 arquivos...
python prune_db.py
if errorlevel 1 (
    echo [ERRO] Falha ao separar a sessao.
    pause
    exit /b 1
)
if not exist "WHATSAPP_SESSION_PART1.txt" (
    echo [ERRO] Arquivo WHATSAPP_SESSION_PART1.txt nao foi criado.
    echo        Verifique se a sessao foi gerada no passo 2.
    pause
    exit /b 1
)
if not exist "WHATSAPP_SESSION_PART2.txt" (
    echo [ERRO] Arquivo WHATSAPP_SESSION_PART2.txt nao foi criado.
    pause
    exit /b 1
)
echo   Arquivos gerados com sucesso!
echo Done.
echo.

REM ---------- 4) Enviar os 2 arquivos para o GitHub ----------
echo [4/4] Enviando os arquivos para o GitHub (secrets)...
gh secret set WHATSAPP_SESSION_PART1 --body-file "WHATSAPP_SESSION_PART1.txt" --repo japinhadouglas/deu-no-poste
if errorlevel 1 (
    echo [ERRO] Falha ao enviar WHATSAPP_SESSION_PART1.
    pause
    exit /b 1
)
gh secret set WHATSAPP_SESSION_PART2 --body-file "WHATSAPP_SESSION_PART2.txt" --repo japinhadouglas/deu-no-poste
if errorlevel 1 (
    echo [ERRO] Falha ao enviar WHATSAPP_SESSION_PART2.
    pause
    exit /b 1
)
echo Done.
echo.

echo ================================================================
echo   TUDO PRONTO!
echo   Os secrets foram enviados. Agora va no GitHub:
echo   Actions ^> Bot COR ^> Run workflow  (para testar)
echo ================================================================
pause
