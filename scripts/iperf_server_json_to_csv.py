#!/usr/bin/env python3

import sys
import json
import csv

def parse_iperf3_json_to_csv():
    # Lê o JSON da entrada padrão
    data = json.load(sys.stdin)

    # Verifica se a chave "intervals" e "end" existem no JSON
    if "intervals" not in data or "end" not in data:
        print("Erro: JSON inválido. Chaves 'intervals' ou 'end' não encontradas.", file=sys.stderr)
        sys.exit(1)

    csv_rows = []
    
    # Processa dados de "intervals"
    for interval in data["intervals"]:
        if "sum" in interval:
            sum_data = interval["sum"]
            total_bytes = sum_data.get("bytes", 0)
            bits_per_second = sum_data.get("bits_per_second", 0)
            jitter = sum_data.get("jitter_ms", 0)
            lost_packets = sum_data.get("lost_packets", 0)
            lost_percent = sum_data.get("lost_percent", 0)
            csv_rows.append([
                total_bytes,
                bits_per_second,
                jitter,
                lost_packets,
                lost_percent
            ])
    
    # Processa dados de "end"
    end_data = data["end"]["streams"][0]["udp"]
    total_bytes = end_data.get("bytes", 0)
    bits_per_second = end_data.get("bits_per_second", 0)
    jitter = end_data.get("jitter_ms", 0)
    lost_packets = end_data.get("lost_packets", 0)
    lost_percent = end_data.get("lost_percent", 0)
    csv_rows.append([
        total_bytes,
        bits_per_second,
        jitter,
        lost_packets,
        lost_percent
    ])

    # Descarta a última linha
    csv_rows = csv_rows[:-1]

    # Escreve no CSV
    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow(["total_bytes_transferidos", "taxa_de_bits_por_segundo", "jitter", "total_pacotes_perdidos", "porcentagem_pacotes_perdidos"])
    csv_writer.writerows(csv_rows)

if __name__ == "__main__":
    parse_iperf3_json_to_csv()