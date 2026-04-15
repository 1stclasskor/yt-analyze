import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json
import re

st.set_page_config(page_title="유튜브 분석기 V3.9", layout="wide")
st.title("📊 유튜브 채널 데이터 정밀 분석기")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

st.info("💡 이제 구독자 수, 가입일, 숫자 콤마 표시까지 완벽하게 지원합니다.")

uploaded_files = st.file_uploader("캡처 이미지 선택", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 정밀 분석 시작"):
        all_raw_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, file in enumerate(uploaded_files):
            status_text.text(f"🔍 {i+1}/{len(uploaded_files)} 분석 중...")
            try:
                base64_image = base64.b64encode(file.read()).decode('utf-8')
                # 프롬프트에 구독자 수와 가입일 추가 요청
                prompt = """이미지에서 정보를 추출해 JSON으로만 답해줘.
                항목: channel_name, handle(@주소), subscriber_count(구독자수), email, category, join_date(가입일), total_views(전체조회수), video_count(전체영상개수)
                - 가입일은 2025.07.09 형식으로 추출.
                - 숫자에 포함된 '만', '천' 등은 그대로 텍스트로 포함할 것.
                """
                
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    "response_format": { "type": "json_object" }
                }
                
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res_data = response.json()['choices'][0]['message']['content']
                all_raw_data.append(json.loads(res_data))
            except:
                continue
            progress_bar.progress((i + 1) / len(uploaded_files))

        # 병합 로직
        merged = {}
        for item in all_raw_data:
            h = item.get('handle') or item.get('channel_name')
            if not h: continue
            if h not in merged: merged[h] = item
            else:
                for k, v in item.items():
                    if v and not merged[h].get(k): merged[h][k] = v

        # 숫자 변환 함수 (만, 천 단위 처리)
        def parse_korean_num(v):
            if not v: return 0
            s = str(v).replace(',', '').replace('명', '').replace('개', '').replace('회', '').strip()
            mult = 1
            if '억' in s: mult *= 100000000; s = s.replace('억', '')
            if '만' in s: mult *= 10000; s = s.replace('만', '')
            if '천' in s: mult *= 1000; s = s.replace('천', '')
            
            nums = re.findall(r'\d+\.?\d*', s)
            if not nums: return 0
            return int(float(nums[0]) * mult)

        final_list = []
        for h, data in merged.items():
            handle_clean = str(h).replace('@', '')
            
            # 숫자 데이터 파싱
            total_v = parse_korean_num(data.get('total_views', 0))
            video_c = parse_korean_num(data.get('video_count', 0))
            sub_c = parse_korean_num(data.get('subscriber_count', 0))
            
            # 영상 1개당 평균 조회수 계산
            avg_per_video = int(total_v / video_c) if video_c > 0 else 0

            final_list.append({
                "채널명": data.get('channel_name'),
                "유튜브 주소": f"https://www.youtube.com/@{handle_clean}",
                "구독자 수": sub_c,
                "영상 총 개수": video_c,
                "영상 1개당 평균 조회수": avg_per_video,
                "전체 조회수": total_v,
                "카테고리": data.get('category'),
                "이메일": data.get('email'),
                "채널 가입일": data.get('join_date')
            })

        if final_list:
            df = pd.DataFrame(final_list)
            
            # 화면 출력용 (천단위 콤마 적용)
            df_display = df.copy()
            num_cols = ["구독자 수", "영상 총 개수", "영상 1개당 평균 조회수", "전체 조회수"]
            for col in num_cols:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,}")

            st.subheader("📋 정밀 분석 결과")
            st.dataframe(df_display.astype(str))
            
            # 엑셀 다운로드용 (데이터 타입 유지)
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 정밀 분석 엑셀 다운로드", out.getvalue(), "youtube_business_list.xlsx")
            status_text.success("완벽해 형! 이제 진짜 비즈니스 데이터야!")
