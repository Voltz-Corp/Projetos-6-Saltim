import { useEffect } from 'react'

const VLIBRAS_SCRIPT_ID = 'vlibras-plugin-script'
const VLIBRAS_APP_URL = 'https://vlibras.gov.br/app'
const vlibrasRootAttrs = { vw: '' }
const vlibrasAccessButtonAttrs = { 'vw-access-button': '' }
const vlibrasPluginWrapperAttrs = { 'vw-plugin-wrapper': '' }

declare global {
  interface Window {
    VLibras?: {
      Widget: new (baseUrl: string) => void
    }
    __saltimVLibrasInitialized?: boolean
  }
}

function initVLibrasWidget() {
  if (window.VLibras && !window.__saltimVLibrasInitialized) {
    new window.VLibras.Widget(VLIBRAS_APP_URL)
    window.__saltimVLibrasInitialized = true
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
    <div {...vlibrasRootAttrs} className="enabled saltim-vlibras">
      <div
        {...vlibrasAccessButtonAttrs}
        className="active !right-0 !top-[calc(50%+48px)] !z-40"
      />
      <div {...vlibrasPluginWrapperAttrs}>
        <div className="vw-plugin-top-wrapper" />
      </div>
    </div>
  )
}
