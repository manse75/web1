-- ============================================================
-- Supabase 대시보드 > SQL Editor 에서 1회 실행하는 초기 설정입니다.
-- 실행 전에 아래 두 곳의 자리표시자를 본인 값으로 바꾸세요:
--   YOUR_PROJECT_REF : 프로젝트 설정 > General 의 Reference ID
--   YOUR_ANON_KEY    : 프로젝트 설정 > API > anon public 키
-- (이 파일 자체는 자리표시자 상태로만 커밋하고, 실제 키는 절대 커밋 금지)
-- ============================================================

-- 1) 카카오 refresh token 보관 테이블 (Edge Function이 service role로 읽고 씀)
create table if not exists public.kakao_tokens (
  id int primary key,
  refresh_token text not null,
  updated_at timestamptz not null default now()
);

-- RLS를 켜고 정책을 만들지 않음 → anon/일반 사용자는 접근 불가, service role만 접근
alter table public.kakao_tokens enable row level security;

-- 2) 스케줄러 확장 활성화
create extension if not exists pg_cron;
create extension if not exists pg_net;

-- 3) 매일 한국시간 06:30 (= UTC 21:30) 에 Edge Function 호출
select cron.schedule(
  'stock-robot-daily',
  '30 21 * * *',
  $$
  select net.http_post(
    url     := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/stock-robot',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer YOUR_ANON_KEY'
    ),
    body    := '{}'::jsonb
  );
  $$
);

-- 참고: 스케줄 확인  -> select * from cron.job;
-- 참고: 스케줄 삭제  -> select cron.unschedule('stock-robot-daily');
-- 참고: 실행 이력    -> select * from cron.job_run_details order by start_time desc limit 10;
