import urllib.request
import urllib.error
import json

def test(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type")
            print(f"[200 OK] {url} -> {len(data)} bytes, Content-Type: {ct}")
            return True, data
    except urllib.error.HTTPError as e:
        print(f"[{e.code} HTTP] {url}")
        return False, e.code

print("=== TESTING OPEN-MELAYU WORKBENCH HTTP SERVER ===")
test("http://127.0.0.1:8766/api/health")
test("http://127.0.0.1:8766/api/stats")
test("http://127.0.0.1:8766/")
test("http://127.0.0.1:8766/styles.css")
test("http://127.0.0.1:8766/app.js")
test("http://127.0.0.1:8766/data/manifest.json")
test("http://127.0.0.1:8766/data/search_index.json")
test("http://127.0.0.1:8766/data/shards/s.json")
test("http://127.0.0.1:8766/missing_file.json")
test("http://127.0.0.1:8766/../server.py")
print("=================================================")
