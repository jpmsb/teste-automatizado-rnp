#!/usr/bin/env python3

import sys
import json
import csv

def json_to_csv():
    # Ler o JSON da entrada padrão
    data = json.load(sys.stdin)
    
    # Extrair informações do início e do final
    destination_host = data["start"]["connected"][0]["remote_host"]
    destination_port = data["start"]["connected"][0]["remote_port"]
    protocol = data["start"]["test_start"]["protocol"]

    # Criar o writer CSV
    csv_writer = csv.writer(sys.stdout)
    
    # Escrever o cabeçalho
    csv_writer.writerow([
        "host_destino", 
        "porta_destino", 
        "protocolo", 
        "pacotes_perdidos", 
        "%_pacotes_perdidos", 
        "bytes_transferidos", 
        "bits_por_segundo"
    ])
    
    # Processar cada intervalo
    for interval in data["intervals"]:
        for stream in interval["streams"]:
            bytes_transferred = stream["bytes"]
            bits_per_second = stream["bits_per_second"]
            # Esses campos não estão nos streams, definindo como 0
            lost_packets = 0
            lost_percent = 0
            
            csv_writer.writerow([
                destination_host,
                destination_port,
                protocol,
                lost_packets,
                lost_percent,
                bytes_transferred,
                f"{bits_per_second:.2f}"
            ])
    
    # Processar os dados finais
    end_data = data["end"]["streams"][0]["udp"]
    lost_packets = end_data.get("lost_packets", 0)  # Define 0 caso não esteja presente
    lost_percent = end_data.get("lost_percent", 0)  # Define 0 caso não esteja presente
    bytes_transferred = end_data["bytes"]
    bits_per_second = end_data["bits_per_second"]

    csv_writer.writerow([
        destination_host,
        destination_port,
        protocol,
        lost_packets,
        f"{lost_percent:.6f}",
        bytes_transferred,
        f"{bits_per_second:.2f}"
    ])

if __name__ == "__main__":
    json_to_csv()