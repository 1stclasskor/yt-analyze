import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json

st.set_page_config(page_title="유튜브 채널 세트 분석기", layout="wide")
st.title("👨‍🔧 유튜브 채널 정보 병합 & 엑셀 추출기")

# API 키 설정
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

st.info("💡 동일한 채널의 [정보 화면]과 [영상 화면] 캡처본을 동시에 올려주세요. AI가 핸들(@)을 기준으로 합쳐서 분석합니다.")

# 1. 멀티 업로드 (accept_multiple_files=True)
uploaded_files = st.file_uploader("캡처 이미지 세트들을 선택하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 세트 병합 및 분석 시작"):
        # 이미지를 base64로 미리 변환
        images_data = []
        for file in uploaded_files:
            base64_image = base64.b64encode(file.read()).decode('utf-8')
            images_data.append({"name": file.name, "base64": base64_image})

        # --- AI에게 던질 프롬프트 (핵심 로직) ---
        prompt = """
        당신은 유튜브 채널 분석 마스터입니다. 업로드된 여러 이미지들을 분석하여 다음 미션을 수행하세요.

        [미션 1: 이미지 병합]
        이미지 속의 고유 핸들(예: @건강루카스77)을 찾으세요. 동일한 핸들을 가진 이미지들은 서로 다른 화면(예: 채널 정보창, 인기영상창)을 캡처한 '한 세트'입니다. 

        [미션 2: 정보 추출 및 취합]
        각 '핸들 세트'별로 다음 정보를 통합하여 추출하세요. 정보가 여러 이미지에 흩어져 있어도 하나로 합쳐야 합니다.

        [추출 항목 (JSON 키값)]
        - handle: @로 시작하는 채널 고유 주소 (이걸로 세트 판별)
        - channel_name: 채널명
        - email: 설명란에 있는 이메일 (없으면 "없음")
        - category: 채널의 주력 콘텐츠 카테고리
        - recent_5_avg_views: 최근/인기 영상 5개의 평균 조회수 (계산)
        - total_views: 추가 정보에 있는 총 조회수
        - video_count: 동영상 개수
        - total_avg_efficiency: total_views / video_count 계산값
        - growth_factor: 썸네일, 제목, 카테고리를 종합한 떡상 요인 3줄 분석

        출력은 반드시 다른 설명 없이 JSON 배열 형식으로만 하세요.
        예시: [{"handle": "@test", ...}, {"handle": "@test2", ...}]
        """

        # 이미지 리스트 생성
        image_content = [{"type": "text", "text": prompt}]
        for img in images_data:
            image_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img['base64']}"}
            })

        with st.spinner('AI가 이미지 세트를 병합하고 분석 중입니다... 시간이 좀 걸릴 수 있습니다.'):
            # API 호출
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": image_content}],
                "response_format": { "type": "json_object" }
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # 결과 처리
            try:
                res_json = response.json()
                # GPT가 'choices' 안에 답을 주지 않을 때를 대비한 예외처리
                if 'choices' not in res_json or not res_json['choices']:
                    st.error(f"API 호출 오류: {res_json}")
                    st.stop()

                raw_content = res_json['choices'][0]['message']['content']
                # 내용이 비어있거나 JSON 형식이 아닐 때를 대비
                if not raw_content:
                    st.error("AI가 답변을 생성하지 못했습니다. 다시 시도해 주세요.")
                    st.stop()

                # 'channels'라는 키로 묶여서 나올 수 있으므로 처리
                data_dict = json.loads(raw_content)
                # 만약 전체가 배열이라면 그대로 쓰고, 키 안에 있다면 그 키를 가져옴
                if isinstance(data_dict, list):
                    all_results = data_dict
                elif isinstance(data_dict, dict):
                    # 가장 널리 쓰이는 키 이름들 확인
                    keys = ['channels', 'results', 'data']
                    found_key = next((k for k in keys if k in data_dict), None)
                    if found_key:
                        all_results = data_dict[found_key]
                    else:
                        # 키를 못 찾으면 딕셔너리의 첫 번째 값(배열일 확률 높음)을 가져옴
                        all_results = next(iter(data_dict.values())) if data_dict.values() else []
                else:
                    all_results = []

                if not all_results or not isinstance(all_results, list):
                     st.error("분석 결과를 표로 변환하지 못했습니다. AI 답변 형식을 확인해야 합니다.")
                     st.stop()

                # 2. 데이터프레임 생성 및 출력
                df = pd.DataFrame(all_results)
                
                # 순서 보장을 위해 컬럼명 지정 (AI가 준 키값과 일치해야 함)
                cols = ['handle', 'channel_name', 'email', 'category', 'recent_5_avg_views', 'total_views', 'video_count', 'total_avg_efficiency', 'growth_factor']
                # AI가 주지 않은 컬럼이 있을 수 있으므로 존재하는 것만 필터링
                actual_cols = [c for c in cols if c in df.columns]
                df = df[actual_cols]

                st.subheader("📋 병합 분석 결과 미리보기")
                st.dataframe(df)

                # 3. 엑셀 다운로드 버튼
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='YouTube_Analysis')
                
                st.download_button(
                    label="📥 병합된 엑셀 파일 다운로드",
                    data=output.getvalue(),
                    file_name="youtube_merged_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except json.JSONDecodeError:
                st.error("AI의 답변을 JSON으로 변환하는 데 실패했습니다. 프롬프트를 점검해야 합니다.")
                st.write("AI 답변 원문:", raw_content)
