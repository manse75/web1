# -*- coding: utf-8 -*-
"""카카오 refresh token 최초/재발급 도우미.

사전 준비 (Kakao Developers https://developers.kakao.com):
  1. 내 애플리케이션 > 앱 설정 > 앱 키 → REST API 키 확인
  2. 제품 설정 > 카카오 로그인 → 활성화 ON, Redirect URI에 https://localhost:3000 등록
  3. 제품 설정 > 카카오 로그인 > 보안 → Client Secret 발급, 상태 "사용함"
  4. 제품 설정 > 카카오 로그인 > 동의항목 → "카카오톡 메시지 전송(talk_message)" 활성화

사용법 (PowerShell):
  $env:KAKAO_REST_API_KEY = "재발급한_REST_API_키"
  $env:KAKAO_CLIENT_SECRET = "재발급한_Client_Secret"
  python get_kakao_token.py
"""
import json
import os
import sys
import urllib.parse
import webbrowser

import requests

REDIRECT_URI = "https://localhost:3000"


def main():
    rest_api_key = os.environ.get("KAKAO_REST_API_KEY")
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET")
    if not rest_api_key or not client_secret:
        print("환경 변수 KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET 를 먼저 설정하세요.")
        sys.exit(1)

    auth_url = (
        "https://kauth.kakao.com/oauth/authorize?"
        + urllib.parse.urlencode({
            "client_id": rest_api_key,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message",
        })
    )
    print("브라우저에서 카카오 로그인 후, 주소창에 뜨는 URL의 code= 뒷부분을 복사하세요.")
    print(f"인증 URL: {auth_url}")
    webbrowser.open(auth_url)

    code = input("\ncode 값 입력: ").strip()

    res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
    )
    tokens = res.json()
    if "refresh_token" not in tokens:
        print(f"발급 실패: {tokens}")
        sys.exit(1)

    with open("kakao_token.json", "w", encoding="utf-8") as fp:
        json.dump(tokens, fp, ensure_ascii=False, indent=2)

    print("\n발급 성공! (kakao_token.json 에도 저장됨 — 이 파일은 .gitignore 처리되어 있음)")
    print(f"  access_token : {tokens['access_token'][:12]}... (수명 짧음)")
    print(f"  refresh_token: {tokens['refresh_token']}")
    print("\n위 refresh_token 을 Supabase 시크릿 KAKAO_REFRESH_TOKEN 으로 등록하세요:")
    print("  대시보드 > Edge Functions > Secrets, 또는")
    print("  supabase secrets set KAKAO_REFRESH_TOKEN=... --project-ref <프로젝트REF>")


if __name__ == "__main__":
    main()
