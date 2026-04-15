import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json
import time

st.set_page_config(page_title="유튜브 채널 세트 분석기", layout="wide")
st.title("👨‍🔧 유튜브 채널 정보 병합 & 엑셀 추출기")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

st.info("💡 동일한 채널의 이미지들을 한꺼번에 올려주세요. AI가 핸들(@)을 기준으로 똑똑하게 합쳐드립니다.")

uploaded_files = st.file_uploader("캡처 이미지들을 선택하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 분석 시작"):
        all_raw_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. 각 이미지를 개별적으로 분석 (안정성 확보)
        for i, file in enumerate(uploaded_files):
            status_text.text(f"🔍 {i+1}/{len(uploaded_files)} 번째 이미지 분석 중...")
            base64_image = base64.b64encode(file.read()).decode('utf-8')

            prompt = """
            이 유튜브 캡처 이미지에서 정보를 추출해 JSON으로만 답해줘.
            키값: handle(@주소), channel_name, email, category, views(보이는 영상들 조회수 리스트), total_views, video_count, growth_factor(분석)
            데이터가 없으면 null로 표시해.
            """

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                "response_format": { "type": "json_object" }
            }

            try:
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res_data = response.json()['choices'][0]['message']['content']
                all_raw_data.append(json.loads(res_data))
            except Exception as e:
                st.warning(f"{file.name} 분석 중 오류 발생: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))

        # 2. 핸들(@) 기준으로 데이터 합치기
        status_text.text("📊 데이터 병합 및 정리 중...")
        merged_dict = {}

        for item in all_raw_data:
            h = item.get('handle')
            if not h: continue
            
            if h not in merged_dict:
                merged_dict[h] = item
            else:
                # 데이터 업데이트 (null이 아닌 값으로 덮어쓰기)
                for key, value in item.items():
                    if value and not merged_dict[h].get(key):
                        merged_dict[h][key] = value
                    # 조회수 리스트는 합치기
                    if key == 'views' and value:
                        if isinstance(merged_dict[h]['views'], list):
                            merged_dict[h]['views'].extend(value)
                        else:
                            merged_dict[h]['views'] = value

        # 3. 평균 조회수 등 추가 계산
        final_list = []
        for h, data in merged_dict.items():
            # 평균 조회수 계산 (최근 5개)
            views = data.get('views', [])
            if isinstance(views, list) and len(views) > 0:
                # 숫자만 추출 (예: '418만회' -> 4180000)
                def clean_view(v):
                    if isinstance(v, int): return v
                    v = str(v).replace('조회수', '').replace('회', '').strip()
                    if '만' in v: return float(v.replace('만', '')) * 10000
                    if '천' in v: return float(v.replace('천', '')) * 1000
                    return float(v) if v.isdigit() else 0
                
                clean_views = [clean_view(v) for v in views]
                data['recent_5_avg_views'] = sum(clean_views[:5]) / min(len(clean_views), 5)
            else:
                data['recent_5_avg_views'] = 0

            final_list.append(data)

        # 4. 결과 출력
        df = pd.DataFrame(final_list)
        st.subheader("📋 분석 결과 미리보기")
        st.dataframe(df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(label="📥 엑셀 다운로드", data=output.getvalue(), file_name="yt_analysis.xlsx")
        status_text.success("✅ 분석 완료!")
