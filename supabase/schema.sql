-- 오디픽 데이터베이스 (Supabase SQL Editor에 통째로 붙여넣고 Run)

create table if not exists places (
  id bigint generated always as identity primary key,
  kakao_place_id text unique,
  name text not null,
  place_type text,           -- rest / cafe / bar / play / shop / beauty
  category text,
  cats jsonb default '[]',
  district text,             -- 서구 …
  neighborhood text,         -- 둔산동 …
  road_address text,
  latitude double precision,
  longitude double precision,
  phone text,
  kakao_place_url text,
  hours text,
  budget int,
  cap int,
  sit jsonb default '[]',
  fac jsonb default '{}',
  mood jsonb default '[]',
  v text,
  src text default 'local',  -- reel = 공주픽
  status text default 'open',-- open / closed / suspect
  likes int,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists contents (
  id bigint generated always as identity primary key,
  place_id bigint references places(id),
  platform text default 'instagram',
  code text unique,          -- 릴스 코드
  caption text,
  published_at date,
  likes int, comments int,
  is_ad boolean default false,
  created_at timestamptz default now()
);

create table if not exists place_facts (
  id bigint generated always as identity primary key,
  place_id bigint references places(id),
  field_name text, field_value text,
  source_type text,          -- princess / owner / user / kakao
  confidence int default 50,
  verified_at timestamptz default now(),
  expires_at timestamptz
);

create table if not exists user_reports (
  id bigint generated always as identity primary key,
  place_id bigint references places(id),
  report_type text,          -- open / parking / quiet / wait / price / menu / wrong
  value text,
  created_at timestamptz default now(),
  verification_status text default 'pending'
);

create table if not exists recommendation_logs (
  id bigint generated always as identity primary key,
  query text,
  parsed_conditions jsonb,
  result_count int,
  clicked_place text,
  created_at timestamptz default now()
);

-- 접근 규칙: 손님은 제보·검색기록만 쓸 수 있고, 읽기는 공개 데이터만
alter table places enable row level security;
alter table contents enable row level security;
alter table user_reports enable row level security;
alter table recommendation_logs enable row level security;
create policy "read places" on places for select using (true);
create policy "read contents" on contents for select using (true);
create policy "insert reports" on user_reports for insert with check (true);
create policy "insert logs" on recommendation_logs for insert with check (true);
