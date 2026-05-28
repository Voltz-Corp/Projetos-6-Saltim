import { useEffect } from 'react'

const VLIBRAS_SCRIPT_ID = 'vlibras-plugin-script'
const VLIBRAS_APP_URL = 'https://vlibras.gov.br/app'

declare global {
  interface Window {
    VLibras?: {
      Widget: new (baseUrl: string) => void
    }
  }
}

function initVLibrasWidget() {
  if (window.VLibras) {
    new window.VLibras.Widget(VLIBRAS_APP_URL)
  }
}

export function VLibrasWidget() {
  useEffect(() => {
    const existingScript = document.getElementById(VLIBRAS_SCRIPT_ID)

    if (existingScript) {
      initVLibrasWidget()
      return
    }

    const script = document.createElement('script')
    script.id = VLIBRAS_SCRIPT_ID
    script.src = `${VLIBRAS_APP_URL}/vlibras-plugin.js`
    script.async = true
    script.onload = initVLibrasWidget
    document.body.appendChild(script)
  }, [])

  return (
    <div {...({ vw: true } as object)} className="enabled saltim-vlibras">
      <div {...({ 'vw-access-button': true } as object)} className="active" />
      <div {...({ 'vw-plugin-wrapper': true } as object)}>
        <div className="vw-plugin-top-wrapper" />
      </div>
    </div>
  )
}
