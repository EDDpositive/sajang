"""사장님 지원금 레이더 사이트 생성기.
매일 GitHub Actions에서 기업마당 공식 API(지원사업정보)로 공고를 받아
목록 페이지, 공고별 페이지, sitemap.xml을 만든다. API 키는 저장소 비밀값 BIZINFO_KEY.
로컬 테스트: python build.py --fixture fixtures/sample.json
"""
import html, json, os, re, sys, datetime, urllib.parse, urllib.request

SITE = "https://eddpositive.github.io/sajang"
API = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
OPENCHAT = os.environ.get("OPENCHAT_URL") or "https://open.kakao.com/o/gUfaZ8Wi"  # 오픈채팅 링크가 정해지면 Actions 변수로 넣는다
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).date()
KEEP = ["소상공인", "자영업", "1인 창업", "1인창업", "1인 기업", "1인기업", "전통시장", "상인", "상점가", "점포", "골목", "희망리턴", "재창업", "폐업", "정책자금", "예비창업", "창업기업", "초기창업", "온라인 판로", "온라인판로", "배달"]
DROP = ["R&D", "연구", "실증", "과제", "기술개발", "반도체", "바이오", "나노", "수출바우처", "해외전시", "대학", "산학"]
REGIONS = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

def esc(s): return html.escape(str(s or ""), quote=True)
def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()

def fetch():
    key = os.environ.get("BIZINFO_KEY", "").strip()
    if not key: raise SystemExit("BIZINFO_KEY가 없습니다 (저장소 Settings > Secrets > Actions)")
    items = []
    for page in range(1, 6):
        q = urllib.parse.urlencode({"crtfcKey": key, "dataType": "json", "pageIndex": page, "pageUnit": 100})
        req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "Mozilla/5.0 sajang-radar"})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode("utf-8"))
        arr = data.get("jsonArray") if isinstance(data, dict) else data
        if isinstance(data, dict) and data.get("reqErr"): raise SystemExit("API 오류: " + str(data.get("reqErr")))
        if not arr: break
        items += arr
        if len(arr) < 100: break
    return items

def dates(s):
    s = str(s or "")
    found = re.findall(r"(20\d{2})[-.]?(\d{2})[-.]?(\d{2})", s)
    out = []
    for y, m, d in found:
        try: out.append(datetime.date(int(y), int(m), int(d)))
        except ValueError: pass
    return out

def norm(it):
    title = clean(it.get("pblancNm") or it.get("title"))
    period = clean(it.get("reqstBeginEndDe"))
    ds = dates(period)
    end = ds[-1] if len(ds) >= 1 else None
    begin = ds[0] if len(ds) >= 2 else None
    url = it.get("pblancUrl") or ""
    if url.startswith("/"): url = "https://www.bizinfo.go.kr" + url
    text = " ".join([title, clean(it.get("bsnsSumryCn")), clean(it.get("trgetNm")), clean(it.get("hashtags")), clean(it.get("jrsdInsttNm"))])
    region = next((r for r in REGIONS if r in (clean(it.get("hashtags")) + title + clean(it.get("jrsdInsttNm")))), "전국")
    return {
        "id": re.sub(r"[^A-Za-z0-9_-]", "", str(it.get("pblancId") or "")) or None,
        "title": title, "summary": clean(it.get("bsnsSumryCn"))[:600],
        "target": clean(it.get("trgetNm")), "org": clean(it.get("jrsdInsttNm")), "exec": clean(it.get("excInsttNm")),
        "field": clean(it.get("pldirSportRealmLclasCodeNm")), "period": period,
        "begin": begin.isoformat() if begin else None, "end": end.isoformat() if end else None,
        "url": url, "region": region, "text": text, "tags": clean(it.get("hashtags")),
    }

def relevant(x):
    if not x["id"] or not x["title"]: return False
    if x["end"] and datetime.date.fromisoformat(x["end"]) < TODAY: return False
    if x["field"] == "기술" or any(k in x["title"] for k in DROP): return False
    core = " ".join([x["title"], x["target"], x["tags"]])
    if re.search(r"(?<!중)소기업", core): return True
    return any(k in core for k in KEEP)

def dday(x):
    if not x["end"]: return "상시·예산 소진 시"
    n = (datetime.date.fromisoformat(x["end"]) - TODAY).days
    return "오늘 마감" if n == 0 else f"D-{n}"

CSS = """:root{--bg:#f6f4ef;--ink:#1d1b18;--sub:#6b665d;--line:#e2ddd2;--card:#fff;--acc:#2f5d50;--acc2:#e8f0ec;--hot:#b4532a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:0 18px 48px}header{padding:36px 0 14px}h1{font-size:clamp(24px,4.6vw,34px);line-height:1.25;margin:0 0 8px;letter-spacing:-.02em}
.lead{color:var(--sub);margin:0}.meta{font-size:12px;color:var(--sub);margin-top:6px}a{color:var(--acc)}
.chip{border:1px solid var(--line);background:#fff;border-radius:99px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}.chip:hover{background:var(--acc2)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 12px}.bar input,.bar select{padding:10px 12px;border:1px solid var(--line);border-radius:10px;font:inherit;background:#fff}.bar input{flex:1;min-width:200px}
.item{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit}
.item b{display:block;font-size:16px;margin-bottom:4px}.row{display:flex;gap:6px;flex-wrap:wrap;font-size:12px;color:var(--sub)}
.tag{background:var(--acc2);color:var(--acc);border-radius:99px;padding:1px 8px;font-weight:700}.tag.hot{background:#fbeee7;color:var(--hot)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin:14px 0}.card p{margin:6px 0}
.cta{background:var(--ink);color:#fff;border-radius:16px;padding:18px;margin:20px 0}.cta a{color:#fff;font-weight:700}
.btn{display:inline-block;background:var(--acc);color:#fff;text-decoration:none;border-radius:10px;padding:10px 14px;font-weight:700}
footer{font-size:12px;color:var(--sub);margin-top:24px}dt{font-size:12px;color:var(--sub);margin-top:10px}dd{margin:2px 0 0}"""

def page(title, desc, path, body, ld=None):
    canon = f"{SITE}/{path}"
    ldtag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}">
{ldtag}<style>{CSS}</style></head><body><div class="wrap">{body}
<footer>공고 정보는 기업마당 공식 데이터를 매일 자동으로 정리한 것입니다. 지원 자격과 내용은 반드시 공고 원문에서 확인하세요. 이 사이트는 신청을 대행하거나 선정을 보장하지 않습니다.</footer></div></body></html>"""

def cta():
    if OPENCHAT:
        return f'<div class="cta">매주 월요일, 마감 임박 지원금만 골라 카톡으로 받아 보세요. <a href="{esc(OPENCHAT)}">사장님 지원금 레이더 오픈채팅 입장 →</a></div>'
    return '<div class="cta">매주 월요일, 마감 임박 지원금 소식을 카톡 오픈채팅 "사장님 지원금 레이더"에서 받아 볼 수 있어요.</div>'

def build(raw, out="."):
    xs = [norm(i) for i in raw]
    seen, items = set(), []
    for x in xs:
        if relevant(x) and x["id"] not in seen:
            seen.add(x["id"]); items.append(x)
    items.sort(key=lambda x: (x["end"] is None, x["end"] or "9999"))
    os.makedirs(f"{out}/p", exist_ok=True)
    for x in items:
        hot = x["end"] and (datetime.date.fromisoformat(x["end"]) - TODAY).days <= 7
        ld = {"@context": "https://schema.org", "@type": "GovernmentService", "name": x["title"],
              "provider": {"@type": "GovernmentOrganization", "name": x["org"] or x["exec"] or "정부·지자체"},
              "areaServed": x["region"], "url": f"{SITE}/p/{x['id']}.html"}
        desc = f"{x['title']} 신청 기간 {x['period'] or '공고 확인'} · 대상 {x['target'] or '공고 확인'} · {x['org']}. 마감일과 원문 링크를 한눈에."
        body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(x['title'])}</h1>
<div class="row"><span class="tag{' hot' if hot else ''}">{esc(dday(x))}</span><span class="tag">{esc(x['region'])}</span>{f'<span class="tag">{esc(x["field"])}</span>' if x['field'] else ''}</div></header>
<div class="card"><dl><dt>신청 기간</dt><dd>{esc(x['period'] or '공고 원문 확인')}</dd><dt>지원 대상</dt><dd>{esc(x['target'] or '공고 원문 확인')}</dd>
<dt>담당 기관</dt><dd>{esc(' / '.join(v for v in [x['org'], x['exec']] if v) or '공고 원문 확인')}</dd>
{f'<dt>사업 내용 요약</dt><dd>{esc(x["summary"])}</dd>' if x['summary'] else ''}</dl>
<p style="margin-top:14px"><a class="btn" href="{esc(x['url'])}" rel="nofollow noopener" target="_blank">공고 원문 보기</a></p></div>{cta()}"""
        open(f"{out}/p/{x['id']}.html", "w", encoding="utf-8").write(page(f"{x['title']} | 신청 기간·대상 정리", desc, f"p/{x['id']}.html", body, ld))
    lst = "\n".join(
        f'<a class="item" href="p/{x["id"]}.html" data-r="{esc(x["region"])}" data-f="{esc(x["field"])}" data-t="{esc((x["title"]+" "+x["target"]+" "+x["org"]).lower())}"><b>{esc(x["title"])}</b>'
        f'<div class="row"><span class="tag{" hot" if x["end"] and (datetime.date.fromisoformat(x["end"])-TODAY).days<=7 else ""}">{esc(dday(x))}</span><span>{esc(x["region"])}</span><span>{esc(x["org"])}</span></div></a>'
        for x in items)
    regions = "".join(f"<option>{r}</option>" for r in ["전국"] + REGIONS)
    fields = "".join(f"<option>{esc(f)}</option>" for f in sorted({x['field'] for x in items if x['field']}))
    now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    chips = "".join(f'<button type="button" class="chip" data-k="{k}">{k}</button>' for k in ["정책자금", "대출", "보증", "희망리턴", "재창업", "판로", "마케팅", "디지털", "창업"])
    body = f"""<header><h1>소상공인 정책자금·지원금 지금 신청 가능한 공고</h1>
<p class="lead">자영업자·소상공인·1인 창업자가 지금 신청할 수 있는 정책자금, 지원금, 지원사업 공고를 마감이 가까운 순서로 모았어요. 기업마당 공식 데이터로 매일 자동 갱신돼요.</p>
<p class="meta">마지막 갱신 {now} (한국 시간) · 지금 신청 가능한 공고 {len(items)}건</p></header>
<div class="bar" style="margin-bottom:0">{chips}</div>
<div class="bar"><input id="q" placeholder="검색: 예) 온라인 판로, 마케팅, 정책자금"><select id="r"><option value="">지역 전체</option>{regions}</select><select id="f"><option value="">분야 전체</option>{fields}</select></div>
<div id="list">{lst}</div><p id="none" class="meta" hidden>조건에 맞는 공고가 없어요.</p>{cta()}
<script>const q=document.getElementById('q'),r=document.getElementById('r'),f=document.getElementById('f');
function go(){{const t=q.value.trim().toLowerCase();let n=0;document.querySelectorAll('#list .item').forEach(a=>{{const ok=(!t||a.dataset.t.includes(t))&&(!r.value||a.dataset.r===r.value||a.dataset.r==='전국')&&(!f.value||a.dataset.f===f.value);a.hidden=!ok;if(ok)n++}});document.getElementById('none').hidden=n>0}}
[q,r,f].forEach(e=>e.addEventListener('input',go));document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{{q.value=c.dataset.k;go();}});</script>"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "사장님 지원금 레이더", "url": f"{SITE}/"}
    open(f"{out}/index.html", "w", encoding="utf-8").write(page("소상공인 정책자금·지원금 신청 가능한 공고 (마감 임박 순) | 사장님 지원금 레이더",
        "소상공인 정책자금, 소상공인 지원금, 자영업자 지원사업 중 지금 신청할 수 있는 공고를 마감 순으로 매일 정리합니다. 지역·분야별로 찾고 공고 원문으로 바로 이동하세요.", "", body, ld))
    # 지금 목록에 없는 공고 페이지(마감·기준 밖)는 지워 사이트 주제를 사장님 공고로 유지한다.
    keep_ids = {x["id"] for x in items}
    for fn in os.listdir(f"{out}/p"):
        if fn.endswith(".html") and fn[:-5] not in keep_ids: os.remove(f"{out}/p/{fn}")
    urls = [f"{SITE}/"] + [f"{SITE}/p/{x['id']}.html" for x in items]
    open(f"{out}/sitemap.xml", "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"built {len(items)} of {len(raw)} items")
    return items

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--fixture":
        raw = json.load(open(sys.argv[2], encoding="utf-8"))["jsonArray"]; build(raw, "/tmp/sajang_out")
    else:
        build(fetch())
