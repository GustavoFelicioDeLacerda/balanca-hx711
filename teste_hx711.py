from hx711 import HX711
import time
import json
import os
import sys

DT = 5
SCK = 6
CALIB_FILE = "calibracao.json"
DRIFT_MAX = 3000  # tolerancia p/ auto-correcao de tara (em unidades brutas)

try:
    hx = HX711(DT, SCK)
    print("HX711 detectado nos pinos DT={} SCK={}".format(DT, SCK))
except Exception as e:
    print("ERRO: Nao foi possivel conectar ao HX711.")
    print("Verifique a fiacao dos pinos DT={} e SCK={}".format(DT, SCK))
    print("Detalhe: {}".format(e))
    sys.exit(1)

def ler_bruto():
    for metodo in ("get_raw_data", "get_data", "get_value", "read"):
        if hasattr(hx, metodo):
            try:
                v = getattr(hx, metodo)()
                if isinstance(v, list):
                    return sum(v) / len(v) if v else 0
                return float(v)
            except Exception:
                continue
    raise RuntimeError("Nenhum metodo de leitura encontrado no HX711")

def ler_media_filtrada(n=15):
    valores = []
    for _ in range(n):
        try:
            valores.append(ler_bruto())
        except Exception:
            pass
        time.sleep(0.05)
    if len(valores) < 3:
        return sum(valores) / len(valores) if valores else 0
    media = sum(valores) / len(valores)
    desvio = (sum((x - media) ** 2 for x in valores) / len(valores)) ** 0.5
    filtrados = [x for x in valores if abs(x - media) <= 1.5 * desvio]
    if not filtrados:
        return media
    return sum(filtrados) / len(filtrados)

def calibrar():
    print("\n=== CALIBRACAO ===")
    print("Deixe a balanca VAZIA e aguarde...")
    time.sleep(3)
    tara = ler_media_filtrada(20)
    print("Tara calibrada: {:.0f}".format(tara))
    print()
    print("Coloque um PESO CONHECIDO sobre a balanca.")
    peso_conhecido = float(input("Digite o valor do peso em kg (ex: 1.034): "))
    print("Aguardando estabilizar...")
    time.sleep(3)
    bruto_com_peso = ler_media_filtrada(20)
    print("Bruto com peso: {:.0f}".format(bruto_com_peso))
    delta = bruto_com_peso - tara
    if delta == 0:
        print("ERRO: Delta zero! Verifique se o peso esta sobre a balanca.")
        return None, None
    fator = delta / peso_conhecido
    print("FATOR calculado: {:.0f}".format(fator))
    with open(CALIB_FILE, "w") as f:
        json.dump({"tara": tara, "fator": fator}, f)
    print("Calibracao salva em {}!".format(CALIB_FILE))
    print("==================\n")
    return tara, fator

def carregar_calibracao():
    if not os.path.exists(CALIB_FILE):
        print("Nenhuma calibracao encontrada. Vamos calibrar!")
        return calibrar()
    with open(CALIB_FILE, "r") as f:
        dados = json.load(f)
    tara_salva = dados["tara"]
    fator = dados["fator"]
    print("Calibracao carregada do arquivo.")
    print("Fator: {:.0f}".format(fator))
    # Auto-correcao de drift
    print("Verificando drift...")
    time.sleep(2)
    bruto_atual = ler_media_filtrada(20)
    diferenca = abs(bruto_atual - tara_salva)
    if diferenca < DRIFT_MAX:
        print("Drift detectado: {:.0f} (dentro da tolerancia). Corrigindo tara...".format(diferenca))
        tara_salva = bruto_atual
        dados["tara"] = tara_salva
        with open(CALIB_FILE, "w") as f:
            json.dump(dados, f)
        print("Tara auto-corrigida: {:.0f}".format(tara_salva))
    else:
        print("Peso detectado na balanca (diferenca: {:.0f}). Mantendo tara salva.".format(diferenca))
    return tara_salva, fator

# --- Inicio ---
TARA, FATOR = carregar_calibracao()

if TARA is None or FATOR is None:
    print("Calibracao falhou. Saindo.")
    sys.exit(1)

print("\nBalanca pronta. Ctrl+C para sair.")
print("-" * 50)

try:
    while True:
        bruto = ler_media_filtrada(15)
        peso = (bruto - TARA) / FATOR
        print("Bruto: {:.0f}  |  Peso: {:.3f} kg".format(bruto, peso))
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nEncerrado.")
except Exception as e:
    print("\nERRO durante leitura: {}".format(e))
    print("Verifique a conexao do HX711.")
