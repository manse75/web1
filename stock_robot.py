# -*- coding: utf-8 -*-
"""로컬 테스트용 증시 카카오톡 봇.

실제 운영은 supabase/functions/stock-robot/index.ts (Edge Function)가 담당하고,
이 파일은 PC에서 동작을 미리 확인할 때만 사용합니다.

키는 절대 코드에 적지 않고 환경 변수로만 읽습니다 (PowerShell):
  $env:KAKAO_REST_API_KEY = "REST_API_키"
  $env:KAKAO_CLIENT_SECRET = "Client_Secret"
  python stock_robot.py
refresh token은 get_kakao_token.py 가 만들어 준 kakao_token.json 에서 읽습니다.
"""
import json
import os
import sys
from datetime import datetime

import requests
import yfinance as yf

REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET")


def refresh_kakao_token():
    """refresh token으로 access token을 갱신하고 kakao_token.json을 업데이트합니다."""
    if not REST_API_KEY or not CLIENT_SECRET:
        print("⚠️ 환경 변수 KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET 를 설정하세요.")
        sys.exit(1)

    try:
        with open("kakao_token.json", "r", encoding="utf-8") as fp:
            tokens = json.load(fp)
    except FileNotFoundError:
        print("⚠️ kakao_token.json 이 없습니다. 먼저 get_kakao_token.py 를 실행하세요.")
        return None

    response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": REST_API_KEY,
            "client_secret": CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        },
    )
    new_tokens = response.json()

    if "access_token" in new_tokens:
        tokens["access_token"] = new_tokens["access_token"]
        if "refresh_token" in new_tokens:
            tokens["refresh_token"] = new_tokens["refresh_token"]
        with open("kakao_token.json", "w", encoding="utf-8") as fp:
            json.dump(tokens, fp, ensure_ascii=False, indent=2)
        return tokens["access_token"]
    print(f"⚠️ 토큰 갱신 실패: {new_tokens}")
    return None


def send_kakao_message(text):
    """카카오톡 '나에게 보내기'로 메시지를 전송합니다."""
    access_token = refresh_kakao_token()
    if not access_token:
        print("⚠️ 토큰 갱신 실패로 메시지를 보낼 수 없습니다.")
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": "https://finance.yahoo.com",
                "mobile_web_url": "https://finance.yahoo.com",
            },
            "button_title": "미국 증시 자세히 보기",
        })
    }
    res = requests.post(url, headers=headers, data=payload)
    print(f"전송 결과: {res.json()}")


def market_report_job():
    """증시를 조회하여 카카오톡용 요약 메시지를 작성·발송합니다."""
    tickers = {
        "S&P500": "^GSPC",
        "나스닥": "^IXIC",
        "다우존스": "^DJI",
        "필반도": "^SOX",
    }

    now = datetime.now().strftime("%m-%d")
    report = f"[[전하, {now} 증시 요약]]\n"

    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            data = data.dropna(subset=["Close"])

            if len(data) >= 2:
                close_price = data["Close"].iloc[-1]
                prev_close = data["Close"].iloc[-2]
                pct_change = (close_price - prev_close) / prev_close * 100
                sign = "▲" if pct_change >= 0 else "▼"
                report += f"📊{name}: {close_price:.1f} ({sign}{pct_change:+.2f}%)\n"
            else:
                report += f"⚠️{name}: 데이터 부족\n"
        except Exception:
            report += f"⚠️{name} 실패\n"

    send_kakao_message(report)


if __name__ == "__main__":
    market_report_job()
