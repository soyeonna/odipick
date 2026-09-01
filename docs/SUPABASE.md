# 데이터베이스(Supabase) 연결 — 소연님이 할 5분

1. <https://supabase.com> 접속 → **Start your project** → 깃허브 계정으로 가입
2. **New project** → 이름 `odipick`, 지역 `Northeast Asia (Seoul)`, 비밀번호는 아무거나 만들어 메모
3. 왼쪽 메뉴 **SQL Editor** → `supabase/schema.sql` 파일 내용 전체 붙여넣고 **Run**
4. 왼쪽 메뉴 **Settings → API** 에서 두 값을 복사:
   - `Project URL`
   - `service_role` 키 (secret 이라고 표시된 것)
5. 컴퓨터의 `.env` 파일에 두 줄 추가:
   ```
   SUPABASE_URL=복사한 URL
   SUPABASE_SERVICE_KEY=복사한 키
   ```
6. 끝. 클로드한테 "수파베이스 연결됐어" 라고 말하면 데이터 업로드부터 이어서 합니다.

**주의**: service_role 키는 비밀번호와 같습니다. 채팅에 붙여넣지 말고 .env 에만.
