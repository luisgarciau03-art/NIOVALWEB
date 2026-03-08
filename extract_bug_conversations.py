"""
Script para extraer conversaciones completas de bugs detectados
"""
import re
import glob

BRUCES_TO_ANALYZE = {
    'BRUCE2075': 'BRUCE_MUDO (CRITICO)',
    'BRUCE2076': 'GPT_LOGICA_ROTA',
    'BRUCE2078': 'Multiple bugs',
    'BRUCE2079': 'GPT_LOGICA_ROTA',
    'BRUCE2080': 'CLIENTE_HABLA_ULTIMO',
    'BRUCE2081': 'GPT_LOGICA_ROTA',
    'BRUCE2086': 'GPT_FUERA_DE_TEMA',
    'BRUCE2087': 'GPT_LOGICA_ROTA',
    'BRUCE2091': 'GPT_LOGICA_ROTA'
}

def extract_conversation(bruce_id, log_content):
    """Extrae la conversación completa de un BRUCE ID"""

    # Buscar sección del BRUCE
    pattern = rf'ID BRUCE generado: {bruce_id}(.*?)(?=ID BRUCE generado:|$)'
    match = re.search(pattern, log_content, re.DOTALL)

    if not match:
        return None

    section = match.group(1)

    # Extraer turnos de conversación
    cliente_pattern = r'\[20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[CLIENTE\] ' + bruce_id + r' - CLIENTE DIJO: "([^"]*)"'
    bruce_pattern = r'\[20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[BRUCE\] ' + bruce_id + r' DICE: "([^"]*)"'

    cliente_turns = [(m.group(1), 'cliente') for m in re.finditer(cliente_pattern, section)]
    bruce_turns = [(m.group(1), 'bruce') for m in re.finditer(bruce_pattern, section)]

    # Combinar y ordenar por posición en el texto
    all_turns = []
    for text, role in cliente_turns:
        pos = section.find(f'CLIENTE DIJO: "{text}"')
        if pos != -1:
            all_turns.append((pos, role, text))

    for text, role in bruce_turns:
        pos = section.find(f'BRUCE DICE: "{text}"')
        if pos != -1:
            all_turns.append((pos, role, text))

    all_turns.sort(key=lambda x: x[0])

    # Extraer bugs detectados
    bug_pattern = rf'\[BUG_DETECTOR\] {bruce_id}:(.*?)(?=\n\n|\[\w+\]|$)'
    bug_match = re.search(bug_pattern, section, re.DOTALL)
    bugs = bug_match.group(1).strip() if bug_match else "No bugs detected in logs"

    return {
        'turns': [(role, text) for _, role, text in all_turns],
        'bugs': bugs
    }

def main():
    log_files = glob.glob('LOGS/11_02PT*.txt')

    for bruce_id, bug_type in BRUCES_TO_ANALYZE.items():
        print(f"\n{'='*80}")
        print(f"{bruce_id} - {bug_type}")
        print('='*80)

        found = False
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                result = extract_conversation(bruce_id, content)

                if result:
                    found = True
                    print(f"\nConversación ({len(result['turns'])} turnos):")
                    for i, (role, text) in enumerate(result['turns'][:20], 1):
                        speaker = "Cliente" if role == 'cliente' else "Bruce"
                        text_preview = text[:150] + ('...' if len(text) > 150 else '')
                        print(f"{i}. {speaker}: {text_preview}")

                    if len(result['turns']) > 20:
                        print(f"... ({len(result['turns']) - 20} turnos más)")

                    print(f"\nBugs detectados:")
                    print(result['bugs'][:500])
                    break
            except Exception as e:
                print(f"Error reading {log_file}: {e}")
                continue

        if not found:
            print(f"No se encontró información para {bruce_id}")

if __name__ == '__main__':
    main()
