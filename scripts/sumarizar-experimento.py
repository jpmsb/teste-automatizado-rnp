#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

##############################
# FUNÇÕES AUXILIARES
##############################
def format_label(name):
    return name.replace("_", " ").title().replace("Cpu", "CPU")

def get_round_dirs(test_dir):
    """Retorna os diretórios de rodada (ex.: rodada_1, rodada_2, …) em ordem."""
    rounds = [d for d in os.listdir(test_dir) if d.startswith("rodada_") and os.path.isdir(os.path.join(test_dir, d))]
    return sorted(rounds)

def format_throughput(value):
    """
    Recebe um valor em Mbps e retorna uma string formatada:
      - se >= 1000, converte para Gbps com 2 casas decimais e adiciona " G"
      - caso contrário, mantém em Mbps com 2 casas decimais e adiciona " M"
    Ex.: 9908.5 -> "9.91 G"
    """
    if value >= 1000:
        return f"{value/1000:.2f} G"
    else:
        return f"{value:.2f} M"

# Escolhe a escala com base no maior valor em bps
def choose_bps_scale(max_bps: float):
    scales = [
        ("bps", 1.0),
        ("kbps", 1e3),
        ("Mbps", 1e6),
        ("Gbps", 1e9),
        ("Tbps", 1e12),
    ]
    for i, (name, factor) in enumerate(scales):
        next_factor = scales[i + 1][1] if i + 1 < len(scales) else None
        if next_factor is None or max_bps < next_factor:
            return name, factor
    return scales[-1]

# Formata valores para rótulo usando a unidade escolhida
def format_value(v_bps, fator):
    return v_bps / fator

##############################
# FUNÇÕES DE PLOTAGEM (com error bars)
##############################
def plot_cpu_usage_for_round(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    overall_cpu_values = {}  # acumula os valores de cada núcleo em cada rodada
    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            print(f"Aviso: {mpstat_file} não encontrado.")
            continue
        df = pd.read_csv(mpstat_file)
        cpu_usage_mean = {}
        cpu_usage_err = {}
        n = len(df)
        for col in df.columns:
            m = df[col].mean()
            std = df[col].std()
            err = 1.96 * std / np.sqrt(n)
            cpu_usage_mean[col] = m
            cpu_usage_err[col] = err

        cores_from_header = list(cpu_usage_mean.keys())
        cores = [re.search(r'\d+', c).group() for c in cores_from_header]

        valores = [cpu_usage_mean[c] for c in cores_from_header]
        err_values = [cpu_usage_err[c] for c in cores_from_header]

        plt.figure(figsize=(8,6))
        bars = plt.bar(cores, valores, yerr=err_values, capsize=5)
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
        plt.ylabel("Uso médio de CPU (%)")
        plt.xlabel("Núcleo")
        plt.title(f"Uso de CPU - {format_label(rodada)} - {format_label(test_name)}")
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        # Acumula os valores por núcleo
        for core, value in cpu_usage_mean.items():
            overall_cpu_values.setdefault(core, []).append(value)
        count += 1

    return overall_cpu_values, count

def plot_cpu_usage_for_test(overall_cpu_values, test_dir, test_name):
    overall_cpu = {}
    overall_cpu_err = {}
    for core, values in overall_cpu_values.items():
        overall_cpu[core] = np.mean(values)
        overall_cpu_err[core] = 1.96 * np.std(values, ddof=1) / np.sqrt(len(values))

    cores_from_header = list(overall_cpu.keys())
    cores = [re.search(r'\d+', c).group() for c in cores_from_header]

    valores = [overall_cpu[c] for c in cores_from_header]
    err_values = [overall_cpu_err[c] for c in cores_from_header]

    plt.figure(figsize=(8,6))
    bars = plt.bar(cores, valores, yerr=err_values, capsize=5)
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                    ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title(f"{format_label(test_name)} - Uso de CPU (Média das Rodadas)")
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.png")
    svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()
    overall_cpu_agg = {core: (overall_cpu[core], overall_cpu_err[core]) for core in overall_cpu}
    return overall_cpu_agg

def plot_vazao_barra_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    cliente_list = []
    servidor_list = []
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
        col_server = 'bits_por_segundo' if 'bits_por_segundo' in df_server.columns else None

        # Cálculos em bps
        if col_client and len(df_client) > 0:
            n_client = len(df_client)
            mean_client_bps = float(df_client[col_client].mean())
            err_client_bps  = float(1.96 * df_client[col_client].std(ddof=1) / np.sqrt(n_client))

        else:
            mean_client_bps = err_client_bps = 0.0

        if col_server and len(df_server) > 0:
            n_server = len(df_server)
            mean_server_bps = float(df_server[col_server].mean())
            err_server_bps  = float(1.96 * df_server[col_server].std(ddof=1) / np.sqrt(n_server))

        else:
            mean_server_bps = err_server_bps = 0.0

        # Armazena os valores para o gráfico desta rodada em bits por segundo
        labels = ['Cliente', 'Servidor']
        valores_bps   = [mean_client_bps, mean_server_bps]
        erros_bps     = [err_client_bps,  err_server_bps]

        # Escolhe a escala ótima para esta rodada
        max_bps = max(valores_bps) if valores_bps else 0.0
        unidade, fator = choose_bps_scale(max_bps)

        # Normaliza valores/erros para a escala escolhida
        valores_norm = [v / fator for v in valores_bps]
        erros_norm   = [e / fator for e in erros_bps]

        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores_norm, width, yerr=erros_norm, capsize=5)
        for bar, raw_bps in zip(bars, valores_bps):
            plt.text(
                bar.get_x() + bar.get_width()/2,
                bar.get_height(),
                f"{format_value(raw_bps, fator):.2f}",
                ha='center', va='bottom'
            )

        plt.ylabel(f"Vazão Média ({unidade})")
        plt.xlabel("Origem")
        plt.title(f"Vazão - {format_label(rodada)} - {format_label(test_name)}")
        plt.xticks(x, labels)
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-vazao_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

        # Salva os valores em bps para o gráfico agregado
        cliente_list.append((mean_client_bps, err_client_bps))
        servidor_list.append((mean_server_bps, err_server_bps))
        count += 1

    # Gráfico agregado (Média das Rodadas)
    if count > 0:
        cliente_means_bps  = [val for val, _ in cliente_list]
        servidor_means_bps = [val for val, _ in servidor_list]
        media_cliente_bps  = float(np.mean(cliente_means_bps)) if cliente_means_bps else 0.0
        media_servidor_bps = float(np.mean(servidor_means_bps)) if servidor_means_bps else 0.0

        err_cliente_bps  = float(1.96 * np.std(cliente_means_bps,  ddof=1) / np.sqrt(len(cliente_means_bps)))  if len(cliente_means_bps)  > 1 else 0.0
        err_servidor_bps = float(1.96 * np.std(servidor_means_bps, ddof=1) / np.sqrt(len(servidor_means_bps))) if len(servidor_means_bps) > 1 else 0.0

        # Converte em bps para escolher a escala do gráfico agregado
        valores_bps = [media_cliente_bps, media_servidor_bps]
        erros_bps   = [err_cliente_bps, err_servidor_bps]

        max_bps = max(valores_bps) if valores_bps else 0.0
        unidade, fator = choose_bps_scale(max_bps)

        valores_norm = [v / fator for v in valores_bps]
        erros_norm   = [e / fator for e in erros_bps]

        labels = ['Cliente', 'Servidor']
        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores_norm, width, yerr=erros_norm, capsize=5)
        for bar, raw_bps in zip(bars, valores_bps):
            plt.text(
                bar.get_x() + bar.get_width()/2,
                bar.get_height(),
                f"{format_value(raw_bps, fator):.2f}",
                ha='center', va='bottom'
            )
        plt.ylabel(f"Vazão Média ({unidade})")
        plt.xlabel("Origem")
        plt.title(f"{format_label(test_name)} - Vazão (Média das Rodadas)")
        plt.xticks(x, labels)
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-vazao_barra.png")
        svg_path = os.path.join(test_dir, f"{test_name}-vazao_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

        # Retorno dos valores médios e erros em bps, e também formatados
        return ((media_cliente_bps, err_cliente_bps),
                (media_servidor_bps, err_servidor_bps),
                (format_value(media_cliente_bps, fator), format_value(media_servidor_bps, fator)), unidade)
    else:
        return ((0, 0), (0, 0), (0, 0))

def plot_perda_barra_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    perda_list = []
    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        # Tenta pegar a perda do servidor (UDP) ou retransmissões do cliente (TCP)
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")

        m = 0
        err = 0

        # Primeiro tenta UDP no servidor: "porcentagem_pacotes_perdidos"
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "porcentagem_pacotes_perdidos" in df_srv.columns:
                n = len(df_srv)
                m = df_srv["porcentagem_pacotes_perdidos"].mean()
                err = 1.96 * df_srv["porcentagem_pacotes_perdidos"].std() / np.sqrt(n)
            # Se não, tenta TCP no cliente: "retransmissoes"
            elif os.path.exists(client_file):
                df_cli = pd.read_csv(client_file)
                if "retransmissoes" in df_cli.columns:
                    n = len(df_cli)
                    m = df_cli["retransmissoes"].mean()
                    err = 1.96 * df_cli["retransmissoes"].std() / np.sqrt(n)
                else:
                    # Sem dados de perda/retransmissão
                    m = 0
                    err = 0
        # Se não tem server_file, tenta só no cliente
        elif os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            # Para UDP no cliente, não tem perda (apenas bits por segundo), então pula
            # Para TCP no cliente, "retransmissoes"
            if "retransmissoes" in df_cli.columns:
                n = len(df_cli)
                m = df_cli["retransmissoes"].mean()
                err = 1.96 * df_cli["retransmissoes"].std() / np.sqrt(n)
            else:
                m = 0
                err = 0
        else:
            print(f"Aviso: Nenhum arquivo iperf3 encontrado para {rodada}.")
            continue

        plt.figure(figsize=(6,5))
        bars = plt.bar(["Perda"], [m], yerr=[err], capsize=5)
        plt.text(0, m, f"{m:.4f}", ha='center', va='bottom')
        plt.ylabel("Perda (%)" if m < 1e2 else "Retransmissões")
        plt.title(f"Perda - {format_label(rodada)} - {format_label(test_name)}")
        plt.ylim(bottom=0)
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        
        perda_list.append((m, err))
        count += 1

    if count > 0:
        perda_means = [val for val, err in perda_list]
        media_perda = np.mean(perda_means)
        err_perda = 1.96 * np.std(perda_means, ddof=1) / np.sqrt(len(perda_means))
        plt.figure(figsize=(6,5))
        bars = plt.bar(["Perda"], [media_perda], yerr=[err_perda], capsize=5)
        plt.text(0, media_perda, f"{media_perda:.4f}", ha='center', va='bottom')
        plt.ylabel("Perda (%)" if media_perda < 1e2 else "Retransmissões")
        plt.title(f"{format_label(test_name)} - Perda (Média das Rodadas)")
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-perda_barra.png")
        svg_path = os.path.join(test_dir, f"{test_name}-perda_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        return (media_perda, err_perda)
    else:
        return (0,0)

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
        plt.tight_layout()
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
        plt.tight_layout()
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
    if not (dfs_client and dfs_server):
        print(f"Aviso: Não foi possível criar o gráfico temporal para {test_name} por falta de dados.")
        return

    # Calcula o menor comprimento comum
    common_length = min(min(len(df) for df in dfs_client), min(len(df) for df in dfs_server))
    df_med_client = dfs_client[0].iloc[:common_length].copy()
    df_med_server = dfs_server[0].iloc[:common_length].copy()

    # Faz média das séries temporais para o cliente
    if 'bits_por_segundo' in df_med_client.columns:
        values_list_client = [
            pd.to_numeric(df['bits_por_segundo'].iloc[:common_length], errors='coerce').fillna(0).values.astype(float)
            for df in dfs_client if 'bits_por_segundo' in df.columns
        ]
        if values_list_client:
            df_med_client['bits_por_segundo'] = np.mean(values_list_client, axis=0)

    # Faz média das séries temporais para o servidor
    if 'bits_por_segundo' in df_med_server.columns:
        values_list_server = [
            pd.to_numeric(df['bits_por_segundo'].iloc[:common_length], errors='coerce').fillna(0).values.astype(float)
            for df in dfs_server if 'bits_por_segundo' in df.columns
        ]
        if values_list_server:
            df_med_server['bits_por_segundo'] = np.mean(values_list_server, axis=0)

    # Plotagem
    plt.figure(figsize=(8,6))
    plotted_any = False
    if 'bits_por_segundo' in df_med_client.columns:
        plt.plot(df_med_client['tempo'], df_med_client['bits_por_segundo']/1e6, label="Cliente")
        plotted_any = True
    if 'bits_por_segundo' in df_med_server.columns:
        plt.plot(df_med_server['tempo'], df_med_server['bits_por_segundo']/1e6, label="Servidor")
        plotted_any = True
    if not plotted_any:
        print(f"Nenhuma coluna 'bits_por_segundo' encontrada nos arquivos para {test_name}.")
        return
    plt.ylabel("Vazão (Mbps)")
    plt.xlabel("Tempo (s)")
    plt.title(f"{format_label(test_name)} - Vazão Temporal")
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-vazao_temporal.png")
    svg_path = os.path.join(test_dir, f"{test_name}-vazao_temporal.svg")
    plt.tight_layout()
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
        plt.tight_layout()
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
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

def plot_cpu_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data = {}
    errors = {}
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            continue
        df = pd.read_csv(mpstat_file)
        cpu_dict = {}
        err_dict = {}
        n = len(df)
        for col in df.columns:
            m = df[col].mean()
            std = df[col].std()
            err = 1.96 * std / np.sqrt(n)
            cpu_dict[col] = m
            err_dict[col] = err
        data[rodada] = cpu_dict
        errors[rodada] = err_dict
    if not data:
        return

    cores_from_header = list(next(iter(data.values())).keys())
    cores = [re.search(r'\d+', c).group() for c in cores_from_header]

    x = np.arange(len(cores_from_header))
    width = 0.8 / len(data)
    plt.figure(figsize=(10,6))
    for i, rodada in enumerate(sorted(data.keys())):
        round_number = re.search(r'rodada_(\d+)', rodada).group(1)
        cpu_dict = data[rodada]
        err_dict = errors[rodada]
        values = [cpu_dict[core] for core in cores_from_header]
        err_values = [err_dict[core] for core in cores_from_header]
        bars = plt.bar(x + i*width, values, width, yerr=err_values, capsize=5, label=f"Rodada {round_number}")
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title(f"{format_label(test_name)} - Comparativo do uso de CPU por rodada")
    plt.xticks(x + width*(len(data)-1)/2, [format_label(c) for c in cores])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_por_rodada.png")
    svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_por_rodada.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_cpu_comparativo_por_teste(resultados_dir, tests, cpu_aggregate):
    if not cpu_aggregate:
        return
    prefix = "-".join(sorted(tests))
    test_keys = sorted([test for test in tests if test in cpu_aggregate])
    cores = list(next(iter(cpu_aggregate.values())).keys())
    n_tests = len(test_keys)
    n_cores = len(cores)
    x = np.arange(n_tests)
    width = 0.8 / n_cores

    plt.figure(figsize=(10,6))
    for j, core in enumerate(cores):
        values = []
        err_values = []
        for test in test_keys:
            mean_err = cpu_aggregate[test].get(core, (0,0))
            values.append(mean_err[0])
            err_values.append(mean_err[1])
        offset = (j - (n_cores - 1)/2) * width
        bars = plt.bar(x + offset, values, width, yerr=err_values, capsize=5, label=format_label(core))
        for i, bar in enumerate(bars):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Teste")
    plt.title("Uso de CPU por teste")
    plt.xticks(x, [format_label(test) for test in test_keys])
    plt.legend(title="Núcleo")
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_teste_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_teste_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_cpu_comparativo_por_nucleo(resultados_dir, tests, cpu_aggregate):
    if not cpu_aggregate:
        return
    prefix = "-".join(sorted(tests))
    first = next(iter(cpu_aggregate.values()))

    cores_from_header = list(first.keys())
    cores = [re.search(r'\d+', c).group() for c in cores_from_header]

    x = np.arange(len(cores_from_header))
    width = 0.8 / len(tests)
    plt.figure(figsize=(10,6))
    for i, test in enumerate(sorted(tests)):
        if test not in cpu_aggregate:
            continue
        cpu_dict = cpu_aggregate[test]
        values = [cpu_dict.get(core, (0,0))[0] for core in cores_from_header]
        err_values = [cpu_dict.get(core, (0,0))[1] for core in cores_from_header]
        bars = plt.bar(x + i*width, values, width, yerr=err_values, capsize=5, label=format_label(test))
        for bar in bars:
            plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                     ha='center', va='bottom')
    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title("Uso de CPU de cada teste por Núcleo")
    plt.xticks(x + width*(len(tests)-1)/2, [format_label(core) for core in cores])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_nucleo_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_nucleo_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data = {}
    errors = {}
    labels_map = {}  # rodada -> label

    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")

        # UDP servidor: porcentagem_pacotes_perdidos
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "porcentagem_pacotes_perdidos" in df_srv.columns:
                n = len(df_srv)
                m = df_srv["porcentagem_pacotes_perdidos"].mean()
                err = 1.96 * df_srv["porcentagem_pacotes_perdidos"].std() / np.sqrt(n)
                data[rodada] = m
                errors[rodada] = err
                labels_map[rodada] = "Perda (%)"
                continue  # Achou, passa pra próxima rodada

        # TCP cliente: retransmissoes
        if os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "retransmissoes" in df_cli.columns:
                n = len(df_cli)
                m = df_cli["retransmissoes"].mean()
                err = 1.96 * df_cli["retransmissoes"].std() / np.sqrt(n)
                data[rodada] = m
                errors[rodada] = err
                labels_map[rodada] = "Retransmissões"
                continue

    if not data:
        print("Nenhum dado de perda/retransmissão encontrado para as rodadas.")
        return

    rounds_sorted = sorted(data.keys())
    rounds_sorted_numbers = [re.search(r'rodada_(\d+)', r).group(1) for r in rounds_sorted]

    x = np.arange(len(rounds_sorted))
    values = [data[r] for r in rounds_sorted]
    err_values = [errors[r] for r in rounds_sorted]

    # Se houver só um tipo de label, usa no ylabel; se houver mistura, exibe ambos
    label_set = set(labels_map[r] for r in rounds_sorted)
    if len(label_set) == 1:
        ylabel = list(label_set)[0]
        title_tipo = ylabel
    else:
        ylabel = "Perda/Retransmissões"
        title_tipo = "Perda/Retransmissões"

    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5, yerr=err_values, capsize=5)
    for i, bar in enumerate(bars):
        rodada = rounds_sorted[i]
        lbl = labels_map[rodada]
        val = bar.get_height()
        plt.text(bar.get_x()+bar.get_width()/2, val, f"{val:.4f}\n({lbl})",
                 ha='center', va='bottom', fontsize=9)
    plt.ylabel(ylabel)
    plt.xlabel("Rodada")
    plt.title(f"{format_label(test_name)} - {title_tipo} por rodada")
    plt.xticks(x, rounds_sorted_numbers)
    plt.ylim(bottom=0)
    png_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.png")
    svg_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_teste(resultados_dir, tests, perda_aggregate):
    prefix = "-".join(sorted(tests))
    tests_sorted = sorted(perda_aggregate.keys())
    x = np.arange(len(tests_sorted))
    values = [perda_aggregate[test][0] for test in tests_sorted]
    err_values = [perda_aggregate[test][1] for test in tests_sorted]
    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5, yerr=err_values, capsize=5)
    for bar in bars:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.4f}",
                 ha='center', va='bottom')
    plt.ylabel("Perda (%)")
    plt.xlabel("Teste")
    plt.title("Perda Comparativo por Teste")
    plt.xticks(x, [format_label(test) for test in tests_sorted])
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, f"{prefix}-perda_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-perda_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_rodada(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    data_client = {}
    data_server = {}
    err_client = {}
    err_server = {}

    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        if not os.path.exists(client_file) or not os.path.exists(server_file):
            continue

        df_client = pd.read_csv(client_file)
        df_server = pd.read_csv(server_file)

        # Cliente (em bps)
        if 'bits_por_segundo' in df_client.columns and len(df_client) > 0:
            n_client  = len(df_client)
            m_client  = df_client['bits_por_segundo'].mean()  # bps
            e_client  = 1.96 * df_client['bits_por_segundo'].std(ddof=1) / np.sqrt(n_client)  # bps
            data_client[rodada] = float(m_client)
            err_client[rodada]  = float(e_client)

        # Servidor (em bps)
        if 'bits_por_segundo' in df_server.columns and len(df_server) > 0:
            n_server  = len(df_server)
            m_server  = df_server['bits_por_segundo'].mean()  # bps
            e_server  = 1.96 * df_server['bits_por_segundo'].std(ddof=1) / np.sqrt(n_server)  # bps
            data_server[rodada] = float(m_server)
            err_server[rodada]  = float(e_server)

    # Considera apenas rodadas presentes em ambos
    rounds_sorted = sorted(set(data_client.keys()) & set(data_server.keys()))
    if not rounds_sorted:
        print("Nenhum dado de vazão encontrado em comum para cliente e servidor.")
        return

    # Vetores em bps
    client_values_bps     = [data_client[r] for r in rounds_sorted]
    server_values_bps     = [data_server[r] for r in rounds_sorted]
    client_err_values_bps = [err_client[r]  for r in rounds_sorted]
    server_err_values_bps = [err_server[r]  for r in rounds_sorted]

    # Encontra a maior unidade de escala pelo maior valor entre cliente e servidor
    max_bps = max(max(client_values_bps), max(server_values_bps))
    unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

    # Normaliza para a escala encontrada
    client_values = [v / fator for v in client_values_bps]
    server_values = [v / fator for v in server_values_bps]
    client_err_values = [e / fator for e in client_err_values_bps]
    server_err_values = [e / fator for e in server_err_values_bps]

    # Eixo X (rodada N)
    x = np.arange(len(rounds_sorted))
    rounds_sorted_numbers = [re.search(r'rodada_(\d+)', r).group(1) for r in rounds_sorted]

    width = 0.35
    plt.figure(figsize=(8, 6))
    bars1 = plt.bar(x - width/2, client_values, width, yerr=client_err_values,
                    capsize=5, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, yerr=server_err_values,
                    capsize=5, label="Servidor")

    # Rótulos acima das barras
    for bar, raw_bps in zip(bars1, client_values_bps):
        plt.text(
            bar.get_x() + bar.get_width()/2,
            bar.get_height(),
            f"{format_value(raw_bps, fator):.2f}",
            ha='center', va='bottom'
        )
    for bar, raw_bps in zip(bars2, server_values_bps):
        plt.text(
            bar.get_x() + bar.get_width()/2,
            bar.get_height(),
            f"{format_value(raw_bps, fator):.2f}",
            ha='center', va='bottom'
        )

    # Eixos e título
    plt.ylabel(f"Vazão Média ({unidade})")
    plt.xlabel("Rodada")
    plt.title(f"{format_label(test_name)} - Vazão média por rodada")
    plt.xticks(x, rounds_sorted_numbers)

    # Ajuste do topo para não colidir com os rótulos
    max_height = max(max(client_values), max(server_values))
    plt.ylim(bottom=0, top=(max_height * 1.1) if max_height > 0 else 1.0)

    plt.legend()
    plt.tight_layout()

    png_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo_por_rodada.png")
    svg_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo_por_rodada.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_teste(resultados_dir, tests, vazao_aggregate):
    prefix = "-".join(sorted(tests))
    tests_sorted = sorted(vazao_aggregate.keys())
    x = np.arange(len(tests_sorted))
    client_values = [vazao_aggregate[test][0][0] for test in tests_sorted]
    server_values = [vazao_aggregate[test][1][0] for test in tests_sorted]
    client_err_values = [vazao_aggregate[test][0][1] for test in tests_sorted]
    server_err_values = [vazao_aggregate[test][1][1] for test in tests_sorted]
    width = 0.35
    plt.figure(figsize=(8,6))
    bars1 = plt.bar(x - width/2, client_values, width, yerr=client_err_values, capsize=5, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, yerr=server_err_values, capsize=5, label="Servidor")
    for bar in bars1:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    for bar in bars2:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    plt.ylabel("Vazão Média (Mbps)")
    plt.xlabel("Teste")
    plt.title("Vazão média por teste")
    plt.xticks(x, [format_label(test) for test in tests_sorted])
    plt.legend()
    plt.ylim(bottom=0)
    png_path = os.path.join(resultados_dir, f"{prefix}-vazao_barra_comparativo_por_teste.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-vazao_barra_comparativo_por_teste.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_servidor_comparativo(resultados_dir, tests, vazao_aggregate):
    tests_sorted = sorted(tests)
    x = np.arange(len(tests_sorted))
    server_values = [vazao_aggregate[test][1][0] for test in tests_sorted if test in vazao_aggregate]
    server_err_values = [vazao_aggregate[test][1][1] for test in tests_sorted if test in vazao_aggregate]
    width = 0.5
    plt.figure(figsize=(8,6))
    bars = plt.bar(x, server_values, width, yerr=server_err_values, capsize=5)
    for bar in bars:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    plt.ylabel("Vazão Média do Servidor (Mbps)")
    plt.xlabel("Teste")
    plt.title("Vazão do Servidor Comparativo")
    plt.xticks(x, [format_label(test) for test in tests_sorted])
    plt.ylim(bottom=0)
    prefix = "-".join(tests_sorted)
    png_path = os.path.join(resultados_dir, f"{prefix}-vazao_servidor_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-vazao_servidor_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

##############################
# FUNÇÕES AGREGADAS – SÉRIES TEMPORAIS (usadas apenas para PERDA)
##############################
def aggregate_perda_temporal_for_test(test_dir, test_name):
    rounds = get_round_dirs(test_dir)
    dfs = []
    col = None
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")

        df = None
        # Prioridade: UDP servidor
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "porcentagem_pacotes_perdidos" in df_srv.columns:
                df = df_srv
                col = "porcentagem_pacotes_perdidos"
        # Se não, TCP cliente
        if df is None and os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "retransmissoes" in df_cli.columns:
                df = df_cli
                col = "retransmissoes"
        if df is not None and col is not None:
            df = df.reset_index(drop=True)
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
    prefix = "-".join(sorted(tests))
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
    png_path = os.path.join(resultados_dir, f"{prefix}-perda_temporal_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-perda_temporal_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

##############################
# NOVA FUNÇÃO: GRÁFICO COMPARATIVO DE VAZÃO DO SERVIDOR COM REFERÊNCIA
##############################
def plot_vazao_com_referencia(resultados_dir, tests, vazao_aggregate, ref_srv, ref_test):
    """
    Gera um gráfico de barras comparativo da vazão do servidor de cada teste em relação à
    vazão do servidor do teste de referência.
    O nome do arquivo seguirá o padrão:
      <ref_test>-<teste1>-<teste2>-...-comparativo_vazao_com_referencia.png (e .svg)

    Nesta versão, a barra de referência fica à esquerda.
    """
    tests_ordered = tests  # mantém a ordem conforme informada
    n_tests = len(tests_ordered)
    test_srv_values = [vazao_aggregate[test][1][0] for test in tests_ordered if test in vazao_aggregate]
    test_srv_errs = [vazao_aggregate[test][1][1] for test in tests_ordered if test in vazao_aggregate]
    ref_values = [ref_srv[0]] * n_tests
    ref_errs = [ref_srv[1]] * n_tests

    x = np.arange(n_tests)
    width = 0.35
    plt.figure(figsize=(10,6))
    bars1 = plt.bar(x - width/2, ref_values, width, yerr=ref_errs, capsize=5, label="Referência")
    bars2 = plt.bar(x + width/2, test_srv_values, width, yerr=test_srv_errs, capsize=5, label="Teste")
    for bar in bars1:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    for bar in bars2:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    plt.ylabel("Vazão Média do Servidor (Mbps)")
    plt.xlabel("Teste")
    plt.title("Vazão do Servidor - Comparativo com Referência")
    plt.xticks(x, [format_label(test) for test in tests_ordered])
    plt.legend()
    plt.ylim(bottom=0)
    plt.tight_layout()
    prefix_filename = f"{ref_test}-{'-'.join(tests_ordered)}-comparativo_vazao_com_referencia"
    filename_png = f"{prefix_filename}.png"
    filepath_png = os.path.join(resultados_dir, filename_png)
    plt.savefig(filepath_png)
    filename_svg = f"{prefix_filename}.svg"
    filepath_svg = os.path.join(resultados_dir, filename_svg)
    plt.savefig(filepath_svg)
    plt.close()

##############################
# FUNÇÃO DE SUMARIZAÇÃO E MAIN
##############################
def print_summarization(test_name, cpu_usage, vazao_cliente, vazao_servidor, perda, round_count):
    print(f"\nResumo para {format_label(test_name)}:")
    print("\nUso de CPU por núcleo:")
    for core, usage in cpu_usage.items():
        print(f"    {format_label(core)}: {usage[0]:.2f}%")
    
    print("\nVazão:")
    print(f"{'Origem':<10}{'Vazão (Mbps)':<15}")
    print(f"{'Cliente':<10}{vazao_cliente[0]:<15.2f}")
    print(f"{'Servidor':<10}{vazao_servidor[0]:<15.2f}")
    
    print("\nPerda (%):")
    print(f"{'Média':<10}{perda[0]:<15.4f}")

    print(f"\nNúmero de rodadas computadas: {round_count}\n")

def main():
    parser = argparse.ArgumentParser(description="Sumariza experimento e gera gráficos comparativos.")
    parser.add_argument("-d", "--resultados", required=True,
                        help="Diretório de resultados (fonte dos dados).")
    parser.add_argument("-t", "--teste", action="append", required=True,
                        help="Nome do teste. Pode ser especificado múltiplas vezes.")
    parser.add_argument("-c", "--cpus", help="Lista de CPUs a serem consideradas, separadas por vírgula. Ex: 1,2")
    parser.add_argument("-r", "--referencia", help="Nome do teste de referência para comparar a vazão do servidor.")
    args = parser.parse_args()

    resultados_dir = args.resultados
    tests = args.teste
    cpus = args.cpus.split(",") if args.cpus else None
    referencia = args.referencia

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
        overall_cpu_values, round_count = plot_cpu_usage_for_round(test_dir, test)
        cpu_overall = plot_cpu_usage_for_test(overall_cpu_values, test_dir, test)
        vazao_cli, vazao_srv = plot_vazao_barra_for_test(test_dir, test)
        perda_overall = plot_perda_barra_for_test(test_dir, test)
        
        plot_cpu_temporal_for_test(test_dir, test)
        plot_vazao_temporal_for_test(test_dir, test)
        plot_perda_temporal_for_test(test_dir, test)

        plot_cpu_comparativo_por_rodada(test_dir, test)
        plot_perda_comparativo_por_rodada(test_dir, test)
        plot_vazao_comparativo_por_rodada(test_dir, test)

        print_summarization(test, cpu_overall, vazao_cli, vazao_srv, perda_overall, round_count)

        cpu_aggregate[test] = cpu_overall
        perda_aggregate[test] = perda_overall
        vazao_aggregate[test] = (vazao_cli, vazao_srv)
        perda_temporal_agg[test] = aggregate_perda_temporal_for_test(test_dir, test)

    sumarizado_dir = os.path.join(resultados_dir, "sumarizado-" + "-".join(tests))
    if not os.path.exists(sumarizado_dir):
        os.makedirs(sumarizado_dir)

    plot_cpu_comparativo_por_teste(sumarizado_dir, tests, cpu_aggregate)
    plot_cpu_comparativo_por_nucleo(sumarizado_dir, tests, cpu_aggregate)
    plot_perda_comparativo_por_teste(sumarizado_dir, tests, perda_aggregate)
    plot_vazao_comparativo_por_teste(sumarizado_dir, tests, vazao_aggregate)
    # Chamada da nova função: gráfico somente da vazão do servidor para cada teste.
    plot_vazao_servidor_comparativo(sumarizado_dir, tests, vazao_aggregate)

    agg_perda_temp = aggregate_all_perda_temporal(resultados_dir, tests)
    plot_perda_temporal_comparativo_por_teste(sumarizado_dir, tests, agg_perda_temp)

    if cpus:
        def plot_cpu_comparativo_por_teste_cpus(resultados_dir, tests, cpu_aggregate, cpus):
            tests_sorted = sorted([test for test in tests if test in cpu_aggregate])
            n_tests = len(tests_sorted)
            n_cpus = len(cpus)
            x = np.arange(n_tests)
            width = 0.8 / n_cpus
            plt.figure(figsize=(10,6))
            for j, cpu in enumerate(cpus):
                values = []
                err_values = []
                for test in tests_sorted:
                    usage = 0
                    err = 0
                    for key, val in cpu_aggregate[test].items():
                        k = key.lower()
                        if k.startswith("cpu"):
                            num = k[3:]
                            if num.startswith("_"):
                                num = num[1:]
                            if num == cpu:
                                usage, err = val
                                break
                    values.append(usage)
                    err_values.append(err)
                offset = (j - (n_cpus - 1)/2) * width
                bars = plt.bar(x + offset, values, width, yerr=err_values, capsize=5, label=f"CPU {cpu}")
                for i, bar in enumerate(bars):
                    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                             ha='center', va='bottom')
            plt.ylabel("Uso médio de CPU (%)")
            plt.xlabel("Teste")
            plt.title("Uso de CPU Comparativo por Teste (CPUs Selecionadas)")
            plt.xticks(x, [format_label(test) for test in tests_sorted])
            plt.legend(title="CPU")
            plt.ylim(bottom=0)
            plt.tight_layout()
            prefix = "-".join(tests_sorted)
            cpus_str = "-".join([f"cpu_{cpu}" for cpu in cpus])
            filename_png = f"{prefix}-{cpus_str}-comparativo_cpu_por_teste.png"
            filepath_png = os.path.join(resultados_dir, filename_png)
            plt.savefig(filepath_png)
            filename_svg = f"{prefix}-{cpus_str}-comparativo_cpu_por_teste.svg"
            filepath_svg = os.path.join(resultados_dir, filename_svg)
            plt.savefig(filepath_svg)
            plt.close()
        plot_cpu_comparativo_por_teste_cpus(sumarizado_dir, tests, cpu_aggregate, cpus)

    if referencia:
        ref_test = referencia
        ref_dir = os.path.join(resultados_dir, ref_test)
        if not os.path.isdir(ref_dir):
            print(f"Aviso: Diretório do teste de referência {ref_dir} não encontrado.")
        else:
            print(f"\nProcessando teste de referência {format_label(ref_test)} ...")
            vazao_ref = plot_vazao_barra_for_test(ref_dir, ref_test)
            plot_vazao_com_referencia(sumarizado_dir, tests, vazao_aggregate, vazao_ref[1], ref_test)

if __name__ == "__main__":
    main()