import requests
from bs4 import BeautifulSoup
import time
import json

# 🔧 CONFIGURE HERE
WEBHOOK_URL = "https://discord.com/api/webhooks/1400462331217182792/8KKhh2PYqH0Wz5Vzs7lYy6vB4c531wq4WUr5AZMgu8S_wl1EUWGKv_q1lrB1FTijqJce"
CARD_NAME = "Jolteon 153/131"
MAX_PRICE = 145.00

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def search_ebay(card_name, max_price):
    try:
        search_url = f"https://www.ebay.co.uk/sch/i.html?_nkw={card_name.replace(' ', '+')}&_sop=15"
        response = requests.get(search_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

    soup = BeautifulSoup(response.text, "lxml")
    listings = soup.select(".s-item")

    for item in listings:
        try:
            title = item.select_one(".s-item__title").text
            price_text = item.select_one(".s-item__price").text
            price = float(price_text.replace("£", "").replace(",", "").split()[0])
            location = item.select_one(".s-item__location").text if item.select_one(".s-item__location") else "Unknown"
            url = item.select_one(".s-item__link")["href"]

            if price <= max_price:
                return {
                    "title": title,
                    "price": f"£{price}",
                    "location": location,
                    "url": url
                }
        except Exception as e:
            continue

    return None

def send_discord_notification(listing):
    data = {
        "content": f"🔔 **MATCH FOUND!**\n\n**{listing['title']}**\n💷 Price: {listing['price']}\n📍 Location: {listing['location']}\n🔗 [View Listing]({listing['url']})"
    }
    response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        print("✅ Sent to Discord!")
    else:
        print(f"❌ Discord error: {response.status_code}")

# 🔁 MAIN LOOP
while True:
    print(f"🔍 Searching for {CARD_NAME} under £{MAX_PRICE}...")
    result = search_ebay(CARD_NAME, MAX_PRICE)
    if result:
        print("🎉 Match found! Sending to Discord...")
        send_discord_notification(result)
        time.sleep(60 * 15)  # Wait 15 minutes before checking again after a find
    else:
        print("😔 No match found. Retrying in 5 minutes.")
        time.sleep(60 * 5)  # Wait 5 minutes between checks
