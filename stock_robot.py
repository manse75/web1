import yfinance as yf
import requests
import json
from datetime import datetime

def refresh_kakao_token():
    """카카오 관청에 보낸 마패(토큰)를 자동으로 갱신하는 함수이옵니다."""
    REST_API_KEY = "e9b2c83cd51ed8f2fbff760b3e56d859"
    try:
        with open("kakao_token.json", "r") as fp:
            tokens = json.load(fp)
    except FileNotFoundError:
        print("⚠️ 최초 토큰 파일(kakao_token.json)이 없사옵니다.")
        return None

    with open("kakao_secret.txt", "r") as f:
        client_secret = f.read().strip()

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": "e9b2c83cd51ed8f2fbff760b3e56d859",
        "client_secret": client_secret,
        "refresh_token": tokens["refresh_token"]
    }

    response = requests.post(url, data=data)
    new_tokens = response.json()

    if "access_token" in new_tokens:
        tokens["access_token"] = new_tokens["access_token"]
        if "refresh_token" in new_tokens:
            tokens["refresh_token"] = new_tokens["refresh_token"]
        with open("kakao_token.json", "w") as fp:
            json.dump(tokens, fp)
        return tokens["access_token"]
    else:
        return None

def send_kakao_message(text):
    """전하의 카카오톡 '나에게 보내기' 창으로 메시지를 쏘는 함수이옵니다."""
    access_token = refresh_kakao_token()
    if not access_token:
        print("⚠️ 토큰 갱신 실패로 메시지를 보낼 수 없사옵니다.")
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": text,
            "link": {"web_url": "https://finance.yahoo.com", "mobile_web_url": "https://finance.yahoo.com"},
            "button_title": "미국 증시 자세히 보기"
        })
    }
    requests.post(url, headers=headers, data=payload)

def market_report_job():
    """증시를 조회하여 모바일 카카오톡에 최적화된 상소문을 작성하옵니다."""
    tickers = {
        "S&P500": "^GSPC",
        "나스닥": "^IXIC",
        "다우존스": "^DJI",
        "필반도": "^SOX"  # 이름을 짧게 줄여 글자 수를 아꼈사옵니다.
    }

    now = datetime.now().strftime('%m-%d')
    # 줄 바꿈을 최소화하여 카카오톡 허용 범위를 넘지 않게 하옵니다.
    report = f"[[전하, {now} 증시 요약]]\n"

    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")

            # 💡 [보완] Close(종가) 데이터 중 비어 있는 값(NaN)이 있다면 행 자체를 삭제하옵니다.
            data = data.dropna(subset=['Close'])

            # 실제 숫자가 찍힌 데이터가 최소 2일 치 이상 존재할 때만 계산하옵니다.
            if len(data) >= 2:
                close_price = data['Close'].iloc[-1]
                prev_close = data['Close'].iloc[-2]
                price_change = close_price - prev_close
                pct_change = (price_change / prev_close) * 100
                sign = "▲" if price_change > 0 else "▼"

                # 한 줄에 지수와 변동률이 모두 들어가도록 압축했사옵니다.
                report += f"📊{name}: {close_price:.1f} ({sign}{pct_change:+.2f}%)\n"
            else:
                report += f"⚠️{name}: 데이터 부족\n"
                # 한 줄에 지수와 변동률이 모두 들어가도록 압축했사옵니다.
                report += f"📊{name}: {close_price:.1f} ({sign}{pct_change:+.2f}%)\n"
        except Exception as e:
            report += f"⚠️{name} 실패\n"

    # 완성된 압축 상소문을 카카오톡으로 발송하옵니다.
    send_kakao_message(report)

# 클라우드에 안치했을 때 딱 한 번 실행하고 종료되게 설정함
# (상단 생략: refresh_kakao_token, send_kakao_message, market_report_job 함수는 그대로 두시옵소서)

if __name__ == "__main__":
    # 무한 루프를 모두 걷어내고, 실행 시 상소문만 딱 한 번 올리고 끝나게 하옵니다.
    market_report_job()