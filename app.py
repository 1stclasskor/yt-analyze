import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json

st.set_page_config(page_title="유튜브 채널 세트 분석기 V3.5", layout="wide")
st.title("👨‍🔧 유튜브 채널 정보 병합 & 엑셀 추출기")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

st.info("💡 이미지들을 올려주세요. AI가 채널명과 주소를 정리하여 엑셀로 만들어 드립니다.")

uploaded_files = st.file_uploader("캡처 이미지들을 선택하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 분석 시작"):
        all_raw_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, file in enumerate(uploaded_files):
            status_text.text(f"🔍 {i+1}/{len(uploaded_files)} 번째 이미지 분석 중...")
            try:
                base64_image = base64.b64encode(file.read()).decode('utf-8')
                prompt = "이미지에서 channel_name, handle(@포함), email, category, views(조회수리스트), total_views, video_count, growth_factor를 JSON으로 추출해줘."
                
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
                
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res_data = response.json()['choices'][0]['message']['content']
                all_raw_data.append(json.loads(res_data))
            except Exception as e:
                st.warning(f"{file.name} 분석 중 오류 발생")
            
            progress_bar.progress((i + 1) / len(uploaded_files))

        merged_dict = {}
        for item in all_raw_data:
            h = item.get('handle')
            if not h: continue
            if h not in merged_dict:
                merged_dict[h] = item
            else:
                for key, value in item.items():
                    if value and not merged_dict[h].get(key):
                        merged_dict[h][key] = value
                    if key == 'views' and value:
                        if isinstance(merged_dict[h]['views'], list):
                            merged_dict[h]['views'].extend(value)

        final_list = []
        for h, data in merged_dict.items():
            clean_handle = h.replace('@', '')
            channel_url = f"https://www.youtube.com/@{clean_handle}"
            
            views = data.get('views', [])
            avg_val = 0
            if isinstance(views, list) and len(views) > 0:
                def clean_view(v):
                    v = str(v).replace('조회수', '').replace('회', '').strip()
                    if '만' in v: return float(v.replace('만', '')) * 10000
                    if '천' in v: return float(v.replace('천', '')) * 1000
                    try: return float(v)
                    except: return 0
                clean_views = [clean_view(v) for v in views]
                avg_val = int(sum(clean_views[:5]) / min(len(clean_views), 5))
            
            ordered_data = {
                "채널명": data.get('channel_name'),
                "유튜브 주소": channel_url,
                "카테고리": data.get('category'),
                "이메일": data.get('email'),
                "최근 5개 평균 조회수": avg_val,
                "총 조회수": data.get('total_views'),
                "영상 개수": data.get('video_count'),
                "떡상 요인 분석": data.get('growth_factor')
            }
            final_list.append(ordered_data)

        if final_list:
            df = pd.DataFrame(final_list)
            st.subheader("📋 분석 결과 미리보기")
            st.dataframe(df.astype(str), column_config={"유튜브 주소": st.column_config.Link_Column()})
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            st.download_button(label="📥 최종 엑셀 다운로드", data=output.getvalue(), file_name="youtube_master_list.xlsx")
            status_text.success("✅ 모든 분석 완료!")
