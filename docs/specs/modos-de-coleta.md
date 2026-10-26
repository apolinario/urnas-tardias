# Modos de coleta

Status: implementada. Governa `crawl.py` e o novo `base_dados.py`.

## Contexto

A coleta completa faz ~1 milhão de requisições e leva de 14 a 22 horas. Quem quer só reproduzir a análise não deveria ter que repeti-la, e quem quer auditar os dados deveria poder baixá-los de novo do TSE. A base (~1,8 GB em JSONL, ~480 MB comprimida) é grande demais para o histórico do git.

## Dentro do escopo

- `crawl.py` ganha três modos, escolhidos por flag: `retomar` (padrão, comportamento atual), `--refazer` e `--publicado`.
- `base_dados.py` empacota a pasta de coleta em `.jsonl.gz` por UF com um `MANIFESTO.json` (tamanho e sha256 de cada arquivo e do original) e baixa/verifica uma base publicada.
- O README descreve os modos e onde está a base.

## Fora do escopo

- Publicar o Release com os dados (passo manual depois que a coleta terminar).
- Mudar o formato das linhas do JSONL ou o parser.

## Critérios de aceitação

1. Sem flags, o comportamento é idêntico ao atual: reaproveita o que já está em `OUT_DIR` e baixa só o que falta.
2. `--refazer` não apaga nada: move `{uf}.jsonl` para `{uf}.jsonl.anterior` (sobrescrevendo um `.anterior` mais antigo só se `--refazer` for repetido) e baixa tudo do TSE.
3. `--publicado URL_OU_MANIFESTO` baixa cada `{uf}.jsonl.gz`, confere o sha256 do arquivo comprimido, descomprime, confere o sha256 do conteúdo e **falha sem gravar** se algum não bater. Depois segue como `retomar`.
4. `empacotar` e `--publicado` formam um ciclo: empacotar uma pasta e baixar o resultado (via `file://`) devolve arquivos idênticos byte a byte.
5. Os modos podem ser limitados a UFs (`crawl.py --refazer rj sp`).
6. O manifesto é entrada não confiável: nome fora de `[a-z]{2}.jsonl`, `gz` diferente de `nome.gz`, sha256 malformado ou conteúdo maior que o declarado abortam sem gravar fora da pasta.
7. Testes automatizados cobrem os critérios 2, 3, 4 e 6 sem rede.

## Rastreabilidade

- `PROTOCOLO.md`, seções 3 e 10 (checksum dos dados e comandos de reprodução).
- `README.md`, seções "Rodar" e "Arquivos".
