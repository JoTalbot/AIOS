from aios_core.security import constitution_enforced

@constitution_enforced
def run(context):
    print("Выполняю автономный навык: google-calendar-sync")
    return {"status": "ok"}
