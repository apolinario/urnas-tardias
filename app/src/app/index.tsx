import { createContext, useContext, useMemo, useState } from "react";
import {
  FlatList,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useColorScheme,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

// Gerados por ../analisa.py a partir dos logs das urnas baixados por ../crawl.py.
import card from "../../assets/card.json";
import votosJson from "../../assets/votos.json";

const VERDE = "#1ABC9C";
const LIMAO = "#A3D911";

const CLARO = {
  topo: VERDE,
  fundo: "#FFFFFF",
  texto: "#2C3E50",
  suave: "#5D6D7E",
  linha: "#E3E6E8",
  realce: "#16876F",
  fila: "#AEB6BF",
  segmentos: "#EEF1F2",
  rodape: "#2C3E50",
  rodapeLinha: "#46586A",
};

const ESCURO: typeof CLARO = {
  topo: "#128C74",
  fundo: "#17202A",
  texto: "#ECF0F1",
  suave: "#AEB6BF",
  linha: "#2C3A47",
  realce: VERDE,
  fila: "#5D6D7E",
  segmentos: "#212F3C",
  rodape: "#0F161D",
  rodapeLinha: "#2C3A47",
};

type Cores = typeof CLARO;

const Tema = createContext({ c: CLARO, s: criaEstilos(CLARO) });
const useTema = () => useContext(Tema);
const REPO = "github.com/leobragatti/urnas-tardias";
const DADOS = "https://drive.proton.me/urls/JA1QGKHMXC#o63Kx0NBdjaN";

const ESTADOS: Record<string, string> = {
  AC: "Acre",
  AL: "Alagoas",
  AM: "Amazonas",
  AP: "Amapá",
  BA: "Bahia",
  CE: "Ceará",
  DF: "Distrito Federal",
  ES: "Espírito Santo",
  GO: "Goiás",
  MA: "Maranhão",
  MG: "Minas Gerais",
  MS: "Mato Grosso do Sul",
  MT: "Mato Grosso",
  PA: "Pará",
  PB: "Paraíba",
  PE: "Pernambuco",
  PI: "Piauí",
  PR: "Paraná",
  RJ: "Rio de Janeiro",
  RN: "Rio Grande do Norte",
  RO: "Rondônia",
  RR: "Roraima",
  RS: "Rio Grande do Sul",
  SC: "Santa Catarina",
  SE: "Sergipe",
  SP: "São Paulo",
  TO: "Tocantins",
};

// [municipio, urnas, estendidas, votos até 17h, votos depois das 17h, votos depois das 17h nas estendidas]
type Mun = [string, number, number, number, number, number];
const VOTOS = votosJson as unknown as Record<string, Record<string, Mun>>;

type Recorte = {
  urnas: number;
  estendidas: number;
  ate17: number;
  depois17: number;
  depois17Est: number;
};

function soma(linhas: Mun[]): Recorte {
  const r = { urnas: 0, estendidas: 0, ate17: 0, depois17: 0, depois17Est: 0 };
  for (const [, u, e, a, d, de] of linhas) {
    r.urnas += u;
    r.estendidas += e;
    r.ate17 += a;
    r.depois17 += d;
    r.depois17Est += de;
  }
  return r;
}

const BRASIL = soma(Object.values(VOTOS).flatMap((ms) => Object.values(ms)));

const JANELAS = [
  { id: "ate17", nome: "Até 17h", legenda: "votos computados até as 17h" },
  {
    id: "depois17",
    nome: "Depois das 17h",
    legenda: "votos computados depois das 17h, em todas as urnas",
  },
  { id: "total", nome: "Total", legenda: "votos registrados nas urnas" },
] as const;
type Janela = (typeof JANELAS)[number]["id"];

function int(n: number) {
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function pct(parte: number, todo: number, casas: number) {
  return todo
    ? `${((100 * parte) / todo).toFixed(casas).replace(".", ",")}%`
    : "–";
}

// Ignora acentos e caixa: "sao paulo" encontra "SÃO PAULO".
function normaliza(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

type Opcao = { id: string; nome: string };

function Seletor({
  rotulo,
  valor,
  opcoes,
  onEscolhe,
  desativado,
}: {
  rotulo: string;
  valor: string;
  opcoes: Opcao[];
  onEscolhe: (id: string) => void;
  desativado?: boolean;
}) {
  const { c, s } = useTema();
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState("");
  const { top, bottom } = useSafeAreaInsets();
  const lista = useMemo(() => {
    const q = normaliza(busca.trim());
    return q ? opcoes.filter((o) => normaliza(o.nome).includes(q)) : opcoes;
  }, [opcoes, busca]);

  function escolhe(id: string) {
    onEscolhe(id);
    setAberto(false);
    setBusca("");
  }

  return (
    <>
      <Pressable
        disabled={desativado}
        onPress={() => setAberto(true)}
        style={({ pressed }) => [
          s.seletor,
          { opacity: desativado ? 0.45 : pressed ? 0.7 : 1 },
        ]}
      >
        <Text style={s.seletorRotulo}>{rotulo}</Text>
        <Text style={s.seletorValor} numberOfLines={1}>
          {valor} ▾
        </Text>
      </Pressable>
      <Modal
        visible={aberto}
        animationType="slide"
        onRequestClose={() => setAberto(false)}
      >
        <View
          style={[s.modal, { paddingTop: top + 12, paddingBottom: bottom }]}
        >
          <View style={s.modalTopo}>
            <Text style={s.modalTitulo}>{rotulo}</Text>
            <Pressable onPress={() => setAberto(false)} hitSlop={12}>
              <Text style={s.fechar}>Fechar</Text>
            </Pressable>
          </View>
          <TextInput
            value={busca}
            onChangeText={setBusca}
            placeholder="Buscar"
            placeholderTextColor={c.suave}
            autoCorrect={false}
            clearButtonMode="while-editing"
            style={s.busca}
          />
          <FlatList
            data={lista}
            keyExtractor={(o) => o.id}
            keyboardShouldPersistTaps="handled"
            renderItem={({ item }) => (
              <Pressable
                onPress={() => escolhe(item.id)}
                style={({ pressed }) => [
                  s.opcao,
                  pressed && { backgroundColor: c.linha },
                ]}
              >
                <Text
                  style={[
                    s.opcaoTexto,
                    item.nome === valor && {
                      color: c.realce,
                      fontFamily: "Lato_700Bold",
                    },
                  ]}
                >
                  {item.nome}
                </Text>
              </Pressable>
            )}
          />
        </View>
      </Modal>
    </>
  );
}

function Linha({
  rotulo,
  sub,
  valor,
  extra,
  forte,
  ultima,
}: {
  rotulo: string;
  sub?: string;
  valor: string;
  extra?: string;
  forte?: boolean;
  ultima?: boolean;
}) {
  const { c, s } = useTema();
  return (
    <View style={[s.linha, !ultima && s.divisa]}>
      <View style={s.rotulos}>
        <Text style={[s.rotulo, forte && s.rotuloForte]}>{rotulo}</Text>
        {sub && <Text style={s.sub}>{sub}</Text>}
      </View>
      <Text style={[s.valor, forte && { color: c.realce }]}>
        {valor}
        {extra && <Text style={s.extra}> {extra}</Text>}
      </Text>
    </View>
  );
}

function Barra({
  rotulo,
  valor,
  fracao,
  cor,
}: {
  rotulo: string;
  valor: number;
  fracao: number;
  cor: string;
}) {
  const { s } = useTema();
  return (
    <View style={s.barraBloco}>
      <View style={s.barraTopo}>
        <Text style={s.barraRotulo}>{rotulo}</Text>
        <Text style={s.barraValor}>{int(valor)}</Text>
      </View>
      <View
        style={[s.barra, { width: `${100 * fracao}%`, backgroundColor: cor }]}
      />
    </View>
  );
}

// Separa os votos depois das 17h entre a fila das 17h e a prorrogação. No rodapé,
// que tem fundo escuro nos dois temas, usa cores claras e compara com a vantagem.
function Divisao({
  fila,
  prorrogacao,
  vantagem,
}: {
  fila: number;
  prorrogacao: number;
  vantagem?: number;
}) {
  const { c, s } = useTema();
  const rodape = vantagem !== undefined;
  const todo = fila + prorrogacao;
  const corProrrogacao = rodape ? LIMAO : c.realce;
  const partes = [
    {
      cor: rodape ? "#7F8C8D" : c.fila,
      valor: fila,
      titulo: "Fila das 17h",
      texto:
        "Urnas que fecharam no horário normal. São eleitores que já estavam na fila às 17h, o que é permitido em qualquer eleição.",
    },
    {
      cor: corProrrogacao,
      valor: prorrogacao,
      titulo: "Prorrogação",
      texto:
        "Urnas estendidas, que fecharam depois das 17h45 por causa da decisão do STF.",
    },
  ];
  return (
    <View style={s.divisao}>
      <View
        style={[s.divisaoBarra, rodape && { backgroundColor: c.rodapeLinha }]}
      >
        {partes.map(
          (p) =>
            p.valor > 0 && (
              <View
                key={p.titulo}
                style={{ flex: p.valor, minWidth: 4, backgroundColor: p.cor }}
              />
            ),
        )}
      </View>
      {partes.map((p) => (
        <View key={p.titulo} style={s.parte}>
          <View style={[s.ponto, { backgroundColor: p.cor }]} />
          <View style={s.rotulos}>
            <Text style={[s.parteTitulo, rodape && s.textoRodape]}>
              {p.titulo}
            </Text>
            <Text style={[s.sub, rodape && s.subRodape]}>{p.texto}</Text>
          </View>
          <View style={s.parteNumeros}>
            <Text
              style={[
                s.parteValor,
                rodape && s.textoRodape,
                p.cor === corProrrogacao && { color: corProrrogacao },
              ]}
            >
              {int(p.valor)}
            </Text>
            <Text style={[s.sub, rodape && s.subRodape]}>
              {rodape
                ? `${pct(p.valor, vantagem, 2)} da vantagem`
                : pct(p.valor, todo, 0)}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

export default function Card() {
  const sistema = useColorScheme();
  const [escolhido, setEscolhido] = useState<"claro" | "escuro">();
  const nome = escolhido ?? (sistema === "dark" ? "escuro" : "claro");
  const tema = useMemo(() => {
    const c = nome === "escuro" ? ESCURO : CLARO;
    return { c, s: criaEstilos(c) };
  }, [nome]);
  return (
    <Tema.Provider value={tema}>
      <Conteudo
        tema={nome}
        alterna={() => setEscolhido(nome === "escuro" ? "claro" : "escuro")}
      />
    </Tema.Provider>
  );
}

function Conteudo({
  tema,
  alterna,
}: {
  tema: "claro" | "escuro";
  alterna: () => void;
}) {
  const { c, s } = useTema();
  const { top, bottom } = useSafeAreaInsets();
  const [uf, setUf] = useState<string>();
  const [mun, setMun] = useState<string>();
  const [janela, setJanela] = useState<Janela>("depois17");

  const estados = useMemo(
    () => [
      { id: "", nome: "Brasil" },
      ...Object.keys(VOTOS).map((id) => ({ id, nome: ESTADOS[id] ?? id })),
    ],
    [],
  );
  const municipios = useMemo(
    () => [
      { id: "", nome: "Todos" },
      ...Object.entries(uf ? VOTOS[uf] : {}).map(([id, l]) => ({
        id,
        nome: l[0],
      })),
    ],
    [uf],
  );

  const r = useMemo(() => {
    if (uf && mun) return soma([VOTOS[uf][mun]]);
    return soma(
      Object.entries(VOTOS).flatMap(([u, ms]) =>
        !uf || u === uf ? Object.values(ms) : [],
      ),
    );
  }, [uf, mun]);

  const lugar =
    uf && mun ? `${VOTOS[uf][mun][0]} (${uf})` : uf ? ESTADOS[uf] : "Brasil";
  const total = r.ate17 + r.depois17;
  const valor = { ate17: r.ate17, depois17: r.depois17, total }[janela];
  const info = JANELAS.find((j) => j.id === janela)!;

  return (
    <View style={{ flex: 1, backgroundColor: c.rodape }}>
      <ScrollView contentContainerStyle={{ paddingBottom: bottom + 88 }}>
        <View style={[s.topo, { paddingTop: top + 40 }]}>
          <View style={s.coluna}>
            <Text style={s.titulo}>
              QUANTOS VOTOS ENTRARAM DEPOIS DAS 17H NA PRORROGAÇÃO?
            </Text>
            <Text style={s.subtitulo}>
              O STF estendeu a votação até as 19h, mas a ordem chegou quando a
              maioria das urnas já tinha fechado.
            </Text>
          </View>
        </View>

        <View style={s.meio}>
          <View style={s.coluna}>
            <View style={s.filtros}>
              <View style={s.seletores}>
                <Seletor
                  rotulo="Estado"
                  valor={uf ? ESTADOS[uf] : "Brasil"}
                  opcoes={estados}
                  onEscolhe={(id) => {
                    setUf(id || undefined);
                    setMun(undefined);
                  }}
                />
                <Seletor
                  rotulo="Município"
                  valor={uf && mun ? VOTOS[uf][mun][0] : "Todos"}
                  opcoes={municipios}
                  onEscolhe={(id) => setMun(id || undefined)}
                  desativado={!uf}
                />
              </View>
              <View style={s.segmentos}>
                {JANELAS.map((j) => (
                  <Pressable
                    key={j.id}
                    onPress={() => setJanela(j.id)}
                    style={[s.segmento, janela === j.id && s.segmentoAtivo]}
                  >
                    <Text
                      style={[
                        s.segmentoTexto,
                        janela === j.id && s.segmentoTextoAtivo,
                      ]}
                    >
                      {j.nome}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>

            <View style={[s.destaque, s.divisa]}>
              <Text
                style={[
                  s.destaqueNumero,
                  janela === "depois17" && { color: c.texto },
                ]}
              >
                {int(valor)}
              </Text>
              <Text style={s.destaqueLegenda}>
                {info.legenda} · {lugar}
                {janela !== "total" &&
                  ` · ${pct(valor, total, janela === "ate17" ? 2 : 3)} do total`}
              </Text>
              {janela === "depois17" && (
                <Divisao
                  fila={r.depois17 - r.depois17Est}
                  prorrogacao={r.depois17Est}
                />
              )}
            </View>

            <Linha
              rotulo={uf ? "Urnas" : "Urnas no país"}
              valor={int(r.urnas)}
            />
            <Linha
              rotulo="Urnas estendidas"
              sub="fecharam depois das 17h45"
              valor={int(r.estendidas)}
              extra={pct(r.estendidas, r.urnas, 2)}
              forte
            />
            <Linha
              rotulo="Votos depois das 17h nas urnas estendidas"
              valor={int(r.depois17Est)}
              forte
            />
            <Linha rotulo="Votos registrados nas urnas" valor={int(total)} />
            <Linha
              rotulo="Peso dos votos tardios"
              valor={pct(r.depois17Est, total, 3)}
              ultima
            />
          </View>
        </View>

        <View style={s.rodape}>
          <View style={s.coluna}>
            <Text style={s.manchete}>
              VOTOS TARDIOS ={" "}
              <Text style={{ color: LIMAO }}>
                {pct(card.votos_apos_17h, card.vantagem, 2)}
              </Text>{" "}
              DA VANTAGEM DE LULA
            </Text>
            <Barra
              rotulo="Vantagem de Lula sobre Flávio"
              valor={card.vantagem}
              fracao={1}
              cor={VERDE}
            />
            <View style={s.barraTopo}>
              <Text style={s.barraRotulo}>Votos depois das 17h</Text>
              <Text style={s.barraValor}>{int(BRASIL.depois17)}</Text>
            </View>
            <Divisao
              fila={BRASIL.depois17 - BRASIL.depois17Est}
              prorrogacao={BRASIL.depois17Est}
              vantagem={card.vantagem}
            />
            <View style={s.fonte}>
              <Text style={s.fonteTitulo}>Fonte: TSE</Text>
              <Text style={s.fonteTexto}>
                Logs das 499 mil urnas no site de resultados. Urna estendida =
                encerrou depois das 17h45 (horário de Brasília); contados só os
                votos depois das 17h. Exclui o exterior. Os votos depois das 17h
                em urnas que não foram estendidas são de eleitores que já
                estavam na fila às 17h.
              </Text>
              <Text style={s.fonteTexto}>
                Arquivos coletados:{" "}
                <Text
                  style={s.linkDiscreto}
                  onPress={() => Linking.openURL(DADOS)}
                >
                  baixar do Proton Drive
                </Text>
              </Text>
              <Text
                style={s.link}
                onPress={() => Linking.openURL(`https://${REPO}`)}
              >
                {REPO}
              </Text>
              <Text style={s.fonteTexto}>
                Inspirado no projeto feito pelo{" "}
                <Text
                  style={s.link}
                  onPress={() =>
                    Linking.openURL(
                      `https://${REPO.replace("leobragatti", "apolinario")}`,
                    )
                  }
                >
                  Apolinario
                </Text>
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
      <Pressable
        onPress={alterna}
        accessibilityRole="button"
        accessibilityLabel={`Mudar para o tema ${tema === "escuro" ? "claro" : "escuro"}`}
        style={({ pressed }) => [
          s.fab,
          { bottom: bottom + 20, transform: [{ scale: pressed ? 0.94 : 1 }] },
        ]}
      >
        {/* \uFE0E pede o símbolo em texto, não o emoji colorido do iOS */}
        <Text style={s.fabIcone}>
          {tema === "escuro" ? "\u2600\uFE0E" : "\u263E\uFE0E"}
        </Text>
      </Pressable>
    </View>
  );
}

function criaEstilos(c: Cores) {
  return StyleSheet.create({
    coluna: {
      width: "100%",
      maxWidth: 560,
      alignSelf: "center",
      paddingHorizontal: 24,
    },

    topo: { backgroundColor: c.topo, paddingBottom: 36 },
    titulo: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 30,
      lineHeight: 34,
      color: "#FFFFFF",
      textAlign: "center",
    },
    subtitulo: {
      fontFamily: "Lato_400Regular",
      fontSize: 16,
      lineHeight: 22,
      color: "#FFFFFF",
      textAlign: "center",
      marginTop: 14,
    },

    meio: { backgroundColor: c.fundo, paddingVertical: 8 },
    filtros: {
      paddingTop: 16,
      paddingBottom: 18,
      gap: 12,
      borderBottomWidth: 1,
      borderBottomColor: c.linha,
    },
    seletores: { flexDirection: "row", gap: 10 },
    seletor: {
      flex: 1,
      borderWidth: 1,
      borderColor: c.linha,
      borderRadius: 10,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },
    seletorRotulo: {
      fontFamily: "Lato_400Regular",
      fontSize: 12,
      color: c.suave,
    },
    seletorValor: {
      fontFamily: "Lato_700Bold",
      fontSize: 15,
      color: c.texto,
      marginTop: 2,
    },
    segmentos: {
      flexDirection: "row",
      backgroundColor: c.segmentos,
      borderRadius: 10,
      padding: 3,
    },
    segmento: {
      flex: 1,
      borderRadius: 8,
      paddingVertical: 8,
      alignItems: "center",
    },
    segmentoAtivo: { backgroundColor: VERDE },
    segmentoTexto: { fontFamily: "Lato_700Bold", fontSize: 14, color: c.suave },
    segmentoTextoAtivo: { color: "#FFFFFF" },
    destaque: { paddingVertical: 18, gap: 4 },
    destaqueNumero: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 40,
      color: c.realce,
      fontVariant: ["tabular-nums"],
    },
    destaqueLegenda: {
      fontFamily: "Lato_400Regular",
      fontSize: 14,
      lineHeight: 20,
      color: c.suave,
    },
    divisao: { marginTop: 14, gap: 14 },
    divisaoBarra: {
      flexDirection: "row",
      height: 14,
      borderRadius: 7,
      overflow: "hidden",
      gap: 2,
      backgroundColor: c.linha,
    },
    parte: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
    ponto: { width: 12, height: 12, borderRadius: 6, marginTop: 4 },
    parteTitulo: { fontFamily: "Lato_700Bold", fontSize: 15, color: c.texto },
    parteNumeros: { alignItems: "flex-end" },
    parteValor: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 20,
      color: c.texto,
      fontVariant: ["tabular-nums"],
    },

    modal: { flex: 1, backgroundColor: c.fundo, paddingHorizontal: 16 },
    modalTopo: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 12,
    },
    modalTitulo: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 20,
      color: c.texto,
    },
    fechar: { fontFamily: "Lato_700Bold", fontSize: 16, color: c.realce },
    busca: {
      borderWidth: 1,
      borderColor: c.linha,
      borderRadius: 10,
      paddingHorizontal: 12,
      paddingVertical: 10,
      fontSize: 16,
      color: c.texto,
      marginBottom: 8,
    },
    opcao: {
      paddingVertical: 14,
      paddingHorizontal: 4,
      borderBottomWidth: 1,
      borderBottomColor: c.linha,
    },
    opcaoTexto: { fontFamily: "Lato_400Regular", fontSize: 16, color: c.texto },

    linha: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      paddingVertical: 18,
    },
    divisa: { borderBottomWidth: 1, borderBottomColor: c.linha },
    rotulos: { flex: 1 },
    rotulo: { fontFamily: "Lato_400Regular", fontSize: 16, color: c.suave },
    rotuloForte: { fontFamily: "Lato_700Bold", color: c.texto },
    sub: {
      fontFamily: "Lato_400Regular",
      fontSize: 13,
      color: c.suave,
      marginTop: 2,
    },
    valor: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 26,
      color: c.texto,
      fontVariant: ["tabular-nums"],
    },
    extra: { fontSize: 13, color: c.suave },

    rodape: { backgroundColor: c.rodape, paddingTop: 28, paddingBottom: 32 },
    manchete: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 18,
      color: "#FFFFFF",
      marginBottom: 16,
    },
    barraBloco: { marginBottom: 18 },
    barraTopo: {
      flexDirection: "row",
      justifyContent: "space-between",
      gap: 12,
      marginBottom: 8,
    },
    barraRotulo: {
      flex: 1,
      fontFamily: "Lato_400Regular",
      fontSize: 14,
      color: "#E5E8EB",
    },
    barraValor: { fontFamily: "Lato_700Bold", fontSize: 14, color: "#FFFFFF" },
    barra: { height: 26, minWidth: 3, borderRadius: 3 },
    fonte: {
      borderTopWidth: 1,
      borderTopColor: c.rodapeLinha,
      marginTop: 8,
      paddingTop: 20,
      gap: 8,
    },
    fonteTitulo: {
      fontFamily: "Montserrat_800ExtraBold",
      fontSize: 17,
      color: "#FFFFFF",
    },
    fonteTexto: {
      fontFamily: "Lato_400Regular",
      fontSize: 13,
      lineHeight: 19,
      color: "#AEB6BF",
    },
    link: { fontFamily: "Montserrat_800ExtraBold", fontSize: 15, color: LIMAO },
    linkDiscreto: { textDecorationLine: "underline" },
    fab: {
      position: "absolute",
      right: 20,
      width: 56,
      height: 56,
      borderRadius: 28,
      backgroundColor: VERDE,
      alignItems: "center",
      justifyContent: "center",
      boxShadow: "0 4px 12px rgba(0, 0, 0, 0.35)",
    },
    textoRodape: { color: "#FFFFFF" },
    subRodape: { color: "#AEB6BF" },
    fabIcone: { fontSize: 24, lineHeight: 28, color: "#FFFFFF" },
  });
}
