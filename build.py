"""사장님 지원금 레이더 사이트 생성기.
매일 GitHub Actions에서 기업마당 공식 API(지원사업정보)로 공고를 받아
목록 페이지, 공고별 페이지, 지역별·주제별 모음 페이지, sitemap.xml을 만든다. API 키는 저장소 비밀값 BIZINFO_KEY.
로컬 테스트: python build.py --fixture fixtures/sample.json
"""
import html, json, os, re, sys, time, datetime, urllib.parse, urllib.request

SITE = "https://eddpositive.github.io/sajang"
API = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
OPENCHAT = os.environ.get("OPENCHAT_URL") or "https://open.kakao.com/o/gUfaZ8Wi"  # 오픈채팅 링크가 정해지면 Actions 변수로 넣는다
NEWSLETTER = os.environ.get("NEWSLETTER_URL") or "https://s-newsletter-80c205.beehiiv.com/subscribe"  # beehiiv 이메일 구독 페이지
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).date()
MONTH = f"{TODAY.month}월"
KEEP = ["소상공인", "자영업", "1인 창업", "1인창업", "1인 기업", "1인기업", "전통시장", "상인", "상점가", "점포", "골목", "희망리턴", "재창업", "폐업", "정책자금", "예비창업", "창업기업", "초기창업", "온라인 판로", "온라인판로", "배달"]
DROP = ["R&D", "연구", "실증", "과제", "기술개발", "반도체", "바이오", "나노", "수출바우처", "해외전시", "대학", "산학"]
REGIONS = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
# 지역별 모음 페이지 주소(r/<slug>.html). 검색어 "서울 소상공인 지원금" 같은 지역 검색을 받는다.
REGION_SLUG = {"전국": "nationwide", "서울": "seoul", "경기": "gyeonggi", "인천": "incheon", "부산": "busan", "대구": "daegu",
               "광주": "gwangju", "대전": "daejeon", "울산": "ulsan", "세종": "sejong", "강원": "gangwon", "충북": "chungbuk",
               "충남": "chungnam", "전북": "jeonbuk", "전남": "jeonnam", "경북": "gyeongbuk", "경남": "gyeongnam", "제주": "jeju"}
# 주제별 모음 페이지(t/<slug>.html): (주소, 이름, 제목·요약·태그에서 찾을 말)
TOPICS = [
    ("policy-fund", "소상공인 정책자금·대출·보증", ["정책자금", "대출", "보증", "융자", "자금"]),
    ("hope-return", "희망리턴패키지·폐업·재창업 지원", ["희망리턴", "폐업", "재창업", "재기"]),
    ("startup", "예비창업·초기창업 지원", ["예비창업", "초기창업", "창업"]),
    ("sales", "온라인 판로·마케팅 지원", ["판로", "마케팅", "홍보", "라이브커머스", "온라인", "배달"]),
    ("digital", "스마트상점·디지털 전환 지원", ["디지털", "스마트", "키오스크"]),
    ("market", "전통시장·상점가 지원", ["전통시장", "상점가", "골목", "상인"]),
]

def esc(s): return html.escape(str(s or ""), quote=True)
def clean(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).strip()

def fetch():
    key = os.environ.get("BIZINFO_KEY", "").strip()
    if not key: raise SystemExit("BIZINFO_KEY가 없습니다 (저장소 Settings > Secrets > Actions)")
    items = []
    for page in range(1, 6):
        q = urllib.parse.urlencode({"crtfcKey": key, "dataType": "json", "pageIndex": page, "pageUnit": 100})
        req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "Mozilla/5.0 sajang-radar"})
        data = None
        for attempt in range(4):  # 기업마당 서버가 가끔 늦게 응답해서 다시 시도한다
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except Exception as e:
                print(f"page {page} attempt {attempt+1} failed: {e}")
                time.sleep(20 * (attempt + 1))
        if data is None: raise SystemExit("기업마당 API 응답 없음. 기존 사이트는 그대로 둔다.")
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

def is_hot(x):
    return bool(x["end"]) and (datetime.date.fromisoformat(x["end"]) - TODAY).days <= 7

def topics_of(x):
    blob = " ".join([x["title"], x["summary"], x["tags"], x["field"]])
    return [t for t in TOPICS if any(k in blob for k in t[2])]

CSS = """:root{--bg:#f6f4ef;--ink:#1d1b18;--sub:#6b665d;--line:#e2ddd2;--card:#fff;--acc:#2f5d50;--acc2:#e8f0ec;--hot:#b4532a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:0 18px 48px}header{padding:36px 0 14px}h1{font-size:clamp(24px,4.6vw,34px);line-height:1.25;margin:0 0 8px;letter-spacing:-.02em}
h2{font-size:18px;margin:26px 0 10px;letter-spacing:-.01em}
.lead{color:var(--sub);margin:0}.meta{font-size:12px;color:var(--sub);margin-top:6px}a{color:var(--acc)}
.chip{border:1px solid var(--line);background:#fff;border-radius:99px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}.chip:hover{background:var(--acc2)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 12px}.bar input,.bar select{padding:10px 12px;border:1px solid var(--line);border-radius:10px;font:inherit;background:#fff}.bar input{flex:1;min-width:200px}
.item{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit}
.item b{display:block;font-size:16px;margin-bottom:4px}.row{display:flex;gap:6px;flex-wrap:wrap;font-size:12px;color:var(--sub)}
.tag{background:var(--acc2);color:var(--acc);border-radius:99px;padding:1px 8px;font-weight:700}.tag.hot{background:#fbeee7;color:var(--hot)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin:14px 0}.card p{margin:6px 0}
.cta{background:var(--ink);color:#fff;border-radius:16px;padding:18px;margin:20px 0}.cta a{color:#fff;font-weight:700}
.cta-links{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:10px}
.btn{display:inline-block;background:var(--acc);color:#fff;text-decoration:none;border-radius:10px;padding:10px 14px;font-weight:700}
.links a{display:inline-block;margin:4px 6px 4px 0;padding:6px 12px;border:1px solid var(--line);border-radius:99px;background:#fff;text-decoration:none;font-size:14px}
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
    links = []
    if NEWSLETTER:
        sep = "&" if "?" in NEWSLETTER else "?"
        links.append(f'<a class="btn" href="{esc(NEWSLETTER + sep + "utm_source=sajang")}" rel="noopener" target="_blank">이메일로 받기 (무료)</a>')
    if OPENCHAT:
        links.append(f'<a href="{esc(OPENCHAT)}">카톡 오픈채팅으로 받기 →</a>')
    return ('<div class="cta">매주 월요일, 마감 임박 지원금만 골라 보내 드려요.'
            f'<div class="cta-links">{" ".join(links)}</div></div>')

def li(x, base=""):
    """목록 한 줄. base는 p/ 앞에 붙일 상대 경로(목록 페이지 "", 모음 페이지 "../")."""
    return (f'<a class="item" href="{base}p/{x["id"]}.html" data-r="{esc(x["region"])}" data-f="{esc(x["field"])}" data-t="{esc((x["title"]+" "+x["target"]+" "+x["org"]).lower())}"><b>{esc(x["title"])}</b>'
            f'<div class="row"><span class="tag{" hot" if is_hot(x) else ""}">{esc(dday(x))}</span><span>{esc(x["region"])}</span><span>{esc(x["org"])}</span></div></a>')

def hub_links(region_hubs, topic_hubs, base=""):
    """지역별·주제별 모음 페이지 링크 묶음(검색 로봇이 따라갈 수 있는 일반 링크)."""
    if not region_hubs and not topic_hubs: return ""
    out = ""
    if region_hubs:
        out += "<h2>지역별 지원금</h2><p class=\"links\">" + "".join(
            f'<a href="{base}r/{slug}.html">{esc(reg)} ({n})</a>' for reg, slug, n in region_hubs) + "</p>"
    if topic_hubs:
        out += "<h2>주제별 지원금</h2><p class=\"links\">" + "".join(
            f'<a href="{base}t/{slug}.html">{esc(name)} ({n})</a>' for slug, name, n in topic_hubs) + "</p>"
    return out

def write_hub(out, path, h1, title, desc, lead, groups, nav):
    now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    total = sum(len(g) for _, g in groups)
    sections = ""
    for heading, xs in groups:
        if not xs: continue
        if heading: sections += f"<h2>{esc(heading)}</h2>"
        sections += "\n".join(li(x, "../") for x in xs)
    body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(h1)}</h1>
<p class="lead">{esc(lead)}</p><p class="meta">마지막 갱신 {now} (한국 시간) · 공고 {total}건</p></header>
{sections}{cta()}{nav}"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "url": f"{SITE}/{path}"}
    open(f"{out}/{path}", "w", encoding="utf-8").write(page(title, desc, path, body, ld))

def build(raw, out="."):
    xs = [norm(i) for i in raw]
    seen, items = set(), []
    for x in xs:
        if relevant(x) and x["id"] not in seen:
            seen.add(x["id"]); items.append(x)
    items.sort(key=lambda x: (x["end"] is None, x["end"] or "9999"))
    for d in ("p", "r", "t"):
        os.makedirs(f"{out}/{d}", exist_ok=True)

    # 모음 페이지 대상: 공고가 1건 이상인 지역·주제만 만든다(빈 페이지는 만들지 않는다).
    by_region = {reg: [x for x in items if x["region"] == reg] for reg in REGION_SLUG}
    region_hubs = [(reg, REGION_SLUG[reg], len(by_region[reg])) for reg in REGION_SLUG if by_region[reg]]
    by_topic = {slug: [x for x in items if any(t[0] == slug for t in topics_of(x))] for slug, _, _ in TOPICS}
    topic_hubs = [(slug, name, len(by_topic[slug])) for slug, name, _ in TOPICS if by_topic[slug]]
    region_ok = {reg for reg, _, _ in region_hubs}
    topic_ok = {slug for slug, _, _ in topic_hubs}

    for x in items:
        ld = {"@context": "https://schema.org", "@type": "GovernmentService", "name": x["title"],
              "provider": {"@type": "GovernmentOrganization", "name": x["org"] or x["exec"] or "정부·지자체"},
              "areaServed": x["region"], "url": f"{SITE}/p/{x['id']}.html"}
        desc = f"{x['title']} 신청 기간 {x['period'] or '공고 확인'} · 대상 {x['target'] or '공고 확인'} · {x['org']}. 마감일과 원문 링크를 한눈에."
        more = []
        if x["region"] in region_ok:
            more.append(f'<a href="../r/{REGION_SLUG[x["region"]]}.html">{esc(x["region"])} 지원금 전체 보기</a>')
        for slug, name, _ in topics_of(x):
            if slug in topic_ok: more.append(f'<a href="../t/{slug}.html">{esc(name)}</a>')
        more_html = f'<h2>비슷한 공고 더 보기</h2><p class="links">{"".join(more)}</p>' if more else ""
        body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(x['title'])}</h1>
<div class="row"><span class="tag{' hot' if is_hot(x) else ''}">{esc(dday(x))}</span><span class="tag">{esc(x['region'])}</span>{f'<span class="tag">{esc(x["field"])}</span>' if x['field'] else ''}</div></header>
<div class="card"><dl><dt>신청 기간</dt><dd>{esc(x['period'] or '공고 원문 확인')}</dd><dt>지원 대상</dt><dd>{esc(x['target'] or '공고 원문 확인')}</dd>
<dt>담당 기관</dt><dd>{esc(' / '.join(v for v in [x['org'], x['exec']] if v) or '공고 원문 확인')}</dd>
{f'<dt>사업 내용 요약</dt><dd>{esc(x["summary"])}</dd>' if x['summary'] else ''}</dl>
<p style="margin-top:14px"><a class="btn" href="{esc(x['url'])}" rel="nofollow noopener" target="_blank">공고 원문 보기</a></p></div>{more_html}{cta()}"""
        open(f"{out}/p/{x['id']}.html", "w", encoding="utf-8").write(page(f"{x['title']} | 신청 기간·대상 정리", desc, f"p/{x['id']}.html", body, ld))

    # 지역별 모음 페이지
    nav_sub = hub_links(region_hubs, topic_hubs, "../")
    hub_paths = []
    nationwide = by_region.get("전국", [])
    for reg, slug, n in region_hubs:
        path = f"r/{slug}.html"
        if reg == "전국":
            h1 = f"전국 소상공인 지원금·정책자금 {MONTH} 신청 가능한 공고"
            lead = "지역 제한 없이 전국 소상공인·자영업자가 신청할 수 있는 지원금, 정책자금, 지원사업 공고를 마감이 가까운 순서로 모았어요."
            groups = [(None, by_region[reg])]
        else:
            h1 = f"{reg} 소상공인 지원금·정책자금 {MONTH} 신청 가능한 공고"
            lead = f"{reg} 지역 소상공인·자영업자가 지금 신청할 수 있는 지원금과 정책자금 공고예요. 아래에는 어느 지역이든 신청할 수 있는 전국 공고도 함께 있어요."
            groups = [(f"{reg} 지역 공고 {n}건", by_region[reg]), (f"전국 공고 {len(nationwide)}건 (지역 제한 없음)", nationwide)]
        title = f"{reg} 소상공인 지원금·정책자금 {MONTH} 공고 {n}건 (마감 순) | 사장님 지원금 레이더"
        desc = f"{reg} 소상공인·자영업자가 {MONTH} 지금 신청할 수 있는 지원금, 정책자금, 지원사업 공고 {n}건을 마감 순으로 정리했어요. 기업마당 공식 데이터로 매일 갱신."
        write_hub(out, path, h1, title, desc, lead, groups, nav_sub)
        hub_paths.append(path)

    # 주제별 모음 페이지
    for slug, name, n in topic_hubs:
        path = f"t/{slug}.html"
        h1 = f"{name} {MONTH} 신청 가능한 공고"
        lead = f"소상공인·자영업자를 위한 {name} 공고 중 지금 신청할 수 있는 것을 마감이 가까운 순서로 모았어요."
        title = f"{name} {MONTH} 공고 {n}건 (마감 순) | 사장님 지원금 레이더"
        desc = f"{name} 관련 소상공인 지원사업 공고 {n}건을 마감 순으로 정리했어요. 지역·마감일·원문 링크를 한눈에. 기업마당 공식 데이터로 매일 갱신."
        write_hub(out, path, h1, title, desc, lead, [(None, by_topic[slug])], nav_sub)
        hub_paths.append(path)

    lst = "\n".join(li(x, "") for x in items)
    regions = "".join(f"<option>{r}</option>" for r in ["전국"] + REGIONS)
    fields = "".join(f"<option>{esc(f)}</option>" for f in sorted({x['field'] for x in items if x['field']}))
    now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    chips = "".join(f'<button type="button" class="chip" data-k="{k}">{k}</button>' for k in ["정책자금", "대출", "보증", "희망리턴", "재창업", "판로", "마케팅", "디지털", "창업"])
    nav_index = hub_links(region_hubs, topic_hubs, "")
    body = f"""<header><h1>소상공인 정책자금·지원금 지금 신청 가능한 공고</h1>
<p class="lead">자영업자·소상공인·1인 창업자가 지금 신청할 수 있는 정책자금, 지원금, 지원사업 공고를 마감이 가까운 순서로 모았어요. 기업마당 공식 데이터로 매일 자동 갱신돼요.</p>
<p class="meta">마지막 갱신 {now} (한국 시간) · 지금 신청 가능한 공고 {len(items)}건</p></header>
<div class="bar" style="margin-bottom:0">{chips}</div>
<div class="bar"><input id="q" placeholder="검색: 예) 온라인 판로, 마케팅, 정책자금"><select id="r"><option value="">지역 전체</option>{regions}</select><select id="f"><option value="">분야 전체</option>{fields}</select></div>
<div id="list">{lst}</div><p id="none" class="meta" hidden>조건에 맞는 공고가 없어요.</p>{cta()}{nav_index}
<script>const q=document.getElementById('q'),r=document.getElementById('r'),f=document.getElementById('f');
function go(){{const t=q.value.trim().toLowerCase();let n=0;document.querySelectorAll('#list .item').forEach(a=>{{const ok=(!t||a.dataset.t.includes(t))&&(!r.value||a.dataset.r===r.value||a.dataset.r==='전국')&&(!f.value||a.dataset.f===f.value);a.hidden=!ok;if(ok)n++}});document.getElementById('none').hidden=n>0}}
[q,r,f].forEach(e=>e.addEventListener('input',go));document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{{q.value=c.dataset.k;go();}});</script>"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "사장님 지원금 레이더", "url": f"{SITE}/"}
    open(f"{out}/index.html", "w", encoding="utf-8").write(page("소상공인 정책자금·지원금 신청 가능한 공고 (마감 임박 순) | 사장님 지원금 레이더",
        "소상공인 정책자금, 소상공인 지원금, 자영업자 지원사업 중 지금 신청할 수 있는 공고를 마감 순으로 매일 정리합니다. 지역·분야별로 찾고 공고 원문으로 바로 이동하세요.", "", body, ld))
    # 지금 목록에 없는 공고 페이지(마감·기준 밖)와 공고가 0건이 된 모음 페이지는 지운다.
    keep_ids = {x["id"] for x in items}
    for fn in os.listdir(f"{out}/p"):
        if fn.endswith(".html") and fn[:-5] not in keep_ids: os.remove(f"{out}/p/{fn}")
    keep_hubs = set(hub_paths)
    for d in ("r", "t"):
        for fn in os.listdir(f"{out}/{d}"):
            if fn.endswith(".html") and f"{d}/{fn}" not in keep_hubs: os.remove(f"{out}/{d}/{fn}")
    urls = [f"{SITE}/"] + [f"{SITE}/{p}" for p in hub_paths] + [f"{SITE}/p/{x['id']}.html" for x in items]
    open(f"{out}/sitemap.xml", "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"built {len(items)} of {len(raw)} items, {len(hub_paths)} hub pages")
    return items

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--fixture":
        raw = json.load(open(sys.argv[2], encoding="utf-8"))["jsonArray"]; build(raw, "/tmp/sajang_out")
    else:
        build(fetch())
