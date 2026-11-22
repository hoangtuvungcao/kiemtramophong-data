#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to extract and organize all 120 simulation questions, answers, and metadata
from kiemtramophong.com into a structured folder hierarchy.
"""

import os
import sys
import re
import json
import csv
import unicodedata
import requests

COOKIES = {
    'kiem_tra_mo_phong_session': 'eyJpdiI6ImM2ZmZnWGxEVFJib3JXVXhCeEU5UGc9PSIsInZhbHVlIjoiZ3dwTHZ4K2dXYjRkcS9SOERUYkR1Q013T0Q0WkZMclZGeDVvNDZISHpKZDByV0hmM29QbEJ2YzZwWDVqR0Z4aTNYTUV6M3R6Mkd2aHkxOGxXWS95dGllRk4xSzhNTEdnZFFnUEU4TEpxQU9KWkY5Wlg4YnhxL2hnVTFSQUF3T1EiLCJtYWMiOiJjMWI1OWMwNjY0ZTRmNDk0ZjNhOTBiMWU2YjkxNmYzNThlYjkyMjViODc5ZmNlMjU4NDc5ZDQ5ZWE4ZWM1ZmRlIiwidGFnIjoiIn0=',
    'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d': 'eyJpdiI6InRWNWFGMVVoWW9jOW9lSzBHVXN3MkE9PSIsInZhbHVlIjoiOGFrNTErWnkwemNwZDNJd0FmSUdnNHNQdzFlbWJqbGpwY3kvWXZlL21XNHZWZ2FkZHkwTUUyYlNmTHA2SVBGRThJZ0ZQbzJlVW9BMmZmS1ZvOVUxSk5Nb3k5NmVFaitWSmVFZnpCdWVkRHk4VUtkRUJFQ2JQYVdrRnRud1hlaW1JR3FjQUgxdVRITmVUeHBFOS91SXdyZ3BlMHNqQWlpY0VoUllUYXZINXY3RzhZNUpTakZHa2w3K0VYR1NYZ2NpRHRmM29ZLzl6K3ZyZ08zV1JzVjNQTVhqUnJpaStaeXY5ZzR6WWhFSzcwcz0iLCJtYWMiOiI1YmRiNjc3ZjJmNzFiZDE0NDYyZWNjZWU5YzgxNDJjMzIwOWE4M2M0MzAwOGE1YzcxNjM0Yjk3ZTI1ODE4ODE1IiwidGFnIjoiIn0='
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def sanitize_name(text):
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '_', text)
    return text

CHAPTER_FOLDER_MAP = {
    'Chương I - Giao thông trong đô thị, khu đông dân cư': 'Chuong_01_Do_thi_va_khu_dong_dan_cu',
    'Chương II - Giao thông trên đường nông thôn': 'Chuong_02_Duong_nong_thon',
    'Chương III - Giao thông trên đường cao tốc': 'Chuong_03_Duong_cao_toc',
    'Chương IV - Giao thông trên đường núi': 'Chuong_04_Duong_nui',
    'Chương V - Giao thông trên đường quốc lộ': 'Chuong_05_Duong_quoc_lo',
    'Chương VI - Tình huống tai nạn giao thông thực tế': 'Chuong_06_Tai_nan_giao_thong_thuc_te'
}

def fetch_customer_answers():
    print("[1/3] Đang tải danh sách tình huống từ customer-answers...")
    url = 'https://kiemtramophong.com/admin/simulation/customer-answers'
    r = requests.get(url, headers=HEADERS, cookies=COOKIES)
    r.raise_for_status()
    
    rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', r.text, re.DOTALL)
    ca_dict = {}
    for row in rows[1:]:
        cols = re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        if len(cols) >= 5:
            stt = int(' '.join(re.sub(r'<[^>]+>', ' ', cols[0]).split()))
            title = ' '.join(re.sub(r'<[^>]+>', ' ', cols[1]).split())
            chapter = ' '.join(re.sub(r'<[^>]+>', ' ', cols[2]).split())
            status = ' '.join(re.sub(r'<[^>]+>', ' ', cols[3]).split())
            edit_link = re.search(r'href=[\"\']([^\"\']+)[\"\']', cols[4])
            ca_dict[stt] = {
                'stt': stt,
                'title': title,
                'chapter': chapter,
                'status': status,
                'edit_url': edit_link.group(1) if edit_link else None
            }
    print(f" -> Lấy thành công thông tin {len(ca_dict)} tình huống.")
    return ca_dict

def fetch_practice_details(ca_dict):
    print("[2/3] Đang tải dữ liệu câu hỏi và đáp án từ trang ôn tập...")
    url = 'https://kiemtramophong.com/simulation/practice'
    r = requests.get(url, headers=HEADERS, cookies=COOKIES)
    r.raise_for_status()
    
    divs = re.findall(r'<div class=\"practice-detail[^\"]*\" data-clip-id=\"(\d+)\">(.*?)(?=<div class=\"practice-detail|$)', r.text, re.DOTALL)
    all_situations = []
    
    for clip_id_str, chunk in divs:
        clip_id = int(clip_id_str)
        stt_m = re.search(r'Tình huống (\d+)', chunk)
        stt = int(stt_m.group(1)) if stt_m else clip_id - 1
        
        video_m = re.search(r'data-play-url=\"([^\"]+)\"', chunk)
        play_url_api = video_m.group(1) if video_m else f'https://kiemtramophong.com/simulation/videos/{stt}/play-url'
        
        meta = ca_dict.get(stt, {})
        title = meta.get('title', f'Tình huống {stt}')
        chapter = meta.get('chapter', 'Chưa phân loại')
        
        # Clean section suffix if last item
        if '</section>' in chunk:
            chunk = chunk[:chunk.find('</section>')]
            
        cards = chunk.split('practice-question-card')
        questions = []
        for c_idx, card in enumerate(cards[1:]):
            h6 = re.search(r'<h6[^>]*>(.*?)</h6>', card, re.DOTALL)
            q_name = ' '.join(re.sub(r'<[^>]+>', ' ', h6.group(1)).split()) if h6 else f'Câu {c_idx+1}'
            
            options = []
            opt_matches = re.findall(r'data-correct=\"(\d+)\".*?<span class=\"practice-answer-text\">(.*?)</span>', card, re.DOTALL)
            for corr, text_ans in opt_matches:
                clean_ans = text_ans.strip()
                options.append({
                    'text': clean_ans,
                    'is_correct': (corr == '1')
                })
            
            if not options:
                continue
                
            correct_ans = next((o['text'] for o in options if o['is_correct']), None)
            wrong_ans = [o['text'] for o in options if not o['is_correct']]
            
            questions.append({
                'question_index': len(questions) + 1,
                'question_name': q_name,
                'correct_answer': correct_ans,
                'wrong_answers': wrong_ans,
                'all_options': options
            })
            
        all_situations.append({
            'stt': stt,
            'clip_id': clip_id,
            'title': title,
            'chapter': chapter,
            'play_url_api': play_url_api,
            'edit_url': meta.get('edit_url'),
            'questions': questions
        })
        
    all_situations.sort(key=lambda x: x['stt'])
    print(f" -> Thu thập đầy đủ dữ liệu {len(all_situations)} tình huống.")
    return all_situations

def generate_markdown(item):
    md = []
    md.append(f"# Tình Huống {item['stt']:03d}: {item['title']}\n")
    md.append(f"- **Chương:** {item['chapter']}")
    md.append(f"- **STT:** {item['stt']}")
    md.append(f"- **Clip ID:** {item['clip_id']}")
    md.append(f"- **API Play URL:** `{item['play_url_api']}`")
    if item.get('edit_url'):
        md.append(f"- **Trang cấu hình admin:** [{item['edit_url']}]({item['edit_url']})")
    md.append(f"- **File video cục bộ:** `video.mp4`\n")
    md.append("---\n")
    md.append("## Danh Sách Câu Hỏi & Đáp Án\n")
    
    for q in item['questions']:
        md.append(f"### {q['question_name']}")
        for opt in q['all_options']:
            if opt['is_correct']:
                md.append(f"- [x] **{opt['text']}**  *(ĐÁP ÁN ĐÚNG)*")
            else:
                md.append(f"- [ ] {opt['text']}")
        md.append("")
        
    return "\n".join(md)

def save_structured_data(situations):
    print("[3/3] Đang lưu cấu trúc thư mục, JSON, CSV và Markdown...")
    
    # 1. Master JSON
    all_json_path = os.path.join(BASE_DIR, 'tat_ca_cau_hoi.json')
    with open(all_json_path, 'w', encoding='utf-8') as f:
        json.dump(situations, f, ensure_ascii=False, indent=2)
    print(f" -> Đã lưu file tổng hợp JSON: {all_json_path}")
    
    # 2. Master CSV
    all_csv_path = os.path.join(BASE_DIR, 'tat_ca_cau_hoi.csv')
    with open(all_csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'STT', 'Chương', 'Tên tình huống', 'API Play URL',
            'Câu 1 - Tiêu đề', 'Câu 1 - Đáp án đúng', 'Câu 1 - Đáp án sai',
            'Câu 2 - Tiêu đề', 'Câu 2 - Đáp án đúng', 'Câu 2 - Đáp án sai',
            'Câu 3 - Tiêu đề', 'Câu 3 - Đáp án đúng', 'Câu 3 - Đáp án sai',
            'Câu 4 - Tiêu đề', 'Câu 4 - Đáp án đúng', 'Câu 4 - Đáp án sai'
        ])
        for s in situations:
            row = [s['stt'], s['chapter'], s['title'], s['play_url_api']]
            for q_idx in range(4):
                if q_idx < len(s['questions']):
                    q = s['questions'][q_idx]
                    row.extend([
                        q['question_name'],
                        q['correct_answer'] or '',
                        ' | '.join(q['wrong_answers'])
                    ])
                else:
                    row.extend(['', '', ''])
            writer.writerow(row)
    print(f" -> Đã lưu file tổng hợp CSV: {all_csv_path}")
    
    # 3. Structure folders per chapter and per situation
    for s in situations:
        ch_folder_name = CHAPTER_FOLDER_MAP.get(s['chapter'])
        if not ch_folder_name:
            ch_folder_name = sanitize_name(s['chapter'])
            
        sit_folder_name = f"TH{s['stt']:03d}_{sanitize_name(s['title'])}"
        target_dir = os.path.join(BASE_DIR, ch_folder_name, sit_folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Save info.json
        with open(os.path.join(target_dir, 'info.json'), 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
            
        # Save cau_hoi_va_dap_an.md
        with open(os.path.join(target_dir, 'cau_hoi_va_dap_an.md'), 'w', encoding='utf-8') as f:
            f.write(generate_markdown(s))
            
    print(f" -> Đã tạo cấu trúc thư mục thành công cho toàn bộ {len(situations)} tình huống!")

def main():
    try:
        ca_dict = fetch_customer_answers()
        situations = fetch_practice_details(ca_dict)
        save_structured_data(situations)
        print("\n Hoàn tất xuất toàn bộ 120 câu hỏi và đáp án vào các folder có cấu trúc!")
    except Exception as e:
        print(f"\n[LỖI] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
