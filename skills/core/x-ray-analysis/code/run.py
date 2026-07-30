from aios_core.security import constitution_enforced

@constitution_enforced
def run(context):
    print("Выполнение загруженного навыка Radiology-Scan!")
    return {"status": "analyzed"}
