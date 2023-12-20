import html
import json
import pprint
import environ
import requests
import feedparser
from keybert import KeyBERT
from urllib.parse import urlparse
from google_alerts import GoogleAlerts
from relevancy import run_relevance_scoring
from langchain.document_loaders import WebBaseLoader

env = environ.Env()
environ.Env.read_env()

API_KEY = env("API_KEY")
SEARCH_ENGINE_ID = env("SEARCH_ENGINE_ID")


class Curator:
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def create_feed(
        self,
        topic,
        delivery="RSS",
        match_type="ALL",
        alert_frequency="AS_IT_HAPPENS",
        region="US",
        language="en",
    ):
        """
        Args:
            delivery: 'RSS' or 'MAIL'
            match_type: 'ALL' or 'BEST'
            alert_frequency: 'AT_MOST_ONCE_A_DAY' or 'AS_IT_HAPPENS' or 'AT_MOST_ONCE_A_WEEK'
        """
        ga = GoogleAlerts(self.email, self.password)
        ga.authenticate()
        feed = ga.create(
            topic,
            {
                "delivery": delivery,
                "match_type": match_type,
                "alert_frequency": alert_frequency,
                "region": region,
                "language": language,
            },
        )
        return feed

    def read_feeds(self, rss_url):
        results = []

        feed = feedparser.parse(rss_url)

        entries = feed.entries
        print(entries)
        for entry in entries:
            google_affiliate_url_parse = urlparse(entry.link).query.split("&")
            for url in google_affiliate_url_parse:
                if url.startswith("url"):
                    entry["link"] = url.split("=")[-1]

            try:
                del entry["guidislink"]
            except:
                pass
            try:
                del entry["published_parsed"]
            except:
                pass
            try:
                del entry["updated_parsed"]
            except:
                pass
            try:
                del entry["author_detail"]
            except:
                pass
            try:
                del entry["title_detail"]
            except:
                pass
            try:
                del entry["links"]
            except:
                pass
            try:
                del entry["content"]
            except:
                pass

            entry["title"] = html.unescape(
                entry["title"].replace("</b>", "").replace("<b>", "")
            )
            entry["summary"] = html.unescape(
                entry["summary"].replace("</b>", "").replace("<b>", "")
            )
            results.append(entry)
        return results

    def get_relevancy_score(self, topic, feeds):
        return run_relevance_scoring(topic, feeds)

    def curate(self, topic: str, context: str):
        """To be done"""
        return {"topic": "", "content": ""}

    def run(
        self,
        rss_urls=[
            "https://www.google.com/alerts/feeds/17807583742681731767/9147937363070830210"
        ],
    ):
        feeds = self.get_feeds(rss_urls)
        for feed in feeds:
            # pprint.pprint(feed)
            results = curator.google_search(feed.title)

            pprint.pprint(results)
            with open("response.json", "w") as file:
                file.write(json.dumps(results, indent=4))

            relevancy, hallucination = generate_relevance_score(
                results,
                query={"topic": feed.title},
                num_result_in_prompt=10,
            )

            links = [rel["link"] for rel in relevancy]

            contexts = self.load_pages(links)

            content = self.curate(feed.title, contexts)
            yield content


if "__name__" == "__name__":
    curator = Curator("hi", "there")
    feeds = curator.read_feeds(
        "https://www.google.com.ng/alerts/feeds/17807583742681731767/11397651099657751387"
    )
    with open("feeds.json", "w") as file:
        file.write(json.dumps(feeds, indent=4))
