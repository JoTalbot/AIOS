import sqlite3, glob

for p in glob.glob("/root/AIOS/data/chrome_twin/default/**/Cookies", recursive=True):
    try:
        conn = sqlite3.connect(p)
        cur = conn.execute(
            "SELECT host_key FROM cookies "
            "WHERE host_key LIKE '%privat24%' OR host_key LIKE '%abank%' OR host_key LIKE '%a-bank%'")
        hosts = sorted(set(r[0] for r in cur.fetchall()))
        print(p)
        print("  банк-cookies:", hosts[:15] if hosts else "НЕТ")
        conn.close()
    except Exception as e:
        print("err", p, str(e)[:80])
