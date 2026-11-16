"""사이트맵의 주소를 IndexNow로 검색엔진(빙·네이버 등)에 알린다. 매일 빌드 뒤 한 번 돈다.
키 파일(<KEY>.txt)은 저장소 루트에 있고 사이트에 그대로 공개된다(IndexNow 규칙).
실패해도 사이트에는 영향이 없다(워크플로에서 continue-on-error).
"""
import json, re, sys, urllib.request

KEY = "6bec0220f2d08b66fd20aa72a229c247"
SITE = "https://eddpositive.github.io/sajang"

def main():
    xml = open("sitemap.xml", encoding="utf-8").read()
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    if not urls:
        print("sitemap에 주소 없음"); return
    body = json.dumps({"host": "eddpositive.github.io", "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt",
                       "urlList": urls[:10000]}).encode("utf-8")
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow {r.status}: {len(urls)} urls")
    except urllib.error.HTTPError as e:
        print(f"IndexNow HTTP {e.code}: {e.read()[:200]!r}"); sys.exit(1)

if __name__ == "__main__":
    main()
