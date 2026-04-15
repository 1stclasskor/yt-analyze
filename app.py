import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json
import re
from difflib import SequenceMatcher # 이름 유사도 비교용

st.set_page_config(page_title="유튜브 분석기 V4.1", layout="wide")
st.title("📊 유튜브 데이터 분석기 (오타 자동 병합)")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

uploaded_files = st.file_uploader("캡처 이미지 선택", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 분석 시작"):
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

        # 유사도 기반 병합 로직
        def is_similar(a, b):
            return SequenceMatcher(None, a, b).ratio() > 0.8

        merged = []
        for new_item in all_raw_data:
            new_h = str(new_item.get('handle') or new_item.get('channel_name', ''))
            found = False
            for existing_item in merged:
                ex_h = str(existing_item.get('handle') or existing_item.get('channel_name', ''))
                if is_similar(new_h, ex_h):
                    # 유사하면 데이터 합치기
                    for k, v in new_item.items():
                        if v and not existing_item.get(k):
                            existing_item[k] = v
                    found = True
                    break
            if not found:
                merged.append(new_item)

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
        for data in merged:
            total_v = parse_korean_num(data.get('total_views', 0))
            video_c = parse_korean_num(data.get('video_count', 0))
            sub_c = parse_korean_num(data.get('subscriber_count', 0))
            avg_per_video = int(total_v / video_c) if video_c > 0 else 0
            h_name = str(data.get('handle') or data.get('channel_name', '')).replace('@', '')
            
            final_list.append({
                "채널명": data.get('channel_name'),
                "유튜브 주소": f"https://www.youtube.com/@{h_name}",
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
            df_display = df.copy()
            for col in ["구독자 수", "영상 총 개수", "영상 1개당 평균 조회수", "전체 조회수"]:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,}")
            st.dataframe(df_display.astype(str))
            
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='YouTube')
                workbook, worksheet = writer.book, writer.sheets['YouTube']
                num_format = workbook.add_format({'num_format': '#,##0'})
                worksheet.set_column('C:F', 18, num_format)
            st.download_button("📥 엑셀 다운로드", out.getvalue(), "youtube_master.xlsx")
