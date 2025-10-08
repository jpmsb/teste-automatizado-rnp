#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import configparser

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

def _safe(v):
        return 0.0 if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)

def get_test_display_name_from_conf(test_dir: str) -> str:
    """
    Tenta encontrar o nome amigável do teste no arquivo INI de configuração.
    """
    try:
        test_name = os.path.basename(test_dir)
        ini_path = os.path.join(test_dir, f"{test_name}-conf.ini")
        if os.path.exists(ini_path):
            cfg = configparser.ConfigParser()
            # Mantém case-sensitivity das chaves
            cfg.optionxform = str
            cfg.read(ini_path, encoding="utf-8")
            if cfg.has_section("Teste") and cfg.has_option("Teste", "Nome"):
                nome = cfg.get("Teste", "Nome", fallback="").strip()
                if nome:
                    return nome
    except Exception as e:
        # Não interrompe o fluxo caso o INI esteja ausente/malformado
        print(f"Aviso: falha ao ler '{test_name}-conf.ini': {e}")
    return format_label(test_name)

########################
# FUNÇÕES DE PLOTAGEM  #
########################
def plot_cpu_usage_for_round(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    overall_cpu_values = {}  # acumula os valores de cada núcleo em cada rodada
    test_display_name = get_test_display_name_from_conf(test_dir)

    count = 0
    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        if not os.path.exists(mpstat_file):
            print(f"Aviso: {mpstat_file} não encontrado.")
            continue

        df = pd.read_csv(mpstat_file)
        cpu_usage_mean, cpu_usage_err = {}, {}
        n = len(df)
        for col in df.columns:
            m = df[col].mean()
            std = df[col].std(ddof=1)
            err = 1.96 * std / np.sqrt(n) if n > 1 else 0.0
            cpu_usage_mean[col] = float(m)
            cpu_usage_err[col]  = float(err)

        cores_from_header = list(cpu_usage_mean.keys())
        cores = [re.search(r'\d+', c).group() for c in cores_from_header]

        valores = [cpu_usage_mean[c] for c in cores_from_header]
        err_values = [cpu_usage_err[c] for c in cores_from_header]

        # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
        y_max = max((v + e) for v, e in zip(valores, err_values)) if valores else 0.0
        top = (y_max * 1.08) if y_max > 0 else 1.0            # mantém 8% de folga no topo
        label_offset = 0.005 * top                            # distância do valor até o topo da barra

        plt.figure(figsize=(8,6))
        bars = plt.bar(cores, valores, yerr=err_values if mostrar_intervalo_confianca else 0, capsize=5 if mostrar_intervalo_confianca else 0)

        for i, bar in enumerate(bars):
            e = err_values[i] if i < len(err_values) else 0.0
            y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x() + bar.get_width()/2, y, f"{bar.get_height():.2f}",
                     ha='center', va='bottom')

        plt.ylabel("Uso médio de CPU (%)")
        plt.xlabel("Núcleo")
        plt.title(f"Uso de CPU - {format_label(rodada)} - {test_display_name}")
        plt.ylim(bottom=0, top=top)

        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-uso_de_cpu_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

        for core, value in cpu_usage_mean.items():
            overall_cpu_values.setdefault(core, []).append(value)
        count += 1

    return overall_cpu_values, count

def plot_cpu_usage_for_test(overall_cpu_values, test_dir, test_name, mostrar_intervalo_confianca=False):
    overall_cpu = {}
    overall_cpu_err = {}
    test_display_name = get_test_display_name_from_conf(test_dir)

    for core, values in overall_cpu_values.items():
        overall_cpu[core] = np.mean(values)
        overall_cpu_err[core] = 1.96 * np.std(values, ddof=1) / np.sqrt(len(values)) if len(values) > 1 else 0.0

    cores_from_header = list(overall_cpu.keys())
    cores = [re.search(r'\d+', c).group() for c in cores_from_header]

    valores = [overall_cpu[c] for c in cores_from_header]
    err_values = [overall_cpu_err[c] for c in cores_from_header]

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    y_max = max((_safe(v) + _safe(e)) for v, e in zip(valores, err_values)) if valores else 0.0
    top = (y_max * 1.08) if y_max > 0 else 1.0   # 8% de folga no topo
    label_offset = 0.005 * top                   # distância do valor até o topo da barra

    plt.figure(figsize=(8,6))
    bars = plt.bar(cores, valores, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)

    # Rótulos acima das barras
    for i, bar in enumerate(bars):
        e = _safe(err_values[i]) if i < len(err_values) else 0.0
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x() + bar.get_width()/2, y, f"{bar.get_height():.2f}",
                 ha='center', va='bottom')

    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title(f"{test_display_name} - Uso de CPU (Média das Rodadas)")
    plt.ylim(bottom=0, top=top)

    png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.png")
    svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

    overall_cpu_agg = {core: (overall_cpu[core], overall_cpu_err[core]) for core in overall_cpu}
    return overall_cpu_agg

def plot_vazao_barra_for_test(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    cliente_list = []
    servidor_list = []
    count = 0
    test_display_name = get_test_display_name_from_conf(test_dir)

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
            err_client_bps  = float(1.96 * df_client[col_client].std(ddof=1) / np.sqrt(n_client)) if n_client > 1 else 0.0
        else:
            mean_client_bps = err_client_bps = 0.0

        if col_server and len(df_server) > 0:
            n_server = len(df_server)
            mean_server_bps = float(df_server[col_server].mean())
            err_server_bps  = float(1.96 * df_server[col_server].std(ddof=1) / np.sqrt(n_server)) if n_server > 1 else 0.0
        else:
            mean_server_bps = err_server_bps = 0.0

        # Armazena os valores para o gráfico desta rodada em bits por segundo
        labels = ['Cliente', 'Servidor']
        valores_bps = [mean_client_bps, mean_server_bps]
        erros_bps   = [err_client_bps,  err_server_bps]

        # Encontra a escala ótima para esta rodada
        max_bps = max(valores_bps) if valores_bps else 0.0
        unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

        # Normaliza valores/erros para a escala escolhida
        valores_norm = [v / fator for v in valores_bps]
        erros_norm   = [e / fator for e in erros_bps]

        # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
        y_max = max((_safe(v) + _safe(e)) for v, e in zip(valores_norm, erros_norm)) if valores_norm else 0.0
        top = (y_max * 1.08) if y_max > 0 else 1.0
        label_offset = 0.012 * top

        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores_norm, width, yerr=erros_norm if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)
        plt.ylim(bottom=0, top=top)

        # Rótulos acima das barras + erro (na mesma unidade do eixo)
        for bar, raw_bps, e in zip(bars, valores_bps, erros_norm):
            y = bar.get_height() + (_safe(e) if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x() + bar.get_width()/2, y, f"{format_value(raw_bps, fator):.2f}",
                     ha='center', va='bottom')

        plt.ylabel(f"Vazão Média ({unidade})")
        plt.xlabel("Origem")
        plt.title(f"Vazão - {format_label(rodada)} - {test_display_name}")
        plt.xticks(x, labels)
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

        # Escala do gráfico agregado
        valores_bps = [media_cliente_bps, media_servidor_bps]
        erros_bps   = [err_cliente_bps, err_servidor_bps]

        max_bps = max(valores_bps) if valores_bps else 0.0
        unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

        valores_norm = [v / fator for v in valores_bps]
        erros_norm   = [e / fator for e in erros_bps]

        # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
        y_max = max((_safe(v) + _safe(e)) for v, e in zip(valores_norm, erros_norm)) if valores_norm else 0.0
        top = (y_max * 1.08) if y_max > 0 else 1.0
        label_offset = 0.012 * top

        labels = ['Cliente', 'Servidor']
        x = np.arange(len(labels))
        width = 0.3
        plt.figure(figsize=(8,6))
        bars = plt.bar(x, valores_norm, width, yerr=erros_norm if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)
        plt.ylim(bottom=0, top=top)

        for bar, raw_bps, e in zip(bars, valores_bps, erros_norm):
            y = bar.get_height() + (_safe(e) if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x() + bar.get_width()/2, y, f"{format_value(raw_bps, fator):.2f}",
                     ha='center', va='bottom')

        plt.ylabel(f"Vazão Média ({unidade})")
        plt.xlabel("Origem")
        plt.title(f"{test_display_name} - Vazão (Média das Rodadas)")
        plt.xticks(x, labels)
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

def plot_perda_barra_for_test(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    perda_list = []
    count = 0
    test_display_name = get_test_display_name_from_conf(test_dir)

    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")

        m = 0.0
        err = 0.0

        # Primeiro tenta UDP no servidor: "porcentagem_pacotes_perdidos"
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "porcentagem_pacotes_perdidos" in df_srv.columns:
                n = len(df_srv)
                m = float(df_srv["porcentagem_pacotes_perdidos"].mean())
                std = float(df_srv["porcentagem_pacotes_perdidos"].std(ddof=1))
                err = 1.96 * std / np.sqrt(n) if n > 1 and not np.isnan(std) else 0.0
            # Se não, tenta TCP no cliente: "retransmissoes"
            elif os.path.exists(client_file):
                df_cli = pd.read_csv(client_file)
                if "retransmissoes" in df_cli.columns:
                    n = len(df_cli)
                    m = float(df_cli["retransmissoes"].mean())
                    std = float(df_cli["retransmissoes"].std(ddof=1))
                    err = 1.96 * std / np.sqrt(n) if n > 1 and not np.isnan(std) else 0.0
                else:
                    m = 0.0
                    err = 0.0
        # Se não tem server_file, tenta só no cliente
        elif os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "retransmissoes" in df_cli.columns:
                n = len(df_cli)
                m = float(df_cli["retransmissoes"].mean())
                std = float(df_cli["retransmissoes"].std(ddof=1))
                err = 1.96 * std / np.sqrt(n) if n > 1 and not np.isnan(std) else 0.0
            else:
                m = 0.0
                err = 0.0
        else:
            print(f"Aviso: Nenhum arquivo iperf3 encontrado para {rodada}.")
            continue

        plt.figure(figsize=(6,5))
        plt.bar(["Perda"], [m], yerr=[err] if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)

        # Ajusta o topo para que caiba o rótulo
        y_max = _safe(m) + _safe(err)
        top = (y_max * 1.08) if y_max > 0 else 1.0
        label_offset = 0.005 * top
        plt.ylim(bottom=0, top=top)

        # Rótulo acima da barra + erro
        plt.text(0, m + (_safe(err) if mostrar_intervalo_confianca else 0) + label_offset, f"{m:.4f}", ha='center', va='bottom')

        plt.ylabel("Perda (%)" if m < 1e2 else "Retransmissões")
        plt.title(f"Perda - {format_label(rodada)} - {test_display_name}")
        png_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.png")
        svg_path = os.path.join(rodada_path, f"{rodada}-{test_name}-perda_barra.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()
        
        perda_list.append((m, err))
        count += 1

    if count > 0:
        perda_means = [val for val, _ in perda_list]
        media_perda = float(np.mean(perda_means))
        err_perda = float(1.96 * np.std(perda_means, ddof=1) / np.sqrt(len(perda_means))) if len(perda_means) > 1 else 0.0

        plt.figure(figsize=(6,5))
        plt.bar(["Perda"], [media_perda], yerr=[err_perda] if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)

        # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
        y_max = _safe(media_perda) + _safe(err_perda)
        top = (y_max * 1.08) if y_max > 0 else 1.0
        label_offset = 0.005 * top
        plt.ylim(bottom=0, top=top)

        plt.text(0, media_perda + (_safe(err_perda) if mostrar_intervalo_confianca else 0) + label_offset, f"{media_perda:.4f}",
                 ha='center', va='bottom')

        plt.ylabel("Perda (%)" if media_perda < 1e2 else "Retransmissões")
        plt.title(f"{test_display_name} - Perda (Média das Rodadas)")
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
    test_display_name = get_test_display_name_from_conf(test_dir)

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
        plt.title(f"CPU Temporal - {format_label(rodada)} - {test_display_name}")
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
        plt.title(f"{test_display_name} - CPU Temporal (Média das Rodadas)")
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
    test_display_name = get_test_display_name_from_conf(test_dir)

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
        print(f"Aviso: Não foi possível criar o gráfico temporal para {test_display_name} por falta de dados.")
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
    plt.title(f"{test_display_name} - Vazão Temporal")
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
    test_display_name = get_test_display_name_from_conf(test_dir)

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
        plt.title(f"Perda Temporal - {format_label(rodada)} - {test_display_name}")
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
        plt.title(f"{test_display_name} - Perda Temporal (Média das Rodadas)")
        plt.legend()
        plt.ylim(bottom=0)
        png_path = os.path.join(test_dir, f"{test_name}-perda_temporal.png")
        svg_path = os.path.join(test_dir, f"{test_name}-perda_temporal.svg")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.savefig(svg_path)
        plt.close()

def plot_cpu_comparativo_por_rodada(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    data = {}
    errors = {}
    test_display_name = get_test_display_name_from_conf(test_dir)

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
            m = float(pd.to_numeric(df[col], errors='coerce').mean())
            std = float(pd.to_numeric(df[col], errors='coerce').std(ddof=1))
            err = 1.96 * std / np.sqrt(n) if n > 1 and not np.isnan(std) else 0.0
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

    # acompanhar topo global e guardar barras/erros para rotular depois
    y_max_total = 0.0
    all_bars_and_errs = []  # [(bars, err_values)]

    for i, rodada in enumerate(sorted(data.keys())):
        round_number = re.search(r'rodada_(\d+)', rodada).group(1)
        cpu_dict = data[rodada]
        err_dict = errors[rodada]
        values = [cpu_dict[core] for core in cores_from_header]
        err_values = [err_dict[core] for core in cores_from_header]

        # atualiza topo global com (valor + erro)
        if values:
            y_max_local = max(v + (0.0 if (e is None or np.isnan(e)) else float(e))
                              for v, e in zip(values, err_values))
            y_max_total = max(y_max_total, y_max_local)

        bars = plt.bar(x + i*width, values, width, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label=f"Rodada {round_number}")
        all_bars_and_errs.append((bars, err_values))

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    top = (y_max_total * 1.08) if y_max_total > 0 else 1.0   # 8% de folga no topo
    label_offset = 0.005 * top                               # distância do valor até o topo da barra
    plt.ylim(bottom=0, top=top)

    # Rótulos acima das barras
    for bars, err_values in all_bars_and_errs:
        for i, bar in enumerate(bars):
            e = err_values[i] if i < len(err_values) else 0.0
            e = 0.0 if (e is None or (isinstance(e, float) and np.isnan(e))) else float(e)
            y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x()+bar.get_width()/2, y, f"{bar.get_height():.2f}",
                     ha='center', va='bottom')

    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title(f"{test_display_name} - Comparativo do uso de CPU por rodada")
    plt.xticks(x + width*(len(data)-1)/2, [format_label(c) for c in cores])
    plt.legend()

    png_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_por_rodada.png")
    svg_path = os.path.join(test_dir, f"{test_name}-uso_de_cpu_barra_por_rodada.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_cpu_comparativo_por_teste(resultados_dir, tests, cpu_aggregate, mostrar_intervalo_confianca=False):
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

    # Encontrar o maior valor de topo para ajustar o eixo y
    y_max_total = 0.0
    all_bars_and_errs = []  # [(bars, err_values)]

    for j, core in enumerate(cores):
        values = []
        err_values = []
        for test in test_keys:
            mean_err = cpu_aggregate[test].get(core, (0,0))
            v = float(mean_err[0]) if mean_err and mean_err[0] is not None else 0.0
            e = float(mean_err[1]) if mean_err and mean_err[1] is not None else 0.0
            values.append(v)
            err_values.append(e)

        offset = (j - (n_cores - 1)/2) * width
        bars = plt.bar(x + offset, values, width, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label=format_label(core))
        all_bars_and_errs.append((bars, err_values))

        if values:
            y_max_local = max(v + (e if not np.isnan(e) else 0.0) for v, e in zip(values, err_values))
            y_max_total = max(y_max_total, y_max_local)

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    top = (y_max_total * 1.08) if y_max_total > 0 else 1.0   # 8% de folga no topo
    label_offset = 0.005 * top                               # distância do valor até o topo da barra
    plt.ylim(bottom=0, top=top)

    # Rótulos acima das barras
    for bars, err_values in all_bars_and_errs:
        for i, bar in enumerate(bars):
            e = err_values[i] if i < len(err_values) and err_values[i] is not None else 0.0
            e = 0.0 if np.isnan(e) else float(e)
            y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x() + bar.get_width()/2, y, f"{bar.get_height():.2f}",
                     ha='center', va='bottom')

    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Teste")
    plt.title("Uso de CPU por teste")
    plt.xticks(x, [get_test_display_name_from_conf(os.path.join(os.path.dirname(resultados_dir), test)) for test in test_keys])
    plt.legend(title="Núcleo")

    png_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_teste_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_teste_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_cpu_comparativo_por_nucleo(resultados_dir, tests, cpu_aggregate, mostrar_intervalo_confianca=False):
    if not cpu_aggregate:
        return
    prefix = "-".join(sorted(tests))
    first = next(iter(cpu_aggregate.values()))

    cores_from_header = list(first.keys())
    cores = [re.search(r'\d+', c).group() for c in cores_from_header]

    x = np.arange(len(cores_from_header))
    width = 0.8 / len(tests)
    plt.figure(figsize=(10,6))

    y_max_total = 0.0
    all_bars_and_errs = []

    for i, test in enumerate(sorted(tests)):
        if test not in cpu_aggregate:
            continue

        test_dir = os.path.join(os.path.dirname(resultados_dir), test)
        test_display_name = get_test_display_name_from_conf(test_dir)
        cpu_dict = cpu_aggregate[test]
        values = [cpu_dict.get(core, (0,0))[0] for core in cores_from_header]
        err_values = [cpu_dict.get(core, (0,0))[1] for core in cores_from_header]

        y_max_local = max((v + e) for v, e in zip(values, err_values)) if values else 0.0
        y_max_total = max(y_max_total, y_max_local)

        bars = plt.bar(x + i*width, values, width, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label=test_display_name)
        all_bars_and_errs.append((bars, err_values))

    top = (y_max_total * 1.08) if y_max_total > 0 else 1.0
    label_offset = 0.005 * top   # distância do valor até o topo da barra

    for bars, err_values in all_bars_and_errs:
        for i, bar in enumerate(bars):
            e = err_values[i] if i < len(err_values) else 0.0
            y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
            plt.text(bar.get_x()+bar.get_width()/2, y, f"{bar.get_height():.2f}",
                     ha='center', va='bottom')

    plt.ylabel("Uso médio de CPU (%)")
    plt.xlabel("Núcleo")
    plt.title("Uso de CPU de cada teste por Núcleo")
    plt.xticks(x + width*(len(tests)-1)/2, [format_label(core) for core in cores])
    plt.legend()
    plt.ylim(bottom=0, top=top)

    png_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_nucleo_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-uso_de_cpu_por_nucleo_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_rodada(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    data = {}
    errors = {}
    labels_map = {}  # rodada -> label
    test_display_name = get_test_display_name_from_conf(test_dir)

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
                err = 1.96 * df_srv["porcentagem_pacotes_perdidos"].std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
                data[rodada] = float(m)
                errors[rodada] = float(err)
                labels_map[rodada] = "Perda (%)"
                continue  # Achou, passa pra próxima rodada

        # TCP cliente: retransmissoes
        if os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "retransmissoes" in df_cli.columns:
                n = len(df_cli)
                m = df_cli["retransmissoes"].mean()
                err = 1.96 * df_cli["retransmissoes"].std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
                data[rodada] = float(m)
                errors[rodada] = float(err)
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

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    y_max = max((_safe(v) + _safe(e)) for v, e in zip(values, err_values)) if values else 0.0
    top = (y_max * 1.08) if y_max > 0 else 1.0     # 8% de folga no topo
    label_offset = 0.005 * top                     # distância do valor até o topo da barra

    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)

    # Rótulos acima das barras
    for i, bar in enumerate(bars):
        e = _safe(err_values[i]) if i < len(err_values) else 0.0
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(
            bar.get_x() + bar.get_width()/2,
            y,
            f"{bar.get_height():.4f}",
            ha='center', va='bottom', fontsize=9
        )

    plt.ylabel(ylabel)
    plt.xlabel("Rodada")
    plt.title(f"{test_display_name} - {title_tipo} por rodada")
    plt.xticks(x, rounds_sorted_numbers)
    plt.ylim(bottom=0, top=top)

    png_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.png")
    svg_path = os.path.join(test_dir, f"{test_name}-perda_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_perda_comparativo_por_teste(resultados_dir, tests, perda_aggregate, mostrar_intervalo_confianca=False):
    prefix = "-".join(sorted(tests))
    tests_sorted = sorted(perda_aggregate.keys())
    x = np.arange(len(tests_sorted))

    values = [perda_aggregate[test][0] for test in tests_sorted]
    err_values = [perda_aggregate[test][1] for test in tests_sorted]

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    y_max = max((_safe(v) + _safe(e)) for v, e in zip(values, err_values)) if values else 0.0
    top = (y_max * 1.08) if y_max > 0 else 1.0   # 8% de folga no topo
    label_offset = 0.005 * top                   # distância do valor até o topo da barra

    plt.figure(figsize=(8,6))
    bars = plt.bar(x, values, width=0.5, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0)

    # Rótulos acima das barras
    for i, bar in enumerate(bars):
        e = _safe(err_values[i]) if i < len(err_values) else 0.0
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x()+bar.get_width()/2, y, f"{bar.get_height():.4f}",
                 ha='center', va='bottom')

    plt.ylabel("Perda (%)")
    plt.xlabel("Teste")
    plt.title("Perda Comparativo por Teste")
    plt.xticks(x, [get_test_display_name_from_conf(os.path.join(os.path.dirname(resultados_dir), test)) for test in tests_sorted])
    plt.ylim(bottom=0, top=top)

    png_path = os.path.join(resultados_dir, f"{prefix}-perda_barra_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-perda_barra_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_rodada(test_dir, test_name, mostrar_intervalo_confianca=False):
    rounds = get_round_dirs(test_dir)
    data_client = {}
    data_server = {}
    err_client = {}
    err_server = {}
    test_display_name = get_test_display_name_from_conf(test_dir)

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
            e_client  = 1.96 * df_client['bits_por_segundo'].std(ddof=1) / np.sqrt(n_client) if n_client > 1 else 0.0
            data_client[rodada] = float(m_client)
            err_client[rodada]  = float(e_client)

        # Servidor (em bps)
        if 'bits_por_segundo' in df_server.columns and len(df_server) > 0:
            n_server  = len(df_server)
            m_server  = df_server['bits_por_segundo'].mean()  # bps
            e_server  = 1.96 * df_server['bits_por_segundo'].std(ddof=1) / np.sqrt(n_server) if n_server > 1 else 0.0
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

    # Eixo X
    x = np.arange(len(rounds_sorted))
    rounds_sorted_numbers = [re.search(r'rodada_(\d+)', r).group(1) for r in rounds_sorted]

    width = 0.35
    plt.figure(figsize=(8, 6))
    bars1 = plt.bar(x - width/2, client_values, width, yerr=client_err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, yerr=server_err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Servidor")

    # Ajuste do topo para caber os rótulos
    y_max_cli = max((_safe(v) + _safe(e)) for v, e in zip(client_values, client_err_values)) if client_values else 0.0
    y_max_srv = max((_safe(v) + _safe(e)) for v, e in zip(server_values, server_err_values)) if server_values else 0.0
    y_max_total = max(y_max_cli, y_max_srv)
    top = (y_max_total * 1.08) if y_max_total > 0 else 1.0   # 8% de folga
    label_offset = 0.005 * top                               # distância do valor até o topo da barra
    plt.ylim(bottom=0, top=top)

    # Rótulos acima das barras
    for bar, raw_bps, err in zip(bars1, client_values_bps, client_err_values):
        y = bar.get_height() + (_safe(err) if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x() + bar.get_width()/2, y,
                 f"{format_value(raw_bps, fator):.2f}",
                 ha='center', va='bottom')

    for bar, raw_bps, err in zip(bars2, server_values_bps, server_err_values):
        y = bar.get_height() + (_safe(err) if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x() + bar.get_width()/2, y,
                 f"{format_value(raw_bps, fator):.2f}",
                 ha='center', va='bottom')

    # Eixos e título
    plt.ylabel(f"Vazão Média ({unidade})")
    plt.xlabel("Rodada")
    plt.title(f"{test_display_name} - Vazão média por rodada")
    plt.xticks(x, rounds_sorted_numbers)

    plt.legend()
    plt.tight_layout()

    png_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo_por_rodada.png")
    svg_path = os.path.join(test_dir, f"{test_name}-vazao_barra_comparativo_por_rodada.svg")
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_comparativo_por_teste(resultados_dir, tests, vazao_aggregate, mostrar_intervalo_confianca=False):
    prefix = "-".join(sorted(tests))
    tests_sorted = sorted(vazao_aggregate.keys())
    x = np.arange(len(tests_sorted))

    # Vetores em bps
    client_values_bps = [vazao_aggregate[test][0][0] for test in tests_sorted]
    server_values_bps = [vazao_aggregate[test][1][0] for test in tests_sorted]
    client_err_bps    = [vazao_aggregate[test][0][1] for test in tests_sorted]
    server_err_bps    = [vazao_aggregate[test][1][1] for test in tests_sorted]

    # Escala ótima com base no maior bps entre cliente/servidor
    max_bps = max(max(client_values_bps) if client_values_bps else 0.0,
                  max(server_values_bps) if server_values_bps else 0.0)
    unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

    # Normaliza para a escala encontrada
    client_values = [v / fator for v in client_values_bps]
    server_values = [v / fator for v in server_values_bps]
    client_err    = [e / fator for e in client_err_bps]
    server_err    = [e / fator for e in server_err_bps]

    width = 0.35
    plt.figure(figsize=(8,6))
    bars1 = plt.bar(x - width/2, client_values, width, yerr=client_err if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Cliente")
    bars2 = plt.bar(x + width/2, server_values, width, yerr=server_err if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Servidor")

    # Ajuste para que o topo se ajuste à barra e o valor de amplitude no topo dela
    y_max_client = max((_safe(v) + _safe(e) for v, e in zip(client_values, client_err)), default=0.0)
    y_max_server = max((_safe(v) + _safe(e) for v, e in zip(server_values, server_err)), default=0.0)
    y_max_total  = max(y_max_client, y_max_server)
    top = (y_max_total * 1.08) if y_max_total > 0 else 1.0   # 8% de folga no topo
    label_offset = 0.005 * top                               # distância do valor até o topo da barra
    plt.ylim(bottom=0, top=top)

    # Rótulos acima das barras (na mesma unidade do eixo)
    for bar, raw_bps, err in zip(bars1, client_values_bps, client_err):
        e = _safe(err)
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x()+bar.get_width()/2, y,
                 f"{format_value(raw_bps, fator):.2f}",
                 ha='center', va='bottom')

    for bar, raw_bps, err in zip(bars2, server_values_bps, server_err):
        e = _safe(err)
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(bar.get_x()+bar.get_width()/2, y,
                 f"{format_value(raw_bps, fator):.2f}",
                 ha='center', va='bottom')

    plt.ylabel(f"Vazão Média ({unidade})")
    plt.xlabel("Teste")
    plt.title("Vazão média por teste")
    plt.xticks(x, [get_test_display_name_from_conf(os.path.join(os.path.dirname(resultados_dir), test)) for test in tests_sorted])
    plt.legend()

    png_path = os.path.join(resultados_dir, f"{prefix}-vazao_barra_comparativo_por_teste.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-vazao_barra_comparativo_por_teste.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

def plot_vazao_servidor_comparativo(resultados_dir, tests, vazao_aggregate, mostrar_intervalo_confianca=False, mostrar_media=False):
    # Mantém apenas testes presentes no agregado e na mesma ordem do parâmetro 'tests'
    tests_sorted = [t for t in tests if t in vazao_aggregate]
    if not tests_sorted:
        print("Nenhum teste com dados de vazão no agregado.")
        return

    x = np.arange(len(tests_sorted))

    # Vetores em bps
    server_values_bps = [vazao_aggregate[test][1][0] for test in tests_sorted]
    server_err_bps    = [vazao_aggregate[test][1][1] for test in tests_sorted]

    # Encontra a maior escala a partir do maior valor em bps
    max_bps = max(server_values_bps) if server_values_bps else 0.0
    unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

    # Normaliza pela escala encontrada
    server_values = [v / fator for v in server_values_bps]
    server_err    = [e / fator for e in server_err_bps]

    # Média das barras
    media_barras = (np.mean(server_values) if server_values else 0.0)

    # Ajusta o topo para que caiba o rótulo
    y_max = max((_safe(v) + _safe(e)) for v, e in zip(server_values, server_err)) if server_values else 0.0
    top = (y_max * 1.08) if y_max > 0 else 1.0       # 8% de folga no topo
    label_offset = 0.005 * top                       # distância do valor até o topo da barra

    width = 0.5
    plt.figure(figsize=(8,6))
    ax = plt.gca()
    bars = plt.bar(x, server_values, width, yerr=server_err if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Servidor")

    # Linha de média das barras
    if mostrar_media and len(server_values) > 0:
        # Extremos horizontais cobrindo todas as barras
        x_start = (x[0] - width/2) if len(x) > 0 else -0.5
        x_end   = (x[-1] + width/2) if len(x) > 0 else 0.5
        ax.hlines(
            media_barras,
            x_start,
            x_end,
            colors='orange',
            linestyles='solid',
            linewidth=5,
            label="Média"
        )

    # Rótulos acima das barras
    for i, (bar, raw_bps) in enumerate(zip(bars, server_values_bps)):
        e = _safe(server_err[i]) if i < len(server_err) else 0.0
        y = bar.get_height() + (e if mostrar_intervalo_confianca else 0) + label_offset
        plt.text(
            bar.get_x() + bar.get_width()/2,
            y,
            f"{format_value(raw_bps, fator):.2f}",
            ha='center', va='bottom'
        )

    plt.ylabel(f"Vazão média do servidor ({unidade})")
    plt.xlabel("Teste")
    plt.title("Vazão do servidor por teste")
    plt.xticks(x, [get_test_display_name_from_conf(os.path.join(os.path.dirname(resultados_dir), test)) for test in tests_sorted])
    plt.ylim(bottom=0, top=top)
    plt.legend()

    prefix = "-".join(tests_sorted)
    png_path = os.path.join(resultados_dir, f"{prefix}-vazao_servidor_comparativo.png")
    svg_path = os.path.join(resultados_dir, f"{prefix}-vazao_servidor_comparativo.svg")
    plt.tight_layout()
    plt.savefig(png_path)
    plt.savefig(svg_path)
    plt.close()

########################################
# FUNÇÕES AGREGADAS – SÉRIES TEMPORAIS #
########################################
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
        # Obtém o diretório pai de resultados_dir
        test_dir = os.path.join(os.path.dirname(resultados_dir), test)
        test_display_name = get_test_display_name_from_conf(test_dir)
        tempo, perda = perda_temporal_agg[test]
        plt.plot(tempo, perda, label=test_display_name)
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

###########################################################
# GRÁFICO COMPARATIVO DE VAZÃO DO SERVIDOR COM REFERÊNCIA #
###########################################################
def plot_vazao_com_referencia(resultados_dir, tests, vazao_aggregate, ref_srv, ref_test, mostrar_intervalo_confianca=False):
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
    bars1 = plt.bar(x - width/2, ref_values, width, yerr=ref_errs if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Referência")
    bars2 = plt.bar(x + width/2, test_srv_values, width, yerr=test_srv_errs if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label="Teste")
    for bar in bars1:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    for bar in bars2:
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), format_throughput(bar.get_height()),
                 ha='center', va='bottom')
    plt.ylabel("Vazão média do servidor (Mbps)")
    plt.xlabel("Teste")
    plt.title("Vazão do servidor - Comparativo com Referência")
    plt.xticks(x, [get_test_display_name_from_conf(os.path.join(resultados_dir, test)) for test in tests_ordered])
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

#####################################################
# FUNÇÃO DE SUMARIZAÇÃO, GERAÇÃO DO MARKDOWN E MAIN #
#####################################################
def print_summarization(test_name, cpu_usage, vazao_cli_srv_formatada, unidade, perda, round_count):
    print(f"\nResumo para {test_name}:")
    print("\nUso de CPU por núcleo:")
    for core, usage in cpu_usage.items():
        print(f"    {format_label(core)}: {usage[0]:.2f}%")
    
    print("\nVazão:")
    print(f"{'Origem':<10}{'Vazão (' + unidade + ')':<15}")
    print(f"{'Cliente':<10}{vazao_cli_srv_formatada[0]:<15.4f}")
    print(f"{'Servidor':<10}{vazao_cli_srv_formatada[1]:<15.4f}")
    
    print("\nPerda (%):")
    print(f"{'Média':<10}{perda[0]:<15.4f}")

    print(f"\nNúmero de rodadas computadas: {round_count}\n")

def _compute_round_tables_for_test(resultados_dir, test_name, cpu_keys_sorted, fator_vazao, unidade_vazao):
    """
    Lê os arquivos por rodada do teste e retorna:
      - header_cols: cabeçalho "| Rodada | Cliente (...) | Servidor (...) | Perda (%) | CPU 0 (%) | ... |"
      - lines: linhas da tabela (uma por rodada)
    """
    test_dir = os.path.join(resultados_dir, test_name)
    rounds = get_round_dirs(test_dir)

    # Cabeçalho fixo para todas as tabelas por rodada (usa mesmas CPUs do resumo global)
    header_cols = ["Rodada", f"Cliente ({unidade_vazao})", f"Servidor ({unidade_vazao})", "Perda (%)"]
    for k in cpu_keys_sorted:
        idxm = re.search(r'(\d+)', k or "")
        idx = idxm.group(1) if idxm else k
        header_cols.append(f"CPU {idx} (%)")

    lines = []
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join([":---:"]*len(header_cols)) + "|")

    for rodada in rounds:
        rodada_path = os.path.join(test_dir, rodada)
        rodada_numero = re.search(r'rodada_(\d+)', rodada).group(1)

        # Vazão por rodada
        cli_bps = srv_bps = 0.0
        client_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_client.csv")
        server_file = os.path.join(rodada_path, f"{rodada}-{test_name}-iperf3_server.csv")
        if os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "bits_por_segundo" in df_cli.columns and len(df_cli) > 0:
                cli_bps = float(df_cli["bits_por_segundo"].mean())
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "bits_por_segundo" in df_srv.columns and len(df_srv) > 0:
                srv_bps = float(df_srv["bits_por_segundo"].mean())

        cli_v = f"{(cli_bps / fator_vazao):.2f}"
        srv_v = f"{(srv_bps / fator_vazao):.2f}"

        # Perda por rodada
        perda_val = ""
        if os.path.exists(server_file):
            df_srv = pd.read_csv(server_file)
            if "porcentagem_pacotes_perdidos" in df_srv.columns and len(df_srv) > 0:
                perda_val = f"{float(df_srv['porcentagem_pacotes_perdidos'].mean()):.4f}"
        if perda_val == "" and os.path.exists(client_file):
            df_cli = pd.read_csv(client_file)
            if "retransmissoes" in df_cli.columns and len(df_cli) > 0:
                perda_val = f"{float(df_cli['retransmissoes'].mean()):.4f}"

        # CPU por rodada
        cpu_vals = []
        mpstat_file = os.path.join(rodada_path, f"{rodada}-{test_name}-mpstat.csv")
        cpu_means = {}
        if os.path.exists(mpstat_file):
            df_mp = pd.read_csv(mpstat_file)
            for col in df_mp.columns:
                try:
                    cpu_means[col] = float(df_mp[col].mean())
                except Exception:
                    pass
        for k in cpu_keys_sorted:
            v = ""
            if k in cpu_means:
                v = f"{cpu_means[k]:.2f}"
            cpu_vals.append(v)

        lines.append("| " + " | ".join([rodada_numero, cli_v, srv_v, perda_val] + cpu_vals) + " |")

    return header_cols, lines

def _cpu_idx(k):
    m = re.search(r'(\d+)', k or "")
    return int(m.group(1)) if m else 10**9

def write_markdown_summary(resultados_dir, tests, cpu_aggregate, vazao_aggregate, perda_aggregate):
    # Determina a maior unidade de vazão entre todos os testes
    all_bps = []
    for t in tests:
        if t in vazao_aggregate:
            cli_bps = vazao_aggregate[t][0][0] if vazao_aggregate[t][0] else 0.0
            srv_bps = vazao_aggregate[t][1][0] if vazao_aggregate[t][1] else 0.0
            all_bps.extend([cli_bps, srv_bps])
    max_bps = max(all_bps) if all_bps else 0.0
    unidade, fator = choose_bps_scale(max_bps if max_bps > 0 else 1.0)

    # Descobre todos os núcleos de CPU (para colunas fixas em todas as tabelas)
    cpu_keys_set = set()
    for t in tests:
        if t in cpu_aggregate and cpu_aggregate[t]:
            cpu_keys_set.update(cpu_aggregate[t].keys())

    # Ordena as CPUs
    cpu_keys_sorted = sorted(cpu_keys_set, key=_cpu_idx)

    # Tabela com os resultados de todos os testes
    header_cols = ["Nome do teste",
                   f"Cliente ({unidade})",
                   f"Servidor ({unidade})",
                   "Perda (%)"]
    for k in cpu_keys_sorted:
        idxm = re.search(r'(\d+)', k or "")
        idx = idxm.group(1) if idxm else k
        header_cols.append(f"CPU {idx} (%)")

    # Linhas da tabela, sendo uma por teste, respeitando a ordem informada pelo usuário
    lines = []
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join([":---:"]*len(header_cols)) + "|")

    for t in tests:
        test_dir = os.path.join(resultados_dir, t)
        nome = get_test_display_name_from_conf(test_dir)

        # Vazão
        if t in vazao_aggregate:
            cli_bps = vazao_aggregate[t][0][0]
            srv_bps = vazao_aggregate[t][1][0]
            cli_val = f"{(cli_bps / fator):.2f}"
            srv_val = f"{(srv_bps / fator):.2f}"
        else:
            cli_val = ""
            srv_val = ""

        # Perda
        if t in perda_aggregate and perda_aggregate[t] is not None:
            perda_media = perda_aggregate[t][0]
            perda_val = f"{perda_media:.4f}"
        else:
            perda_val = ""

        cpu_vals = []
        for k in cpu_keys_sorted:
            v = ""
            if t in cpu_aggregate and cpu_aggregate[t]:
                mean_err = cpu_aggregate[t].get(k)
                if mean_err:
                    v = f"{mean_err[0]:.2f}"
            cpu_vals.append(v)

        lines.append("| " + " | ".join([nome, cli_val, srv_val, perda_val] + cpu_vals) + " |")

    # Gerando o arquvivo Markdown
    sumarizado_dir = os.path.join(resultados_dir, "sumarizado-" + "-".join(tests))
    prefix = "sumarizado-" + "-".join(tests)
    md_path = os.path.join(sumarizado_dir, f"{prefix}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        # Título e resumo global
        f.write("# Sumarização dos resultados\n\n")
        f.write("## Geral\n\n")
        f.write("Abaixo, está a tabela com a sumarização global dos testes:\n\n")
        f.write("\n".join(lines) + "\n\n")

        # Tabelas de cada teste
        if resultados_dir is None:
            # quando não informado, assume que o diretório pai de sumarizado-... é o diretório de resultados
            resultados_dir = os.path.dirname(sumarizado_dir)

        f.write("## Por teste\n\n")
        for t in tests:
            test_display_name = get_test_display_name_from_conf(os.path.join(resultados_dir, t))
            f.write(f"### {test_display_name}\n\n")
            f.write(f"Tabela com os dados de cada rodada para o teste \"{test_display_name}\".\n\n")
            _hdr, round_lines = _compute_round_tables_for_test(
                resultados_dir, t, cpu_keys_sorted, fator, unidade
            )
            f.write("\n".join(round_lines) + "\n\n")

    print(f"Arquivo Markdown gerado: {md_path}")

def main():
    parser = argparse.ArgumentParser(description="Sumariza experimento e gera gráficos comparativos.")
    parser.add_argument("-d", "--resultados", required=True,
                        help="Diretório de resultados (fonte dos dados).")
    parser.add_argument("-t", "--teste", action="append", required=True,
                        help="Nome do teste. Pode ser especificado múltiplas vezes.")
    parser.add_argument("-c", "--cpus", help="Lista de CPUs a serem consideradas, separadas por vírgula. Ex: 1,2")
    parser.add_argument("-r", "--referencia", help="Nome do teste de referência para comparar a vazão do servidor.")
    parser.add_argument("-i", "--intervalo-confianca", action="store_true",
                        help="Mostra as linhas do intervalo de confiança nos gráficos de barras.")
    parser.add_argument("-m", "--media", action="store_true",
                        help="Traça uma linha horizontal de média sobre cada grupo de barras nos gráficos.")
    args = parser.parse_args()

    resultados_dir = args.resultados
    tests = args.teste
    cpus = args.cpus.split(",") if args.cpus else None
    referencia = args.referencia
    mostrar_intervalo_confianca = args.intervalo_confianca
    mostrar_media = args.media

    cpu_aggregate = {}
    perda_aggregate = {}
    vazao_aggregate = {}
    perda_temporal_agg = {}

    for test in tests:
        test_dir = os.path.join(resultados_dir, test)
        if not os.path.isdir(test_dir):
            print(f"Aviso: Diretório do teste {test_dir} não encontrado.")
            continue

        test_display_name = get_test_display_name_from_conf(test_dir)
        print(f"\nProcessando {test_display_name} ...")
        overall_cpu_values, round_count = plot_cpu_usage_for_round(test_dir, test, mostrar_intervalo_confianca)
        cpu_overall = plot_cpu_usage_for_test(overall_cpu_values, test_dir, test, mostrar_intervalo_confianca)
        vazao_cli, vazao_srv, vazao_cli_srv_formatada, unidade = plot_vazao_barra_for_test(test_dir, test, mostrar_intervalo_confianca)
        perda_overall = plot_perda_barra_for_test(test_dir, test, mostrar_intervalo_confianca)
        
        plot_cpu_temporal_for_test(test_dir, test)
        plot_vazao_temporal_for_test(test_dir, test)
        plot_perda_temporal_for_test(test_dir, test)

        plot_cpu_comparativo_por_rodada(test_dir, test, mostrar_intervalo_confianca)
        plot_perda_comparativo_por_rodada(test_dir, test, mostrar_intervalo_confianca)
        plot_vazao_comparativo_por_rodada(test_dir, test, mostrar_intervalo_confianca)

        print_summarization(test_display_name, cpu_overall, vazao_cli_srv_formatada, unidade, perda_overall, round_count)

        cpu_aggregate[test] = cpu_overall
        perda_aggregate[test] = perda_overall
        vazao_aggregate[test] = (vazao_cli, vazao_srv)
        perda_temporal_agg[test] = aggregate_perda_temporal_for_test(test_dir, test)

    sumarizado_dir = os.path.join(resultados_dir, "sumarizado-" + "-".join(tests))
    if not os.path.exists(sumarizado_dir):
        os.makedirs(sumarizado_dir)

    plot_cpu_comparativo_por_teste(sumarizado_dir, tests, cpu_aggregate, mostrar_intervalo_confianca)
    plot_cpu_comparativo_por_nucleo(sumarizado_dir, tests, cpu_aggregate, mostrar_intervalo_confianca)
    plot_perda_comparativo_por_teste(sumarizado_dir, tests, perda_aggregate, mostrar_intervalo_confianca)
    plot_vazao_comparativo_por_teste(sumarizado_dir, tests, vazao_aggregate, mostrar_intervalo_confianca)
    plot_vazao_servidor_comparativo(sumarizado_dir, tests, vazao_aggregate, mostrar_intervalo_confianca, mostrar_media)

    agg_perda_temp = aggregate_all_perda_temporal(resultados_dir, tests)
    plot_perda_temporal_comparativo_por_teste(sumarizado_dir, tests, agg_perda_temp)

    if cpus:
        def plot_cpu_comparativo_por_teste_cpus(resultados_dir, tests, cpu_aggregate, cpus, mostrar_intervalo_confianca=False):
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
                bars = plt.bar(x + offset, values, width, yerr=err_values if mostrar_intervalo_confianca else None, capsize=5 if mostrar_intervalo_confianca else 0, label=f"CPU {cpu}")
                for i, bar in enumerate(bars):
                    plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{bar.get_height():.2f}",
                             ha='center', va='bottom')
            plt.ylabel("Uso médio de CPU (%)")
            plt.xlabel("Teste")
            plt.title("Uso de CPU por teste (CPUs Selecionadas)")
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
        plot_cpu_comparativo_por_teste_cpus(sumarizado_dir, tests, cpu_aggregate, cpus, mostrar_intervalo_confianca)

    if referencia:
        ref_test = referencia
        ref_dir = os.path.join(resultados_dir, ref_test)
        if not os.path.isdir(ref_dir):
            print(f"Aviso: Diretório do teste de referência {ref_dir} não encontrado.")
        else:
            print(f"\nProcessando teste de referência {format_label(ref_test)} ...")
            vazao_ref = plot_vazao_barra_for_test(ref_dir, ref_test, mostrar_intervalo_confianca)
            plot_vazao_com_referencia(sumarizado_dir, tests, vazao_aggregate, vazao_ref[1], ref_test, mostrar_intervalo_confianca)

    write_markdown_summary(resultados_dir, tests, cpu_aggregate, vazao_aggregate, perda_aggregate)

if __name__ == "__main__":
    main()