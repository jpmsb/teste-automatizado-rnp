#!/usr/bin/env python3
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

##############################
# FUNÇÕES AUXILIARES
##############################
def format_label(name):
    return name.replace("_", " ").title().replace("Cpu", "CPU")

def get_round_dirs(test_dir):
    """Retorna os diretórios de rodada (ex.: rodada_1, rodada_2, …) em ordem."""
    rounds = [d for d in os.listdir(test_dir) if d.startswith("rodada_") and os.path.isdir(os.path.join(test_dir, d))]
    return sorted(rounds)

##############################
# FUNÇÕES ORIGINAIS DE PLOTAGEM (por rodada e por teste)
##############################
def plot_cpu_usage_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    overall_cpu = {}
    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            print(f"Aviso: {mpstat_file} não encontrado.")
            continue
        df = pd.read_csv(mpstat_file)
        cpu_usage = {col: df[col].mean() for col in df.columns}
        cores = list(cpu_usage.keys())
        valores = [cpu_usage[c] for c in cores]
        plt.figure(figsize=(8,6))
        bars = plt.bar(cores, valores)
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
        plt.ylabel("Uso médio de CPU (%)")
        plt.xlabel("Núcleo")
        plt.title(f"Uso de CPU - {format_label(rodada)} - {format_label(test_name)}")
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        for core, usage in cpu_usage.items():
            overall_cpu[core] = overall_cpu.get(core, 0) + usage
        count += 1

    if count > 0:
        overall_cpu_avg = {core: val/count for core, val in overall_cpu.items()}
        cores = list(overall_cpu_avg.keys())
        valores = [overall_cpu_avg[c] for c in cores]
        plt.figure(figsize=(8,6))
        bars = plt.bar(cores, valores)
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
        plt.ylabel("Uso médio de CPU (%)")
        plt.xlabel("Núcleo")
        plt.title(f"{format_label(test_name)} - Uso de CPU (Média das Rodadas)")
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.png")
        svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        return overall_cpu_avg
    else:
        return {}

def plot_vazao_barra_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    soma_cliente = 0
    soma_servidor = 0
    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        if not os.path.exists(client_file) or not os.path.exists(server_file):
            print(f"Aviso: Arquivos de vazão não encontrados em {rodada_path}.")
            continue
        df_client = pd.read_csv(client_file)
        df_server = pd.read_csv(server_file)
        col_client = 'bits_por_segundo' if 'bits_por_segundo' in df_client.columns else None
        col_server = 'taxa_de_bits_por_segundo' if 'taxa_de_bits_por_segundo' in df_server.columns else None
        vazao_cliente = df_client[col_client].mean() / 1e6 if col_client else 0
        vazao_servidor = df_server[col_server].mean() / 1e6 if col_server else 0
        
        labels = ['Cliente', 'Servidor']
        valores = [vazao_cliente, vazao_servidor]
        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores, width)
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
        plt.ylabel("Vazão Média (Mbps)")
        plt.xlabel("Origem")
        plt.title(f"Vazão - {format_label(rodada)} - {format_label(test_name)}")
        plt.xticks(x, labels)
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        
        soma_cliente += vazao_cliente
        soma_servidor += vazao_servidor
        count += 1

    if count > 0:
        media_cliente = soma_cliente / count
        media_servidor = soma_servidor / count
        labels = ['Cliente', 'Servidor']
        valores = [media_cliente, media_servidor]
        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores, width)
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
        plt.ylabel("Vazão Média (Mbps)")
        plt.xlabel("Origem")
        plt.title(f"{format_label(test_name)} - Vazão (Média das Rodadas)")
        plt.xticks(x, labels)
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-vazao_barra.png")
        svg_path = os.path.join(test_dir, f"{test_name}-vazao_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        return media_cliente, media_servidor
    else:
        return 0, 0

def plot_perda_barra_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    soma_perda = 0
    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        if not os.path.exists(client_file):
            print(f"Aviso: {client_file} não encontrado.")
            continue
        df_client = pd.read_csv(client_file)
        col = '%_pacotes_perdidos' if '%_pacotes_perdidos' in df_client.columns else None
        perda = df_client[col].mean() if col else 0
        
        plt.figure(figsize=(6,5))
        bar = plt.bar(["Perda (%)"], [perda])
        plt.text(0, perda, f"{perda:.2f}", ha='center', va='bottom')
        plt.ylabel("Perda (%)")
        plt.title(f"Perda - {format_label(rodada)} - {format_label(test_name)}")
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        
        soma_perda += perda
        count += 1

    if count > 0:
        media_perda = soma_perda / count
        plt.figure(figsize=(6,5))
        plt.bar(["Perda (%)"], [media_perda])
        plt.text(0, media_perda, f"{media_perda:.2f}", ha='center', va='bottom')
        plt.ylabel("Perda (%)")
        plt.title(f"{format_label(test_name)} - Perda (Média das Rodadas)")
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-perda_barra.png")
        svg_path = os.path.join(test_dir, f"{test_name}-perda_barra.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        return media_perda
    else:
        return 0

def plot_cpu_temporal_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    dfs = []
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            print(f"Aviso: {mpstat_file} não encontrado.")
            continue
        df = pd.read_csv(mpstat_file)
        df['tempo'] = range(len(df))
        dfs.append(df)
        plt.figure(figsize=(8,6))
        for col in df.columns:
            if col == 'tempo':
                continue
            plt.plot(df['tempo'], df[col], label=format_label(col))
        plt.ylabel("Uso de CPU (%)")
        plt.xlabel("Tempo (s)")
        plt.title(f"CPU Temporal - {format_label(rodada)} - {format_label(test_name)}")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-CPU_temporal.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-CPU_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
    if dfs:
        min_len = min(len(df) for df in dfs)
        df_med = dfs[0].iloc[:min_len].copy()
        for col in df_med.columns:
            if col == 'tempo':
                continue
            values_list = [pd.to_numeric(df[col].iloc[:min_len], errors='coerce').fillna(0).values.astype(float)
                           for df in dfs if col in df.columns]
            if values_list:
                df_med[col] = np.mean(values_list, axis=0)
        plt.figure(figsize=(8,6))
        for col in df_med.columns:
            if col == 'tempo':
                continue
            plt.plot(df_med['tempo'], df_med[col], label=format_label(col))
        plt.ylabel("Uso de CPU (%)")
        plt.xlabel("Tempo (s)")
        plt.title(f"{format_label(test_name)} - CPU Temporal (Média das Rodadas)")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-CPU_temporal.png")
        svg_path = os.path.join(test_dir, f"{test_name}-CPU_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

def plot_vazao_temporal_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    dfs_client = []
    dfs_server = []
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        if not os.path.exists(client_file) or not os.path.exists(server_file):
            print(f"Aviso: Arquivos de vazão não encontrados em {rodada_path}.")
            continue
        df_client = pd.read_csv(client_file)
        df_server = pd.read_csv(server_file)
        df_client['tempo'] = range(len(df_client))
        df_server['tempo'] = range(len(df_server))
        dfs_client.append(df_client)
        dfs_server.append(df_server)
        plt.figure(figsize=(8,6))
        if 'bits_por_segundo' in df_client.columns:
            plt.plot(df_client['tempo'], df_client['bits_por_segundo']/1e6, label="Cliente")
        if 'taxa_de_bits_por_segundo' in df_server.columns:
            plt.plot(df_server['tempo'], df_server['taxa_de_bits_por_segundo']/1e6, label="Servidor")
        plt.ylabel("Vazão (Mbps)")
        plt.xlabel("Tempo (s)")
        plt.title(f"Vazão Temporal - {format_label(rodada)} - {format_label(test_name)}")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_temporal.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
    if dfs_client and dfs_server:
        common_length = min(min(len(df) for df in dfs_client), min(len(df) for df in dfs_server))
        df_med_client = dfs_client[0].iloc[:common_length].copy()
        for col in df_med_client.columns:
            if col == 'tempo':
                continue
            values_list = [pd.to_numeric(df[col].iloc[:common_length], errors='coerce').fillna(0).values.astype(float)
                           for df in dfs_client if col in df.columns]
            if values_list:
                df_med_client[col] = np.mean(values_list, axis=0)
        df_med_server = dfs_server[0].iloc[:common_length].copy()
        for col in df_med_server.columns:
            if col == 'tempo':
                continue
            values_list = [pd.to_numeric(df[col].iloc[:common_length], errors='coerce').fillna(0).values.astype(float)
                           for df in dfs_server if col in df.columns]
            if values_list:
                df_med_server[col] = np.mean(values_list, axis=0)
        plt.figure(figsize=(8,6))
        if 'bits_por_segundo' in df_med_client.columns:
            plt.plot(df_med_client['tempo'], df_med_client['bits_por_segundo']/1e6, label="Cliente")
        if 'taxa_de_bits_por_segundo' in df_med_server.columns:
            plt.plot(df_med_server['tempo'], df_med_server['taxa_de_bits_por_segundo']/1e6, label="Servidor")
        plt.ylabel("Vazão (Mbps)")
        plt.xlabel("Tempo (s)")
        plt.title(f"{format_label(test_name)} - Vazão Temporal (Média das Rodadas)")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-vazao_temporal.png")
        svg_path = os.path.join(test_dir, f"{test_name}-vazao_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

def plot_perda_temporal_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    dfs = []
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        if not os.path.exists(client_file):
            print(f"Aviso: {client_file} não encontrado.")
            continue
        df = pd.read_csv(client_file)
        col = '%_pacotes_perdidos' if '%_pacotes_perdidos' in df.columns else None
        if col is None:
            continue
        df['tempo'] = range(len(df))
        dfs.append(df)
        plt.figure(figsize=(8,6))
        plt.plot(df['tempo'], df[col], label="Perda (%)")
        plt.ylabel("Perda (%)")
        plt.xlabel("Tempo (s)")
        plt.title(f"Perda Temporal - {format_label(rodada)} - {format_label(test_name)}")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_temporal.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
    if dfs:
        common_length = min(len(df) for df in dfs)
        df_med = dfs[0].iloc[:common_length].copy()
        col = '%_pacotes_perdidos'
        values_list = [pd.to_numeric(df[col].iloc[:common_length], errors='coerce').fillna(0).values.astype(float)
                       for df in dfs if col in df.columns]
        if values_list:
            df_med[col] = np.mean(values_list, axis=0)
        plt.figure(figsize=(8,6))
        plt.plot(df_med['tempo'], df_med[col], label="Perda (%)")
        plt.ylabel("Perda (%)")
        plt.xlabel("Tempo (s)")
        plt.title(f"{format_label(test_name)} - Perda Temporal (Média das Rodadas)")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-perda_temporal.png")
        svg_path = os.path.join(test_dir, f"{test_name}-perda_temporal.svg")
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

##############################
# FUNÇÕES COMPARATIVAS – BARRAS
##############################
def plot_cpu_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data = {}
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            continue
        df = pd.read_csv(mpstat_file)
        data[rodada] = {col: df[col].mean() for col in df.columns}
    if not data:
        return
    cores = list(next(iter(data.values())).keys())
    x = np.arange(len(cores))
    width = 0.8 / len(data)
    plt.figure(figsize=(10,6))
    for i, (rodada, cpu_dict) in enumerate(sorted(data.items())):
        values = [cpu_dict[core] for core in cores]
        bars = plt.bar(x + i*width, values, width, label=rodada)
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title(f"{format_label(test_name)} - Uso de CPU Comparativo por Rodada")
    plt.xticks(x + width*(len(data)-1)/2, [format_label(c) for c in cores])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_comparativo.png")
    svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_cpu_comparativo_por_teste(resultados_dir, tests, cpu_aggregate):
    if not cpu_aggregate:
        return
    first = next(iter(cpu_aggregate.values()))
    cores = list(first.keys())
    x = np.arange(len(cores))
    width = 0.8 / len(tests)
    plt.figure(figsize=(10,6))
    for i, test in enumerate(sorted(tests)):
        if test not in cpu_aggregate:
            continue
        cpu_dict = cpu_aggregate[test]
        values = [cpu_dict[core] for core in cores]
        bars = plt.bar(x + i*width, values, width, label=format_label(test))
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title("Uso de CPU Comparativo por Teste")
    plt.xticks(x + width*(len(tests)-1)/2, [format_label(c) for c in cores])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, "uso_de_cpu_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, "uso_de_cpu_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data = {}
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        if not os.path.exists(client_file):
            continue
        df = pd.read_csv(client_file)
        col = '%_pacotes_perdidos' if '%_pacotes_perdidos' in df.columns else None
        if col:
            data[rodada] = df[col].mean()
    if not data:
        return
    rounds_sorted = sorted(data.keys())
    x = np.arange(len(rounds_sorted))
    values = [data[r] for r in rounds_sorted]
    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5)
    for bar in bars:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    plt.ylabel("Perda (%)")
    plt.xlabel("Rodada")
    plt.title(f"{format_label(test_name)} - Perda Comparativo por Rodada")
    plt.xticks(x, rounds_sorted)
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.png")
    svg_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_teste(resultados_dir, tests, perda_aggregate):
    tests_sorted = sorted(perda_aggregate.keys())
    x = np.arange(len(tests_sorted))
    values = [perda_aggregate[test] for test in tests_sorted]
    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5)
    for bar in bars:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    plt.ylabel("Perda (%)")
    plt.xlabel("Teste")
    plt.title("Perda Comparativo por Teste")
    plt.xticks(x, [format_label(test) for test in tests_sorted])
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, "perda_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, "perda_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data_client = {}
    data_server = {}
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        if not os.path.exists(client_file) or not os.path.exists(server_file):
            continue
        df_client = pd.read_csv(client_file)
        df_server = pd.read_csv(server_file)
        col_client = 'bits_por_segundo' if 'bits_por_segundo' in df_client.columns else None
        col_server = 'taxa_de_bits_por_segundo' if 'taxa_de_bits_por_segundo' in df_server.columns else None
        if col_client:
            data_client[rodada] = df_client[col_client].mean() / 1e6
        if col_server:
            data_server[rodada] = df_server[col_server].mean() / 1e6
    rounds_sorted = sorted(set(data_client.keys()) & set(data_server.keys()))
    if not rounds_sorted:
        return
    x = np.arange(len(rounds_sorted))
    width = 0.35
    client_values = [data_client[r] for r in rounds_sorted]
    server_values = [data_server[r] for r in rounds_sorted]
    plt.figure(figsize=(8,6))
    bars1 = plt.bar(x - width/2, client_values, width, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, label="Servidor")
    for bar in bars1:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    for bar in bars2:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    plt.ylabel("Vazão Média (Mbps)")
    plt.xlabel("Rodada")
    plt.title(f"{format_label(test_name)} - Vazão Comparativo por Rodada")
    plt.xticks(x, rounds_sorted)
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo.png")
    svg_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_teste(resultados_dir, tests, vazao_aggregate):
    tests_sorted = sorted(vazao_aggregate.keys())
    x = np.arange(len(tests_sorted))
    client_values = [vazao_aggregate[test][0] for test in tests_sorted]
    server_values = [vazao_aggregate[test][1] for test in tests_sorted]
    width = 0.35
    plt.figure(figsize=(8,6))
    bars1 = plt.bar(x - width/2, client_values, width, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, label="Servidor")
    for bar in bars1:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    for bar in bars2:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                 ha='center', va='bottom')
    plt.ylabel("Vazão Média (Mbps)")
    plt.xlabel("Teste")
    plt.title("Vazão Comparativo por Teste")
    plt.xticks(x, [format_label(test) for test in tests_sorted])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, "vazao_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, "vazao_barra_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

##############################
# FUNÇÕES AGREGADAS – SÉRIES TEMPORAIS (usadas apenas para PERDA)
##############################
def aggregate_perda_temporal_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    dfs = []
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        if not os.path.exists(client_file):
            continue
        df = pd.read_csv(client_file)
        col = '%_pacotes_perdidos' if '%_pacotes_perdidos' in df.columns else None
        if col:
            df['tempo'] = range(len(df))
            dfs.append(df[['tempo', col]])
    if not dfs:
        return None, None
    common_length = min(len(df) for df in dfs)
    tempos = dfs[0]['tempo'].iloc[:common_length].values
    values = np.mean([df[col].iloc[:common_length].values.astype(float) for df in dfs if col in df.columns], axis=0)
    return tempos, values

def aggregate_all_perda_temporal(resultados_dir, tests):
    agg = {}
    for test in tests:
        test_dir = os.path.join(resultados_dir, test)
        tempo, values = aggregate_perda_temporal_for_test(test_dir, test)
        if tempo is not None:
            agg[test] = (tempo, values)
    return agg

def plot_perda_temporal_comparativo_por_teste(resultados_dir, tests, perda_temporal_agg):
    tests_sorted = sorted(perda_temporal_agg.keys())
    plt.figure(figsize=(10,6))
    for test in tests_sorted:
        tempo, perda = perda_temporal_agg[test]
        plt.plot(tempo, perda, label=format_label(test))
    plt.ylabel("Perda (%)")
    plt.xlabel("Tempo (s)")
    plt.title("Perda Temporal Comparativo por Teste")
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, "perda_temporal_comparativo.png")
    svg_path = os.path.join(resultados_dir, "perda_temporal_comparativo.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

##############################
# FUNÇÃO DE SUMARIZAÇÃO
##############################
def print_summarization(test_name, cpu_usage, vazao_cliente, vazao_servidor, perda):
    print(f"\nResumo para {format_label(test_name)}:")
    print("\nUso de CPU por núcleo:")
    for core, usage in cpu_usage.items():
        print(f"    {format_label(core)}: {usage:.2f}%")
    
    print("\nVazão:")
    print(f"{'Origem':<10}{'Vazão (Mbps)':<15}")
    print(f"{'Cliente':<10}{vazao_cliente:<15.2f}")
    print(f"{'Servidor':<10}{vazao_servidor:<15.2f}")
    
    print("\nPerda (%):")
    print(f"{'Média':<10}{perda:<15.2f}")

##############################
# FUNÇÃO MAIN
##############################
def main():
    if len(sys.argv) < 3:
        print("Uso: ./sumariza-experimento <diretório de resultados> <teste_1> <teste_2> ...")
        sys.exit(1)
    
    resultados_dir = sys.argv[1]
    tests = sys.argv[2:]
    
    # Dicionários para os comparativos entre testes (barras e séries temporais para PERDA)
    cpu_aggregate = {}
    perda_aggregate = {}
    vazao_aggregate = {}
    perda_temporal_agg = {}
    
    for test in tests:
        test_dir = os.path.join(resultados_dir, test)
        if not os.path.isdir(test_dir):
            print(f"Aviso: Diretório do teste {test_dir} não encontrado.")
            continue
        
        print(f"\nProcessando {format_label(test)} ...")
        cpu_overall = plot_cpu_usage_for_test(test_dir, test)
        vazao_cli, vazao_srv = plot_vazao_barra_for_test(test_dir, test)
        perda_overall = plot_perda_barra_for_test(test_dir, test)
        
        plot_cpu_temporal_for_test(test_dir, test)
        plot_vazao_temporal_for_test(test_dir, test)
        plot_perda_temporal_for_test(test_dir, test)
        
        # Gráficos comparativos por rodada (barras e séries temporais) no diretório de cada teste
        plot_cpu_comparativo_por_rodada(test_dir, test)
        plot_perda_comparativo_por_rodada(test_dir, test)
        plot_vazao_comparativo_por_rodada(test_dir, test)
        
        print_summarization(test, cpu_overall, vazao_cli, vazao_srv, perda_overall)
        
        # Armazena dados para os comparativos entre testes (barras)
        cpu_aggregate[test] = cpu_overall
        perda_aggregate[test] = perda_overall
        vazao_aggregate[test] = (vazao_cli, vazao_srv)
        
        # Agrega as séries temporais de perda para os comparativos entre testes
        perda_temporal_agg[test] = aggregate_perda_temporal_for_test(test_dir, test)
    
    # Gera gráficos comparativos entre testes (barras)
    plot_cpu_comparativo_por_teste(resultados_dir, tests, cpu_aggregate)
    plot_perda_comparativo_por_teste(resultados_dir, tests, perda_aggregate)
    plot_vazao_comparativo_por_teste(resultados_dir, tests, vazao_aggregate)
    
    # Gera o gráfico comparativo de série temporal apenas para PERDA (no diretório raiz de resultados)
    agg_perda_temp = aggregate_all_perda_temporal(resultados_dir, tests)
    plot_perda_temporal_comparativo_por_teste(resultados_dir, tests, agg_perda_temp)

if __name__ == "__main__":
    main()