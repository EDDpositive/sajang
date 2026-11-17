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
# 방문 분석(GoatCounter, 쿠키 없음). 계정 주소가 바뀌면 Actions 변수 GOATCOUNTER로 바꾼다.
GOAT = os.environ.get("GOATCOUNTER") or "https://eddpositive.goatcounter.com/count"
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

# 오래 남는 안내 페이지(g/<slug>.html). 공고 목록과 달리 검색량이 큰 주제를 설명한다.
# 금리처럼 분기마다 바뀌는 숫자는 쓰지 않고 공식 페이지로 연결한다. 숫자를 고치면 CHECKED 날짜도 고친다.
CHECKED = "2026-11-16"
GUIDES = [
    {"slug": "policy-fund-guide", "topic": "policy-fund",
     "h1": "소상공인 정책자금 신청 방법 한 번에 정리",
     "title": "소상공인 정책자금 신청 방법·자격·한도 정리 (2026) | 사장님 지원금 레이더",
     "desc": "소상공인 정책자금이 무엇인지, 누가 받을 수 있는지, 어디서 어떻게 신청하는지 순서대로 정리했어요. 지금 신청 가능한 정책자금 공고도 함께 봐요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 소상공인 정책자금은 정부(소상공인시장진흥공단)가 시중보다 낮은 금리로 빌려주는 사업 자금이에요. 받는 돈이 아니라 갚는 돈이에요.</p></div>
<h2>누가 받을 수 있나요</h2>
<p>사업자등록을 한 소상공인이 대상이에요. 업종마다 상시 근로자 수 기준(대부분 5명 미만, 제조업 등은 10명 미만)이 있고, 자금 종류마다 업력·신용·나이 조건이 따로 붙어요. 휴·폐업 중이거나 세금·대출이 연체 중이면 받기 어려워요.</p>
<h2>자금은 크게 이렇게 나뉘어요</h2>
<ul>
<li><b>일반경영안정자금</b>: 업력과 관계없이 운영 자금이 필요한 사장님. 공고 기준 최대 7천만 원.</li>
<li><b>청년·신용취약 등 대상별 자금</b>: 나이나 신용 상황에 맞춘 자금이 따로 있어요.</li>
<li><b>대환대출</b>: 이미 받은 고금리 대출을 정책자금으로 갈아타는 자금이에요.</li>
</ul>
<p>금리는 \"정책자금 기준금리 + 자금별 가산금리\"로 정해지고 분기마다 바뀌어요. 그래서 여기에는 숫자를 적지 않아요. <a href="https://ols.semas.or.kr/ols/man/SMAN019M/page.do" rel="nofollow noopener" target="_blank">공식 금리표</a>에서 지금 금리를 확인하세요.</p>
<h2>신청 순서</h2>
<ol>
<li><a href="https://ols.semas.or.kr" rel="nofollow noopener" target="_blank">소상공인정책자금 누리집</a>에 들어가 간편인증이나 공동인증서로 로그인해요.</li>
<li>\"정책자금 내비게이터\"로 내 상황에 맞는 자금을 먼저 찾아요.</li>
<li>온라인으로 신청하고, 필요한 서류를 올려요.</li>
<li>공단 확인과 심사를 거쳐 보증서를 받거나 은행에서 대출이 실행돼요(자금마다 방식이 달라요).</li>
</ol>
<p>자금은 예산이 떨어지면 마감돼요. 공고를 미리 확인해 두세요. 헷갈리면 소상공인 통합콜센터 1533-0100에 물어보세요.</p>
<h2>조심할 것</h2>
<p>정책자금은 본인이 직접 신청할 수 있어요. \"대신 받아 주겠다\"며 수수료를 요구하는 브로커를 조심하세요. 공단도 제3자 부당 개입을 주의하라고 안내해요.</p>"""},
    {"slug": "hope-return-guide", "topic": "hope-return",
     "h1": "희망리턴패키지, 폐업하는 사장님이 받을 수 있는 지원",
     "title": "희망리턴패키지 신청 자격·지원 내용 정리 (2026) | 사장님 지원금 레이더",
     "desc": "가게를 접거나 업종을 바꾸려는 소상공인을 위한 희망리턴패키지. 점포철거비, 재취업, 재창업 지원을 누가 어떻게 받는지 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 희망리턴패키지는 폐업했거나 폐업을 앞둔 소상공인이 가게를 정리하고, 다시 취업하거나 창업하도록 돕는 정부 지원이에요.</p></div>
<h2>세 갈래로 나뉘어요</h2>
<ul>
<li><b>원스톱 폐업지원</b>: 점포 철거·원상복구 비용 일부와 폐업 관련 상담(세무·법률 등)을 지원해요. 철거비는 면적에 따라 정해지고 공고 기준 최대 600만 원이에요.</li>
<li><b>재취업 지원</b>: 취업 교육을 받고 취업하면 전직장려수당(공고 기준 최대 100만 원, 나눠서 지급)을 받을 수 있어요.</li>
<li><b>재창업 지원</b>: 다시 창업하려는 사장님에게 교육과 멘토링, 사업화 자금을 지원해요. 차수별로 모집해요.</li>
</ul>
<h2>꼭 알아 둘 조건</h2>
<ul>
<li><b>철거비는 철거하기 전에 신청</b>해야 해요. 이미 철거한 뒤에는 받기 어려워요.</li>
<li>철거비는 돈을 내고 빌린 점포(유상 임대)를 일정 기간 이상 운영한 경우가 대상이에요. 자기 소유 점포는 대상이 아니에요.</li>
<li>재취업 수당은 교육 이수와 고용보험 가입 사업장 취업 같은 조건이 붙어요.</li>
<li>예산이 떨어지면 마감되고, 세부 조건은 해마다 바뀌어요. 신청 전에 공고문을 꼭 확인하세요.</li>
</ul>
<h2>어디서 신청하나요</h2>
<p><a href="https://www.sbiz24.kr" rel="nofollow noopener" target="_blank">소상공인24</a>에서 \"희망리턴패키지\"를 찾아 신청해요. 문의는 소상공인 통합콜센터 1533-0100.</p>"""},
    {"slug": "support-types-guide", "topic": "*",
     "h1": "소상공인 지원금 종류와 찾는 법 한눈에",
     "title": "소상공인 지원금 종류·찾는 법 총정리 (2026) | 사장님 지원금 레이더",
     "desc": "소상공인 지원금은 갚는 돈(정책자금), 안 갚는 돈(사업 지원), 바우처, 인건비·보험료 지원, 폐업 지원으로 나뉘어요. 종류별 차이와 어디서 찾는지, 놓치지 않는 법을 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: \"소상공인 지원금\"은 하나가 아니에요. 갚아야 하는 돈과 안 갚아도 되는 돈, 현금이 아니라 서비스로 받는 지원이 섞여 있어요. 내 상황에 맞는 종류부터 고르면 찾기가 훨씬 쉬워요.</p></div>
<h2>지원금은 다섯 갈래예요</h2>
<ul>
<li><b>정책자금(융자)</b>: 낮은 금리로 빌리는 돈이에요. 갚아야 해요. 운영 자금이 급할 때 봐요. <a href="policy-fund-guide.html">정책자금 신청 방법</a></li>
<li><b>사업 지원(무상)</b>: 판로 개척, 온라인 진출, 시설 개선 같은 사업 비용을 지원해요. 대신 선정 심사가 있고 자부담이 붙는 경우가 많아요.</li>
<li><b>바우처</b>: 현금 대신 정해진 곳에 쓸 수 있는 이용권이에요. 마케팅, 디지털 전환, 컨설팅에 자주 나와요.</li>
<li><b>인건비·보험료 지원</b>: 직원을 뽑았을 때 부담을 덜어 줘요. 대표적인 게 <b>두루누리 사회보험료 지원</b>으로, 근로자 10명 미만 사업장의 신규 가입 근로자에 대해 고용보험·국민연금 보험료의 80%를 지원해요. 보수 기준과 지원 기간 조건이 있으니 근로복지공단 두루누리 안내에서 확인하세요.</li>
<li><b>폐업·재기 지원</b>: 가게를 정리하거나 다시 시작할 때 받는 지원이에요. <a href="hope-return-guide.html">희망리턴패키지 정리</a></li>
</ul>
<h2>어디서 찾나요</h2>
<ul>
<li><b>기업마당</b>: 중앙부처와 지자체의 사업 공고가 모이는 곳이에요. 이 사이트도 기업마당 공식 데이터를 매일 정리해요.</li>
<li><b>소상공인24</b>: 소상공인시장진흥공단 사업(희망리턴패키지 등)을 신청하는 곳이에요.</li>
<li><b>정부24 보조금24</b>: 로그인하면 개인과 가구 기준으로 받을 수 있는 혜택을 조회해 줘요. 사업 공고보다는 개인 혜택 위주예요.</li>
</ul>
<h2>놓치지 않는 법</h2>
<ol>
<li>내 지역과 관심 분야부터 정해요. 지역별·주제별 모음에서 보면 빨라요.</li>
<li>마감일을 먼저 봐요. 예산이 떨어지면 공고 기간 안에도 일찍 끝나요.</li>
<li>공고문의 \"지원 대상\"과 \"제외 대상\"을 꼭 읽어요. 업력, 매출, 업종 조건이 자주 걸려요.</li>
<li>대신 받아 주겠다며 수수료를 요구하는 브로커는 조심하세요. 대부분 직접 신청할 수 있어요.</li>
</ol>"""},
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

AMT1 = re.compile(r"최대\s*([0-9][0-9,\.]*)\s*(억|천만|백만|만)?\s*원")
AMT2 = re.compile(r"([0-9][0-9,]*)\s*(억|천만|백만|만)\s*원\s*(?:한도|이내)")
def amount(x):
    """공고 제목·요약에서 지원 한도를 뽑는다. 못 찾으면 빈 문자열(추측하지 않는다)."""
    blob = x["title"] + " " + x["summary"]
    m = AMT1.search(blob) or AMT2.search(blob)
    if not m: return ""
    return f"최대 {m.group(1)}{m.group(2) or ''} 원"

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
.tag.amt{background:#fff6dc;color:#7a5a00}.tool{display:grid;gap:10px}.tool label{font-weight:700}.tool select,.tool input{padding:10px 12px;border:1px solid var(--line);border-radius:10px;font:inherit;background:#fff}.res{border-radius:12px;padding:14px;margin-top:8px;font-weight:700}.res.ok{background:var(--acc2);color:var(--acc)}.res.no{background:#fbeee7;color:var(--hot)}
footer{font-size:12px;color:var(--sub);margin-top:24px}dt{font-size:12px;color:var(--sub);margin-top:10px}dd{margin:2px 0 0}"""

def page(title, desc, path, body, ld=None):
    canon = f"{SITE}/{path}"
    ldtag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:site_name" content="사장님 지원금 레이더"><meta property="og:locale" content="ko_KR"><meta property="og:image" content="{SITE}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
{ldtag}<style>{CSS}</style><script data-goatcounter="{GOAT}" async src="//gc.zgo.at/count.js"></script></head><body><div class="wrap">{body}
<footer>공고 정보는 기업마당 공식 데이터를 매일 자동으로 정리한 것입니다. 지원 자격과 내용은 반드시 공고 원문에서 확인하세요. 이 사이트는 신청을 대행하거나 선정을 보장하지 않습니다. <a href="{SITE}/about.html">운영 원칙</a></footer></div></body></html>"""

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
            f'<div class="row"><span class="tag{" hot" if is_hot(x) else ""}">{esc(dday(x))}</span>{f'<span class="tag amt">{esc(amount(x))}</span>' if amount(x) else ""}<span>{esc(x["region"])}</span><span>{esc(x["org"])}</span></div></a>')

def hub_links(region_hubs, topic_hubs, base=""):
    """지역별·주제별 모음 페이지 링크 묶음(검색 로봇이 따라갈 수 있는 일반 링크)."""
    out = f'<h2>도구</h2><p class="links"><a href="{base}check.html">우리 가게, 소상공인 맞나요? (30초 확인)</a></p>'
    out += "<h2>알아 두면 좋은 안내</h2><p class=\"links\">" + "".join(
        f'<a href="{base}g/{g["slug"]}.html">{esc(g["h1"])}</a>' for g in GUIDES) + "</p>"
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

def write_extras(out, items, nav_sub):
    """도구·운영 원칙·주간 카드 페이지."""
    nav_root = nav_sub.replace('href="../', 'href="')
    # 소상공인 확인기: 소상공인기본법 기준(상시근로자 수) + 소기업 매출 기준 안내
    check = f"""<header><p class="meta"><a href="./">← 지원금 전체 목록</a></p><h1>우리 가게, 소상공인 맞나요?</h1>
<p class="lead">소상공인 전용 지원금은 이 기준을 먼저 봐요. 업종과 직원 수만 고르면 30초 안에 확인할 수 있어요.</p></header>
<div class="card tool"><label for="ind">주된 업종</label>
<select id="ind"><option value="5">음식점·카페·소매·미용·서비스 등 (대부분 업종)</option><option value="10">제조업</option><option value="10">건설업</option><option value="10">운수업</option><option value="10">광업</option></select>
<label for="emp">상시 근로자 수 (사장님 본인과 가족 무급 종사자는 빼고 세요)</label>
<input id="emp" type="number" min="0" max="999" value="2" inputmode="numeric">
<div class="res ok" id="res" role="status"></div></div>
<div class="card"><p><b>함께 봐야 하는 매출 기준</b>: 소상공인은 먼저 \"소기업\"이어야 해요. 소기업은 업종별로 최근 3년 평균 매출액이 10억~120억 원 이하인 기업이에요. 대부분의 동네 가게는 여기에 들어가요.</p>
<p><b>공식 확인</b>: 지원 신청에 \"소상공인 확인서\"가 필요하면 <a href="https://sminfo.mss.go.kr" rel="nofollow noopener" target="_blank">중소기업현황정보시스템</a>에서 발급해요.</p>
<p class="meta">기준: 소상공인기본법. 광업·제조업·건설업·운수업은 상시 근로자 10명 미만, 그 밖의 업종은 5명 미만. 확인일 {CHECKED}. 개별 사업의 자격은 공고문이 우선이에요.</p></div>
{cta()}{nav_root}
<script>const ind=document.getElementById('ind'),emp=document.getElementById('emp'),res=document.getElementById('res');
function go(){{const lim=+ind.value,n=Math.max(0,Math.floor(+emp.value||0));const ok=n<lim;res.className='res '+(ok?'ok':'no');
res.textContent=ok?`직원 수 기준으로는 소상공인이에요 (${{n}}명 < ${{lim}}명). 매출 기준도 함께 확인하세요.`:`직원 수 기준(${{lim}}명 미만)을 넘어요. 소상공인 전용 지원은 어렵지만, 소기업·중소기업 대상 공고는 신청할 수 있어요.`;}}
[ind,emp].forEach(e=>e.addEventListener('input',go));go();</script>"""
    open(f"{out}/check.html", "w", encoding="utf-8").write(page("소상공인 기준 확인: 우리 가게 소상공인 맞나요? (직원 수·매출) | 사장님 지원금 레이더",
        "업종과 상시 근로자 수만 고르면 소상공인 기준에 드는지 바로 확인해요. 광업·제조·건설·운수업 10명 미만, 그 밖의 업종 5명 미만. 매출 기준과 확인서 발급처도 함께 안내해요.", "check.html", check,
        {"@context": "https://schema.org", "@type": "WebApplication", "name": "소상공인 기준 확인", "applicationCategory": "BusinessApplication", "url": f"{SITE}/check.html"}))
    # 운영 원칙
    about = f"""<header><p class="meta"><a href="./">← 지원금 전체 목록</a></p><h1>운영 원칙</h1></header>
<div class="card"><p><b>데이터</b>: 중소벤처기업부 기업마당의 공식 지원사업 데이터를 매일 오전 6시경 자동으로 받아 정리해요. 소상공인·자영업자와 관련 있는 공고만 골라요.</p>
<p><b>하지 않는 것</b>: 신청 대행, 대출 알선, 선정 보장, 수수료 요구를 하지 않아요. 이런 걸 요구하는 연락은 이 사이트와 관련이 없어요.</p>
<p><b>정확성</b>: 지원 한도 같은 값은 공고 요약에서 자동으로 뽑아요. 틀릴 수 있으니 신청 전에 공고 원문을 꼭 확인하세요.</p>
<p><b>비용</b>: 무료이고 가입이 필요 없어요.</p></div>{cta()}"""
    open(f"{out}/about.html", "w", encoding="utf-8").write(page("운영 원칙 | 사장님 지원금 레이더", "사장님 지원금 레이더의 데이터 출처, 갱신 방식, 하지 않는 일(신청 대행·대출 알선)을 안내해요.", "about.html", about))
    # 주간 카드(인스타그램·스레드용, 1080×1350으로 캡처). 검색엔진에는 내보내지 않는다.
    top = [x for x in items if x["end"]][:5]
    rows = "".join(f'<li><span class="d">{esc(dday(x))}</span><span class="t">{esc(x["title"][:46])}</span><span class="m">{esc(x["region"])}{" · " + esc(amount(x)) if amount(x) else ""}</span></li>' for x in top)
    card = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="robots" content="noindex"><title>마감 임박 지원금 카드</title>
<style>body{{margin:0;background:#1d1b18}}.c{{width:1080px;height:1350px;box-sizing:border-box;padding:80px;background:#f6f4ef;color:#1d1b18;font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans CJK KR",sans-serif;display:flex;flex-direction:column}}
h1{{font-size:68px;line-height:1.2;margin:0 0 12px;letter-spacing:-.02em}}p{{font-size:30px;color:#6b665d;margin:0 0 44px}}ol{{list-style:none;padding:0;margin:0;display:grid;gap:26px;flex:1}}
li{{background:#fff;border:2px solid #e2ddd2;border-radius:28px;padding:26px 30px;display:grid;gap:6px}}.d{{color:#b4532a;font-weight:800;font-size:30px}}.t{{font-size:36px;font-weight:700;line-height:1.3}}.m{{font-size:26px;color:#6b665d}}
.f{{font-size:30px;font-weight:700;color:#2f5d50;margin-top:30px}}</style></head><body><div class="c">
<h1>마감이 가까운<br>소상공인 지원금 {len(top)}건</h1><p>{TODAY.month}월 {TODAY.day}일 기준 · 기업마당 공식 데이터</p><ol>{rows}</ol>
<div class="f">전체 목록: eddpositive.github.io/sajang</div></div></body></html>"""
    open(f"{out}/card.html", "w", encoding="utf-8").write(card)

def build(raw, out="."):
    xs = [norm(i) for i in raw]
    seen, items = set(), []
    for x in xs:
        if relevant(x) and x["id"] not in seen:
            seen.add(x["id"]); items.append(x)
    items.sort(key=lambda x: (x["end"] is None, x["end"] or "9999"))
    for d in ("p", "r", "t", "c"):
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
<div class="card"><dl>{f'<dt>지원 한도 (공고 요약에서 자동 추출)</dt><dd><b>{esc(amount(x))}</b> · 실제 금액은 원문에서 확인하세요</dd>' if amount(x) else ''}<dt>신청 기간</dt><dd>{esc(x['period'] or '공고 원문 확인')}</dd><dt>지원 대상</dt><dd>{esc(x['target'] or '공고 원문 확인')}</dd>
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

    # 지역×주제 모음 페이지(c/<지역>-<주제>.html). "서울 소상공인 정책자금" 같은 긴 검색어를 받는다.
    # 그 지역 공고가 2건 이상인 조합만 만든다(얇은 페이지는 만들지 않는다).
    for reg, rslug, _ in region_hubs:
        if reg == "전국": continue
        for tslug, tname, _ in topic_hubs:
            local = [x for x in by_topic[tslug] if x["region"] == reg]
            if len(local) < 2: continue
            nat = [x for x in by_topic[tslug] if x["region"] == "전국"]
            path = f"c/{rslug}-{tslug}.html"
            h1 = f"{reg} {tname} {MONTH} 신청 가능한 공고"
            lead = f"{reg} 소상공인·자영업자가 지금 신청할 수 있는 {tname} 공고를 마감 순으로 모았어요. 아래에는 지역 제한 없는 전국 공고도 있어요."
            title = f"{reg} {tname} {MONTH} 공고 {len(local)}건 (마감 순) | 사장님 지원금 레이더"
            desc = f"{reg} 소상공인을 위한 {tname} 공고 {len(local)}건과 전국 공고 {len(nat)}건을 마감 순으로 정리했어요. 기업마당 공식 데이터로 매일 갱신."
            write_hub(out, path, h1, title, desc, lead, [(f"{reg} 공고 {len(local)}건", local), (f"전국 공고 {len(nat)}건", nat)], nav_sub)
            hub_paths.append(path)

    # 안내 페이지: 설명 + 관련 주제의 지금 신청 가능한 공고(최대 10건)
    os.makedirs(f"{out}/g", exist_ok=True)
    for g in GUIDES:
        path = f"g/{g['slug']}.html"
        rel = items if g["topic"] == "*" else by_topic.get(g["topic"], [])
        rel_html = ""
        if rel:
            rel_html = f"<h2>지금 신청 가능한 관련 공고 {len(rel)}건</h2>" + "\n".join(li(x, "../") for x in rel[:10])
            if len(rel) > 10:
                more = "../" if g["topic"] == "*" else f'../t/{g["topic"]}.html'
                rel_html += f'<p class="meta"><a href="{more}">관련 공고 {len(rel)}건 전체 보기 →</a></p>'
        body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(g['h1'])}</h1>
<p class="meta">내용 확인일 {CHECKED} · 세부 조건은 해마다 바뀌니 신청 전 공고문을 꼭 확인하세요.</p></header>
{g['body']}{rel_html}{cta()}{nav_sub}"""
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": g["h1"], "dateModified": CHECKED,
              "url": f"{SITE}/{path}"}
        open(f"{out}/{path}", "w", encoding="utf-8").write(page(g["title"], g["desc"], path, body, ld))
        hub_paths.append(path)

    write_extras(out, items, nav_sub)
    hub_paths += ["check.html", "about.html"]

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
    for d in ("r", "t", "c"):
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
