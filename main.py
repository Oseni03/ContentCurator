import html
import json
import pprint
import environ
import requests
import feedparser
from keybert import KeyBERT
from urllib.parse import urlparse
from google_alerts import GoogleAlerts
from relevancy import generate_relevance_score, process_subject_fields
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
        feed = ga.create(topic, {"delivery": delivery, "match_type": match_type})
        return feed

    def read_feeds(self, rss_urls):
        results = []

        for rss_url in rss_urls:
            feed = feedparser.parse(rss_url)

            entries = feed.entries
            for entry in entries:
                google_affiliate_url_parse = urlparse(entry.link).query.split("&")
                for url in google_affiliate_url_parse:
                    if url.startswith("url"):
                        entry["link"] = url.split("=")[-1]
                del entry["id"]
                del entry["guidislink"]
                del entry["published_parsed"]
                del entry["updated_parsed"]
                del entry["author_detail"]
                del entry["title_detail"]
                del entry["links"]
                del entry["content"]

                entry["title"] = html.unescape(
                    entry["title"].replace("</b>", "").replace("<b>", "")
                )
                entry["summary"] = html.unescape(
                    entry["summary"].replace("</b>", "").replace("<b>", "")
                )
                results.append(entry)
        return results

    def extract_keywords(self, texts):
        kw_model = KeyBERT(model="all-mpnet-base-v2")
        keywords = kw_model.extract_keywords(
            texts,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            highlight=False,
            top_n=10,
        )
        keywords_list = list(dict(keywords).keys())
        return keywords_list

    def google_search(self, query):
        url = "https://customsearch.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "key": API_KEY,
            "cx": SEARCH_ENGINE_ID,
        }
        response = requests.get(url, params=params).json()

        pprint.pprint(response)

        results = []
        for item in response["items"]:
            if "webpage" in item["pagemap"]:
                try:
                    data = {
                        "thumbnail": item["pagemap"]["cse_thumbnail"],
                        "datemodified": item["pagemap"]["webpage"][0]["datemodified"],
                        "datecreated": item["pagemap"]["webpage"][0]["datecreated"],
                        "keywords": item["pagemap"]["webpage"][0]["keywords"].split(
                            ","
                        ),
                        "name": item["pagemap"]["webpage"][0]["name"],
                        "site_name": item["pagemap"]["metatags"][0]["og:site_name"],
                        "image_url": item["pagemap"]["webpage"][0]["image"],
                        "link": item["pagemap"]["metatags"][0]["og:url"],
                    }
                    results.append(data)
                except:
                    pass
        return results

    def load_pages(self, urls: list):
        loader = WebBaseLoader(urls)
        docs = loader.load()
        return [doc.page_content for doc in docs]

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
    curator = Curator()
    curator.run()
