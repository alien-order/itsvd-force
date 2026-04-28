"""
테스트 VOC 데이터 삭제 스크립트
voc_number가 'TEST'로 시작하는 데이터를 삭제합니다.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'voc.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.execute("DELETE FROM vocs WHERE voc_number LIKE 'TEST%'")
conn.commit()
print(f'Deleted: {cur.rowcount}')
conn.close()
