# MIGRACION REALISTA A $5000 SIN BORRAR POSICIONES
def migrar_a_5000_real():
    global data
    total_pos_val = sum([p['monto'] * (1 + p.get('gan',0)/100) for p in data['pos']])
    total_actual = data['b'] + total_pos_val
    objetivo = 5000.0
    if total_actual < 4900: # si aun no esta en 5000
        diferencia = objetivo - total_actual
        data['b'] += diferencia
        print(f"MIGRADO A $5000: +${diferencia:.2f} al saldo")
        save_data()

# Llamalo despues de load_data()
load_data()
migrar_a_5000_real()
