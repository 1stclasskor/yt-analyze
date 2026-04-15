# ... (상단 생략, 병합 로직 부분만 집중 수정)

        # 유사도 기반 병합 (더 똑똑하게)
        def is_same_channel(a_name, a_handle, b_name, b_handle):
            # 1. 핸들이 존재하고 80% 이상 유사하면 동일 채널 (영문 아이디는 정확도가 높음)
            if a_handle and b_handle:
                if SequenceMatcher(None, str(a_handle), str(b_handle)).ratio() > 0.8:
                    return True
            
            # 2. 채널명 유사도 (받침 오타 고려하여 75%로 완화)
            name_sim = SequenceMatcher(None, str(a_name), str(b_name)).ratio()
            if name_sim > 0.75:
                return True
            
            return False

        for new_item in new_raw_data:
            # AI가 가끔 핸들에 @를 빼먹으므로 강제로 보정
            raw_h = str(new_item.get('handle') or '').strip()
            if raw_h and not raw_h.startswith('@'):
                new_item['handle'] = '@' + raw_h
            
            new_name = new_item.get('channel_name')
            new_handle = new_item.get('handle')
            
            found = False
            for existing_item in st.session_state['analysis_history']:
                if is_same_channel(new_name, new_handle, existing_item.get('channel_name'), existing_item.get('handle')):
                    # 동일 채널이면 데이터 보완 (더 긴 이름이나 정보가 있는 쪽 선택)
                    if len(str(new_name)) > len(str(existing_item.get('channel_name'))):
                        existing_item['channel_name'] = new_name
                    for k, v in new_item.items():
                        if v and not existing_item.get(k):
                            existing_item[k] = v
                    found = True
                    break
            if not found:
                st.session_state['analysis_history'].append(new_item)

# ... (하단 URL 생성부)
        # 유튜브 주소 생성 시 한글/특수문자 포함 핸들 정제
        h_raw = str(data.get('handle') or data.get('channel_name', ''))
        # @로 시작하는 핸들만 추출하거나 정제
        clean_handle = h_raw.split(' ')[0] # 공백 뒤 쓰레기 값 제거
        if not clean_handle.startswith('@'):
            clean_handle = f"@{clean_handle}"
            
        final_list.append({
            "채널명": data.get('channel_name'),
            "유튜브 주소": f"https://www.youtube.com/{clean_handle}",
            # ... (나머지 동일)
