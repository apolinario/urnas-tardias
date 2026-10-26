# Protocolo de reavaliação

Pré-registro da análise: define perguntas, medidas, controles e regras de relato **antes** de rodar a análise sobre a nova coleta. Qualquer desvio depois disso entra na seção [Desvios](#desvios), com data e motivo.

## 1. Perguntas

- **P1 (descritiva).** Quantos votos foram registrados depois das 17h de Brasília no 2º turno de 2026, e em quantas urnas?
- **P2 (causal).** Desses, quantos **não teriam ocorrido sem** a prorrogação do STF até as 19h (horário de Brasília)? Sem prorrogação, quem estava na fila às 17h ainda votava (regra da senha), então votos depois das 17h não são, por si, efeito da prorrogação.
- **P3 (consequência).** Qual o efeito máximo sobre a margem entre os candidatos?

Fora de escopo: atribuir votos a candidatos (o log não registra o voto), avaliar a legalidade da decisão, e medir votos **perdidos** por urnas que fecharam às 17h antes de saber da prorrogação.

## 2. O que já era conhecido antes deste protocolo

Para que ninguém confunda confirmação com descoberta:

- O resultado agregado do método original (7.352 urnas estendidas, 5.052 votos depois das 17h, 34.330 com corte às 17h) já havia sido visto e reproduzido a partir de `secoes.csv`.
- Uma amostra de 500 urnas (250 estendidas e 250 normais, semente 7) mostrou que, no 1º turno, essas mesmas urnas tiveram bem mais votos depois das 17h do que no 2º. Isso motivou o desenho abaixo e **não** é usado como evidência final.
- O fuso de cada município inferido pela hora de abertura bate com a regra do TSE (Res. 23.751/2026) nos casos conferidos (AC, AM, MT, MS, RO, RR, Fernando de Noronha).

Tudo o que for estimado abaixo sobre a coleta nova é confirmatório ou, quando dito, exploratório.

## 3. Dados

Log de cada urna (`logd.dat`) de **ambos os turnos**, para todas as seções com arquivo publicado, coletado com `crawl.py`. Por voto guardam-se: hora do voto, ociosidade da urna, tempo identificador→habilitação e habilitação→voto. Por urna: abertura, "Procedimento de encerramento confirmado", "Inicio do Encerramento", total de votos, votos biométricos e histograma em blocos de 30 min.

**Portões de qualidade (reportar todos, por UF):**

1. Cobertura: seções na configuração, sem arquivo (`aux 404`), sem log, com erro. Seções com `aux 404` não têm urna publicada e ficam fora; o número é relatado, não ignorado.
2. Seções com mais de um conjunto de arquivos (`n_hashes > 1`) e como foram tratadas (padrão: o último; sensibilidade: o que tiver mais votos).
3. Votos em datas diferentes de 04/10 e 25/10 (campo `fora`), indicando relógio errado.
4. Abertura fora de 07:30 a 08:30 de Brasília após a conversão de fuso.
5. Total de votos por urna contra o comparecimento publicado no boletim, quando disponível (verificação em amostra).

## 4. Definições operacionais

- **Fuso.** Padrão: moda da abertura por município (a regra do TSE fixa abertura às 8h de Brasília). Conferência independente: tabela fixa por município (AC +2; AM +1 salvo os 11 municípios do fuso do Acre; MT, MS, RO, RR +1; Fernando de Noronha −1). Discordâncias são listadas.
- **Corte** `c` = 17:00:00 de Brasília.
- **U (teto).** Votos computados com hora `≥ c`, em urnas do país, no 2º turno. Reproduz o número do método original. Inclui a fila legal, portanto **é um teto do efeito, nunca o efeito**.
- **Ociosidade** de um voto: tempo entre a urna ficar livre ("Aguardando digitação do identificador") e o mesário digitar o eleitor seguinte. Inclui ~10 s de digitação, então ociosidade longa significa mesa vazia.
- **L (piso).** Em cada urna, seja `k*` o primeiro voto com ociosidade maior que `g` segundos e cuja digitação do identificador ocorreu pelo menos 15 s depois do corte (`t_id − 15 s ≥ c`; 15 s é o tempo típico de digitação). `L` é o número de votos de `k*` em diante. Com a urna livre e ninguém na mesa, o eleitor atendido chegou depois do corte e não estava na fila. É um **piso**: não conta quem chegou depois do corte e entrou numa fila que ainda existia.
- **g** (limiar de ociosidade). Valor principal fixado a priori em **120 s**. Sensibilidade: 60, 300 e 600 s.

## 5. Estimadores

**E1. Intervalo model-free `[L, U]`.** Soma nacional e por UF. É o resultado principal: não depende de modelo, só das definições acima.

**E2. Controle negativo (placebo) no 1º turno.** O mesmo detector `L` aplicado ao 1º turno, onde não houve prorrogação e só a fila podia votar depois das 17h. Qualquer `L > 0` ali é falso positivo (ou descumprimento da regra) e mede a taxa de erro do detector. A taxa é `p = L₁ / N₁`, com `N` o número de urnas com algum voto depois do corte. O piso do 2º turno é reportado **líquido**: `L₂ − p × N₂`, com o bruto ao lado.

**E3. Estimativa calibrada (secundária, modelo).** Ajustar no 1º turno uma regressão de Poisson (pseudo-verossimilhança, que estima bem a média mesmo com superdispersão; a incerteza vem do bootstrap) para os votos depois do corte por urna, com covariáveis medidas **antes** das 17h (votos entre 16h e 17h, fração de tempo ocioso entre 16h30 e 17h, urna ocupada às 16h55, total de votos, modelo da urna, efeito fixo de UF). Predizer a fila esperada de cada urna no 2º turno e estimar `E3 = Σ (observado − predito)`. Validação do modelo: metade dos municípios do 1º turno (sorteio com a semente abaixo) fica de fora do ajuste, e compara-se o total observado com o predito nela, no total e por decil de predição. Se o erro agregado passar de 25%, E3 **não** é reportado como estimativa, só como exploratório. Como verificação secundária, o mesmo cálculo nas urnas do 2º turno que fecharam até 17h10 é mostrado, mas fecharam cedo justamente por não terem fila, então espera-se predição acima do observado e isso **não** reprova o modelo. A bootstrap de E3 refaz o ajuste em 200 réplicas (as demais usam 2.000).

**Incerteza.** Bootstrap por **município** (agrupa urnas que compartilham fila, local e mesários), 2.000 réplicas, semente 20261025, intervalo percentílico de 95%. O resultado principal e os totais por UF vêm com intervalo. As análises de sensibilidade da seção 7 mostram a estimativa pontual.

## 6. Consequência para o resultado (P3)

Cada voto atribuído à prorrogação altera a margem em no máximo 1 voto. Logo, para qualquer atribuição possível, `|Δmargem| ≤ U`. Reporta-se `U` contra a margem oficial do TSE (a ser conferida no portal; o valor do método original, 4.430.191, vem de fonte secundária) e o múltiplo `margem / U`. Esta conclusão é aritmética e vale sem hipótese sobre quem votou em quem.

## 7. Análises de sensibilidade (todas reportadas)

| Escolha | Variações |
|---|---|
| Limiar `g` | 60, 120 (principal), 300, 600 s |
| Corte | 17:00:00 (principal), 17:05, 17:15 |
| Classe "estendida" | fechamento depois de 17:15, 17:45 (principal), 18:00 |
| Fuso | moda da abertura (principal) × tabela fixa |
| Log | último conjunto (principal) × o de mais votos |
| Hora do voto | `t_voto` (principal) × início do atendimento (`t_voto − habilitação→voto − identificador→habilitação`) |
| Amostra | todas × sem urnas de abertura fora do portão 4 × sem Fernando de Noronha |
| Modelo da urna | todas × só o modelo mais comum |

## 8. Regras de relato (contra viés)

1. O intervalo `[L, U]` e o placebo são reportados **qualquer que seja o resultado**, inclusive se incomodarem a hipótese de quem escreve.
2. Não se escolhe o limiar, o corte nem a amostra olhando o resultado; as variações são todas mostradas.
3. Resultados exploratórios (por UF, por município, por modelo de urna) são marcados como tal e não sustentam a conclusão principal.
4. A conclusão é escrita em termos de intervalo e incerteza, sem adjetivos ("insignificante", "alarmante").
5. Código, versão do código (hash do commit), semente e checksum dos dados publicados junto com os números.

## 9. Ameaças à validade

- **Seleção.** Urnas que ficaram abertas até as 19h são as que souberam da decisão a tempo (ou tinham fila). Não são amostra aleatória; `U` e `L` valem para elas.
- **Contrafactual.** A prorrogação pode ter alterado o comportamento antes das 17h (quem sabia que haveria mais tempo pode ter chegado mais tarde). O desenho não separa isso.
- **Fila contaminada.** Se chegadas depois do corte entraram numa fila ainda existente, `L` as perde (por isso é piso).
- **Diferença entre turnos.** O 1º turno tem várias cédulas e é mais lento por voto. O placebo e o modelo E3 usam variáveis de taxa para reduzir, mas não eliminam, essa diferença.
- **Relógio.** Há urnas com hora errada; o portão 4 e a sensibilidade de fuso tratam disso.
- **Votos perdidos.** Urnas que fecharam às 17h sem saber da prorrogação não aparecem no log como votos faltantes. O efeito líquido real da decisão pode ter sinal diferente do medido aqui.

## 10. Reprodução

```sh
OUT_DIR=<pasta> RPS=25 python3 crawl.py     # coleta, retomável
python3 -m unittest test_parse              # testes do parser
python3 analise_reavaliacao.py <pasta>      # produz as tabelas deste protocolo
```

## Desvios

Nenhum até o momento.

### Esclarecimentos antes de rodar a análise

Feitos em 26/10/2026, depois do commit inicial deste protocolo e antes de qualquer análise sobre a coleta nova, ao detalhar os estimadores: (1) definição de `L` com o tempo de digitação de 15 s; (2) fórmula do piso líquido com `p = L₁ / N₁`; (3) Poisson no lugar de binomial negativa e validação por municípios retidos do 1º turno, porque as urnas do 2º turno que fecharam cedo são selecionadas pelo próprio desfecho; (4) intervalos só no resultado principal e nos totais por UF.

### Depuração do script

O `analise_reavaliacao.py` foi executado em 26/10/2026 sobre uma coleta **parcial** (3.571 seções do RJ e Roraima) apenas para depurar o código. Nenhuma definição, limiar ou critério deste protocolo foi alterado depois de ver esses números. Nessa amostra parcial a validação de E3 não passou no critério de 25%; o critério foi mantido e o resultado será reportado como o protocolo manda quando a coleta completa terminar.
