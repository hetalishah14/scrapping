# from flask import Flask, request, jsonify
# from playwright.sync_api import sync_playwright
# import re
# import time

# app = Flask(__name__)

# def clean(text):
#     return text.strip().replace('\n', ' ') if text else "Not Found"

# def scrape_from_chrome(url):
#     with sync_playwright() as p:
#         browser = p.chromium.connect_over_cdp("http://localhost:9222")  # Connect to your open Chrome
#         context = browser.contexts[0] if browser.contexts else browser.new_context()
#         page = context.new_page()

#         try:
#             page.goto(url, timeout=60000)
#             page.wait_for_timeout(8000)

#             # 1. Title
#             title = page.title()
#             company_name = title if "Just a moment" not in title else "Company Name Not Found"

#             # 2. Meta Description
#             description = "Description not found."
#             for tag in ["meta[name='description']", "meta[property='og:description']", "meta[name='twitter:description']"]:
#                 try:
#                     desc = page.locator(tag).first.get_attribute("content")
#                     if desc:
#                         description = desc
#                         break
#                 except:
#                     continue

#             # 3. LinkedIn URL
#             linkedin_url = "LinkedIn URL Not Found"
#             for a in page.locator("a").all():
#                 href = a.get_attribute("href") or ""
#                 if "linkedin.com" in href.lower():
#                     linkedin_url = href
#                     break

#             # 4. Size & Location (from text)
#             full_text = page.inner_text("body")
#             size_match = re.search(r"(\d{1,3}(?:,\d{3})*)\+?\s+(employees|people|members)", full_text, re.I)
#             location_match = re.search(r"(Headquarters|Location):?\s*([^\n]+)", full_text, re.I)

#             return {
#                 "company_name": clean(company_name),
#                 "company_description": clean(description),
#                 "linkedin_url": clean(linkedin_url),
#                 "company_size": clean(size_match.group(1) if size_match else None),
#                 "company_location": clean(location_match.group(2) if location_match else None)
#             }

#         except Exception as e:
#             return {
#                 "company_name": "Error",
#                 "company_description": str(e),
#                 "linkedin_url": "LinkedIn URL Not Found",
#                 "company_size": "Not Found",
#                 "company_location": "Not Found"
#             }
#         finally:
#             page.close()
#             browser.close()

# @app.route('/scrape', methods=['POST'])
# def scrape():
#     data = request.get_json()
#     url = data.get("url")
#     if not url:
#         return jsonify({"error": "URL is required"}), 400

#     return jsonify(scrape_from_chrome(url))

# if __name__ == '__main__':
#     app.run(debug=True)


from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

def get_driver():
    options = uc.ChromeOptions()
    # REMOVE headless for now to allow Cloudflare JS challenge
    # options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options, headless=False)
    return driver

def extract_company_info(url):
    driver = get_driver()
    driver.get(url)

    try:
        # Wait for Cloudflare page to pass (max 15 seconds)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)  # Let the JS finish loading
        
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Company Name
        title_tag = soup.find("title")
        company_name = title_tag.text.strip() if title_tag else ""

        # Description
        desc_tag = soup.find("meta", {"name": "description"})
        description = desc_tag["content"].strip() if desc_tag else ""

        # LinkedIn URL
        linkedin_url = ""
        for link in soup.find_all("a", href=True):
            if "linkedin.com/company" in link["href"]:
                linkedin_url = link["href"]
                break

        # Company Size and Location (basic)
        location = ""
        company_size = ""
        for div in soup.find_all("div"):
            text = div.get_text(strip=True).lower()
            if "employees" in text and not company_size:
                company_size = text
            if ("location" in text or "headquarters" in text) and not location:
                location = text

        return {
            "company_name": company_name,
            "description": description,
            "linkedin_url": linkedin_url,
            "company_size": company_size,
            "location": location
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.quit()

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    info = extract_company_info(url)
    return jsonify(info)

if __name__ == '__main__':
    app.run(debug=True)
