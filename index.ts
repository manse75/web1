Deno.serve(async (req) => {
  try {
    // 수파베이스 구름 관청 안에서 전하의 파이썬 로봇을 깨우는 명령이옵니다.
    const command = new Deno.Command("python3", {
      args: ["stock_robot.py"],
    });

    const { success, stderr } = await command.output();

    if (!success) {
      const errorString = new TextDecoder().decode(stderr);
      return new Response(JSON.stringify({ error: errorString }), { status: 500 });
    }

    return new Response(JSON.stringify({ message: "상소문 송출 완료!" }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
});
