const GENE_LABELS = {
  idle_threshold: "idle",
  breakaway_margin: "breakaway",
  hunger_drain_rate: "hunger",
  water_drain_rate: "thirst",
  rest_drain_rate: "rest",
  vision: "vision",
}

const fmtGene = (value) =>
  Math.abs(value) < 0.1 ? value.toFixed(4) : value.toFixed(3)

export const renderGeneChart = (geneStats) => {
  const UP = "#2aa7c4"
  const DOWN = "#e08a3c"

  const labelOf = (geneStat) =>
    GENE_LABELS[geneStat.name] ?? geneStat.name.replace(/_/g, " ")

  const cols = geneStats
    .map((geneStat) => {
      const label = labelOf(geneStat)
      const up = geneStat.norm >= 0
      const heightPct = (Math.abs(geneStat.norm) * 50).toFixed(1) // half the plot per side
      const cls = up ? "up" : "down"
      const color = up ? UP : DOWN
      const drift = (
        ((geneStat.avg - geneStat.default) / geneStat.default) *
        100
      ).toFixed(1)
      const sign = geneStat.avg - geneStat.default >= 0 ? "+" : ""
      const title = `${label}: avg ${fmtGene(geneStat.avg)} · default ${fmtGene(
        geneStat.default,
      )} (${sign}${drift}%)`
      return `
        <div class="gene-col" title="${title}">
          <div class="gene-fill ${cls}" style="height:${heightPct}%;background:${color}">
            <span class="gene-val">${fmtGene(geneStat.avg)}</span>
          </div>
        </div>`
    })
    .join("")

  const names = geneStats
    .map(
      (geneStat) =>
        `<div class="gene-name">${labelOf(geneStat)}<span class="gene-default">${fmtGene(
          geneStat.default,
        )}</span></div>`,
    )
    .join("")

  return `
    <div class="stats-section gene-section">
      <h4>Genetic Drift</h4>
      <div class="gene-plot-row">${cols}</div>
      <div class="gene-name-row">${names}</div>
    </div>`
}
