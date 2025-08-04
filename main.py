import requests
import time
import json
import base64
import os

# ========== CONFIGURATION from environment variables ==========
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CARD_NAME = os.getenv("CARD_NAME", "Jolteon 153/131")
MAX_PRICE = float(os.getenv("MAX_PRICE", "145"))

if not all([EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, WEBHOOK_URL]):
    print("❌ ERROR: Missing required environment variables.")
    print("Make sure EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, and WEBHOOK_URL are set.")
    exit(1)

# ========== GET OAUTH TOKEN ==========
def get_oauth_token(client_id, client_secret):
    url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }
    
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        expires_in = response.json().get("expires_in")
        print(f"✅ Got OAuth token, expires in {expires_in} seconds")
        return token
    else:
        print(f"❌ Failed to get token: {response.status_code} {response.text}")
        return None

# ========== SEARCH EBAY ==========
def search_ebay(token, card_name, max_price):
    base_url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
    query = card_name.replace(" ", "%20")
    url = f"{base_url}?q={query}&limit=10&filter=price:[0..{max_price}],priceCurrency:GBP"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    if "itemSummaries" not in data:
        print("ℹ️ No items found.")
        return None
    
    for item in data["itemSummaries"]:
        return {
            "title": item.get("title", "No Title"),
            "price": f"£{item['price']['value']}",
            "location": item.get("itemLocation", {}).get("country", "Unknown"),
            "url": item.get("itemWebUrl", "#")
        }
    return None

# ========== SEND DISCORD NOTIFICATION ==========
def send_discord_notification(listing):
    data = {
        "content": f"🔔 **MATCH FOUND!**\n\n**{listing['title']}**\n💷 Price: {listing['price']}\n📍 Location: {listing['location']}\n🔗 [View Listing]({listing['url']})"
    }
    response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        print("✅ Sent to Discord!")
    else:
        print(f"❌ Discord error: {response.status_code}")

# ========== MAIN LOOP ==========
def main():
    token = get_oauth_token(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET)
    if not token:
        print("❌ Cannot continue without OAuth token.")
        return
    
    while True:
        print(f"🔍 Searching for '{CARD_NAME}' under £{MAX_PRICE}...")
        result = search_ebay(token, CARD_NAME, MAX_PRICE)
        if result:
            print("🎉 Match found! Sending to Discord...")
            send_discord_notification(result)
            time.sleep(60 * 15)  # Wait 15 minutes after a find
        else:
            print("😔 No match found. Retrying in 5 minutes.")
            time.sleep(60 * 5)

if __name__ == "__main__":
    main()
