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
    {"slug": "startup-support-guide", "topic": "startup",
     "h1": "예비창업자·초기창업자 지원사업 찾는 법과 신청 준비",
     "title": "예비창업·초기창업 지원사업 찾는 법·신청 준비 정리 | 사장님 지원금 레이더",
     "desc": "예비창업자와 창업 초기 사장님이 받을 수 있는 지원사업을 어디서 찾고, 신청 전에 무엇을 준비하면 좋은지 순서대로 정리했어요. 지금 모집 중인 창업 공고도 함께.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 창업 지원사업은 대부분 <a href="https://www.k-startup.go.kr" rel="nofollow noopener" target="_blank">K-Startup(창업지원포털)</a>과 기업마당에 공고가 올라와요. 사업자등록 전인지, 창업 몇 년 차인지에 따라 신청할 수 있는 사업이 달라요.</p></div>
<h2>먼저 내 단계를 확인해요</h2>
<ul>
<li><b>예비창업자</b>: 아직 사업자등록을 하지 않은 사람. \"예비창업\"이라고 적힌 공고만 신청할 수 있는 경우가 많아요. 등록을 먼저 하면 자격을 잃는 사업도 있으니 공고를 본 뒤에 등록하세요.</li>
<li><b>초기창업자</b>: 보통 창업 3년 이내. 업력은 사업자등록일(법인은 설립일)부터 셉니다.</li>
<li><b>재창업자</b>: 폐업 뒤 다시 창업하는 경우는 <a href="hope-return-guide.html">희망리턴패키지 안내</a>도 함께 보세요.</li>
</ul>
<h2>지원 종류</h2>
<ul>
<li><b>사업화 자금</b>: 시제품·마케팅 등에 쓰는 돈. 사업계획서 심사와 발표 평가가 있어요.</li>
<li><b>공간(창업보육센터)</b>: 사무실·공유 공간을 싸게 빌려줘요. 입주 뒤 주사업장을 옮겨야 하는 곳이 많아요.</li>
<li><b>교육·멘토링</b>: 무료 특강, 1:1 멘토링. 선착순이 많아 빨리 마감돼요.</li>
</ul>
<h2>신청 전 준비</h2>
<ol>
<li>공고문의 \"신청 자격\"과 \"제외 대상\"을 먼저 읽어요(나이, 업력, 지역, 업종).</li>
<li>사업계획서 양식을 내려받아 미리 채워 봐요. 문제, 해결 방법, 고객, 돈 버는 방법, 일정 순서로 쓰면 돼요.</li>
<li>제출 서류(신분증, 사업자등록증명, 소상공인 확인서 등)를 확인해요. <a href="sme-certificate-guide.html">소상공인 확인서 발급 안내</a></li>
</ol>
<p>선정되면 협약과 정산 규칙이 있어요. 지원금은 정해진 용도로만 쓰고 증빙을 남겨야 해요.</p>"""},
    {"slug": "online-sales-guide", "topic": "sales",
     "h1": "소상공인 온라인 판로·마케팅 지원 받는 법",
     "title": "소상공인 온라인 판로·마케팅 지원사업 신청 준비 정리 | 사장님 지원금 레이더",
     "desc": "쇼핑몰 입점, 상세페이지·홍보영상 제작, 라이브커머스, 광고비를 도와주는 온라인 판로 지원사업의 종류와 신청 전 준비를 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 온라인 판로 지원은 정부와 시·군이 쇼핑몰 입점, 상세페이지·영상 제작, 광고비 일부를 대신 내주는 사업이에요. 전국 사업은 <a href="https://www.sbiz24.kr" rel="nofollow noopener" target="_blank">소상공인24</a>, 시·군 사업은 각 지자체 공고로 나와요.</p></div>
<h2>자주 나오는 지원</h2>
<ul>
<li><b>입점 지원</b>: 오픈마켓·종합몰·해외 플랫폼 입점 대행과 초기 수수료 지원.</li>
<li><b>콘텐츠 제작</b>: 상세페이지, 제품 사진, 홍보 영상.</li>
<li><b>광고·라이브커머스</b>: 검색광고, 쇼핑검색 광고, 라이브 방송 기획.</li>
</ul>
<h2>신청 전 준비</h2>
<ol>
<li>팔 상품을 정해요. 대부분 \"이미 판매 중이거나 바로 팔 수 있는 상품\"이 있어야 해요.</li>
<li>사업장 소재지를 확인해요. 시·군 사업은 그 지역에 사업자등록이 돼 있어야 신청할 수 있어요.</li>
<li>자기부담금이 있는지 봐요. 지원금 외에 일부를 사장님이 내는 사업이 많아요.</li>
<li>같은 해에 비슷한 사업을 이미 받았으면 중복 지원이 막히는지 공고문에서 확인해요.</li>
</ol>
<p>모집 기간이 짧고 선착순인 경우가 많아요. 아래 공고를 마감 순으로 보세요.</p>"""},
    {"slug": "digital-transition-guide", "topic": "digital",
     "h1": "스마트상점·디지털 전환 지원, 이렇게 준비해요",
     "title": "스마트상점·키오스크·디지털 전환 지원사업 정리 | 사장님 지원금 레이더",
     "desc": "키오스크, 테이블오더, 스마트 기기 도입과 디지털 교육을 도와주는 스마트상점·디지털 전환 지원사업의 종류와 신청 전 준비를 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 디지털 전환 지원은 가게에 키오스크·테이블오더·서빙로봇 같은 기기를 들이거나, 온라인 예약·결제를 배우는 데 드는 비용을 도와주는 사업이에요. 공고는 <a href="https://www.sbiz24.kr" rel="nofollow noopener" target="_blank">소상공인24</a>와 지자체에 나와요.</p></div>
<h2>지원 종류</h2>
<ul>
<li><b>기기 보급</b>: 키오스크, 테이블오더, 스마트미러 등 기기 값의 일부를 지원. 자기부담금이 있어요.</li>
<li><b>교육·컨설팅</b>: 온라인 예약, SNS 홍보, 배달앱 운영을 1:1로 알려 줘요. 중장년 사장님 대상 사업도 있어요.</li>
</ul>
<h2>신청 전 준비</h2>
<ol>
<li>가게에 무엇이 필요한지 먼저 정해요. 기기를 들인 뒤 유지비(월 이용료·통신비)도 계산해요.</li>
<li>공고문의 업종·면적·업력 조건을 확인해요.</li>
<li>공급업체를 사업 쪽에서 정해 주는지, 사장님이 고르는지 확인해요.</li>
</ol>
<p>\"정부 지원으로 무료\"라며 계약을 서두르게 하는 방문 영업은 조심하세요. 공식 공고와 접수처에서 직접 확인하세요.</p>"""},
    {"slug": "sme-certificate-guide", "topic": "*",
     "h1": "소상공인 확인서 발급 방법 (온라인, 무료)",
     "title": "소상공인 확인서 발급 방법·준비 서류·유효기간 정리 | 사장님 지원금 레이더",
     "desc": "지원사업 신청에 자주 필요한 소상공인 확인서를 중소기업현황정보시스템에서 무료로 발급하는 순서, 미리 볼 것, 자주 막히는 부분을 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 소상공인 확인서는 \"우리 가게가 소상공인 기준에 든다\"는 공식 확인이에요. <a href="https://sminfo.mss.go.kr" rel="nofollow noopener" target="_blank">중소기업현황정보시스템</a>에서 온라인으로 무료 발급해요.</p></div>
<h2>언제 필요한가요</h2>
<p>소상공인 전용 지원사업, 정책자금, 지자체 지원금을 신청할 때 제출 서류로 자주 나와요. 공고문 \"제출 서류\" 칸에 \"소상공인 확인서\"가 있으면 미리 받아 두세요. 기준에 드는지 먼저 보고 싶으면 <a href="../check.html">30초 소상공인 확인</a>부터 해 보세요.</p>
<h2>발급 순서</h2>
<ol>
<li>중소기업현황정보시스템에 회원가입하고 사업자 공동인증서(또는 안내된 인증 방식)로 로그인해요.</li>
<li>\"확인서 신청\"에서 소상공인 확인서를 골라요.</li>
<li>매출·상시 근로자 수 자료를 확인해요. 국세청·4대보험 자료가 연계되는 경우가 많고, 안 되면 서류를 올려요.</li>
<li>검토가 끝나면 사이트에서 확인서를 내려받아요.</li>
</ol>
<h2>자주 막히는 부분</h2>
<ul>
<li><b>신규 사업자</b>: 결산 자료가 없으면 다른 서류로 대신하는 방법이 안내돼요. 사이트 안내를 따라가세요.</li>
<li><b>유효기간</b>: 확인서에는 유효기간이 있어요. 지원사업 신청일에 유효한지 꼭 보세요.</li>
<li><b>직원 수</b>: 사장님 본인과 무급 가족은 상시 근로자에 넣지 않아요.</li>
</ul>
<p>막히면 중소기업현황정보시스템 안내 페이지의 상담 번호로 물어보세요.</p>"""},
    {"slug": "yellow-umbrella-guide", "topic": "*",
     "h1": "노란우산공제, 사장님 퇴직금이 되는 제도",
     "title": "노란우산공제 가입 조건·혜택·소득공제 정리 | 사장님 지원금 레이더",
     "desc": "노란우산공제는 소상공인·소기업 사장님이 매달 넣어 폐업·노령 때 돌려받는 공적 공제예요. 누가 가입하는지, 어떤 혜택이 있는지, 어디서 가입하는지 정리했어요.",
     "body": """<div class="card">
<p><b>한 줄로</b>: 노란우산공제는 중소기업중앙회가 운영하는 소기업·소상공인 공제예요. 매달 넣은 돈을 폐업, 사망, 노령 같은 때 돌려받아서 \"사장님 퇴직금\"이라고 불려요.</p></div>
<h2>누가 가입할 수 있나요</h2>
<p>사업자등록을 한 소기업·소상공인 대표가 대상이에요. 업종에 따라 가입이 제한되는 경우(유흥업 등)가 있으니 가입 전에 확인하세요.</p>
<h2>무엇이 좋은가요</h2>
<ul>
<li><b>소득공제</b>: 낸 돈은 사업소득 크기에 따라 정해진 한도 안에서 종합소득세 소득공제를 받아요. 한도는 공식 안내에서 확인하세요.</li>
<li><b>압류 금지</b>: 공제금은 법으로 압류·양도·담보 제공이 금지돼요. 가게가 어려워져도 생활 자금으로 남아요.</li>
<li><b>폐업 때 받는 돈</b>: 폐업하면 낸 돈에 이자를 붙여 공제금으로 받아요.</li>
<li><b>지자체 장려금</b>: 일부 지자체는 신규 가입 소상공인에게 장려금을 더 얹어 줘요. 지역별 조건은 공식 안내에서 봐요.</li>
</ul>
<h2>조심할 것</h2>
<ul>
<li>폐업·노령 같은 사유 없이 중간에 해지하면, 그동안 받은 소득공제만큼 세금이 붙어 손해일 수 있어요.</li>
<li>매달 넣을 금액은 오래 낼 수 있는 만큼만 정하세요.</li>
</ul>
<h2>어디서 가입하나요</h2>
<p><a href="https://www.8899.or.kr" rel="nofollow noopener" target="_blank">노란우산 공식 누리집</a>이나 시중은행 창구에서 가입해요. 문의는 노란우산 콜센터 1666-9988.</p>"""},
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
    lds = ld if isinstance(ld, list) else ([ld] if ld else [])
    ldtag = "".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>' for d in lds)
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
    out = f'<h2>도구</h2><p class="links"><a href="{base}week.html">이번 주 마감 지원금 골라 보기</a><a href="{base}check.html">우리 가게, 소상공인 맞나요? (30초 확인)</a></p>'
    out += "<h2>알아 두면 좋은 안내</h2><p class=\"links\">" + "".join(
        f'<a href="{base}g/{g["slug"]}.html">{esc(g["h1"])}</a>' for g in GUIDES) + "</p>"
    if region_hubs:
        out += "<h2>지역별 지원금</h2><p class=\"links\">" + "".join(
            f'<a href="{base}r/{slug}.html">{esc(reg)} ({n})</a>' for reg, slug, n in region_hubs) + "</p>"
    if topic_hubs:
        out += "<h2>주제별 지원금</h2><p class=\"links\">" + "".join(
            f'<a href="{base}t/{slug}.html">{esc(name)} ({n})</a>' for slug, name, n in topic_hubs) + "</p>"
    return out

def write_hub(out, path, h1, title, desc, lead, groups, nav, intro=""):
    now = datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    total = sum(len(g) for _, g in groups)
    sections = ""
    for heading, xs in groups:
        if not xs: continue
        if heading: sections += f"<h2>{esc(heading)}</h2>"
        sections += "\n".join(li(x, "../") for x in xs)
    body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(h1)}</h1>
<p class="lead">{esc(lead)}</p><p class="meta">마지막 갱신 {now} (한국 시간) · 공고 {total}건</p></header>
{intro}{sections}{cta()}{nav}"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "url": f"{SITE}/{path}"}
    open(f"{out}/{path}", "w", encoding="utf-8").write(page(title, desc, path, body, ld))

def week_picks(items, n=5):
    """주간 소식에 실을 공고: 14일 안에 마감하는 전국·서울·경기 공고를 마감 순으로, 모자라면 금액이 보이는 상시 전국 공고로 채운다."""
    soon = [x for x in items if x["end"] and (datetime.date.fromisoformat(x["end"]) - TODAY).days <= 14
            and x["region"] in ("전국", "서울", "경기")]
    picks = soon[:n]
    if len(picks) < n:
        extra = [x for x in items if not x["end"] and x["region"] == "전국" and amount(x) and x not in picks]
        picks += extra[:n - len(picks)]
    return picks

def write_week(out, items, nav_root):
    """이번 주 마감 페이지(week.html, 검색 노출)와 뉴스레터 초안(w/newsletter.txt, 피클AI가 beehiiv에 그대로 붙인다)."""
    picks = week_picks(items)
    if not picks: return []
    hot7 = [x for x in items if x["end"] and (datetime.date.fromisoformat(x["end"]) - TODAY).days <= 7]
    star = next((x for x in picks if amount(x)), picks[0])
    def link(x, src): return f"{SITE}/p/{x['id']}.html?utm_source={src}"
    lines = [f"이번 주 사장님 지원금 {len(picks)}건 (마감 순)", ""]
    for i, x in enumerate(picks, 1):
        tag = "[마감 임박] " if is_hot(x) else ""
        what = (x["summary"][:110] + ("…" if len(x["summary"]) > 110 else "")) if x["summary"] else amount(x)
        lines += [f"{i}. {tag}{x['title']}",
                  f"누가: {x['target'] or '공고 확인'} ({x['region']}). 공고문에서 자격 확인 필수",
                  f"무엇을: {what or '공고 원문 확인'}",
                  f"마감: {x['end'] or '예산 소진 시까지'} ({dday(x)}) / {link(x, 'newsletter')}", ""]
    lines += [f"이번 주 꼭 볼 것: {star['title']}", f"{star['summary'][:220] or '공고 원문에서 내용을 확인하세요.'}",
              f"자세히: {link(star, 'newsletter')}", "",
              f"지금 신청 가능한 공고 {len(items)}건 전체 보기: {SITE}/?utm_source=newsletter",
              f"주변 사장님께 전달해 주세요. 이번 주 마감 모음: {SITE}/week.html?utm_source=forward",
              "이 소식은 기업마당 공식 데이터로 자동 정리했어요. 신청 대행·대출 알선은 하지 않아요."]
    os.makedirs(f"{out}/w", exist_ok=True)
    open(f"{out}/w/newsletter.txt", "w", encoding="utf-8").write(f"발행 날짜(초안 생성): {TODAY.isoformat()}\n\n" + "\n".join(lines) + "\n")
    wk = (TODAY.day - 1) // 7 + 1
    h1 = f"이번 주 마감 소상공인 지원금 ({TODAY.month}월 {wk}주차)"
    body = f"""<header><p class="meta"><a href="./">← 지원금 전체 목록</a></p><h1>{esc(h1)}</h1>
<p class="lead">이번 주와 다음 주에 끝나는 지원금 중 전국·서울·경기 사장님이 신청할 수 있는 것을 골랐어요. 7일 안에 끝나는 공고는 아래에 모두 있어요.</p>
<p class="meta">{TODAY.isoformat()} 기준 · 기업마당 공식 데이터로 매일 갱신</p></header>
<h2>이번 주 골라 본 {len(picks)}건</h2>{"".join(li(x, "") for x in picks)}
{f'<h2>7일 안에 마감하는 공고 {len(hot7)}건 (전 지역)</h2>' + "".join(li(x, "") for x in hot7) if hot7 else ""}{cta()}{nav_root}"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "url": f"{SITE}/week.html"}
    open(f"{out}/week.html", "w", encoding="utf-8").write(page(f"{h1} | 사장님 지원금 레이더",
        f"{TODAY.month}월 이번 주에 마감하는 소상공인 지원금·정책자금 공고를 골라 마감 순으로 정리했어요. 전국·서울·경기 {len(picks)}건과 7일 안 마감 {len(hot7)}건.", "week.html", body, ld))
    return ["week.html"]

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
        tslugs = [t[0] for t in topics_of(x)]
        gl = [g for g in GUIDES if g["topic"] in tslugs] + [g for g in GUIDES if g["slug"] == "sme-certificate-guide"]
        more_html += '<h2>신청 전에 보면 좋은 안내</h2><p class="links">' + "".join(
            f'<a href="../g/{g["slug"]}.html">{esc(g["h1"])}</a>' for g in gl[:3]) + "</p>"
        body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(x['title'])}</h1>
<div class="row"><span class="tag{' hot' if is_hot(x) else ''}">{esc(dday(x))}</span><span class="tag">{esc(x['region'])}</span>{f'<span class="tag">{esc(x["field"])}</span>' if x['field'] else ''}</div></header>
<div class="card"><dl>{f'<dt>지원 한도 (공고 요약에서 자동 추출)</dt><dd><b>{esc(amount(x))}</b> · 실제 금액은 원문에서 확인하세요</dd>' if amount(x) else ''}<dt>신청 기간</dt><dd>{esc(x['period'] or '공고 원문 확인')}</dd><dt>지원 대상</dt><dd>{esc(x['target'] or '공고 원문 확인')}</dd>
<dt>담당 기관</dt><dd>{esc(' / '.join(v for v in [x['org'], x['exec']] if v) or '공고 원문 확인')}</dd>
{f'<dt>사업 내용 요약</dt><dd>{esc(x["summary"])}</dd>' if x['summary'] else ''}</dl>
<p style="margin-top:14px"><a class="btn" href="{esc(x['url'])}" rel="nofollow noopener" target="_blank">공고 원문 보기</a></p></div>{more_html}{cta()}"""
        crumbs = [("지원금 전체 목록", f"{SITE}/")]
        if x["region"] in region_ok: crumbs.append((f"{x['region']} 지원금", f"{SITE}/r/{REGION_SLUG[x['region']]}.html"))
        crumbs.append((x["title"], f"{SITE}/p/{x['id']}.html"))
        bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}
        endtag = f" ({x['end'][5:].replace('-', '/')} 마감)" if x["end"] else ""
        open(f"{out}/p/{x['id']}.html", "w", encoding="utf-8").write(page(f"{x['title']}{endtag} | 신청 기간·대상 정리", desc, f"p/{x['id']}.html", body, [ld, bc]))

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
        tg = next((g for g in GUIDES if g["topic"] == slug), None)
        intro = f'<p class="card">처음이면 먼저 읽어 보세요: <a href="../g/{tg["slug"]}.html">{esc(tg["h1"])}</a></p>' if tg else ""
        title = f"{name} {MONTH} 공고 {n}건 (마감 순) | 사장님 지원금 레이더"
        desc = f"{name} 관련 소상공인 지원사업 공고 {n}건을 마감 순으로 정리했어요. 지역·마감일·원문 링크를 한눈에. 기업마당 공식 데이터로 매일 갱신."
        write_hub(out, path, h1, title, desc, lead, [(None, by_topic[slug])], nav_sub, intro)
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
    hub_paths += write_week(out, items, nav_sub.replace('href="../', 'href="'))

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
    # 검색으로 들어온 사람이 404를 보지 않게, 빠진 공고는 30일 동안 "마감" 안내(noindex)로 바꿔 둔 뒤 지운다.
    keep_ids = {x["id"] for x in items}
    closed_path = f"{out}/p/closed.json"
    try: closed = json.load(open(closed_path, encoding="utf-8"))
    except (OSError, ValueError): closed = {}
    for fn in os.listdir(f"{out}/p"):
        if not fn.endswith(".html") or fn[:-5] in keep_ids: continue
        pid = fn[:-5]
        if pid not in closed:
            m = re.search(r"<h1>(.*?)</h1>", open(f"{out}/p/{fn}", encoding="utf-8").read(), re.S)
            closed[pid] = {"since": TODAY.isoformat(), "title": html.unescape(m.group(1)) if m else "이 공고"}
        if (TODAY - datetime.date.fromisoformat(closed[pid]["since"])).days > 30:
            os.remove(f"{out}/p/{fn}"); continue
        body = f"""<header><p class="meta"><a href="../">← 지원금 전체 목록</a></p><h1>{esc(closed[pid]['title'])}</h1>
<div class="row"><span class="tag hot">마감됐거나 목록에서 빠진 공고</span></div></header>
<div class="card"><p>이 공고는 신청 기간이 끝났거나 기업마당 목록에서 내려갔어요. 비슷한 공고는 아래에서 지금 신청할 수 있어요.</p>
<p><a class="btn" href="../week.html">이번 주 마감 지원금 보기</a></p></div>{cta()}{nav_sub}"""
        html_out = page(f"[마감] {closed[pid]['title']} | 사장님 지원금 레이더", "마감된 공고예요. 지금 신청할 수 있는 비슷한 지원금을 확인하세요.", f"p/{fn}", body)
        open(f"{out}/p/{fn}", "w", encoding="utf-8").write(html_out.replace("<head>", '<head><meta name="robots" content="noindex">', 1))
    closed = {k: v for k, v in closed.items() if k not in keep_ids and os.path.exists(f"{out}/p/{k}.html")}
    json.dump(closed, open(closed_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
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
