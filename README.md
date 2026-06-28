# FlexTime Pro

FlexTime Pro is a modern, responsive, and mobile-first web application designed for employees who work contracted weekly hours (e.g., 40 hours per week) and need a reliable, premium tool to track their worked hours, overtime, and running flexitime balance.

It is built as a self-hosted, production-ready solution that answers the core questions every employee has:
* How many hours have I worked this week?
* How many hours do I still need to work?
* How many overtime hours have I earned?
* How many hours do I owe?
* What is my overall flexitime balance?

## Features
* **Real-time Dashboards:** Dynamic charts tracking weekly progress, monthly totals, and running flexitime balance.
* **Premium UI/UX:** A beautiful design system featuring glass-morphism, responsive sidebars, dark mode, and seamless interactions.
* **Smart Time Parsing:** Enter time simply (`8`, `8.5`, `09:00-17:30`, or `8h 30m`) and let the parser handle the rest.
* **Automatic Deductions:** Configurable automatic lunch deductions (e.g., 30 mins) for daily totals.
* **Multi-User Architecture:** Built-in admin controls to manage multiple employee accounts on a single instance.
* **Reporting:** Export your data seamlessly to PDF, Excel, and CSV formats.
* **PWA Ready:** Install the application directly to your mobile device home screen.
* **Fully Self-Hosted:** Easy deployment using Docker and Docker Compose with persistent SQLite database backups.

## Technology Stack
* **Backend:** FastAPI (Python), SQLAlchemy, SQLite (WAL mode)
* **Frontend:** HTML5, Jinja2 Templates, Tailwind CSS (v4), Alpine.js, Chart.js
* **Deployment:** Docker, Docker Compose

## Quick Start (Local Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kiyreload27/FlexTime-Pro.git
   cd FlexTime-Pro
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Build the CSS (Requires Tailwind CLI):**
   ```bash
   ./build.ps1
   ```

4. **Run the server:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Login:** Navigate to `http://127.0.0.1:8000`. The default credentials are:
   * **Username:** `admin`
   * **Password:** `changeme`

## Deployment (Docker)

To deploy FlexTime Pro to a production environment:

1. Clone the repository on your server.
2. Edit `docker-compose.yml` and change the default `SECRET_KEY` and `ADMIN_PASSWORD`.
3. Start the container in detached mode:
   ```bash
   docker-compose up -d --build
   ```
4. (Optional but recommended) Set up a reverse proxy like Nginx or Caddy to expose port `8000` via HTTPS.

## License
MIT License.
