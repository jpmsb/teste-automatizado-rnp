#!/usr/bin/env python3

import sys
import csv

def main():
    # Lê o CSV da entrada padrão
    input_csv = sys.stdin.read()
    rows = list(csv.reader(input_csv.strip().splitlines()))
    
    # Verifica se o CSV não está vazio
    if not rows:
        print("Erro: O CSV está vazio.", file=sys.stderr)
        sys.exit(1)

    # Converte as linhas em números (excluindo valores não numéricos)
    columns = zip(*rows)
    columns = [[float(value) for value in col] for col in columns]

    # Calcula as médias de cada coluna e limita a duas casas decimais
    means = [round(sum(col) / len(col), 2) for col in columns]

    # Prepara o CSV de saída
    output_csv = ",".join(map(str, means))

    # Exibe o resultado no formato CSV
    print(output_csv)

if __name__ == "__main__":
    main()