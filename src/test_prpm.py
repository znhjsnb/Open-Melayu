import urllib.request
import urllib.parse
import re

url = "https://prpm.dbp.gov.my/Cari1?keyword=belajar"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"Status: {resp.status}, HTML length: {len(html)}")
        # Look for titles or definitions
        titles = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', html, re.IGNORECASE)
        print("Headings:", titles[:5])
        # Look for Kamus Dewan blocks
        if "Kamus Dewan" in html:
            print("[+] Kamus Dewan found in response!")
            idx = html.find("Kamus Dewan")
            print(html[idx:idx+500])
        else:
            print("[-] Kamus Dewan text not directly in static html, checking structure...")
            print(html[:500])
except Exception as e:
    print(f"Error: {e}")
