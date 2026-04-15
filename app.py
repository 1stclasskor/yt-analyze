import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="유튜브 채널 엑셀 마스터", layout="wide")
st.title("📊 유튜브 채널 대량 분석 & 엑셀 추출기")

# API 키 설정 (Secrets에서 가져오거나 입력)
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

# 1. 파일 멀티 업로드 설정
uploaded_files = st.file_uploader("채널 캡처 이미지들을 선택하세요 (여러 장 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 대량 분석 시작"):
        all_results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            # 이미지 인코딩
            base64_image = base64.b64encode(file.read()).decode('utf-8')
            
            # AI에게 데이터 요청 (JSON 형식으로 고정)
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이미지에서 정보를 추출해 JSON 형식으로만 답해줘. 키값: 채널명, 채널주소, 카테고리, 최근영상5개평균조회수, 총조회수, 영상개수, 평균조회수(총조회수/영상개수), 떡상요인"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                "response_format": { "type": "json_object" }
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            # 결과값 정리
            import json
            data = json.loads(response.json()['choices'][0]['message']['content'])
            all_results.append(data)
            
            # 진행바 업데이트
            progress_bar.progress((i + 1) / len(uploaded_files))

        # 2. 데이터프레임 생성 및 출력
        df = pd.DataFrame(all_results)
        st.subheader("📋 분석 결과 미리보기")
        st.dataframe(df)

        # 3. 엑셀 다운로드 버튼 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(
            label="📥 엑셀 파일로 다운로드",
            data=output.getvalue(),
            file_name="youtube_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
