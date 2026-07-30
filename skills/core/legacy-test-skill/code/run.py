from aios_core.security import constitution_enforced

import json

@constitution_enforced
def run(params):
    print('Выполнение старого legacy-скилла без защиты...')
    return {'status': 'success', 'data': 'Legacy output'}