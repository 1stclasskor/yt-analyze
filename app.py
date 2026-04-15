import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json

st.set_page_config(page_title="유튜브 채널 세트 분석기 V3", layout="wide")
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
            base64_image = base64.b64encode(file.read()).decode('utf-8')

            # 프롬프트 수정: 주소 형식을 완성하도록 지시
            prompt = """
            이 유튜브 캡처 이미지에서 정보를 추출해 JSON으로만 답해줘.
            키값: channel_name, handle(@주소), email, category, views(조회수 리스트), total_views, video_count, growth_factor
            - handle은 반드시 @를 포함해야 합니다.
            - 데이터가 없으면 null로 표시하세요.
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
                response = requests.post("
