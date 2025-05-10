'use strict'

class MarkerPlot extends HTMLElement {
  constructor() {
    super()
    // シャドウDOMを作成し、デフォルトスタイルを適用
    const shadow = this.attachShadow({ mode: 'open' })
    shadow.innerHTML = `
      <style>
        :host {
          display: inline-block;
          width: 10em;
          height: 10px;
        }
        svg {
          width: 10em;
          height: 10px;
          border: 1px solid black;
        }
      </style>
      <svg></svg>
    `
    this._svg = shadow.querySelector('svg')
  }

  connectedCallback() {
    const data = JSON.parse(this.getAttribute('data') || '[]')
    const min = parseFloat(this.getAttribute('min') || '0')
    const max = parseFloat(this.getAttribute('max') || '100')
    const unit = parseFloat(this.getAttribute('width') || '1')

    const svgNS = "http://www.w3.org/2000/svg"
    //const svg = document.createElementNS(svgNS, 'svg')
    //this.appendChild(svg)

    requestAnimationFrame(() => {
      const svg = this._svg
      const svgWidth = svg.clientWidth
      const svgHeight = svg.clientHeight
      const scale = svgWidth / (max - min)
      const markerWidthPx = unit * scale
      const markerHeightPx = Math.min(markerWidthPx, svgHeight)

      data.forEach(x => {
        const cx = (x - min) * scale
        const cy = svgHeight / 2
        const halfW = markerWidthPx / 2
        const halfH = markerHeightPx / 2

        const diamond = document.createElementNS(svgNS, 'polygon')
        diamond.setAttribute('points', [
          `${cx},${cy - halfH}`, // top
          `${cx + halfW},${cy}`, // right
          `${cx},${cy + halfH}`, // bottom
          `${cx - halfW},${cy}`  // left
        ].join(' '))
        diamond.setAttribute('fill', 'black')
        svg.appendChild(diamond)
      })
    })
  }
}

customElements.define('marker-plot', MarkerPlot)
