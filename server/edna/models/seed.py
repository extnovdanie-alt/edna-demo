"""Validated public equipment catalogue; no user records or secrets."""
import json,hashlib
from collections import Counter

def parse(content):
    from inventory import ALLOWED
    raw=json.loads(content);items=raw.get('items');assert isinstance(items,list) and 0<len(items)<=10000
    records=[];seen=set()
    for item in items:
        assert item['category'] in ALLOWED and isinstance(item['model'],str) and 0<len(item['model'])<=150
        serial=item.get('serial');assert serial or item['category'] in ('mouse','teclado')
        key='serial:'+serial.casefold() if serial else 'id:'+item['external_id']
        assert key not in seen;seen.add(key)
        assert item['state'] in ('available','blocked')
        records.append(dict(key=key,serial=serial,category=item['category'],model=item['model'],sheet='Catálogo inicial',row=0,status=item['source_status'],location=item.get('location',''),state=item['state']))
    return records,dict(source='Catálogo inicial de equipamentos',rows_read=len(records),items=len(records),available=sum(r['state']=='available' for r in records),categories=dict(Counter(r['category'] for r in records)),issues=raw.get('issues',[]),duplicates=0,sheets=[],excluded_sheets=[])
