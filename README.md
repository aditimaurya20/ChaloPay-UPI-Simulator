# ChaloPay – UPI Payments Simulator

A full-stack digital payments platform that simulates how UPI works. Users can create a virtual UPI ID (`name@chalopay`), send money, generate and scan QR codes, and track every transaction. Built as a final-year B.Tech project.

## Features

- **Secure authentication:** register and log in with JWT-based auth and hashed passwords
- **Virtual UPI accounts:** each user gets a UPI ID and a starting balance of ₹10,000
- **Atomic fund transfers:** balance validation, so a failed transfer never leaves half-updated data
- **Daily limit:** transfers are capped at ₹10,000 per day
- **Transaction history:** filter and search by UPI ID, amount, and date range
- **PDF statements:** download your transaction history as a PDF
- **QR codes:** generate a personal QR code and decode one to pay
- **Admin panel:** view accounts and freeze or unfreeze them

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS |
| Database | PostgreSQL |
| Frontend | HTML, CSS, JavaScript (Fetch API), Bootstrap 5 |
| Libraries | qrcode, Pillow, ReportLab |

## Project Structure

```
ChaloPay-UPI-Simulator/
├── app.py              # App entry point and setup
├── routes.py           # API endpoints
├── models.py           # Database models (User, Account, Transaction)
├── extensions.py       # Flask extensions
├── config.py           # Configuration (reads values from .env)
├── requirements.txt
└── templates/          # Frontend pages (login, dashboard, send money, etc.)
```

## Getting Started

**1. Clone the repo**

```bash
git clone https://github.com/aditimaurya20/ChaloPay-UPI-Simulator.git
cd ChaloPay-UPI-Simulator
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Create the database**

In PostgreSQL, create an empty database named `upi_simulator_db`. The tables are created automatically on the first run.

**4. Add a `.env` file** in the project folder

```
DB_PASSWORD=your_postgres_password
JWT_SECRET_KEY=any-long-random-text
```

**5. Run the server**

```bash
python app.py
```

The API runs at `http://localhost:5000`.

**6. Open the frontend**

Open `templates/login.html` in your browser (VS Code Live Server works well).

## Demo Admin Login

An admin account is created automatically on the first run:

- Email: `admin@chalopay.com`
- Password: `admin123`

This is for demo purposes only. Change it in `app.py` if you deploy this anywhere.

## Disclaimer

ChaloPay is a learning project. It simulates payments with virtual money and is not connected to any real banking or UPI network.
