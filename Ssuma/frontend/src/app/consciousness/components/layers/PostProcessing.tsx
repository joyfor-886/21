'use client'

import { EffectComposer, DepthOfField, Bloom, Vignette, ToneMapping } from '@react-three/postprocessing'
import { ToneMappingMode } from 'postprocessing'

interface Props {
  theme?: 'xuanmo' | 'xuanzhi'
}

export default function PostProcessing({ theme = 'xuanmo' }: Props) {
  const isDark = theme === 'xuanmo'

  return (
    <EffectComposer>
      <DepthOfField
        focusDistance={0}
        focalLength={0}
        bokehScale={1}
      />
      <Bloom
        intensity={isDark ? 0.15 : 0.08}
        luminanceThreshold={isDark ? 0.85 : 0.9}
        luminanceSmoothing={0.95}
        mipmapBlur
      />
      <Vignette
        offset={isDark ? 0.15 : 0.1}
        darkness={isDark ? 0.3 : 0.15}
      />
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
    </EffectComposer>
  )
}
