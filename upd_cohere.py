import py_compile

p = "aios_core/llm_balancer.py"
s = open(p, encoding="utf-8").read()

old = '''            "models": [
                "command-r",
                "command-r-plus",
                "command-r7b-12-2024",
            ],'''
new = '''            "models": [
                "command-a-03-2025",
                "command-r-08-2024",
                "command-r7b-12-2024",
            ],'''
assert old in s, "cohere models not found"
s = s.replace(old, new, 1)

# Add Cohere v2 response parsing: content may be a list of {type:text, text}
old_parse = '''                    if "choices" in data and data["choices"]:
                        return data["choices"][0]["message"]["content"]
                    elif "data" in data and isinstance(data["data"], dict) and "choices" in data["data"]:
                        return data["data"]["choices"][0]["message"]["content"]
                    elif "result" in data:
                        return str(data["result"])'''
new_parse = '''                    if "choices" in data and data["choices"]:
                        _c = data["choices"][0]["message"]["content"]
                        return _c if isinstance(_c, str) else ""
                    elif "data" in data and isinstance(data["data"], dict) and "choices" in data["data"]:
                        return data["data"]["choices"][0]["message"]["content"]
                    elif "message" in data and isinstance(data.get("message"), dict):
                        _mc = data["message"].get("content")
                        if isinstance(_mc, list):
                            return "".join(x.get("text", "") for x in _mc if isinstance(x, dict))
                        return str(_mc or "")
                    elif "result" in data:
                        return str(data["result"])'''
assert old_parse in s, "response parse block not found"
s = s.replace(old_parse, new_parse, 1)

open(p, "w", encoding="utf-8").write(s)
py_compile.compile(p, doraise=True)
print("cohere models + v2 parsing patched OK")
