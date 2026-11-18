"use client";

import { useCallback, useEffect, useState } from "react";

const API = "/api";

function formatarData(iso) {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export default function Home() {
  const [relatos, setRelatos] = useState([]);
  const [saude, setSaude] = useState(null);
  const [foto, setFoto] = useState(null);
  const [lat, setLat] = useState("-23.5505");
  const [lon, setLon] = useState("-46.6333");
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([fetch(`${API}/relatos?limite=20`), fetch(`${API}/health`)]);
      if (r.ok) setRelatos(await r.json());
      if (s.ok) setSaude(await s.json());
    } catch {
      setSaude(null);
    }
  }, []);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 15000);
    return () => clearInterval(t);
  }, [carregar]);

  function usarMinhaLocalizacao() {
    navigator.geolocation?.getCurrentPosition(
      (p) => {
        setLat(p.coords.latitude.toFixed(5));
        setLon(p.coords.longitude.toFixed(5));
      },
      () => setErro("Não foi possível obter a localização."),
    );
  }

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setResultado(null);
    setEnviando(true);
    try {
      let resp;
      if (foto) {
        const form = new FormData();
        form.append("foto", foto);
        form.append("lat", lat);
        form.append("lon", lon);
        if (descricao) form.append("descricao", descricao);
        resp = await fetch(`${API}/relatos/foto`, { method: "POST", body: form });
      } else {
        resp = await fetch(`${API}/relatos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat: Number(lat), lon: Number(lon), descricao: descricao || null }),
        });
      }
      const corpo = await resp.json();
      if (!resp.ok) throw new Error(typeof corpo.detail === "string" ? corpo.detail : "Dados inválidos");
      setResultado(foto ? corpo : { relato: corpo });
      setDescricao("");
      setFoto(null);
      e.target.reset();
      carregar();
    } catch (err) {
      setErro(err.message || "Falha ao enviar o relato.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main>
      <header>
        <h1>AlertaBairro</h1>
        <p>Viu um alagamento? Envie uma foto: nossa IA confere se há água na via.</p>
        <span className={`status ${saude?.banco ? "ok" : "off"}`}>
          {saude ? `API no ar · modelo ${saude.modelo_carregado ? "carregado" : "indisponível"}` : "API fora do ar"}
        </span>
      </header>

      <section className="card">
        <h2>Novo relato</h2>
        <form onSubmit={enviar}>
          <label>
            Foto do local (opcional)
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} />
          </label>
          <div className="linha">
            <label>
              Latitude
              <input value={lat} onChange={(e) => setLat(e.target.value)} inputMode="decimal" required />
            </label>
            <label>
              Longitude
              <input value={lon} onChange={(e) => setLon(e.target.value)} inputMode="decimal" required />
            </label>
            <button type="button" className="secundario" onClick={usarMinhaLocalizacao}>
              Usar minha localização
            </button>
          </div>
          <label>
            Descrição
            <textarea maxLength={500} rows={2} value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Ex.: água na altura da calçada" />
          </label>
          <button disabled={enviando}>{enviando ? "Analisando…" : "Enviar relato"}</button>
        </form>
        {erro && <p className="erro">{erro}</p>}
        {resultado && (
          <p className={resultado.alagamento_confirmado ? "confirmado" : "neutro"}>
            {resultado.alagamento_confirmado === undefined
              ? "Relato registrado (sem foto)."
              : resultado.alagamento_confirmado
                ? `Alagamento confirmado pela imagem (confiança ${(resultado.relato.confianca * 100).toFixed(0)}%).`
                : "Relato registrado. A imagem não confirmou alagamento."}
          </p>
        )}
        <small>A foto é analisada e descartada: guardamos só o local e o resultado.</small>
      </section>

      <section className="card">
        <h2>Últimos relatos</h2>
        {relatos.length === 0 ? (
          <p className="vazio">Nenhum relato ainda.</p>
        ) : (
          <ul>
            {relatos.map((r) => (
              <li key={r.id}>
                <span className={`selo ${r.verificado_por_imagem ? "verificado" : ""}`}>
                  {r.verificado_por_imagem ? "Verificado por imagem" : "Não verificado"}
                </span>
                <strong>{r.descricao || "Sem descrição"}</strong>
                <span className="meta">
                  {r.lat.toFixed(4)}, {r.lon.toFixed(4)} · {formatarData(r.criado_em)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
