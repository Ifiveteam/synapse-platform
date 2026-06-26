import tailwindcss from '@tailwindcss/vite'
import { defineConfig, type Plugin } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { crx } from '@crxjs/vite-plugin'
import path from 'node:path'
import manifest from './manifest'

const SYNAPSE_ARCHIVER_BOOT_KEY = '__synapseBootArchiverContent'
const SYNAPSE_TRACKING_BOOT_KEY = '__synapseBootTrackingContent'

const CONTENT_BOOT_KEYS = [SYNAPSE_ARCHIVER_BOOT_KEY, SYNAPSE_TRACKING_BOOT_KEY] as const

/** Rolldown이 content 엔트리의 onExecute export를 제거할 때 CRXJS 로더가 동작하도록 보완 */
function preserveContentOnExecute(): Plugin {
  return {
    name: 'preserve-content-onExecute',
    enforce: 'post',
    generateBundle(_options, bundle) {
      for (const chunk of Object.values(bundle)) {
        if (chunk.type !== 'chunk') continue
        const facade = chunk.facadeModuleId?.replace(/\\/g, '/')
        if (!facade?.includes('entries/content-')) {
          continue
        }
        if (chunk.code.includes('export function onExecute')) continue

        // minify 후 `globalThis[v]=bootFn,bootFn()` 형태 — 키 변수명을 찾아 동일 참조로 export
        const bootMatch = chunk.code.match(
          /globalThis\[(\w+)\]=(\w+),\2\(\);?\s*$/,
        )
        if (bootMatch) {
          const [, keyVar] = bootMatch
          chunk.code += `\nexport function onExecute(){globalThis[${keyVar}]?.()}`
          continue
        }

        const fallbackKey = facade.includes('content-archiver')
          ? SYNAPSE_ARCHIVER_BOOT_KEY
          : SYNAPSE_TRACKING_BOOT_KEY
        if (!CONTENT_BOOT_KEYS.includes(fallbackKey as (typeof CONTENT_BOOT_KEYS)[number])) {
          continue
        }
        chunk.code += `\nexport function onExecute(){globalThis.${fallbackKey}?.()}`
      }
    },
  }
}

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    crx({
      manifest,
      contentScripts: {
        hmrTimeout: 30_000,
      },
    }),
    preserveContentOnExecute(),
  ],

  // Vite 8 + CRXJS dev: WebSocket/HMR 토큰 검사 완화
  legacy: {
    skipTokenCheck: true,
  },

  resolve: {
    // Shadcn UI 및 각 기능(features/) 도메인 간 교차 임포트 시 가독성과 유지보수성을 극대화하기 위한 절대경로 설정
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  build: {
    emptyOutDir: true,
    outDir: 'dist',
    rollupOptions: {
      output: {
        // 엔트리 포인트(Background, Content, Sidepanel) 간 공통 사용 모듈(Shared Library)을
        // 중복 없이 깔끔하게 공통 청크(Chunk)로 쪼개어 익스텐션 크기 및 로딩 성능 최적화
        chunkFileNames: 'assets/chunk-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        entryFileNames: '[name].js',
      },
    },
  },

  // 개발 환경(pnpm dev) 런타임에서 윈도우 환경 파일 유실이나
  // Background 서비스 워커 리로드 시 HMR(실시간 반영)이 씹히는 고질적인 버그 방지
  server: {
    port: 5174,
    strictPort: true,
    cors: true,
    headers: {
      'Access-Control-Allow-Origin': '*',
    },
    hmr: {
      port: 5174,
    },
  },
})
