import html
import json
import pprint
import environ
import requests
import feedparser
from urllib.parse import urlparse

env = environ.Env()
environ.Env.read_env()

API_KEY = env("API_KEY")
SEARCH_ENGINE_ID = env("SEARCH_ENGINE_ID")


class Curator:
    def __init__(self):
        contents = []

    def get_feeds(self, rss_urls):
        results = []

        for rss_url in rss_urls:
            feed = feedparser.parse(rss_url)

            entries = feed.entries
            for entry in entries:
                google_affiliate_url_parse = urlparse(entry.link).query.split('&')
                for url in google_affiliate_url_parse:
                    if url.startswith('url'):
                        entry['link'] = url.split('=')[-1]
                del entry['id']
                del entry['guidislink']
                del entry['published_parsed']
                del entry['updated_parsed']
                del entry['author_detail']
                del entry['title_detail']
                del entry['links']
                del entry['content']

                if 'www.youtube.com' in entry['link']:
                    entry['is_youtube'] = True
                
                entry['title'] = html.unescape(entry['title'].replace('</b>', '').replace('<b>', ''))
                entry['summary'] = html.unescape(entry['summary'].replace('</b>', '').replace('<b>', ''))

                results.append(entry)
        return results
    
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
            if "webpage" in item["pagemap"] and item["pagemap"]["metatags"][0]["og:type"] != "video":
                data = {
                    "thumbnail": item["pagemap"]["cse_thumbnail"],
                    "datemodified": item["pagemap"]["webpage"][0]["datemodified"],
                    "datecreated": item["pagemap"]["webpage"][0]["datecreated"],
                    "keywords": item["pagemap"]["webpage"][0]["keywords"],
                    "name": item["pagemap"]["webpage"][0]["name"],
                    "site_name": item["pagemap"]["metatags"][0]["og:site_name"],
                    "image_url": item["pagemap"]["webpage"][0]["image"],
                    "link": item["pagemap"]["metatags"][0]["og:url"],
                }
                results.append(data)
        return results


if '__name__'=='__name__':
    curator = Curator()
    feeds = curator.get_feeds(['https://www.google.com/alerts/feeds/17807583742681731767/9147937363070830210'])
    pprint.pprint(feeds[0].title)
    results = curator.google_search(feeds[0].title)
    with open("response.json", "w") as file:
        file.write(json.dumps(results, indent=4))
