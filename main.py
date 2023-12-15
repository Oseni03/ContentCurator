import html
import feedparser
from urllib.parse import urlparse
import pprint
from serpapi import GoogleSearch


class Curator:
    def __init__(self):
        contents = []

    def get_feeds(self, rss_url):
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
        return entries
    
    def google_search(self, text):
        params = {
        "q": text,
        "hl": "en",
        "google_domain": "google.com",
        "api_key": "secret_api_key"
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results


if '__name__'=='__name__':
    curator = Curator()
    feeds = curator.get_feeds('https://www.google.com/alerts/feeds/17807583742681731767/9147937363070830210')
    pprint.pprint(feeds[0].title)
    results = curator.google_search(feeds[0].title)
    print(list(results))