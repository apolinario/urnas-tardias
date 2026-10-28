import { useMemo, useState } from "react";
import {
  FlatList,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

// Gerados por ../analisa.py a partir dos logs das urnas baixados por ../crawl.py.
import card from "../../assets/card.json";
import votosJson from "../../assets/votos.json";

const VERDE = "#1ABC9C";
const VERDE_ESCURO = "#16876F";
const AZUL = "#2C3E50";
const CINZA = "#5D6D7E";
const LINHA = "#E3E6E8";
const LIMAO = "#A3D911";
const REPO = "github.com/leobragatti/urnas-tardias";

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
            placeholderTextColor={CINZA}
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
                  pressed && { backgroundColor: LINHA },
                ]}
              >
                <Text
                  style={[
                    s.opcaoTexto,
                    item.nome === valor && {
                      color: VERDE_ESCURO,
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
  return (
    <View style={[s.linha, !ultima && s.divisa]}>
      <View style={s.rotulos}>
        <Text style={[s.rotulo, forte && s.rotuloForte]}>{rotulo}</Text>
        {sub && <Text style={s.sub}>{sub}</Text>}
      </View>
      <Text style={[s.valor, forte && { color: VERDE_ESCURO }]}>
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

export default function Card() {
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
  const escolhido = { ate17: r.ate17, depois17: r.depois17, total }[janela];
  const info = JANELAS.find((j) => j.id === janela)!;

  return (
    <ScrollView
      style={{ backgroundColor: AZUL }}
      contentContainerStyle={{ paddingBottom: bottom }}
    >
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
            <Text style={s.destaqueNumero}>{int(escolhido)}</Text>
            <Text style={s.destaqueLegenda}>
              {info.legenda} · {lugar}
              {janela !== "total" &&
                ` · ${pct(escolhido, total, janela === "ate17" ? 2 : 3)} do total`}
            </Text>
          </View>

          <Linha rotulo={uf ? "Urnas" : "Urnas no país"} valor={int(r.urnas)} />
          <Linha
            rotulo="Urnas estendidas"
            sub="fecharam depois das 17h45"
            valor={int(r.estendidas)}
            extra={pct(r.estendidas, r.urnas, 2)}
            forte
          />
          <Linha
            rotulo="Votos depois das 17h nessas urnas"
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
          <Barra
            rotulo="Votos depois das 17h nas urnas estendidas"
            valor={card.votos_apos_17h}
            fracao={card.votos_apos_17h / card.vantagem}
            cor={LIMAO}
          />
          <View style={s.fonte}>
            <Text style={s.fonteTitulo}>Fonte: TSE</Text>
            <Text style={s.fonteTexto}>
              Logs das 499 mil urnas no site de resultados. Urna estendida =
              encerrou depois das 17h45 (horário de Brasília); contados só os
              votos depois das 17h. Exclui o exterior. Os votos depois das 17h
              em urnas que não foram estendidas são de eleitores que já estavam
              na fila às 17h.
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
  );
}

const s = StyleSheet.create({
  coluna: {
    width: "100%",
    maxWidth: 560,
    alignSelf: "center",
    paddingHorizontal: 24,
  },

  topo: { backgroundColor: VERDE, paddingBottom: 36 },
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

  meio: { backgroundColor: "#FFFFFF", paddingVertical: 8 },
  filtros: {
    paddingTop: 16,
    paddingBottom: 18,
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: LINHA,
  },
  seletores: { flexDirection: "row", gap: 10 },
  seletor: {
    flex: 1,
    borderWidth: 1,
    borderColor: LINHA,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  seletorRotulo: { fontFamily: "Lato_400Regular", fontSize: 12, color: CINZA },
  seletorValor: {
    fontFamily: "Lato_700Bold",
    fontSize: 15,
    color: AZUL,
    marginTop: 2,
  },
  segmentos: {
    flexDirection: "row",
    backgroundColor: "#EEF1F2",
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
  segmentoTexto: { fontFamily: "Lato_700Bold", fontSize: 14, color: CINZA },
  segmentoTextoAtivo: { color: "#FFFFFF" },
  destaque: { paddingVertical: 18, gap: 4 },
  destaqueNumero: {
    fontFamily: "Montserrat_800ExtraBold",
    fontSize: 40,
    color: VERDE_ESCURO,
    fontVariant: ["tabular-nums"],
  },
  destaqueLegenda: {
    fontFamily: "Lato_400Regular",
    fontSize: 14,
    lineHeight: 20,
    color: CINZA,
  },

  modal: { flex: 1, backgroundColor: "#FFFFFF", paddingHorizontal: 16 },
  modalTopo: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  modalTitulo: {
    fontFamily: "Montserrat_800ExtraBold",
    fontSize: 20,
    color: AZUL,
  },
  fechar: { fontFamily: "Lato_700Bold", fontSize: 16, color: VERDE_ESCURO },
  busca: {
    borderWidth: 1,
    borderColor: LINHA,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: AZUL,
    marginBottom: 8,
  },
  opcao: {
    paddingVertical: 14,
    paddingHorizontal: 4,
    borderBottomWidth: 1,
    borderBottomColor: LINHA,
  },
  opcaoTexto: { fontFamily: "Lato_400Regular", fontSize: 16, color: AZUL },

  linha: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 18,
  },
  divisa: { borderBottomWidth: 1, borderBottomColor: LINHA },
  rotulos: { flex: 1 },
  rotulo: { fontFamily: "Lato_400Regular", fontSize: 16, color: CINZA },
  rotuloForte: { fontFamily: "Lato_700Bold", color: AZUL },
  sub: {
    fontFamily: "Lato_400Regular",
    fontSize: 13,
    color: CINZA,
    marginTop: 2,
  },
  valor: {
    fontFamily: "Montserrat_800ExtraBold",
    fontSize: 26,
    color: AZUL,
    fontVariant: ["tabular-nums"],
  },
  extra: { fontSize: 13, color: CINZA },

  rodape: { backgroundColor: AZUL, paddingTop: 28, paddingBottom: 32 },
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
    borderTopColor: "#46586A",
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
});
