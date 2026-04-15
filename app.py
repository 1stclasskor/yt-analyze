import streamlit as st
import base64
import requests

# 1. 사이트 제목 및 설정
st.set_page_config(page_title="유튜브 채널 마스터 분석기", layout="wide")
st.title("📺 유튜브 채널 분석 마스터")

# 2. API 키 입력 (나중에 서버 설정에서 숨길 수 있어)
api_key = st.sidebar.text_input("OpenAI API Key를 입력하세요", type="password")

# 3. 파일 업로드
uploaded_file = st.file_uploader("채널 캡처 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file and api_key:
    # 이미지를 AI가 읽을 수 있게 변환
    base64_image = base64.b64encode(uploaded_file.read()).decode('utf-8')

    if st.button("분석 시작"):
        with st.spinner('AI 마스터가 분석 중입니다...'):
            # OpenAI Vision API에 질문 던지기
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 이미지에서 다음 정보를 추출해서 표 형식으로 정리해줘: 채널명, 채널주소, 카테고리, 최근 영상 5개 평균 조회수, 총 조회수, 업로드 영상 개수, 영상 1개당 평균 조회수, 그리고 이 채널의 떡상 요인 분석까지."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            ans = response.json()['choices'][0]['message']['content']
            
            st.markdown(ans)