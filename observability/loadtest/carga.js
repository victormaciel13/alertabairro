// Teste de carga com k6 (roda em Docker, sem instalar nada):
//   docker run --rm -i -v "$PWD/observability/loadtest:/scripts" -e URL=https://SEU-IP.sslip.io \
//     -e FOTO=/scripts/rua.jpg -e ERROS=true grafana/k6 run /scripts/carga.js
// URL   = endereço público (terraform output url)
// FOTO  = (opcional) foto para exercitar o YOLO em /api/relatos/foto
// ERROS = true chama /api/debug/erro (precisa de chaos_enabled=true) para disparar o alerta de 5xx
import http from "k6/http";
import { check, sleep } from "k6";

const URL = __ENV.URL || "http://localhost:8080";
const FOTO = __ENV.FOTO ? open(__ENV.FOTO, "b") : null;
const ERROS = __ENV.ERROS === "true";

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "3m", target: 25 },
    { duration: "30s", target: 0 },
  ],
};

export default function () {
  const sorteio = Math.random();
  if (ERROS && sorteio < 0.15) {
    http.get(`${URL}/api/debug/erro`, { tags: { rota: "erro" } });
  } else if (FOTO && sorteio < 0.3) {
    const r = http.post(`${URL}/api/relatos/foto`, {
      foto: http.file(FOTO, "rua.jpg", "image/jpeg"),
      lat: String(-23.55 + Math.random() * 0.1),
      lon: String(-46.63 - Math.random() * 0.1),
      descricao: "teste de carga",
    });
    check(r, { "foto 201": (x) => x.status === 201 });
  } else if (sorteio < 0.8) {
    check(http.get(`${URL}/api/relatos?limite=50`), { "lista 200": (x) => x.status === 200 });
  } else {
    check(http.get(`${URL}/`), { "site 200": (x) => x.status === 200 });
  }
  sleep(0.5);
}
