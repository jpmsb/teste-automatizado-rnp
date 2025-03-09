import psutil
import time
import argparse

def monitor_cpu_cores(cores, duration):
    """
    Monitora o uso da CPU em núcleos específicos por um tempo definido.

    Args:
        cores (list): Lista de índices dos núcleos para monitoramento.
        duration (int): Tempo total de monitoramento em segundos.
    """
    end_time = time.time() + duration

    while time.time() < end_time:
        # Obter o uso da CPU por núcleo (retorna porcentagens de uso de cada núcleo)
        cpu_percentages = psutil.cpu_percent(interval=1, percpu=True)

        # Filtrar apenas os núcleos informados
        core_usages = [cpu_percentages[core] for core in cores]

        # Formatar a saída
        output = ", ".join([f"{usage:.2f}%" for usage in core_usages])
        print(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitorar uso de CPU em núcleos específicos.")
    parser.add_argument("cores", type=int, nargs="+", help="Núcleos a serem monitorados, separados por espaço.")
    parser.add_argument("duration", type=int, help="Tempo limite em segundos para monitorar o uso de CPU.")
    args = parser.parse_args()

    # Validar núcleos fornecidos
    total_cores = psutil.cpu_count()
    invalid_cores = [core for core in args.cores if core < 0 or core >= total_cores]

    if invalid_cores:
        print(f"Erro: Os seguintes núcleos não são válidos: {invalid_cores}")
        print(f"Informe núcleos entre 0 e {total_cores - 1}.")
        exit(1)

    monitor_cpu_cores(args.cores, args.duration)