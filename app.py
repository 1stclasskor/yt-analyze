import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json
import re

st.set_page_config(page_title="유튜브 분석기 V4.0", layout="wide")
st.title("📊 유튜브 데이터 분석기 (엑셀 콤마 자동적용)")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

uploaded_files = st.file_uploader("캡처 이미지 선택", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 분석 및 엑셀 생성"):
        all_raw_data = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            try:
                base64_image = base64.b64encode(file.read()).decode('utf-8')
                prompt = "이미지에서 channel_name, handle(@주소), subscriber_count, email, category, join_date(가입일), total_views, video_count를 JSON으로 추출해."
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    "response_format": { "type": "json_object" }
                }
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                all_raw_data.append(json.loads(response.json()['choices'][0]['message']['content']))
            except: continue
            progress_bar.progress((i + 1) / len(uploaded_files))

        merged = {}
        for item in all_raw_data:
            h = item.get('handle') or item.get('channel_name')
            if not h: continue
            if h not in merged: merged[h] = item
            else:
                for k, v in item.items():
                    if v and not merged[h].get(k): merged[h][k] = v

        def parse_korean_num(v):
            if not v: return 0
            s = str(v).replace(',', '').replace('명', '').replace('개', '').replace('회', '').strip()
            mult = 1
            if '억' in s: mult *= 100000000; s = s.replace('억', '')
            if '만' in s: mult *= 10000; s = s.replace('만', '')
            if '천' in s: mult *= 1000; s = s.replace('천', '')
            nums = re.findall(r'\d+\.?\d*', s)
            return int(float(nums[0]) * mult) if nums else 0

        final_list = []
        for h, data in merged.items():
            total_v = parse_korean_num(data.get('total_views', 0))
            video_c = parse_korean_num(data.get('video_count', 0))
            sub_c = parse_korean_num(data.get('subscriber_count', 0))
            avg_per_video = int(total_v / video_c) if video_c > 0 else 0
            
            final_list.append({
                "채널명": data.get('channel_name'),
                "유튜브 주소": f"https://www.youtube.com/@{str(h).replace('@', '')}",
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
            
            # 1. 화면 출력용 (문자열 변환 후 콤마)
            df_display = df.copy()
            num_cols = ["구독자 수", "영상 총 개수", "영상 1개당 평균 조회수", "전체 조회수"]
            for col in num_cols:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,}")
            st.dataframe(df_display.astype(str))
            
            # 2. 엑셀 출력용 (포맷 지정)
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='YouTube')
                workbook  = writer.book
                worksheet = writer.sheets['YouTube']
                
                # 숫자 포맷 정의 (#,##0)
                num_format = workbook.add_format({'num_format': '#,##0'})
                
                # C(구독자)부터 F(전체조회수)까지 콤마 적용 (열 인덱스 2, 3, 4, 5)
                worksheet.set_column('C:F', 15, num_format)
                
            st.download_button("📥 엑셀 다운로드 (콤마 적용됨)", out.getvalue(), "youtube_analysis.xlsx")
