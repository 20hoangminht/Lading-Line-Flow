# SETUP.md — everything you do by hand, in order

Written for someone who does not code. Every step is copy-pasteable. If a step does not work exactly
as written, stop and say which step and what you saw.

## 1. Get the repository onto your computer

Install Git and Docker Desktop first, then:

```
git clone https://github.com/20hoangminht/Lading-Line-Flow.git
cd Lading-Line-Flow
```

## 2. Create your settings file

```
cp .env.example .env
```

Open `.env` in a text editor. Fill in the values marked `CHANGE-ME`. Nothing else needs touching.

## 3. Start the application locally

```
docker compose up
```

Wait until the terminal stops printing new lines. Then open **http://localhost:8000** in a browser.

To stop it: press `Ctrl+C` in that terminal.

## 4. Create your login

In a second terminal, in the same folder:

```
docker compose exec web python manage.py createsuperuser
```

It will ask for an email and a password. Use anything you will remember — this is only on your own
computer.

## 5. Check it is working

Open http://localhost:8000/health. You should see `{"status": "ok"}` and nothing else.

---

*Sections for AWS deployment, the customer onboarding call and teardown will be added at the end of
Phase 4. Do not attempt a cloud deployment before then.*
