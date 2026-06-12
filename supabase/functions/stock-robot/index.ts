// 미국 증시 요약을 카카오톡 "나에게 보내기"로 발송하는 Supabase Edge Function (Deno)
// 필요한 환경 변수(Supabase Secrets): KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN(최초 1회)
import { createClient } from "npm:@supabase/supabase-js@2";

const KAKAO_REST_API_KEY = Deno.env.get("KAKAO_REST_API_KEY") ?? "";
const KAKAO_CLIENT_SECRET = Deno.env.get("KAKAO_CLIENT_SECRET") ?? "";

// SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 는 Supabase가 자동으로 주입해 줍니다.
const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

const TICKERS: Record<string, string> = {
  "S&P500": "^GSPC",
  "나스닥": "^IXIC",
  "다우존스": "^DJI",
  "필반도": "^SOX",
};

// DB에 저장된 refresh token을 읽고, 없으면 환경 변수(최초 1회 시드)를 사용합니다.
async function getRefreshToken(): Promise<string> {
  const { data, error } = await supabase
    .from("kakao_tokens")
    .select("refresh_token")
    .eq("id", 1)
    .maybeSingle();
  if (error) throw new Error(`kakao_tokens 조회 실패: ${error.message}`);
  if (data?.refresh_token) return data.refresh_token;

  const seed = Deno.env.get("KAKAO_REFRESH_TOKEN");
  if (!seed) {
    throw new Error(
      "refresh token이 없습니다. KAKAO_REFRESH_TOKEN 시크릿을 설정하세요 (get_kakao_token.py 참고).",
    );
  }
  return seed;
}

// refresh token으로 access token을 갱신하고, 카카오가 새 refresh token을 주면 DB에 보관합니다.
async function refreshAccessToken(): Promise<string> {
  const refreshToken = await getRefreshToken();

  const res = await fetch("https://kauth.kakao.com/oauth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      client_id: KAKAO_REST_API_KEY,
      client_secret: KAKAO_CLIENT_SECRET,
      refresh_token: refreshToken,
    }),
  });
  const tokens = await res.json();
  if (!tokens.access_token) {
    throw new Error(`카카오 토큰 갱신 실패: ${JSON.stringify(tokens)}`);
  }

  const { error } = await supabase.from("kakao_tokens").upsert({
    id: 1,
    refresh_token: tokens.refresh_token ?? refreshToken,
    updated_at: new Date().toISOString(),
  });
  if (error) console.error(`refresh token 저장 실패: ${error.message}`);

  return tokens.access_token;
}

interface Quote {
  price: number;
  changePct: number;
}

// 야후 파이낸스 차트 API에서 현재가와 전일 종가를 가져옵니다.
async function fetchQuote(symbol: string): Promise<Quote> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${
    encodeURIComponent(symbol)
  }?range=5d&interval=1d`;
  const res = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0 (stock-robot)" },
  });
  if (!res.ok) throw new Error(`Yahoo HTTP ${res.status}`);

  const json = await res.json();
  const meta = json?.chart?.result?.[0]?.meta;
  const price = meta?.regularMarketPrice;
  const prev = meta?.chartPreviousClose;
  if (typeof price !== "number" || typeof prev !== "number" || prev === 0) {
    throw new Error("시세 데이터 없음");
  }
  return { price, changePct: ((price - prev) / prev) * 100 };
}

async function buildReport(): Promise<string> {
  const kstNow = new Date(Date.now() + 9 * 60 * 60 * 1000);
  const mmdd = `${String(kstNow.getUTCMonth() + 1).padStart(2, "0")}-${
    String(kstNow.getUTCDate()).padStart(2, "0")
  }`;

  let report = `[[전하, ${mmdd} 증시 요약]]\n`;
  for (const [name, symbol] of Object.entries(TICKERS)) {
    try {
      const { price, changePct } = await fetchQuote(symbol);
      const sign = changePct >= 0 ? "▲" : "▼";
      report += `📊${name}: ${price.toFixed(1)} (${sign}${changePct.toFixed(2)}%)\n`;
    } catch (_e) {
      report += `⚠️${name}: 조회 실패\n`;
    }
  }
  return report.trimEnd();
}

async function sendKakaoMessage(text: string, accessToken: string) {
  const res = await fetch(
    "https://kapi.kakao.com/v2/api/talk/memo/default/send",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        template_object: JSON.stringify({
          object_type: "text",
          text,
          link: {
            web_url: "https://finance.yahoo.com",
            mobile_web_url: "https://finance.yahoo.com",
          },
          button_title: "미국 증시 자세히 보기",
        }),
      }),
    },
  );
  const result = await res.json();
  if (result.result_code !== 0) {
    throw new Error(`카카오 메시지 전송 실패: ${JSON.stringify(result)}`);
  }
}

Deno.serve(async (_req) => {
  try {
    const accessToken = await refreshAccessToken();
    const report = await buildReport();
    await sendKakaoMessage(report, accessToken);
    return new Response(
      JSON.stringify({ message: "상소문 송출 완료!", report }),
      { headers: { "Content-Type": "application/json" } },
    );
  } catch (err) {
    console.error(err);
    return new Response(
      JSON.stringify({ error: err instanceof Error ? err.message : String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }
});
