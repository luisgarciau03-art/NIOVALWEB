# -*- coding: utf-8 -*-
"""
Análisis rápido de múltiples casos BRUCE
"""
import re

casos = {
    'BRUCE1288': {
        'archivo': 'logs_bruce1288.txt',
        'errores_reportados': ['Interrumpió', 'No detectó salió a comer', 'Falso IVR', 'Delay 8s']
    },
    'BRUCE1289': {
        'archivo': 'logs_bruce1289.txt',
        'errores_reportados': ['No le respondieron', 'Dijo "claro manejamos productos..."']
    },
    'BRUCE1290': {
        'archivo': 'logs_bruce1290.txt',
        'errores_reportados': ['No activó lógica espera', 'Repitió pregunta catálogo']
    },
    'BRUCE1291': {
        'archivo': 'logs_bruce1291.txt',
        'errores_reportados': ['No detectó salió', 'Interrumpió', 'Ya lo tengo registrado']
    },
    'BRUCE1293': {
        'archivo': 'logs_bruce1293.txt',
        'errores_reportados': ['No escucha "Soy yo"', 'Delay respuesta']
    }
}

print("="*80)
print("ANALISIS MASIVO DE CASOS BRUCE")
print("="*80 + "\n")

for bruce_id, info in casos.items():
    print(f"\n{'='*80}")
    print(f"{bruce_id}")
    print(f"{'='*80}")
    print(f"Errores reportados: {', '.join(info['errores_reportados'])}\n")
    
    try:
        with open(info['archivo'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar patrones clave
        conversacion = []
        for line in content.split('\n'):
            if '[CLIENTE]' in line and 'CLIENTE DIJO:' in line:
                match = re.search(r'CLIENTE DIJO: "(.*?)"', line)
                if match:
                    conversacion.append(('CLIENTE', match.group(1)))
            elif '[BRUCE]' in line and 'DICE:' in line:
                match = re.search(r'DICE: "(.*?)"', line)
                if match:
                    conversacion.append(('BRUCE', match.group(1)))
        
        # Mostrar conversación
        print(f"CONVERSACION ({len(conversacion)} intercambios):")
        for i, (quien, texto) in enumerate(conversacion[:10], 1):  # Primeros 10
            texto_corto = texto[:80] + "..." if len(texto) > 80 else texto
            print(f"  [{i}] {quien}: {texto_corto}")
        
        if len(conversacion) > 10:
            print(f"  ... y {len(conversacion) - 10} intercambios mas")
        
        # Buscar problemas específicos
        print(f"\nPROBLEMAS DETECTADOS:")
        
        # 1. Estado ENCARGADO_NO_ESTA
        if 'Estado → ENCARGADO_NO_ESTA' in content or 'ENCARGADO_NO_ESTA' in content:
            print(f"  - Estado ENCARGADO_NO_ESTA: DETECTADO")
        else:
            print(f"  - Estado ENCARGADO_NO_ESTA: NO detectado")
        
        # 2. Interrupciones
        interrupciones = len(re.findall(r'Cliente interrumpió', content))
        if interrupciones > 0:
            print(f"  - Interrupciones: {interrupciones} veces")
        
        # 3. IVR/Contestadora
        if 'IVR/CONTESTADORA DETECTADO' in content:
            print(f"  - IVR detectado: SI")
        elif 'AnsweredBy: machine' in content or 'AnsweredBy: fax' in content:
            print(f"  - IVR detectado por Twilio: SI")
        
        # 4. Frases de "salió", "ocupado", etc.
        frases_ausencia = re.findall(r'salió|salio|ocupado|no está|no esta|anda', content, re.IGNORECASE)
        if len(frases_ausencia) > 0:
            print(f"  - Menciones de ausencia: {len(frases_ausencia)} veces")
        
        # 5. Delays largos
        delays = re.findall(r'latencia: (\d+)ms', content)
        if delays:
            delays_nums = [int(d) for d in delays]
            max_delay = max(delays_nums)
            if max_delay > 5000:
                print(f"  - Delay maximo: {max_delay}ms ({max_delay/1000:.1f}s)")
        
        # 6. Repeticiones
        repeticiones = len(re.findall(r'REPETICIÓN DETECTADA', content))
        if repeticiones > 0:
            print(f"  - Repeticiones detectadas: {repeticiones} veces")
    
    except FileNotFoundError:
        print(f"  ERROR: Archivo {info['archivo']} no encontrado")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*80)
print("ANALISIS COMPLETADO")
print("="*80 + "\n")
