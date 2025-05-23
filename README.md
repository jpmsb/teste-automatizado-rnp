# Teste Automatizado

Este repositório contém _scripts_ que realizam um teste de vazão de forma padrão e automatizada, com o processamento de dados para a geração de gráficos.

Dessa forma:

- O _script_ [`executa-experimento`](scripts/executa-experimento) realiza a criação do cenário a partir de um arquivo `docker-compose.yml` e realiza os testes de vazão utilizando o `iperf`. Nesta rotina, também são verificados quais módulos do Python 3 estão faltando para que sejam instalados;

- O _script_ [`sumarizar-experimento`](scripts/sumarizar-experimento.py) realiza o processamento dos dados gerados pelo `iperf` e gera gráficos com os resultados.

## Pré-requisitos

É necessário possuir os seguintes módulos do Python 3 instalados:

- pandas
- matplotlib.pyplot
- numpy
- sys
- json
- csv
- re

### Instalação dos módulos

- openSUSE Tumbleweed
    ```bash
    sudo zypper install --no-recommends python311-pandas python311-matplotlib python311-numpy
    ```

- Debian/Ubuntu
    ```bash
    sudo apt install --no-install-recommends python3-pandas python3-matplotlib python3-numpy
    ```

## Uso

Primeiramente, clone o repositório:

```bash
git clone https://git.rnp.br/gci/dev/melhorias-monipe/teste-automatizado
```

Em seguida, entre no diretório `scripts`:

```bash
cd teste-automatizado/scripts
```

Abaixo, é demonstrado como utilizar as rotinas:

- `executa-experimento`

    ```bash
    ./executa-experimento -c <cpu cliente> -s <cpu servidor> -d <arquivo docker-compose.yml> -a <nome> -t <duração> -r <repetições> -b <banda máxima>
    ```

    Os argumentos suportados são listados abaixo:

    - [obrigatório] `-c`, `--nucleo-cliente`: núcleo de CPU onde o cliente do `iperf` será executado;

    - [obrigatório] `-s`, `--nucleo-servidor`: núcleo de CPU onde o servidor do `iperf` será executado;

    - [obrigatório] `-d`, `--docker-compose`: arquivo `docker-compose.yml` que contém a descrição do cenário;

    - [obrigatório] `-a`, `--apelido`: apelido do teste;

    - [opcional] `-t`, `--duracao`: tempo de execução, em segundos, do teste. Quando não informado, o valor padrão é 10 segundos;
    
    - [opcional] `-b`, `--banda-maxima`: banda máxima, informada no formato aceito pelo `iperf3`. Ex.: 1M, 1G, 10G. Quando não informado, o valor padrão é 10G;

    - [opcional] `-r`, `--rodadas`: quantidade de repetições do teste. Quando não informado, o valor padrão é 1.

    Exemplo de uso:

    ```bash
    ./executa-experimento -c 2 -s 1 -d ~/teste10Gbit/docker-compose.yml -a "cenario_1" -t 10 -r 5
    ```

    No exemplo acima:

    - O teste será executado com o cliente utilizando o núcleo 2 e o servidor utilizando o núcleo 1;

    - O cenário será criado a partir do arquivo `docker-compose.yml` localizado em `~/teste10Gbit/`;

    - O apelido do teste será `cenario_1`;

    - O teste terá duração de 10 segundos;

    - O teste será repetido 5 vezes.

    Abaixo, é mostrado como ficaria a estrutura de diretórios após a execução do teste:

    ```bash
    .
    │   ├── resultados
    │   ├── teste_1
    │   │   ├── rodada_1
    │   │   │   ├── rodada_1-teste_1-iperf3_client.csv
    │   │   │   ├── rodada_1-teste_1-iperf3_server.csv
    │   │   │   ├── rodada_1-teste_1-mpstat.csv
    │   │   │   └── rodada_1-teste_1-mpstat.log
    │   │   ├── rodada_2
    │   │   │   ├── rodada_2-teste_1-iperf3_client.csv
    │   │   │   ├── rodada_2-teste_1-iperf3_server.csv
    │   │   │   ├── rodada_2-teste_1-mpstat.csv
    │   │   │   └── rodada_2-teste_1-mpstat.log
    │   │   ├── rodada_3
    │   │   │   ├── rodada_3-teste_1-iperf3_client.csv
    │   │   │   ├── rodada_3-teste_1-iperf3_server.csv
    │   │   │   ├── rodada_3-teste_1-mpstat.csv
    │   │   │   └── rodada_3-teste_1-mpstat.log
    │   │   ├── rodada_4
    │   │   │   ├── rodada_4-teste_1-iperf3_client.csv
    │   │   │   ├── rodada_4-teste_1-iperf3_server.csv
    │   │   │   ├── rodada_4-teste_1-mpstat.csv
    │   │   │   └── rodada_4-teste_1-mpstat.log
    │   │   ├── rodada_5
    │   │   │   ├── rodada_5-teste_1-iperf3_client.csv
    │   │   │   ├── rodada_5-teste_1-iperf3_server.csv
    │   │   │   ├── rodada_5-teste_1-mpstat.csv
    │   │   │   └── rodada_5-teste_1-mpstat.log
    │   │   └── teste_1-experimento.log
    │   ├── teste_2
    │   │   ├── rodada_1
    │   │   │   ├── rodada_1-teste_2-iperf3_client.csv
    │   │   │   ├── rodada_1-teste_2-iperf3_server.csv
    │   │   │   ├── rodada_1-teste_2-mpstat.csv
    │   │   │   └── rodada_1-teste_2-mpstat.log
    │   │   ├── rodada_2
    │   │   │   ├── rodada_2-teste_2-iperf3_client.csv
    │   │   │   ├── rodada_2-teste_2-iperf3_server.csv
    │   │   │   ├── rodada_2-teste_2-mpstat.csv
    │   │   │   └── rodada_2-teste_2-mpstat.log
    │   │   ├── rodada_3
    │   │   │   ├── rodada_3-teste_2-iperf3_client.csv
    │   │   │   ├── rodada_3-teste_2-iperf3_server.csv
    │   │   │   ├── rodada_3-teste_2-mpstat.csv
    │   │   │   └── rodada_3-teste_2-mpstat.log
    │   │   ├── rodada_4
    │   │   │   ├── rodada_4-teste_2-iperf3_client.csv
    │   │   │   ├── rodada_4-teste_2-iperf3_server.csv
    │   │   │   ├── rodada_4-teste_2-mpstat.csv
    │   │   │   └── rodada_4-teste_2-mpstat.log
    │   │   ├── rodada_5
    │   │   │   ├── rodada_5-teste_2-iperf3_client.csv
    │   │   │   ├── rodada_5-teste_2-iperf3_server.csv
    │   │   │   ├── rodada_5-teste_2-mpstat.csv
    │   │   │   └── rodada_5-teste_2-mpstat.log
    │   │   └── teste_2-experimento.log
    │   └── teste_3
    │       ├── rodada_1
    │       │   ├── rodada_1-teste_3-iperf3_client.csv
    │       │   ├── rodada_1-teste_3-iperf3_server.csv
    │       │   ├── rodada_1-teste_3-mpstat.csv
    │       │   └── rodada_1-teste_3-mpstat.log
    │       ├── rodada_2
    │       │   ├── rodada_2-teste_3-iperf3_client.csv
    │       │   ├── rodada_2-teste_3-iperf3_server.csv
    │       │   ├── rodada_2-teste_3-mpstat.csv
    │       │   └── rodada_2-teste_3-mpstat.log
    │       ├── rodada_3
    │       │   ├── rodada_3-teste_3-iperf3_client.csv
    │       │   ├── rodada_3-teste_3-iperf3_server.csv
    │       │   ├── rodada_3-teste_3-mpstat.csv
    │       │   └── rodada_3-teste_3-mpstat.log
    │       ├── rodada_4
    │       │   ├── rodada_4-teste_3-iperf3_client.csv
    │       │   ├── rodada_4-teste_3-iperf3_server.csv
    │       │   ├── rodada_4-teste_3-mpstat.csv
    │       │   └── rodada_4-teste_3-mpstat.log
    │       ├── rodada_5
    │       │   ├── rodada_5-teste_3-iperf3_client.csv
    │       │   ├── rodada_5-teste_3-iperf3_server.csv
    │       │   ├── rodada_5-teste_3-mpstat.csv
    │       │   └── rodada_5-teste_3-mpstat.log
    ```

- `sumarizar-experimento`

    ```bash
    ./sumarizar-experimento.py <diretório de resultados> <apelido_teste_1> <apelido_teste_2> ... <apelido_teste_n>
    ```

    Os argumentos suportados são listados abaixo:

    - [obrigatório] `<diretório de resultados>`: diretório onde estão os arquivos de resultados dos testes. É neste diretório que os gráficos gerados serão salvos, de acordo com o contexto de cada um. Por exemplo, gráficos que contenham informação sobre uma rodada de um teste, serão salvos em um diretório com o nome da rodada;

    - [obrigatório] `<apelido_teste_1> <apelido_teste_2> ... <apelido_teste_n>`: apelidos dos testes que serão sumarizados. Estes apelidos são os mesmos informados no momento da execução do teste.

    Exemplo de uso:

    ```bash
    ./sumarizar-experimento.py /home/vagrant/scripts/resultados "teste_1" "teste_2" "teste_3"
    ```

    A saída no terminal será algo como:

    ```bash
    Processando Teste 1 ...

    Resumo para Teste 1:

    Uso de CPU por núcleo:
        CPU 0: 5.39%
        CPU 1: 52.44%
        CPU 2: 65.58%
        CPU 3: 0.61%

    Vazão:
    Origem    Vazão (Mbps)   
    Cliente   9891.86        
    Servidor  9787.17        

    Perda (%):
    Média     0.10           

    Processando Teste 2 ...

    Resumo para Teste 2:

    Uso de CPU por núcleo:
        CPU 0: 5.41%
        CPU 1: 52.29%
        CPU 2: 64.91%
        CPU 3: 0.45%

    Vazão:
    Origem    Vazão (Mbps)   
    Cliente   9817.41        
    Servidor  9747.93        

    Perda (%):
    Média     0.04           

    Processando Teste 3 ...

    Resumo para Teste 3:

    Uso de CPU por núcleo:
        CPU 0: 5.57%
        CPU 1: 52.09%
        CPU 2: 65.53%
        CPU 3: 0.57%

    Vazão:
    Origem    Vazão (Mbps)   
    Cliente   9890.62        
    Servidor  9774.49        

    Perda (%):
    Média     0.10
    ```

    São gerados gráficos nos formatos **png** e **svg**. Abaixo estão alguns exemplos:

    - Gráficos de barras:

        - Gráficos de uso de CPU:

            - Comparação geral dos testes:
                ![uso_cpu](resultados-exemplo/uso_de_cpu_barra_comparativo.png)

            - Comparação entre as rodadas rodada do teste 1:
                ![uso_cpu_teste_1](resultados-exemplo/teste_1/teste_1-uso_de_cpu_barra_comparativo.png)

            - Média das rodadas do teste 1:

                ![uso_cpu_teste_1](resultados-exemplo/teste_1/teste_1-uso_de_cpu_barra.png)

        - Gráficos de vazão:

            - Comparação geral dos testes:
                ![vazao](resultados-exemplo/vazao_barra_comparativo.png)

            - Comparação entre as rodadas do teste 1:
                ![vazao_teste_1](resultados-exemplo/teste_1/teste_1-vazao_barra_comparativo.png)

            - Média das rodadas do teste 1:
                ![vazao_teste_1](resultados-exemplo/teste_1/teste_1-vazao_barra.png)

        - Gráficos de perda:

            - Comparação geral dos testes:
                ![perda](resultados-exemplo/perda_barra_comparativo.png)

            - Comparação entre as rodadas do teste 1:
                ![perda_teste_1](resultados-exemplo/teste_1/teste_1-perda_barra_comparativo.png)

            - Média das rodadas do teste 1:
                ![perda_teste_1](resultados-exemplo/teste_1/teste_1-perda_barra.png)

    - Gráficos de série temporal:

        - Gráficos de uso de CPU:

            - Média das rodadas do teste 1:
                ![uso_cpu_teste_1](resultados-exemplo/teste_1/teste_1-CPU_temporal.png)

        - Gráficos de vazão:

            - Média das rodadas do teste 1:
                ![vazao_teste_1](resultados-exemplo/teste_1/teste_1-vazao_temporal.png)

        - Gráficos de perda:

            - Média das rodadas do teste 1:
                ![perda_teste_1](resultados-exemplo/teste_1/teste_1-perda_temporal.png)