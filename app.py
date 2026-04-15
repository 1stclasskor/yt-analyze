import streamlit as st
import base64
import requests
import pandas as pd
from io import BytesIO
import json
import re
from difflib import SequenceMatcher

st.set_page_config(page_title="유튜브 분석 마스터 V4.5", layout="wide")
st.title("🛡️ 자동 리셋 & 중복 제거 분석기")

# 1. 세션 상태 관리
if 'analysis_history' not in st.session_state:
    st.session_state['analysis_history'] = []
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if not api_key:
    api_key = st.secrets.get("OPENAI_API_KEY", "")

if st.sidebar.button("🗑️ 전체 기록 초기화"):
    st.session_state['analysis_history'] = []
    st.session_state['uploader_key'] += 1 # 업로더 리셋
    st.rerun()

st.info("💡 분석이 완료되면 업로드 리스트가 자동으로 비워집니다. 새 이미지를 바로 올리세요!")

# uploader_key를 바꿔서 업로더를 초기화함
uploaded_files = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'], 
                                  accept_multiple_files=True, 
                                  key=f"uploader_{st.session_state['uploader_key']}")

# 숫자 파싱 및 유사도 비교 함수 (V4.4와 동일)
def parse_korean_num(v):
    if not v: return 0
    s = str(v).replace(',', '').replace('명', '').replace('개', '').replace('회', '').strip()
    mult = 1
    if '억' in s: mult *= 100000000; s = s.replace('억', '')
    if '만' in s: mult *= 10000; s = s.replace('만', '')
    if '천' in s: mult *= 1000; s = s.replace('천', '')
    nums = re.findall(r'\d+\.?\d*', s)
    return int(float(nums[0]) * mult) if nums else 0

def is_same_channel(a_name, a_handle, b_name, b_handle):
    a_h, b_h = str(a_handle or "").strip(), str(b_handle or "").strip()
    if a_h and b_h and a_h == b_h: return True
    return SequenceMatcher(None, str(a_name), str(b_name)).ratio() > 0.75

if uploaded_files and api_key:
    if st.button("🚀 분석 시작 (완료 후 리스트 자동삭제)"):
        new_raw_data = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            try:
                base64_image = base64.b64encode(file.read()).decode('utf-8')
                prompt = "이미지에서 channel_name, handle(@주소), subscriber_count, email, category, join_date, total_views, video_count를 JSON으로 추출해."
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    "response_format": { "type": "json_object" }
                }
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                new_raw_data.append(json.loads(response.json()['choices'][0]['message']['content']))
            except: continue
            progress_bar.progress((i + 1) / len(uploaded_files))

        # 데이터 병합
        for new_item in new_raw_data:
            new_h = str(new_item.get('handle') or '').strip()
            if new_h and not new_h.startswith('@'): new_item['handle'] = '@' + new_h
            
            found = False
            for existing_item in st.session_state['analysis_history']:
                if is_same_channel(new_item.get('channel_name'), new_item.get('handle'), 
                                   existing_item.get('channel_name'), existing_item.get('handle')):
                    for k, v in new_item.items():
                        if v and not existing_item.get(k): existing_item[k] = v
                    found = True
                    break
            if not found: st.session_state['analysis_history'].append(new_item)
        
        # 핵심: 분석 완료 후 업로더 키를 변경해서 리스트를 비움
        st.session_state['uploader_key'] += 1
        st.rerun() 

# 결과 출력 (V4.4와 동일)
if st.session_state['analysis_history']:
    final_list = []
    for data in st.session_state['analysis_history']:
        total_v = parse_korean_num(data.get('total_views', 0))
        video_c = parse_korean_num(data.get('video_count', 0))
        sub_c = parse_korean_num(data.get('subscriber_count', 0))
        avg_per_video = int(total_v / video_c) if video_c > 0 else 0
        h_raw = str(data.get('handle') or data.get('channel_name', '')).split(' ')[0]
        if not h_raw.startswith('@'): h_raw = f"@{h_raw}"
        
        final_list.append({
            "채널명": data.get('channel_name'),
            "유튜브 주소": f"https://www.youtube.com/{h_raw}",
            "구독자 수": sub_c,
            "영상 총 개수": video_c,
            "영상 1개당 평균 조회수": avg_per_video,
            "전체 조회수": total_v,
            "카테고리": data.get('category'),
            "이메일": data.get('email'),
            "채널 가입일": data.get('join_date')
        })

    df = pd.DataFrame(final_list)
    df_display = df.copy()
    for col in ["구독자 수", "영상 총 개수", "영상 1개당 평균 조회수", "전체 조회수"]:
        df_display[col] = df_display[col].apply(lambda x: f"{x:,}")
    
    st.dataframe(df_display.astype(str))
    
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='YouTube_History')
        workbook, worksheet = writer.book, writer.sheets['YouTube_History']
        num_format = workbook.add_format({'num_format': '#,##0'})
        worksheet.set_column('C:F', 18, num_format)
    
    st.download_button("📥 통합 엑셀 다운로드", out.getvalue(), "youtube_master.xlsx")
