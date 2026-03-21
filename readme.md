# 🕵️ E-Commerce Market Intelligence & Inventory Watchdog

A professional-grade monitoring suite designed to track price fluctuations, inventory levels, and product trends across diverse e-commerce platforms. This project demonstrates advanced web scraping techniques, secure data handling, and automated reporting.

## 🌟 Key Features

* **Recursive B2B Crawling:** A specialized module for authenticated B2B portals, capable of deep-traversing category structures to map entire inventories.
* **Multi-Category Monitoring:** Targeted tracking of specific product segments with high-frequency updates.
* **Intelligent Change Detection:** Logic-driven comparison engine that identifies:
    * Price drops and increases.
    * Restock events and out-of-stock statuses.
    * New product arrivals.
* **Automated Reporting:** Integrated SMTP module that generates and sends styled HTML email reports with detected changes.
* **Persistent Storage:** Robust SQLite backend for historical price tracking and data integrity.
* **Security First:** Full implementation of Environment Variables (`.env`) to ensure sensitive credentials and target URLs are never exposed in the source code.

## 🛠️ Tech Stack

* **Language:** Python 3.11
* **Scraping & Parsing:** BeautifulSoup4, Requests
* **Database:** SQLite3
* **Orchestration:** Docker & Docker Compose
* **Environment Management:** Python-Dotenv
* **Communication:** SMTP (MIME Multi-part HTML emails)

## ⏰ Automation (Scheduling)

To ensure continuous monitoring, you can schedule the execution using **Cron** on the host machine. 

### Example Crontab Configuration
To run the monitoring suite every day at 8:00 AM:

```bash
0 8 * * * cd /path/to/watchdog_portfolio_public && /usr/local/bin/docker-compose up --build
```

## 📂 Project Structure

```text
.
├── nautical-b2b-monitor/       # Recursive B2B scraper with authentication
│   ├── data/                   # Persistent SQLite storage
│   ├── .env.example            # Template for environment variables
│   ├── Dockerfile              # Container configuration
│   └── recursive_crawler.py    # Main logic
├── telecom-equipment-tracker/  # Category-based public monitor
│   ├── data/                   # Persistent SQLite storage
│   ├── .env.example            # Template for environment variables
│   ├── Dockerfile              # Container configuration
│   └── category_monitor.py     # Main logic
└── docker-compose.yml          # Multi-container orchestration
