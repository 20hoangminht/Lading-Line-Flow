# SETUP.md — start Flow on a Windows computer

These steps start from a clean computer copy. Run every command in **PowerShell**, not Command
Prompt. Each step says exactly what success looks like. Stop at the first different result.

## 1. Install the two required programs

1. Install **Git for Windows** from <https://git-scm.com/download/win> using the displayed defaults.
2. Install **Docker Desktop for Windows** from <https://www.docker.com/products/docker-desktop/> using
   the displayed defaults.
3. Open Docker Desktop and wait until the bottom-left corner says **Engine running**.
4. Open PowerShell from the Windows Start menu and run:

```powershell
git --version
docker version
docker compose version
```

Success means all three commands print version numbers and no red error text.

## 2. Download a clean copy

Run:

```powershell
git clone https://github.com/20hoangminht/Lading-Line-Flow.git
Set-Location Lading-Line-Flow
```

Success means the first command ends with `done.` and the PowerShell prompt now ends in
`Lading-Line-Flow>`.

## 3. Create the local settings file

Run:

```powershell
Copy-Item .env.example .env
notepad .env
```

In Notepad, replace every `CHANGE-ME` with a private value, then select **File > Save** and close
Notepad. Run this check:

```powershell
Select-String -Path .env -Pattern 'CHANGE-ME'
```

Success means the command prints nothing and returns to the prompt. Do not send `.env` to anyone or
commit it to Git.

## 4. Build and start Flow

Run:

```powershell
docker compose up --build
```

The first build downloads software and can take several minutes. Leave this PowerShell window open.
Success means the output includes `Starting development server at http://0.0.0.0:8000/` and does not
include `unapplied migration(s)`. Flow applies database migrations automatically before the web
server starts.

## 5. Create the local login

Open a second PowerShell window. Run:

```powershell
Set-Location Lading-Line-Flow
docker compose exec web python manage.py createsuperuser
```

Enter an email address and password when asked. Success means the final line is
`Superuser created successfully.` This login exists only on this computer.

## 6. Run the acceptance checks

Run in the second PowerShell window:

```powershell
(Invoke-WebRequest http://localhost:8000/health).Content
docker compose ps
```

Success means the first command prints `{"status": "ok"}`. The second command must list `db` and
`web`; neither may say `Exit` or `Restarting`.

Open <http://localhost:8000> in a browser. Success means the Flow page opens without a browser error.

## 7. Stop Flow without deleting local data

Return to the first PowerShell window and press **Ctrl+C**. Then run:

```powershell
docker compose down
```

Success means the command reports that the containers and network were removed. The database data
remains available for the next start.

## Cost and cloud boundary

Running these steps locally adds **A$0 per month** beyond the computer and internet connection
already in use. AWS deployment is not built yet; do not attempt a cloud deployment before Phase 4.
