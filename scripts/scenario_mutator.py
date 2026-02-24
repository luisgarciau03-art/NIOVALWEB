"""
Scenario Mutator: Genera variaciones de conversaciones reales.

3 estrategias:
  A) Sustitución de sinónimos (variantes reales del cliente)
  B) Inyección de interrupciones (IVR, eco, off-topic)
  C) Combinación de flujos (turnos de diferentes conversaciones)

Uso:
  python scripts/scenario_mutator.py                  # 50 mutaciones
  python scripts/scenario_mutator.py --count 100      # 100 mutaciones
  python scripts/scenario_mutator.py --strategy syn   # Solo sinónimos
"""

import os
import re
import json
import random
import argparse
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'tests', 'test_data')


# ============================================================
# POOLS DE SINÓNIMOS (extraídos de logs reales)
# ============================================================

SYNONYM_POOLS = {
    "saludo": [
        "Bueno", "Sí dígame", "Aló", "Quién habla", "Hola",
        "Mande", "Qué tal", "Sí bueno", "Diga", "A ver dígame",
        "Bueno dígame", "Quién es", "Hola buenas tardes",
        "Buenas tardes", "Sí qué pasó",
    ],
    "es_encargado": [
        "Sí, yo soy", "Servidor", "Yo mero", "Sí, diga",
        "Sí, soy el encargado", "Sí soy yo", "A sus órdenes",
        "Yo soy el dueño", "Sí, él habla", "Con él habla",
    ],
    "no_esta": [
        "No se encuentra", "Salió", "No viene hoy", "Fue a comer",
        "No está ahorita", "Ahorita no está", "No vino hoy",
        "Está ocupado", "Salió a una vuelta", "No se encuentra por el momento",
        "Ahorita no se encuentra", "No está en este momento",
    ],
    "acepta_whatsapp": [
        "Sí, mándalo", "Claro", "Al celular", "Sí, pasa el catálogo",
        "Sí, mándame la información", "Sale, mándalo", "Sí, a este número",
        "Está bien, mándelo", "Órale sí", "Va que sí",
    ],
    "rechazo": [
        "No gracias", "No me interesa", "No", "Nel",
        "No, estamos completos", "No necesitamos nada",
        "Gracias pero no", "No por el momento", "Ahorita no",
        "No, ya tenemos proveedor", "No trabajamos eso",
    ],
    "dicta_numero": [
        "seis seis dos tres cinco tres uno ocho cero cuatro",
        "66 23 53 18 04", "6623531804",
        "seis seis veintitrés cincuenta y tres dieciocho cero cuatro",
        "es el 662 353 1804", "anota 6621234567",
        "el whatsapp es 6623456789", "mi número es 6624567890",
    ],
    "pide_info": [
        "Qué marca es", "Qué es lo que venden", "Cuánto cuesta",
        "Qué tipo de productos manejan", "De dónde llaman",
        "Cómo se llama la empresa", "Qué es nioval",
        "Qué hacen ustedes", "Para qué sirven sus productos",
    ],
    "callback": [
        "Llame más tarde", "Marque mañana", "Hable después",
        "Ahorita no puedo", "Estoy ocupado", "Después me marca",
        "Llámeme en una hora", "Puede llamar a las 3",
    ],
    "acepta_correo": [
        "Sí, le doy un correo", "Es ferreteria arroba gmail punto com",
        "Mi correo es ventas arroba distribuidora punto com",
        "Mándelo a info arroba empresa punto com",
    ],
}

# Clasificación de turnos del cliente por función
TURN_CLASSIFIERS = [
    ("saludo", re.compile(
        r'^(bueno|s[ií]|hola|al[oó]|mande|diga|qu[eé] tal|buenas)',
        re.IGNORECASE)),
    ("es_encargado", re.compile(
        r'(yo soy|servidor|yo mero|s[ií].*(encargado|due[ñn]o)|[eé]l habla|con [eé]l)',
        re.IGNORECASE)),
    ("no_esta", re.compile(
        r'(no (se encuentra|est[aá]|vino)|sali[oó]|fue a|ocupado)',
        re.IGNORECASE)),
    ("acepta_whatsapp", re.compile(
        r'(m[aá]nd(alo|elo|ame)|cl(aro|aro que s[ií])|al celular|'
        r's[ií].*(cat[aá]logo|informaci[oó]n|whatsapp)|sale|[oó]rale|va que)',
        re.IGNORECASE)),
    ("rechazo", re.compile(
        r'(no (gracias|me interesa|necesitamos|trabajamos)|nel|'
        r'estamos completos|ya tenemos|ahorita no$)',
        re.IGNORECASE)),
    ("dicta_numero", re.compile(
        r'(\d{3,}|seis seis|nueve|ocho|siete|whatsapp es|mi n[uú]mero|anota)',
        re.IGNORECASE)),
    ("callback", re.compile(
        r'(llam[eé]? (m[aá]s tarde|ma[nñ]ana|despu[eé]s)|'
        r'marque|hable despu[eé]s|estoy ocupado|despu[eé]s me marca)',
        re.IGNORECASE)),
    ("pide_info", re.compile(
        r'(qu[eé] (marca|es lo que|tipo|hacen|venden)|'
        r'cu[aá]nto cuesta|de d[oó]nde|c[oó]mo se llama)',
        re.IGNORECASE)),
]


# ============================================================
# INYECCIONES (situaciones problemáticas reales)
# ============================================================

INJECTIONS = {
    "ivr": {
        "position": "start",
        "turns": [
            {"role": "client", "text": "Si conoce el número de extensión márquelo ahora, "
             "de lo contrario espere en la línea para ser atendido."},
        ],
    },
    "verificacion_conexion": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": "Bueno? Me escucha?"},
        ],
    },
    "pregunta_offtopic": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": "Oiga y ustedes de dónde son?"},
        ],
    },
    "eco_stt": {
        "position": "mid",
        "turns": [
            # Eco: repetir lo que Bruce dijo (STT captura audio de Bruce)
            {"role": "client", "text": "le llamo de la marca nioval somos distribuidores"},
        ],
    },
    "re_saludo": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": "Qué tal buen día"},
        ],
    },
    "espere_transferencia": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": "Espéreme tantito, se lo paso."},
            {"role": "client", "text": ""},  # Silencio durante transferencia
            {"role": "client", "text": "Bueno? Ya le paso al encargado."},
        ],
    },
    "cliente_enojado": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": "Ya no me marquen, ya les dije que no!"},
        ],
    },
    "ruido_fondo": {
        "position": "mid",
        "turns": [
            {"role": "client", "text": ""},  # STT detecta ruido como silencio
            {"role": "client", "text": "Mm"},
        ],
    },
}


def classify_turn(text):
    """Clasifica un turno del cliente según su función."""
    text_lower = text.lower().strip()
    if not text_lower:
        return "silencio"
    for category, pattern in TURN_CLASSIFIERS:
        if pattern.search(text_lower):
            return category
    return "otro"


# ============================================================
# MUTATOR
# ============================================================

class ScenarioMutator:
    """Genera variaciones de conversaciones reales."""

    def __init__(self, scenario_db):
        self.conversations = scenario_db.get('conversations', {})
        self._mutation_id = 0
        self._build_pools()

    def _build_pools(self):
        """Construye pools de turnos reales por categoría."""
        self.real_pools = defaultdict(list)
        for bruce_id, conv in self.conversations.items():
            for turn in conv.get('turns', []):
                if turn['role'] != 'client':
                    continue
                cat = classify_turn(turn['text'])
                if cat != "otro" and cat != "silencio":
                    self.real_pools[cat].append(turn['text'])

        # Deduplicar
        for cat in self.real_pools:
            self.real_pools[cat] = list(set(self.real_pools[cat]))

    def _next_id(self, prefix):
        self._mutation_id += 1
        return f"MUT-{prefix}-{self._mutation_id:03d}"

    # ----- Estrategia A: Sustitución de sinónimos -----

    def mutate_synonyms(self, conv, bruce_id, n=3):
        """Genera n variaciones reemplazando turnos del cliente con sinónimos."""
        mutations = []
        client_turns = [(i, t) for i, t in enumerate(conv.get('turns', []))
                        if t['role'] == 'client']

        if len(client_turns) < 2:
            return mutations

        for _ in range(n):
            new_turns = list(conv['turns'])
            changes = []
            for idx, turn in client_turns:
                cat = classify_turn(turn['text'])
                pool = self.real_pools.get(cat, SYNONYM_POOLS.get(cat, []))
                if pool and random.random() < 0.6:  # 60% chance de sustituir
                    replacement = random.choice(pool)
                    new_turns[idx] = {'role': 'client', 'text': replacement}
                    changes.append(f"{cat}→'{replacement[:30]}'")

            if changes:
                mutations.append({
                    'id': self._next_id('SYN'),
                    'strategy': 'synonym_substitution',
                    'source_bruce_id': bruce_id,
                    'turns': new_turns,
                    'changes': changes,
                })

        return mutations

    # ----- Estrategia B: Inyección de interrupciones -----

    def mutate_inject(self, conv, bruce_id, injection_types=None):
        """Inyecta situaciones problemáticas en la conversación."""
        mutations = []
        if injection_types is None:
            injection_types = list(INJECTIONS.keys())

        for inj_type in injection_types:
            inj = INJECTIONS.get(inj_type)
            if not inj:
                continue

            new_turns = list(conv.get('turns', []))
            inject_turns = inj['turns']
            position = inj['position']

            if position == 'start':
                insert_idx = 0
            elif position == 'mid':
                # Insertar después del primer turno del cliente
                client_idxs = [i for i, t in enumerate(new_turns) if t['role'] == 'client']
                if len(client_idxs) < 2:
                    insert_idx = len(new_turns) // 2
                else:
                    insert_idx = client_idxs[1]
            else:
                insert_idx = len(new_turns) - 1

            for j, it in enumerate(inject_turns):
                new_turns.insert(insert_idx + j, it)

            mutations.append({
                'id': self._next_id('INJ'),
                'strategy': 'injection',
                'injection_type': inj_type,
                'source_bruce_id': bruce_id,
                'turns': new_turns,
                'changes': [f"inject_{inj_type} at pos {insert_idx}"],
            })

        return mutations

    # ----- Estrategia C: Combinación de flujos -----

    def mutate_flow_combo(self, n=10):
        """Mezcla turnos de diferentes conversaciones."""
        mutations = []
        valid_convs = [
            (bid, c) for bid, c in self.conversations.items()
            if len(c.get('turns', [])) >= 4
        ]

        if len(valid_convs) < 2:
            return mutations

        for _ in range(n):
            # Seleccionar 2 conversaciones aleatorias
            (bid_a, conv_a), (bid_b, conv_b) = random.sample(valid_convs, 2)

            turns_a = conv_a['turns']
            turns_b = conv_b['turns']

            # Tomar primeros N turnos de A, últimos M turnos de B
            split_a = max(2, len(turns_a) // 2)
            split_b = max(2, len(turns_b) // 2)

            new_turns = turns_a[:split_a] + turns_b[-split_b:]

            mutations.append({
                'id': self._next_id('COMBO'),
                'strategy': 'flow_combination',
                'source_bruce_ids': [bid_a, bid_b],
                'turns': new_turns,
                'changes': [f"{bid_a}[:{split_a}] + {bid_b}[-{split_b}:]"],
            })

        return mutations

    # ----- Generar todas las mutaciones -----

    def generate_all(self, n_synonyms=20, n_injections=15, n_combos=15):
        """Genera mutaciones usando las 3 estrategias."""
        all_mutations = []

        # Seleccionar conversaciones representativas
        valid = [(bid, c) for bid, c in self.conversations.items()
                 if len(c.get('turns', [])) >= 4]

        if not valid:
            print("  No hay conversaciones válidas para mutar")
            return all_mutations

        # A) Sinónimos
        selected = random.sample(valid, min(n_synonyms // 3 + 1, len(valid)))
        for bid, conv in selected:
            muts = self.mutate_synonyms(conv, bid, n=3)
            all_mutations.extend(muts)
            if len([m for m in all_mutations if m['strategy'] == 'synonym_substitution']) >= n_synonyms:
                break

        # B) Inyecciones
        selected = random.sample(valid, min(n_injections, len(valid)))
        inj_types = list(INJECTIONS.keys())
        for i, (bid, conv) in enumerate(selected):
            inj_type = inj_types[i % len(inj_types)]
            muts = self.mutate_inject(conv, bid, [inj_type])
            all_mutations.extend(muts)
            if len([m for m in all_mutations if m['strategy'] == 'injection']) >= n_injections:
                break

        # C) Combos
        combos = self.mutate_flow_combo(n=n_combos)
        all_mutations.extend(combos)

        # Truncar si excede
        all_mutations = all_mutations[:n_synonyms + n_injections + n_combos]

        return all_mutations


def main():
    parser = argparse.ArgumentParser(description='Scenario Mutator')
    parser.add_argument('--count', type=int, default=50, help='Total de mutaciones')
    parser.add_argument('--strategy', choices=['syn', 'inj', 'combo', 'all'],
                        default='all', help='Estrategia')
    parser.add_argument('--scenario-db',
                        default=os.path.join(OUTPUT_DIR, 'scenario_db.json'),
                        help='scenario_db.json path')
    parser.add_argument('--output',
                        default=os.path.join(OUTPUT_DIR, 'mutation_scenarios.json'),
                        help='Archivo de salida')
    args = parser.parse_args()

    # Cargar scenario_db
    if not os.path.exists(args.scenario_db):
        print(f"ERROR: {args.scenario_db} no existe. Ejecutar log_scenario_extractor.py primero.")
        return

    with open(args.scenario_db, 'r', encoding='utf-8') as f:
        scenario_db = json.load(f)

    print(f"Cargadas {len(scenario_db.get('conversations', {}))} conversaciones")

    mutator = ScenarioMutator(scenario_db)

    # Calcular distribución
    third = args.count // 3
    remainder = args.count - (third * 3)

    if args.strategy == 'syn':
        mutations = []
        for bid, conv in list(mutator.conversations.items())[:args.count]:
            mutations.extend(mutator.mutate_synonyms(conv, bid, n=1))
    elif args.strategy == 'inj':
        mutations = []
        for bid, conv in list(mutator.conversations.items())[:args.count]:
            mutations.extend(mutator.mutate_inject(conv, bid))
    elif args.strategy == 'combo':
        mutations = mutator.mutate_flow_combo(n=args.count)
    else:
        mutations = mutator.generate_all(
            n_synonyms=third + remainder,
            n_injections=third,
            n_combos=third,
        )

    # Guardar
    output = {
        'metadata': {
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'total_mutations': len(mutations),
            'strategies': {
                'synonym_substitution': sum(1 for m in mutations if m['strategy'] == 'synonym_substitution'),
                'injection': sum(1 for m in mutations if m['strategy'] == 'injection'),
                'flow_combination': sum(1 for m in mutations if m['strategy'] == 'flow_combination'),
            },
        },
        'mutations': mutations,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nMutaciones generadas: {args.output}")
    print(f"  Total: {len(mutations)}")
    for strategy, count in output['metadata']['strategies'].items():
        print(f"  {strategy}: {count}")


if __name__ == '__main__':
    main()
