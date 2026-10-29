# urnas-tardias

Quantos votos entraram depois das 17h no 2º turno de 2026 (25/10), quando o STF estendeu a votação até as 19h.

![card](card.png)

## Resultado (sem o exterior)

| | |
|---|---|
| Urnas no país | 497.882 |
| Urnas estendidas (encerraram depois das 17h45) | 7.352 (1,48%) |
| Votos depois das 17h nessas urnas | 5.052 |
| Votos registrados nas urnas | 127.696.482 |
| Peso dos votos tardios | 0,004% |
| Vantagem de Lula sobre Flávio | 4.430.191 (votos tardios = 0,11%) |

| UF | Urnas estendidas | Votos depois das 17h |
|---|---|---|
| RJ | 3.301 (8,8%) | 1.966 |
| SP | 1.874 (1,8%) | 1.626 |
| BA | 1.014 (2,9%) | 842 |
| PE | 705 (3,3%) | 296 |
| PB | 312 (2,9%) | 140 |
| Demais | 146 | 182 |

### Outros horários de corte

| Urna estendida se encerrou depois de | Urnas | Votos depois das 17h | % da vantagem de Lula |
|---|---|---|---|
| 17h45 (padrão) | 7.352 (1,48%) | 5.052 | 0,11% |
| 17h30 | 7.606 (1,53%) | 5.139 | 0,12% |
| 17h15 | 9.079 (1,82%) | 5.621 | 0,13% |
| 17h (todas as urnas) | 497.882 (100%) | 34.330 | 0,77% |

Com corte às 17h entram todas as urnas, e a maior parte desses votos vem de eleitores que já estavam na fila às 17h, o que é permitido em qualquer eleição.

**Leitura correta dos números:** "votos depois das 17h" inclui a fila legal, então é um **teto** do que a prorrogação pode ter adicionado, não uma medida do efeito. O desenho para separar fila de chegadas novas, com controle no 1º turno e intervalos de incerteza, está em [PROTOCOLO.md](PROTOCOLO.md).

## Método

Os dados vêm do log de cada urna (`logd.dat`), publicado pelo TSE em `resultados.tse.jus.br`. Exemplo com a seção 0517 da zona 0009 do Rio de Janeiro (código do município 60011):

1. A lista de seções de cada UF está no arquivo de configuração:
   https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/config/rj/rj-p003221-cs.json
2. O arquivo auxiliar da seção traz o `hash` da pasta onde estão os arquivos da urna:
   https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados/rj/60011/0009/0517/p003221-rj-m60011-z0009-s0517-aux.json
3. O log fica em `dados/{uf}/{municipio}/{zona}/{secao}/{hash}/{arquivo -log.jez}`:
   https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados/rj/60011/0009/0517/55454d6e504a34786275774b4d6c55696b4b6132756255506e725333432d36544e357a69776b544f31656b3d/o03221rj6001100090517-log.jez

O `.jez` é um zip com o `logd.dat`, um texto em latin1 separado por tab, com os dois turnos. Trecho dessa urna:

```
25/10/2026 08:00:01	INFO	01781484	VOTA	Urna pronta para receber votos	D732412B4E99352D
25/10/2026 18:15:22	INFO	01781484	VOTA	O voto do eleitor foi computado	258C2ED24D7644FC
25/10/2026 19:00:45	INFO	01781484	VOTA	Procedimento de encerramento confirmado	2EC37A3B98BF6D60
```

Para cada seção, usamos só as linhas de 25/10/2026:

- **abertura**: evento "Urna pronta para receber votos"
- **encerramento**: evento "Procedimento de encerramento confirmado"
- **votos**: evento "O voto do eleitor foi computado"

Os horários do log são os do relógio local da urna. A votação abre às 8h de Brasília em todo o país, o que dá 6h no Acre, 7h na maior parte do Amazonas, em MT, MS, RO e RR, e 9h em Fernando de Noronha (Res. TSE 23.751/2026). O fuso de cada município é então a diferença mais comum entre a hora de abertura das suas urnas e as 8h, e tudo é convertido para o horário de Brasília.

A prorrogação do STF foi até as 19h **de Brasília** ("determino prorrogação por duas horas, até as 19h, horário de Brasília"), e os logs concordam: nenhuma urna do oeste fechou depois de 19:01:40 de Brasília, e as urnas de Noronha fecharam perto de 19h de Brasília (20h locais).

Uma urna é **estendida** se encerrou depois das 17h45 de Brasília. Nelas, contam-se os votos computados depois das 17h. O exterior (`ZZ`) fica de fora porque lá a votação segue a hora local de cada país.

Cobertura: 499.248 seções no arquivo de configuração do TSE; 72 sem log (70 no exterior).

## Rodar

```sh
uv run python/crawl.py          # todas as UFs, ou: uv run python/crawl.py rj sp
python3 python/analisa.py       # gera secoes.csv, municipios.csv, app/assets/card.json e app/assets/votos.json
```

São ~1 milhão de requisições e a coleta leva de 14 a 22 horas, então há três modos, à escolha de quem roda:

| Modo | Comando | O que faz |
|---|---|---|
| retomar (padrão) | `python/crawl.py` | reaproveita o que já está em `OUT_DIR` e baixa só o que falta |
| refazer | `python/crawl.py --refazer [rj sp]` | baixa tudo de novo do TSE; o arquivo antigo vira `{uf}.jsonl.anterior`, nada é apagado |
| publicado | `python/crawl.py --publicado URL_DO_MANIFESTO` | baixa a base já coletada (`.jsonl.gz` por UF), confere o sha256 do arquivo e do conteúdo, e depois completa o que faltar |

Para deixar rodando sem supervisão (por exemplo à noite), use `OUT_DIR=/pasta bash python/coletar.sh [--refazer] [ufs]`: ele repete o crawler até uma passada terminar sem falhas de rede, servidor ou disco (espera um disco externo voltar, se desconectar) e mantém o Mac acordado com `caffeinate`. O `--refazer` só vale na primeira passada. O crawler sai com código 3 se sobrou alguma seção com falha, e o limitador volta a subir a taxa sozinho depois de um período sem reclamações do servidor.

Quem coleta pode publicar a base com `python/crawl.py --empacotar DESTINO`, que gera os `.jsonl.gz` e o `MANIFESTO.json` com tamanho e sha256. A base (~1,8 GB, ~480 MB comprimida) não vai no histórico do git: fica num Release, e o manifesto aponta para ela. Uma UF que já existe na pasta é mantida em `--publicado`.

O crawler limita a taxa (`RPS`, padrão 10 req/s; cai sozinho se o servidor reclamar) e retoma de onde parou. Pasta de saída em `OUT_DIR`. Cada linha guarda, para os dois turnos, a abertura, o fechamento, o total de votos e, por voto a partir das 14h locais, a hora e a ociosidade da urna. Testes: `python3 -m unittest discover -s python/tests -t python`.

### App (Expo)

`app/` mostra o card acima como app (web, iOS e Android), com seleção de estado e município e a opção de ver os votos até as 17h, depois das 17h ou o total. Os números vêm de `app/assets/card.json` e `app/assets/votos.json` (votos por município), que o `analisa.py` grava junto com os CSVs; a vantagem de Lula é lida do resultado oficial no TSE.

```sh
cd app
npm install
npx expo start           # escaneie o QR code com o Expo Go, ou tecle w para abrir no navegador
```

## Arquivos

- `secoes.csv`: uma linha por urna (fuso, abertura, encerramento, último voto, votos depois das 17h e das 17h20, total de votos, classe)
- `municipios.csv`: municípios com urnas estendidas
- `python/`: scripts de coleta (`crawl.py`, `coletar.sh`, `base_dados.py`), de análise (`analisa.py`, `analise_reavaliacao.py`) e seus testes (`tests/`)
- `python/base_dados.py`: empacota e baixa a base com conferência de sha256
- `PROTOCOLO.md`: protocolo de reavaliação (perguntas, estimadores, controles e regras de relato)
