from aios_core.security import constitution_enforced

@constitution_enforced
def run(params):
    return {'status': 'healed'}
