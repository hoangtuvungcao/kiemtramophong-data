#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Video downloader for kiemtramophong.com simulation videos.
Features:
- Rate limit aware (monitors X-RateLimit-Remaining to avoid HTTP 429)
- Resumable: skips already downloaded videos
- Automatic heartbeat to keep session alive
- Supports downloading all, by chapter, or by situation range
"""

import os
import sys
import time
import argparse
import json
import requests

COOKIES = {
    'kiem_tra_mo_phong_session': 'eyJpdiI6ImM2ZmZnWGxEVFJib3JXVXhCeEU5UGc9PSIsInZhbHVlIjoiZ3dwTHZ4K2dXYjRkcS9SOERUYkR1Q013T0Q0WkZMclZGeDVvNDZISHpKZDByV0hmM29QbEJ2YzZwWDVqR0Z4aTNYTUV6M3R6Mkd2aHkxOGxXWS95dGllRk4xSzhNTEdnZFFnUEU4TEpxQU9KWkY5Wlg4YnhxL2hnVTFSQUF3T1EiLCJtYWMiOiJjMWI1OWMwNjY0ZTRmNDk0ZjNhOTBiMWU2YjkxNmYzNThlYjkyMjViODc5ZmNlMjU4NDc5ZDQ5ZWE4ZWM1ZmRlIiwidGFnIjoiIn0=',
    'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d': 'eyJpdiI6InRWNWFGMVVoWW9jOW9lSzBHVXN3MkE9PSIsInZhbHVlIjoiOGFrNTErWnkwemNwZDNJd0FmSUdnNHNQdzFlbWJqbGpwY3kvWXZlL21XNHZWZ2FkZHkwTUUyYlNmTHA2SVBGRThJZ0ZQbzJlVW9BMmZmS1ZvOVUxSk5Nb3k5NmVFaitWSmVFZnpCdWVkRHk4VUtkRUJFQ2JQYVdrRnRud1hlaW1JR3FjQUgxdVRITmVUeHBFOS91SXdyZ3BlMHNqQWlpY0VoUllUYXZINXY3RzhZNUpTakZHa2w3K0VYR1NYZ2NpRHRmM29ZLzl6K3ZyZ08zV1JzVjNQTVhqUnJpaStaeXY5ZzR6WWhFSzcwcz0iLCJtYWMiOiI1YmRiNjc3ZjJmNzFiZDE0NDYyZWNjZWU5YzgxNDJjMzIwOWE4M2M0MzAwOGE1YzcxNjM0Yjk3ZTI1ODE4ODE1IiwidGFnIjoiIn0='
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0',
    'Accept': 'application/json'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def send_heartbeat():
    try:
        url = 'https://kiemtramophong.com/online/heartbeat'
        headers = dict(HEADERS)
        headers['Content-Type'] = 'application/json'
        requests.post(url, headers=headers, cookies=COOKIES, json={'url': 'https://kiemtramophong.com/simulation/practice'}, timeout=5)
    except Exception:
        pass

def download_single_video(stt, target_file):
    if os.path.exists(target_file) and os.path.getsize(target_file) > 1024 * 500:
        print(f" [Bỏ qua] Tình huống {stt:03d}: File video đã tồn tại ({os.path.getsize(target_file) / 1024 / 1024:.2f} MB)")
        return True
        
    api_url = f"https://kiemtramophong.com/simulation/videos/{stt}/play-url"
    
    # 1. Fetch play url
    for retry in range(3):
        try:
            r = requests.get(api_url, headers=HEADERS, cookies=COOKIES, timeout=10)
            remaining = r.headers.get('X-RateLimit-Remaining')
            
            if r.status_code == 429:
                print(f"  [RateLimit] Bị giới hạn tần suất (429), chờ 30 giây...")
                time.sleep(30)
                continue
                
            r.raise_for_status()
            data = r.json()
            stream_url = data.get('url')
            if not stream_url:
                print(f"  [Lỗi] Không tìm thấy URL stream trong response của TH {stt}")
                return False
                
            # If remaining rate limit is low, sleep a bit
            if remaining and int(remaining) < 5:
                print(f"  [RateLimit Warning] Còn {remaining} lượt gọi API trong phút này. Chờ 5s...")
                time.sleep(5)
                
            break
        except Exception as e:
            if retry == 2:
                print(f"  [Lỗi gọi play-url TH {stt}]: {e}")
                return False
            time.sleep(2)

    # 2. Download video stream
    tmp_file = target_file + ".tmp"
    t0 = time.time()
    try:
        with requests.get(stream_url, headers=HEADERS, cookies=COOKIES, stream=True, timeout=30) as r_stream:
            r_stream.raise_for_status()
            total_size = int(r_stream.headers.get('content-length', 0))
            downloaded = 0
            with open(tmp_file, 'wb') as f:
                for chunk in r_stream.iter_content(chunk_size=512 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
        if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 1024 * 100:
            os.rename(tmp_file, target_file)
            dur = time.time() - t0
            sz_mb = os.path.getsize(target_file) / 1024 / 1024
            speed = sz_mb / dur if dur > 0 else 0
            print(f" [Tải xong] TH {stt:03d} -> {os.path.basename(os.path.dirname(target_file))}/video.mp4 ({sz_mb:.2f} MB, {dur:.1f}s, {speed:.2f} MB/s)")
            return True
        else:
            print(f"  [Lỗi] File tải về quá nhỏ hoặc không hợp lệ cho TH {stt}")
            if os.path.exists(tmp_file): os.remove(tmp_file)
            return False
    except Exception as e:
        print(f"  [Lỗi tải stream TH {stt}]: {e}")
        if os.path.exists(tmp_file): os.remove(tmp_file)
        return False

def find_target_folder(stt):
    for root, dirs, files in os.walk(BASE_DIR):
        for d in dirs:
            if d.startswith(f"TH{stt:03d}_"):
                return os.path.join(root, d)
    return None

def main():
    parser = argparse.ArgumentParser(description="Tải video mô phỏng giao thông từ kiemtramophong.com")
    parser.add_argument('--all', action='store_true', help="Tải toàn bộ 120 video")
    parser.add_argument('--chapter', type=int, choices=[1, 2, 3, 4, 5, 6], help="Tải theo số chương (1-6)")
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), help="Tải trong khoảng STT (vd: --range 1 10)")
    parser.add_argument('--stt', type=int, help="Tải 1 tình huống theo STT cụ thể (1-120)")
    parser.add_argument('--delay', type=float, default=1.0, help="Thời gian chờ giữa các video để tránh rate limit (mặc định: 1.0 giây)")
    
    args = parser.parse_args()
    
    # Check options
    stt_list = []
    if args.stt:
        stt_list = [args.stt]
    elif args.range:
        stt_list = list(range(args.range[0], args.range[1] + 1))
    elif args.chapter:
        chapter_ranges = {
            1: (1, 29),
            2: (30, 43),
            3: (44, 63),
            4: (64, 73),
            5: (74, 90),
            6: (91, 120)
        }
        r = chapter_ranges[args.chapter]
        stt_list = list(range(r[0], r[1] + 1))
    elif args.all:
        stt_list = list(range(1, 121))
    else:
        print("Vui lòng chọn tùy chọn tải:")
        print("  python3 download_videos.py --range 1 5      (Tải từ tình huống 1 đến 5)")
        print("  python3 download_videos.py --chapter 1      (Tải toàn bộ chương 1)")
        print("  python3 download_videos.py --stt 10         (Tải tình huống 10)")
        print("  python3 download_videos.py --all            (Tải tất cả 120 tình huống)")
        sys.exit(0)
        
    print(f"=== Bắt đầu tải video cho {len(stt_list)} tình huống ===")
    success_count = 0
    
    for i, stt in enumerate(stt_list):
        folder = find_target_folder(stt)
        if not folder:
            print(f"[Cảnh báo] Không tìm thấy thư mục của TH {stt:03d}")
            continue
            
        target_video = os.path.join(folder, 'video.mp4')
        if download_single_video(stt, target_video):
            success_count += 1
            
        # Keep alive heartbeat every 5 videos
        if (i + 1) % 5 == 0:
            send_heartbeat()
            
        if i < len(stt_list) - 1 and args.delay > 0:
            time.sleep(args.delay)
            
    print(f"\n=== Hoàn tất: Đã tải thành công {success_count}/{len(stt_list)} video ===")

if __name__ == '__main__':
    main()
