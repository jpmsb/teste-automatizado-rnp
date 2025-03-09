#!/usr/bin/env python3

import sys
import csv
import re

def clean_input_line(line):
    # Remove caracteres de controle, sequências ANSI e espaços extras
    cleaned_line = re.sub(r'\x1b\[[0-9;]*m', '', line)  # Remove sequências ANSI
    cleaned_line = re.sub(r'[\r\n]', '', cleaned_line)  # Remove retornos de carro e novas linhas
    return cleaned_line.strip()  # Remove espaços em excesso nas extremidades

def parse_mpstat(input_lines):
    results = []
    current_block = []
    cpu_count = 0  # Contador de CPUs para criar o cabeçalho corretamente

    for line in input_lines:
        line = clean_input_line(line)  # Limpa a linha antes de processar

        # Detecta início de um novo bloco por meio do cabeçalho
        if re.match(r'^\d{2}:\d{2}:\d{2} (AM|PM)?\s+CPU\s+%usr', line):
            if current_block:  # Se um bloco atual existe, salva antes de iniciar outro
                results.append(current_block)
                current_block = []
            continue

        # Detecta linhas de CPUs individuais (exclui "all" e outras linhas irrelevantes)
        if re.match(r'^\d{2}:\d{2}:\d{2} (AM|PM)?\s+\d+', line):  # CPUs específicas
            parts = line.split()
            if len(parts) > 11:  # Garante que há dados suficientes na linha
                try:
                    # Obtém o valor de %idle (último campo)
                    idle_value = float(parts[-1].replace(",", "."))
                    active_value = round(100 - idle_value, 2)  # Calcula 100 - %idle
                    current_block.append(active_value)

                    # Conta quantas CPUs existem (apenas na primeira iteração)
                    if len(results) == 0:
                        cpu_count += 1
                except ValueError:
                    continue

    if current_block:  # Adiciona o último bloco se não foi salvo
        results.append(current_block)

    return results, cpu_count

def write_csv(sums, cpu_count):
    writer = csv.writer(sys.stdout, delimiter=',')

    # Escreve o cabeçalho
    headers = [f"CPU_{i}" for i in range(cpu_count)]
    writer.writerow(headers)

    # Escreve os dados
    for block in sums:
        writer.writerow(block)

if __name__ == "__main__":
    # Lê a entrada padrão
    input_lines = sys.stdin.read().splitlines()

    # Faz o parse da saída do mpstat
    cpu_sums, cpu_count = parse_mpstat(input_lines)

    if cpu_sums:
        # Escreve os resultados no formato CSV com cabeçalho
        write_csv(cpu_sums, cpu_count)
    else:
        print("Nenhum dado válido encontrado.", file=sys.stderr)
