# bot-analise-probabilidade

App **100% web** (HTML/CSS/JS) publicado via **GitHub Pages** para **estudo educacional** de estatística e probabilidade com dados históricos (ex.: resultados exportados do Excel em CSV).

> ⚠️ Importante: isto **não prevê resultados**. Em loterias justas, cada sorteio é tratado como evento independente.  
> O objetivo aqui é **análise descritiva** e **auditoria estatística** (frequências, pares, distribuição, qui-quadrado, etc.).

---

## Como acessar

Abra o link do **GitHub Pages** do repositório.

---

## Como usar

1. Exporte sua planilha do Excel como **CSV (delimitado por vírgulas)**  
2. No site, clique em **Escolher arquivo** e selecione o CSV  
3. Clique em **Validar** e depois **Analisar**  
4. (Opcional) Clique em **Exportar relatório (JSON)**

---

## Formato aceito do CSV

- **1 sorteio por linha**
- **6 números por linha** (ex.: 4,5,30,33,41,52)
- Separadores aceitos: **vírgula**, **espaço**, **TAB** ou **;**
- Intervalo esperado: **1–60**
- Não pode ter **número repetido** dentro do mesmo sorteio
- Se sua linha tiver mais colunas, o app usa **somente as 6 primeiras**

✅ Exemplo pronto no repo: `data/exemplo.csv`

---

## O que o app calcula hoje

- ✅ Validação de linhas (quantidade de números, intervalo, duplicidade)
- ✅ Frequência por dezena (Top 10)
- ✅ Co-ocorrência de pares (Top 10)
- ✅ Distribuição de pares/ímpares (quantos pares por sorteio)
- ✅ Soma por sorteio (média, min e max)
- ✅ Qui-quadrado simples vs. uniformidade (aprox.)

---

## Roadmap (próximas evoluções)

- [ ] Carregar `data/exemplo.csv` com 1 clique (fetch direto do repo)
- [ ] Parametrizar jogo (ex.: 1–50, 5 números, etc.)
- [ ] Mais testes: entropia, runs test, autocorrelação simples
- [ ] Gráficos (histograma e heatmap de pares)
- [ ] Página “Relatórios” para salvar/abrir JSON exportado
- [ ] Integração com Telegram:
  - Bot envia link do Pages
  - (opcional) Telegram Web App / Mini App apontando pro Pages

---

## Licença

MIT
