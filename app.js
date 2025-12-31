const $ = (sel) => document.querySelector(sel);

function pct(part, total) {
  if (!total) return "0.00%";
  return ((part / total) * 100).toFixed(2) + "%";
}

function sortNumericKeys(obj) {
  return Object.keys(obj)
    .map((k) => ({ k, n: Number(k), v: obj[k] }))
    .sort((a, b) => a.n - b.n);
}

async function loadJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Falha ao carregar ${path} (${res.status})`);
  return res.json();
}

function renderTable(counts, totalNums) {
  const rows = sortNumericKeys(counts);

  const tbody = rows
    .map(({ k, v }) => {
      return `
        <tr>
          <td>${k}</td>
          <td>${v}</td>
          <td>${pct(v, totalNums)}</td>
        </tr>
      `;
    })
    .join("");

  $("#freqTable").innerHTML = `
    <table>
      <thead>
        <tr><th>Número</th><th>Ocorrências</th><th>%</th></tr>
      </thead>
      <tbody>${tbody}</tbody>
    </table>
  `;
}

async function onSelectDataset(manifest) {
  const id = $("#gameSelect").value;
  const dsInfo = manifest.datasets.find((d) => d.id === id);
  if (!dsInfo) return;

  $("#status").textContent = "Carregando dataset...";
  const ds = await loadJSON("./" + dsInfo.path);

  const rows = ds?.meta?.rows ?? 0;
  const cols = (ds?.meta?.number_columns ?? []).join(", ");
  const lastConcurso = ds?.last?.Concurso ?? "-";
  const lastData = ds?.last?.["Data do Sorteio"] ?? "-";

  const counts = ds?.stats?.number_counts ?? {};
  const totalNums = ds?.stats?.total_numbers ?? 0;

  $("#summary").innerHTML = `
    <div class="card">
      <div><b>Linhas:</b> ${rows}</div>
      <div><b>Colunas numéricas:</b> ${cols || "-"}</div>
      <div><b>Último concurso:</b> ${lastConcurso}</div>
      <div><b>Data:</b> ${lastData}</div>
    </div>
  `;

  renderTable(counts, totalNums);
  $("#status").textContent = "OK";
}

async function main() {
  try {
    $("#status").textContent = "Carregando manifest...";
    const manifest = await loadJSON("./data/json/manifest.json");

    const select = $("#gameSelect");
    select.innerHTML = manifest.datasets
      .map((d) => `<option value="${d.id}">${d.name}</option>`)
      .join("");

    select.addEventListener("change", () => onSelectDataset(manifest));
    await onSelectDataset(manifest);

    $("#status").textContent = "OK";
  } catch (err) {
    console.error(err);
    $("#status").textContent = "Erro ao carregar dados (veja o console).";
  }
}

main();
