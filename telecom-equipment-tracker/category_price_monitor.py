import requests
from bs4 import BeautifulSoup
import os
import time
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "/app/data")
DB_NAME = os.path.join(DB_PATH, "price_monitor.db")
LOGIN_URL = os.getenv("SCRAPE_LOGIN_URL")
BASE_URL = os.getenv("SCRAPE_BASE_URL")
TARGET_CATEGORIES = [
    os.getenv("SCRAPE_CATEGORY_1"),
    os.getenv("SCRAPE_CATEGORY_2"),
    os.getenv("SCRAPE_CATEGORY_3"),
    os.getenv("SCRAPE_CATEGORY_4"),
    os.getenv("SCRAPE_CATEGORY_5"),
    os.getenv("SCRAPE_CATEGORY_6"),
]

def send_email(subject, body_html):
    """Send HTML email notification."""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart()
    msg['From'] = f"Price Monitor <{sender}>"
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print("✓ Email sent successfully.")
    except Exception as e:
        print(f"✗ Email error: {e}")

def generate_report(changes):
    """Generate HTML report with styled table."""
    if not changes:
        return "<p>No changes detected.</p>"
    
    rows = ""
    for change in changes:
        if change["type"] == "NEW":
            color, label = "#28a745", "NEW"
        elif change["type"] == "RESTOCKED":
            color, label = "#007bff", "RESTOCKED"
        elif change["type"] == "OUT_OF_STOCK":
            color, label = "#dc3545", "OUT OF STOCK"
        else:
            color, label = "#fd7e14", "PRICE CHANGE"
        
        rows += f"""
        <tr>
            <td style='border:1px solid #ddd; padding:15px; font-family: Arial, sans-serif;'>
                <span style='color:{color}; font-weight:bold; font-size: 14px;'>[{label}]</span><br>
                <a href='{change["url"]}' style='color: #007bff; text-decoration: none; font-size: 18px; font-weight: bold;'>
                    {change["name"]}
                </a><br>
                <span style='color: #444; font-size: 15px; font-weight: 500;'>{change["message"]}</span>
            </td>
        </tr>
        """
    
    return f"""
    <h2 style='font-family: Arial;'>Daily Price Monitor Report</h2>
    <table style='border-collapse: collapse; width: 100%;'>
        <tr style='background-color: #f2f2f2;'>
            <th style='border:1px solid #ddd; padding:12px; text-align:left; font-family: Arial;'>Detected Events</th>
        </tr>
        {rows}
    </table>
    <p style='font-family: Arial;'><i>Automated Price Monitor</i></p>
    """

def initialize_database():
    """Initialize SQLite database."""
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT,
            price_with_tax TEXT,
            price_without_tax TEXT,
            in_stock INTEGER DEFAULT 1,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def scrape_and_process(session, url, conn, visited_urls, changes):
    """Crawl and extract product data."""
    if url in visited_urls:
        return
    visited_urls.add(url)
    
    print(f"Processing: {url}")
    cursor = conn.cursor()
    
    try:
        res = session.get(url, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')

        links_to_visit = set()

        subcategories = soup.find('div', class_=lambda c: c and 'subcategories_list' in c)
        if subcategories:
            for a in subcategories.find_all('a', href=True):
                href = a['href']
                full_url = href if href.startswith("http") else BASE_URL.rstrip("/") + href
                links_to_visit.add(full_url)

        for a in soup.find_all('a', href=True):
            href = a['href']
            if "paginator-page=" in href:
                full_url = href if href.startswith("http") else BASE_URL.rstrip("/") + href
                full_url = full_url.replace("&paginator-append=1", "").replace("?paginator-append=1", "")
                links_to_visit.add(full_url)

        for full_url in links_to_visit:
            if "/detail/" not in full_url and "action" not in full_url and "/en/" not in full_url and "/de/" not in full_url and "redirect=" not in full_url and "do=" not in full_url:
                scrape_and_process(session, full_url, conn, visited_urls, changes)

        product_list = soup.find('div', id=lambda x: x and 'snippet--products' in x)
        if not product_list:
            return 

        for product_div in product_list.find_all('div', class_=lambda c: c and 'product' in c):
            h2_tag = product_div.find('h2')
            a_tag = h2_tag.find('a') if h2_tag else None
            if not a_tag or not a_tag.has_attr('href'):
                continue
                
            href = a_tag['href']
            p_url = href if href.startswith("http") else BASE_URL.rstrip("/") + href
            name = a_tag.text.strip()
            
            id_input = product_div.find('input', {'name': 'id', 'type': 'hidden'})
            sku = id_input['value'] if id_input else href.split('/')[-1]

            price_without_tax = None
            price_with_tax = None
            
            for span in product_div.find_all('span'):
                cls = span.get('class', [])
                if isinstance(cls, str): 
                    cls = cls.split()
                if 'no-vat' in cls or 'price-no-vat' in cls:
                    price_without_tax = span
                elif 'vat' in cls or 'price-vat' in cls:
                    price_with_tax = span
            
            price_without_tax_text = price_without_tax.text.replace(",-", "").replace(" ", "").replace("\xa0", "").strip() if price_without_tax else "0"
            price_with_tax_text = price_with_tax.text.replace(",-", "").replace(" ", "").replace("\xa0", "").strip() if price_with_tax else "0"

            stock_tag = product_div.find('span', class_=lambda c: c and 'stock' in c)
            in_stock = 0 if stock_tag and 'not-available' in stock_tag.get('class', []) else 1

            cursor.execute("SELECT price_with_tax, price_without_tax, in_stock FROM products WHERE sku=?", (sku,))
            old_record = cursor.fetchone()

            if old_record is None:
                print(f"NEW: {sku} - {name}")
                changes.append({
                    "type": "NEW",
                    "name": f"{sku} - {name}",
                    "url": p_url,
                    "message": f"Price: {price_with_tax_text} (with tax) | {price_without_tax_text} (without tax). Stock: {'Yes' if in_stock else 'No'}"
                })
                cursor.execute("INSERT INTO products (sku, name, price_with_tax, price_without_tax, in_stock) VALUES (?, ?, ?, ?, ?)", 
                               (sku, name, price_with_tax_text, price_without_tax_text, in_stock))
            else:
                old_with_tax, old_without_tax, old_stock = old_record
                update_db = False
                
                if old_with_tax != price_with_tax_text or old_without_tax != price_without_tax_text:
                    print(f"PRICE CHANGE: {sku}")
                    changes.append({
                        "type": "PRICE_CHANGE",
                        "name": f"{sku} - {name}",
                        "url": p_url,
                        "message": f"Price: {old_with_tax} → {price_with_tax_text} (with tax) | {old_without_tax} → {price_without_tax_text} (without tax)"
                    })
                    update_db = True

                if old_stock != in_stock:
                    update_db = True
                    if in_stock == 1:
                        print(f"RESTOCKED: {sku}")
                        changes.append({
                            "type": "RESTOCKED",
                            "name": f"{sku} - {name}",
                            "url": p_url,
                            "message": "Product is back in stock!"
                        })
                    else:
                        print(f"OUT OF STOCK: {sku}")
                        changes.append({
                            "type": "OUT_OF_STOCK",
                            "name": f"{sku} - {name}",
                            "url": p_url,
                            "message": "Product is out of stock or on backorder."
                        })

                if update_db:
                    cursor.execute("UPDATE products SET price_with_tax=?, price_without_tax=?, in_stock=?, last_seen=CURRENT_TIMESTAMP WHERE sku=?", 
                                   (price_with_tax_text, price_without_tax_text, in_stock, sku))
            
        conn.commit()
        time.sleep(0.1) 

    except Exception as e:
        print(f"Error processing {url}: {e}")

def run_monitor():
    """Main monitoring function."""
    conn = initialize_database()
    
    user = os.getenv("SCRAPE_USERNAME")
    password = os.getenv("SCRAPE_PASSWORD")
    payload = {'username': user, 'password': password}

    visited_urls = set()
    changes = []

    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        print("Authenticating...")
        session.post(LOGIN_URL, data=payload)

        print("Starting category scan...")
        for category_url in TARGET_CATEGORIES:
            scrape_and_process(session, category_url, conn, visited_urls, changes)

    print(f"Completed. Found {len(changes)} changes.")
    
    report_html = generate_report(changes)
    status = f"Found {len(changes)} changes" if changes else "No changes"
    send_email(f"Price Monitor Report: {status}", report_html)
    
    conn.close()

if __name__ == "__main__":
    run_monitor()
