import requests
from bs4 import BeautifulSoup
import time
import threading
from flask import Flask, request, render_template_string

app = Flask(__name__)

# === Discord Webhook ===
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1400462331217182792/8KKhh2PYqH0Wz5Vzs7lYy6vB4c531wq4WUr5AZMgu8S_wl1EUWGKv_q1lrB1FTijqJce"

# === Watchlist Storage ===
watchlist = []

# === HTML Template with Styling + Search Now Feature ===
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Pokémon eBay Watcher</title>
    <style>
        body {
            background: linear-gradient(to right, #ffeb3b, #ff4081);
            font-family: 'Comic Sans MS', cursive, sans-serif;
            padding: 30px;
            color: #333;
        }
        h1, h2 {
            text-shadow: 1px 1px white;
        }
        form {
            background: white;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
        }
        input, button {
            padding: 10px;
            margin: 5px 0;
            border-radius: 8px;
            border: 1px solid #ccc;
            width: 100%;
        }
        ul {
            background: #fff;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
        }
        .result {
            margin-bottom: 10px;
            border-bottom: 1px dashed #ccc;
            padding-bottom: 10px;
        }
    </style>
</head>
<body>
    <h1>Pokémon Card Price Watch</h1>

    <h2>Add Card to Watchlist</h2>
    <form method="POST" action="/add">
        <label>Card Name:</label><br>
        <input type="text" name="card_name" required><br>
        <label>Max Price (£):</label><br>
        <input type="number" step="0.01" name="max_price" required><br>
        <button type="submit">Add to Watchlist</button>
    </form>

    <h2>Search Now (View Current Listings)</h2>
    <form method="POST" action="/search-now">
        <label>Card Name:</label><br>
        <input type="text" name="search_name" required><br>
        <button type="submit">Search eBay Now</button>
    </form>

    <h3>🔍 Currently Watching:</h3>
    <ul>
        {% for card in cards %}
            <li>{{ card["name"] }} — £{{ card["price"] }}</li>
        {% endfor %}
    </ul>

    {% if results %}
        <h3>📦 Search Results:</h3>
        <ul>
            {% for r in results %}
                <div class="result">
                    <strong>{{ r["title"] }}</strong><br>
                    Price: £{{ r["price"] }}<br>
                    Location: {{ r["location"] }}<br>
                    <a href="{{ r['link'] }}" target="_blank">View Listing</a>
                </div>
            {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(html_template, cards=watchlist, results=None)

@app.route("/add", methods=["POST"])
def add_card():
    name = request.form["card_name"]
    price = float(request.form["max_price"])
    watchlist.append({"name": name, "price": price})
    return render_template_string(html_template, cards=watchlist, results=None)

@app.route("/search-now", methods=["POST"])
def search_now():
    name = request.form["search_name"]
    query = name.replace(" ", "+")
    url = f"https://www.ebay.co.uk/sch/i.html?_nkw={query}&_sop=15&LH_BIN=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")
        items = soup.select(".s-item")

        for item in items:
            title = item.select_one(".s-item__title")
            price = item.select_one(".s-item__price")
            link = item.select_one(".s-item__link")
            loc = item.select_one(".s-item__location")

            if not title or not price or not link:
                continue

            try:
                price_val = float(price.get_text().replace("£", "").replace(",", "").split(" ")[0])
            except:
                continue

            results.append({
                "title": title.text.strip(),
                "price": price_val,
                "link": link['href'],
                "location": loc.text.strip() if loc else "Unknown"
            })

        # Sort by price
        results.sort(key=lambda x: x["price"])

    except Exception as e:
        results = [{"title": f"Error: {e}", "price": 0, "link": "#", "location": "Error"}]

    return render_template_string(html_template, cards=watchlist, results=results)

def search_ebay_loop():
    while True:
        for card in watchlist:
            name = card["name"]
            max_price = card["price"]
            query = name.replace(" ", "+")
            url = f"https://www.ebay.co.uk/sch/i.html?_nkw={query}&_sop=12&LH_BIN=1"

            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, "lxml")
                items = soup.select(".s-item")

                for item in items:
                    title = item.select_one(".s-item__title")
                    price = item.select_one(".s-item__price")
                    link = item.select_one(".s-item__link")

                    if not title or not price or not link:
                        continue

                    try:
                        price_val = float(price.get_text().replace("£", "").replace(",", "").split(" ")[0])
                    except:
                        continue

                    if price_val <= max_price:
                        message = {
                            "content": f"**{title.text}**\nPrice: £{price_val}\n[View Listing]({link['href']})"
                        }
                        requests.post(DISCORD_WEBHOOK, json=message)
                        print(f"Sent alert for: {title.text}")
                        break

            except Exception as e:
                print(f"Error searching eBay: {e}")

        time.sleep(300)  # Check every 5 minutes

# Run background checker thread
threading.Thread(target=search_ebay_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
