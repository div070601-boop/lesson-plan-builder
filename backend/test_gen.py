import httpx
import json
import time

gen_id = "621dd9c5-f307-4efe-b9e5-82aeed00d683"
print("Waiting 12 seconds for generation to complete...")
time.sleep(12)

r = httpx.get(f"http://localhost:8000/api/generate/{gen_id}/result")
d = r.json()
print(f"Status: {d['status']}")
print(f"Slides: {len(d['slides'])}")
print(f"Download URL: {d['download_url']}")
print(f"Models: {d['models_used']}")

if d['slides']:
    for s in d['slides']:
        print(f"  Slide {s['index']+1}: [{s['slide_type']}] {s['title']}")
