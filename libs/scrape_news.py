import requests
from bs4 import BeautifulSoup
import json

def scrape():
    url = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"
    root_url = "https://news.google.com"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    cards = scrape_cards(soup)

    if not cards:
        print("No news cards found.")
        return

    articles = []

    for idx, card in enumerate(cards, start=1):
        article_data = {}

        title = get_card_title(card)
        if title:
            article_data["title"] = title.text.strip()

        image = get_card_image(card)
        if image:
            article_data["image_link"] = root_url+image.get('src', 'No source URL available')

        news_outlets = get_news_outlets(card)
        outlets_data = []
        if news_outlets:
            for outlet in news_outlets:
                outlet_data = {}
                news_outlet_name = get_news_outlet(outlet)
                news_title = get_news_outlet_title(outlet)

                if news_outlet_name:
                    outlet_data["outlet_name"] = news_outlet_name.text.strip()

                if news_title:
                    news_title_text = news_title.text.strip()
                    news_url = news_title.get('href', None)
                    full_url = f"{root_url}{news_url[1:]}" if news_url else "No URL available"
                    outlet_data["article_title"] = news_title_text
                    outlet_data["url"] = full_url

                if outlet_data:
                    outlets_data.append(outlet_data)

        if outlets_data:
            article_data["outlets"] = outlets_data

        if article_data:
            articles.append(article_data)

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    print("Data in json :):):):)")

def scrape_cards(soup):
    target_classes = {"PO9Zff", "Ccj79", "kUVvS"}
    return soup.find_all("c-wiz", class_=lambda c: c and target_classes == set(c.split()))

def get_news_outlets(card):
    return card.find_all("article", class_="UwIKyb")

def get_news_outlet(article):
    return article.find("div", class_="vr1PYe")

def get_news_outlet_title(article):
    return article.find("a", class_="gPFEn")

def get_card_image(card):
    target_classes = {"Quavad", "vwBmvb"}
    return card.find("img", class_=lambda c: c and target_classes == set(c.split()))

def get_card_title(card):
    title = card.find("a", class_="gPFEn")
    if not title:
        title = card.find("a", class_="JtKRv")
    return title

if __name__ == "__main__":
    scrape()
