#!/usr/bin/env python3
import os, logging, requests
log = logging.getLogger(__name__)

FALLBACKS = [
    "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1200&q=80",
    "https://images.unsplash.com/photo-1555099962-4199c345e5dd?w=1200&q=80",
    "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",
    "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=1200&q=80",
]
_idx = 0

class ImageFetcher:
    def get_image(self, title):
        global _idx
        key = os.getenv("UNSPLASH_ACCESS_KEY","")
        if key:
            try:
                r = requests.get("https://api.unsplash.com/photos/random",
                    params={"query": f"{title} programming","orientation":"landscape"},
                    headers={"Authorization": f"Client-ID {key}"}, timeout=10)
                r.raise_for_status()
                return r.json()["urls"]["regular"]
            except: pass
        key = os.getenv("PEXELS_API_KEY","")
        if key:
            try:
                r = requests.get("https://api.pexels.com/v1/search",
                    params={"query": f"{title} programming","per_page":1},
                    headers={"Authorization": key}, timeout=10)
                r.raise_for_status()
                photos = r.json().get("photos",[])
                if photos: return photos[0]["src"]["large"]
            except: pass
        url = FALLBACKS[_idx % len(FALLBACKS)]
        _idx += 1
        return url
