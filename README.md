# 📈 미국 증시 카카오톡 아침 보고 봇

매일 **한국시간 오전 6시 30분**, S&P500 · 나스닥 · 다우존스 · 필라델피아 반도체 지수 요약을
카카오톡 "나에게 보내기"로 발송합니다.

## 동작 구조

```
GitHub (이 저장소)
   └─ push → GitHub Actions → Supabase Edge Function 자동 배포
Supabase
   ├─ Edge Function (supabase/functions/stock-robot) : 시세 조회 + 카톡 발송
   ├─ DB 테이블 kakao_tokens : 카카오 refresh token 보관 (자동 갱신)
   └─ pg_cron : 매일 UTC 21:30 (= KST 06:30) 함수 호출
```

## 🔑 필요한 카카오 키 3가지와 재발급 방법

모두 [Kakao Developers](https://developers.kakao.com) > 내 애플리케이션에서 처리합니다.

| 키 | 위치 | 재발급 방법 |
|---|---|---|
| **REST API 키** | 앱 설정 > 앱 키 | 앱 키 화면의 **재발급** 버튼 클릭 (기존 키 즉시 무효화) |
| **Client Secret** | 제품 설정 > 카카오 로그인 > 보안 | **코드 재생성** 버튼 클릭, 상태를 "사용함"으로 |
| **Refresh Token** | OAuth 인증으로 발급 | 이 저장소의 `get_kakao_token.py` 실행 (아래 참고) |

> ⚠️ 키가 한 번이라도 공개 저장소에 올라갔다면 세 가지 모두 반드시 재발급하세요.

### Refresh Token 발급 절차

사전 설정 (Kakao Developers, 1회):
1. 제품 설정 > 카카오 로그인 → **활성화 ON**
2. 카카오 로그인 > Redirect URI 에 `https://localhost:3000` 등록
3. 카카오 로그인 > 동의항목 → **카카오톡 메시지 전송(talk_message)** 활성화

발급 (PowerShell):
```powershell
$env:KAKAO_REST_API_KEY = "재발급한_REST_API_키"
$env:KAKAO_CLIENT_SECRET = "재발급한_Client_Secret"
python get_kakao_token.py
```
브라우저 로그인 후 주소창의 `code=` 값을 붙여넣으면 refresh token이 출력됩니다.
(refresh token 유효기간은 약 2개월이지만, 봇이 매일 실행되며 자동 연장되므로 재발급 걱정 없음)

## ⚙️ 환경 변수(시크릿) 설정 위치

### 1. Supabase — 대시보드 > Edge Functions > Secrets

| 이름 | 값 |
|---|---|
| `KAKAO_REST_API_KEY` | REST API 키 |
| `KAKAO_CLIENT_SECRET` | Client Secret |
| `KAKAO_REFRESH_TOKEN` | 발급받은 refresh token (최초 1회 시드용) |

CLI 사용 시: `supabase secrets set KAKAO_REST_API_KEY=... --project-ref <REF>`

### 2. GitHub — 저장소 Settings > Secrets and variables > Actions

| 이름 | 값 |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | [계정 토큰 페이지](https://supabase.com/dashboard/account/tokens)에서 발급 |
| `SUPABASE_PROJECT_REF` | Supabase 프로젝트 설정 > General > Reference ID |

### 3. 로컬 PC — 환경 변수 또는 `.env` (gitignore됨)

`.env.example` 참고. 코드에 키를 직접 적지 않습니다.

## 🚀 최초 설치 순서

1. **Supabase 프로젝트 생성** — https://supabase.com/dashboard → New project
2. **카카오 키 재발급** + `get_kakao_token.py`로 refresh token 발급
3. **Supabase Secrets 등록** (위 표 3개)
4. **GitHub Secrets 등록** (위 표 2개) → main에 push하면 Actions가 함수를 자동 배포
   - 수동 배포: `supabase functions deploy stock-robot --project-ref <REF>`
5. **`setup.sql` 실행** — Supabase 대시보드 > SQL Editor에 붙여넣고
   `YOUR_PROJECT_REF`, `YOUR_ANON_KEY`를 본인 값으로 바꾼 뒤 Run
   (토큰 테이블 생성 + 매일 06:30 KST 스케줄 등록)
6. **테스트** — PowerShell에서:
   ```powershell
   curl.exe -X POST "https://<REF>.supabase.co/functions/v1/stock-robot" -H "Authorization: Bearer <ANON_KEY>"
   ```
   카카오톡으로 보고서가 오면 성공.

## 파일 안내

| 파일 | 역할 |
|---|---|
| `supabase/functions/stock-robot/index.ts` | 메인 봇 (Edge Function, Deno/TypeScript) |
| `setup.sql` | DB 테이블 + pg_cron 스케줄 (SQL Editor에서 1회 실행) |
| `.github/workflows/deploy.yml` | push 시 자동 배포 |
| `get_kakao_token.py` | refresh token 최초/재발급 도우미 |
| `stock_robot.py` | 로컬 테스트용 (운영에는 사용하지 않음) |
| `.env.example` | 필요한 환경 변수 목록 (실제 값 금지) |
