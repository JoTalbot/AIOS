import sys
import xml.etree.ElementTree as ET

t = open(sys.argv[1]).read()
root = ET.fromstring(t)

def walk(n, depth=0):
    txt = n.get('text', '').strip()
    rid = n.get('resource-id', '').strip()
    cl = n.get('class', '').split('.')[-1]
    click = n.get('clickable', 'false')
    b = n.get('bounds', '')
    desc = n.get('content-desc', '').strip()
    focusable = n.get('focusable', 'false')
    if txt or click == 'true' or rid or desc:
        indent = '  ' * depth
        print(f"{indent}{cl} | text='{txt}' | desc='{desc}' | id={rid} | click={click} | {b}")
        depth += 1
    for c in n:
        walk(c, depth)

walk(root)
