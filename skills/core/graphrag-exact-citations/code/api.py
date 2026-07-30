#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json, sqlite3, time, os, re, secrets
from datetime import datetime, timezone
DB='/var/lib/octopus/graphrag.db'
TRACE_RE=re.compile(r'^octo-[0-9]{8}T[0-9]{6}Z-[a-z0-9_-]{1,32}-[0-9a-f]{8}$')

def trace_id(value=None, stream='graphrag'):
    if value and TRACE_RE.fullmatch(value): return value
    now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'octo-{now}-{stream}-{secrets.token_hex(4)}'

def q_fts(text):
    import re
    terms=re.findall(r'[\w]+', (text or 'octopus').lower())
    return ' '.join(terms) or 'octopus'

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
class H(BaseHTTPRequestHandler):
    def sendj(self, obj, code=200):
        b=json.dumps(obj, ensure_ascii=False, indent=2).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
    def do_GET(self):
        u=urlparse(self.path); p=u.path; qs=parse_qs(u.query)
        try:
            c=db()
            if p in ('/health','/healthz'):
                return self.sendj({'status':'ok','service':'octopus-graphrag-api','ts':int(time.time())})
            if p=='/stats':
                docs=c.execute('select count(*) from docs').fetchone()[0]; edges=c.execute('select count(*) from edges').fetchone()[0]
                rel=[dict(x) for x in c.execute('select rel,count(*) count from edges group by rel order by count desc')]
                return self.sendj({'docs':docs,'edges':edges,'relations':rel})
            if p=='/metrics':
                docs=c.execute('select count(*) from docs').fetchone()[0]; edges=c.execute('select count(*) from edges').fetchone()[0]
                body=(f"# HELP octopus_graphrag_docs Indexed GraphRAG documents\n# TYPE octopus_graphrag_docs gauge\noctopus_graphrag_docs {docs}\n"
                      f"# HELP octopus_graphrag_edges Extracted GraphRAG edges\n# TYPE octopus_graphrag_edges gauge\noctopus_graphrag_edges {edges}\n").encode()
                self.send_response(200); self.send_header('Content-Type','text/plain; version=0.0.4'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
            if p=='/search':
                term=qs.get('q',['octopus'])[0][:500]; limit=max(1,min(int(qs.get('limit',['10'])[0]),50)); fq=q_fts(term)
                tid=trace_id(qs.get('trace_id',[None])[0])
                sql='''select docs_fts.path,docs_fts.title,docs_fts.kind,
                              bm25(docs_fts) rank,docs.sha256 source_sha256,
                              docs.mtime source_mtime,docs.size source_size,
                              snippet(docs_fts,2,'<mark>','</mark>',' … ',18) excerpt
                       from docs_fts left join docs on docs.path=docs_fts.path
                       where docs_fts match ? order by rank limit ?'''
                rows=[]
                for x in c.execute(sql,(fq,limit)):
                    row=dict(x)
                    row['citation']={
                        'source_path':row['path'],
                        'source_sha256':row.get('source_sha256'),
                        'source_mtime':row.get('source_mtime'),
                        'source_size':row.get('source_size'),
                        'excerpt':row.get('excerpt'),
                    }
                    rows.append(row)
                return self.sendj({'query':term,'trace_id':tid,'citation_contract':'exact_source_path+indexed_sha256','results':rows})
            if p=='/edges':
                term=qs.get('q',['octopus'])[0]; limit=min(int(qs.get('limit',['20'])[0]),100); like=f'%{term}%'
                rows=[dict(x) for x in c.execute('select src,rel,dst,doc_path from edges where src like ? or rel like ? or dst like ? limit ?', (like,like,like,limit))]
                return self.sendj({'query':term,'edges':rows})
            return self.sendj({'error':'not found','paths':['/health','/stats','/search?q=...','/edges?q=...']},404)
        except Exception as e:
            return self.sendj({'error':str(e)},500)
if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1', 9760), H).serve_forever()
