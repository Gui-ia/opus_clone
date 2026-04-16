# Opus Clone — Contexto para Claude Code (VPS / Orquestrador)

> **Leia este arquivo por inteiro antes de começar a codar.** Ele contém tudo: o que é o produto, a jornada completa, a arquitetura, contratos de API, schema de banco, stack, roadmap e regras. Se algo não estiver aqui, pergunte antes de assumir.

---

## 1. O que é o Opus Clone

**Elevator pitch:** uma plataforma que monitora canais de terceiros em YouTube, Instagram e TikTok e, automaticamente, transforma cada novo vídeo publicado em múltiplos cortes curtos virais prontos pra postar — com reframe vertical, legendas animadas, zooms em picos emocionais e overlays contextuais.

**Para quem é:** criadores de conteúdo, agências e gestores de canal que querem escalar a produção de shorts/reels/clips sem editor humano no meio. O público faz curadoria de **quais canais monitorar** (os seus, os de um cliente, os de referências do nicho) e o sistema cuida do resto 24/7.

**Que problema resolve:** editar cortes à mão de um podcast de 2h leva ~4h de trabalho. O OpusClip original faz isso em 10 min. Este produto faz o mesmo, mas em infraestrutura própria, com custo marginal quase zero por corte, e **monitorando a fonte continuamente** (o OpusClip obriga o usuário a fazer upload toda vez).

**Como funciona em alto nível:**

1. O usuário cadastra canais a monitorar (ex: `@meucanal` no YouTube, `@perfil` no Instagram).
2. Um scheduler detecta publicações novas (webhook pro YouTube, polling pros demais).
3. O vídeo é baixado via um agente de scraping rodando no PC do dev (IP residencial brasileiro).
4. A GPU A100 transcreve, analisa visualmente e pontua com LLM os momentos virais.
5. A GPU renderiza os cortes finais em vertical 9:16 com todas as edições.
6. O usuário aprova no dashboard e o sistema publica automaticamente nas plataformas.

**Diferença estratégica para o OpusClip original:** o produto deles é um editor. O nosso é um **agente autônomo de monitoramento + corte**. O usuário plugga os canais uma vez e o pipeline roda sozinho indefinidamente.

---

## 2. Visualização do sistema — a jornada completa

```
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 1 — CADASTRAR CANAIS                                     │
 ├─────────────────────────────────────────────────────────────────┤
 │  Usuário conecta suas fontes de interesse:                      │
 │                                                                  │
 │    • YouTube:   @canal_exemplo  → POST /api/channels             │
 │    • Instagram: @perfil_exemplo → POST /api/channels             │
 │    • TikTok:    @user_exemplo   → POST /api/channels             │
 │                                                                  │
 │  Persistido em `channels` com:                                   │
 │    • poll_interval_seconds                                       │
 │    • source_types (feed, stories, reels, shorts, video, live)    │
 │    • min_viral_score, max_clips_per_video, style_preset          │
 │                                                                  │
 │  YouTube: inscreve PubSubHubbub (notificação push de uploads)    │
 │  Instagram/TikTok: agenda polling no APScheduler                 │
 └─────────────────────────────────────────────────────────────────┘
                                 ↓
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 2 — DETECTAR CONTEÚDO NOVO                               │
 ├─────────────────────────────────────────────────────────────────┤
 │  YouTube (push)                                                  │
 │    PubSubHubbub POST → /v1/webhooks/youtube-pubsub               │
 │    Chega em segundos após o upload                               │
 │                                                                  │
 │  Instagram (pull)                                                │
 │    APScheduler a cada 15min dispara:                             │
 │      SCRAPER_AGENT POST /ig/user/{u}/{posts|stories|reels}       │
 │    Stories expiram em 24h → polling mais agressivo (1-2h)        │
 │                                                                  │
 │  TikTok (pull)                                                   │
 │    APScheduler a cada 30min:                                     │
 │      SCRAPER_AGENT POST /tk/user/{u}/videos                      │
 │                                                                  │
 │  Deduplicação: UNIQUE(channel_id, external_id)                   │
 │  INSERT source_videos (status='discovered')                      │
 │  enqueue("ingest_video", source_video_id)                        │
 └─────────────────────────────────────────────────────────────────┘
                                 ↓
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 3 — INGERIR VÍDEO (download + upload direto pro MinIO)   │
 ├─────────────────────────────────────────────────────────────────┤
 │  VPS gera presigned PUT URLs do MinIO                            │
 │  SCRAPER_AGENT POST /yt/download (ou análogo IG/TK):             │
 │    → scraper baixa no PC local (IP residencial)                  │
 │    → scraper faz upload direto pro MinIO da VPS                  │
 │    → VPS nunca toca no binário inteiro                           │
 │                                                                  │
 │  Metadata extraída:                                              │
 │    • heatmap YouTube (most-replayed parts)                       │
 │    • view_count, like_count, comment_count                       │
 │    • comments com timestamps explícitos                          │
 │                                                                  │
 │  UPDATE source_videos SET status='downloaded'                    │
 └─────────────────────────────────────────────────────────────────┘
                                 ↓
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 4 — PROCESSAR COM IA (tudo na GPU A100)                  │
 ├─────────────────────────────────────────────────────────────────┤
 │  4a) Transcrever                                                 │
 │      POST /v1/audio/transcriptions → WhisperX word-level + diar. │
 │      Retorno via webhook em ~30s/hora de áudio                   │
 │                                                                  │
 │  4b) Analisar visualmente                                        │
 │      POST /v1/video/analyze → scenes + faces + active speaker    │
 │      Retorno via webhook em ~2-5min/hora                         │
 │                                                                  │
 │  4c) Selecionar momentos virais (LLM)                            │
 │      POST /v1/chat/completions (Qwen 3.5 35B, 100k ctx)          │
 │      Self-consistency N=3 com temperature=0.7                    │
 │      Combina sinais: LLM + heatmap + áudio + comentários          │
 │      NMS temporal, dedup por IoU ≥ 0.5                           │
 │      → retorna top-K candidatos                                   │
 │                                                                  │
 │  4d) Construir EDL por candidato (plano de edição)               │
 │      Para cada clip aprovado:                                    │
 │        • reframe.tracks derivado de active_speaker_timeline      │
 │        • captions.words do transcript (pack 2-3 palavras/tela)   │
 │        • emphasis/cores/emojis (LLM passagem 2)                  │
 │        • zooms em picos                                          │
 │        • broll_cues (opcional)                                   │
 │      INSERT clips (status='planned', edl=...)                    │
 └─────────────────────────────────────────────────────────────────┘
                                 ↓
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 5 — RENDERIZAR CORTES                                    │
 ├─────────────────────────────────────────────────────────────────┤
 │  Para cada clipe em status='planned':                            │
 │    POST /v1/video/render { source_file_id, edl, webhook_url }   │
 │                                                                  │
 │  GPU roda FFmpeg com NVENC:                                      │
 │    • Crop dinâmico 9:16 seguindo falante ativo (sendcmd + EMA)  │
 │    • Legendas .ass karaoke word-highlight via libass             │
 │    • Keywords coloridas + emoji contextuais                      │
 │    • Zooms dinâmicos em picos emocionais                         │
 │    • B-roll overlays (opcional)                                  │
 │    • Normalização áudio −14 LUFS (loudnorm 2-pass)               │
 │    • Watermark                                                   │
 │                                                                  │
 │  Webhook render chega:                                           │
 │    → VPS baixa do GPU → sobe pro MinIO bucket `clips/`           │
 │    → UPDATE clips SET status='ready', final_url, minio_key       │
 │    → Opcional: gera thumbnail via POST /v1/images/generations    │
 └─────────────────────────────────────────────────────────────────┘
                                 ↓
 ┌─────────────────────────────────────────────────────────────────┐
 │  ETAPA 6 — APROVAR E PUBLICAR                                   │
 ├─────────────────────────────────────────────────────────────────┤
 │  Dashboard admin mostra:                                         │
 │    • Prévia do clipe (player)                                    │
 │    • Título sugerido (LLM) + hashtags                            │
 │    • Viral score + rationale                                     │
 │    • Editar metadata / regerar thumbnail / rejeitar              │
 │                                                                  │
 │  Ações do usuário:                                               │
 │    • Aprovar → status='approved'                                 │
 │    • Agendar publicação (janela ótima por plataforma)            │
 │    • Publicar imediatamente                                      │
 │                                                                  │
 │  Worker `publish` consome fila:                                  │
 │    • YouTube Data API → /youtube/v3/videos (upload shorts)       │
 │    • Meta Graph API → Instagram Reels + Feed                     │
 │    • TikTok Content Posting API                                  │
 │                                                                  │
 │  Credenciais OAuth ficam em `publishing_accounts`                │
 │  UPDATE clips SET status='published', published_to=[{...}]       │
 └─────────────────────────────────────────────────────────────────┘
```

**Estados possíveis de um vídeo fonte:**
`discovered → downloading → downloaded → transcribing → analyzing → scoring → ready_to_clip → clipping → completed`
(ou `failed`/`skipped` em qualquer etapa, com retry automático nos casos retryable)

**Estados possíveis de um clipe:**
`planned → rendering → ready → approved → publishing → published` (ou `failed`/`rejected`)

---

## 3. Arquitetura — 3 máquinas separadas

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   PC LOCAL (IP residencial)     │    │   VPS 32GB / 4 vCPU             │
│   Brasil — Cloudflare Tunnel    │    │   ORQUESTRADOR                  │
│                                 │◄───┤                                 │
│   FastAPI: scraper-agent        │    │   • Postgres 16 (opus_clone)    │
│   • instagrapi (sessões quentes)│HTTPS│   • Redis (fila + cache)       │
│   • yt-dlp + cookies Firefox    │    │   • MinIO (raw/clips/assets)    │
│   • TikTokApi (Playwright)      │    │   • FastAPI principal           │
│   • PubSubHubbub listener YT    │    │   • Dramatiq workers            │
│                                 │    │   • LangGraph agent             │
│   Endpoints expostos:           │    │   • APScheduler (polling)       │
│   POST /ig/user/{u}/posts       │    │   • ffprobe / concat leve       │
│   POST /ig/user/{u}/stories     │    │                                 │
│   POST /ig/user/{u}/reels       │    │   Webhook receiver:             │
│   POST /tk/user/{u}/videos      │    │   POST /v1/webhooks/*           │
│   POST /yt/download             │    └──────────────┬──────────────────┘
│   POST /yt/channel/{id}/latest  │                   │
│   GET  /health                  │                   │ HTTPS + Bearer
└─────────────────────────────────┘                   ▼
                                         ┌─────────────────────────────────┐
                                         │   GPU A100 80GB                 │
                                         │   http://69.19.137.207          │
                                         │                                 │
                                         │   Consumido pelo opus-clone:    │
                                         │   • /v1/files/upload            │
                                         │   • /v1/chat/completions        │
                                         │     (Qwen 3.5 35B, 100k ctx)    │
                                         │   • /v1/images/generations      │
                                         │     (thumbnails, overlays)      │
                                         │   • /v1/videos/generations      │
                                         │     (LTX-2.3 B-roll, opcional)  │
                                         │   • /v1/tts/generate            │
                                         │     (voice-over, opcional)      │
                                         │   • /v1/audio/transcriptions ★  │
                                         │   • /v1/video/analyze ★         │
                                         │   • /v1/video/render ★          │
                                         │                                 │
                                         │   ★ = endpoints NOVOS (outro    │
                                         │       Claude Code implementa)   │
                                         └─────────────────────────────────┘
```

**Princípio arquitetural central:**

- **Processamento pesado NUNCA roda na VPS.** Qualquer tarefa que exceda 500MB RAM ou 30s CPU vira endpoint na GPU. Regra dura.
- **Scraping com IP residencial NUNCA roda na VPS.** Qualquer chamada a Instagram/TikTok/YouTube passa pelo PC local via Cloudflare Tunnel.
- **A VPS é só orquestração**: banco, fila, agente LangGraph, rotas HTTP, scheduler. Gasta ~1.5 vCPU médios e ~8-10 GB RAM em regime.

---

## 4. Servidor VPS

| Campo | Valor |
|-------|-------|
| IP | `46.224.85.179` |
| OS | Ubuntu 24.04 (kernel 6.8) |
| CPU/RAM | 16 cores / 30 GB (compartilhadas — conte com ~4 vCPU efetivas) |

### Acesso SSH

- **Chave PPK:** `C:\Users\Guilherme\Downloads\sv_gui.ppk`
- **Via plink:** `plink -i "C:\Users\Guilherme\Downloads\sv_gui.ppk" root@46.224.85.179`
- **Código do projeto:** `/root/opus-clone/`

### Isolamento de recursos

Este projeto é **totalmente isolado** na VPS. Não toca em nada que já esteja rodando. Nada de reutilizar bancos de outros projetos, nada de Temporal, nada de filas compartilhadas.

---

## 5. Infraestrutura dedicada do opus-clone

Sobe tudo via Docker Compose próprio, em portas exclusivas, com nomes prefixados `opus-*` para não colidir com nada que já esteja no servidor.

### 5.1. PostgreSQL 16 (novo, dedicado)

- Container: `opus-postgres`
- Porta externa: `5632` (não-padrão pra não colidir)
- Banco: `opus_clone`
- Extensions: `uuid-ossp`, `pg_trgm`, `vector` (pgvector para few-shot retrieval)
- Credenciais: gerar forte e salvar em `.env`
- Volume: `/var/lib/opus-postgres:/var/lib/postgresql/data`

**URL (formato para `.env`):**
```
DATABASE_URL=postgres://opus:<gerar>@46.224.85.179:5632/opus_clone?sslmode=disable
```

### 5.2. Redis (novo, dedicado)

- Container: `opus-redis`
- Porta externa: `6479` (não-padrão)
- Password auth obrigatório
- DBs:
  - `DB 0`: Dramatiq broker (fila de jobs)
  - `DB 1`: Cache de resultados (transcripts, análises — TTL 24h)
  - `DB 2`: Distributed locks (evitar processar o mesmo vídeo 2×)
- Persistência: AOF (`appendonly yes`)

```
REDIS_URL=redis://:<gerar>@46.224.85.179:6479
```

### 5.3. MinIO (novo, dedicado)

- Container: `opus-minio`
- API: `9600` | Console: `9601`
- Buckets a criar no bootstrap:
  - `raw/` — vídeos fonte baixados. Lifecycle: delete após 7 dias.
  - `clips/` — clipes finais gerados. Retenção permanente (primeiros meses).
  - `assets/` — fontes, logos, B-roll de stock baixado.
- Credenciais: gerar no primeiro `docker compose up` via env.

```
MINIO_ENDPOINT=46.224.85.179:9600
MINIO_ACCESS_KEY=<gerar>
MINIO_SECRET_KEY=<gerar>
```

### 5.4. Proxy reverso (Caddy ou Traefik)

Para expor a API em HTTPS com certificado Let's Encrypt automático. URL pública: `https://opus.seudominio.com`.

**Por que HTTPS é obrigatório:** webhooks do YouTube PubSubHubbub **exigem HTTPS** no callback. A API da GPU também só entrega webhooks em HTTPS.

---

## 6. API da GPU A100 — o que vamos consumir

Gateway em `http://69.19.137.207`. Auth: `Authorization: Bearer <GPU_API_KEY>`. Docs vivas: `http://69.19.137.207/docs` e `/openapi.json`.

**Endpoints existentes que o opus-clone consome:**

| Endpoint | Para quê usamos |
|---|---|
| `POST /v1/files/upload` | Upload de qualquer arquivo (vídeo, imagem, áudio) para obter `file_id`. TTL 24h. |
| `GET /v1/files/{file_id}` | Verificar metadata |
| `POST /v1/chat/completions` | Qwen 3.5 35B (100k ctx). Usado pra viral scoring, seleção de hooks, metadata de edição, geração de títulos/hashtags. |
| `POST /v1/images/generations` | Text-to-image + img2img. Usado pra **thumbnails** dos clipes, covers de stories, overlays ilustrativos. |
| `POST /v1/videos/generations` | LTX-2.3 (9:16, até 20s, com áudio). Usado pra **B-roll gerado** quando não há stock adequado. Assíncrono com webhook. |
| `POST /v1/tts/generate` | TTS (Kokoro 82M + Edge fallback). Usado pra **voice-over opcional** em hooks narrados e outros casos específicos. |
| `GET /outputs/{filename}` | Download de resultados gerados (imagens, vídeos, transcrições). |

**Endpoints NOVOS que o outro Claude Code vai implementar (contratos abaixo):**

- `POST /v1/audio/transcriptions` — ASR word-level + diarização
- `POST /v1/video/analyze` — scene detection + faces + active speaker
- `POST /v1/video/render` — render final FFmpeg NVENC com EDL

### 6.1. Particularidades importantes

- **Admission control + circuit breaker:** respeite 503 com `Retry-After`. Retry com backoff exponencial via `tenacity` no cliente.
- **Janela de contexto do Qwen 3.5 35B:** `max-model-len=100000`. Soma `prompt_tokens + max_tokens ≤ 100000`. `max_tokens` hard cap: 8000. Para transcripts muito longos (>70k tokens), chunk em janelas overlapping de 8–12 min com 1 min de overlap.
- **File upload TTL:** 24h. Se job demorar mais (raro), re-upload antes de invocar próximo endpoint.
- **Webhook entregue até 5× com backoff 2s/4s/6s/8s/10s.** Seu receiver responde 2xx em <15s ou o evento é considerado falho. Para processamento pesado, aceite, enfileire, responda 200.
- **Idempotência:** sempre persista `gpu_job_id` em `gpu_jobs` ANTES de disparar. Em caso de timeout/rede, consulte polling `/v1/{tipo}/status/{job_id}`.

### 6.2. Contratos dos 3 novos endpoints (resumido)

#### `POST /v1/audio/transcriptions`

```json
Request:
{
  "file_id": "uuid-upload",
  "language": "pt",
  "diarize": true,
  "word_timestamps": true,
  "vad_filter": true,
  "min_speakers": 1, "max_speakers": 5,
  "webhook_url": "https://opus.seudominio.com/v1/webhooks/asr"
}

Webhook (sucesso):
{
  "job_id": "tr_abc123",
  "type": "transcription",
  "status": "completed",
  "language": "pt",
  "duration_s": 3612.4,
  "result_file_id": "file_xyz789",
  "result_url": "http://69.19.137.207/outputs/tr_abc123.json",
  "speakers_count": 3,
  "elapsed_seconds": 42.1
}
```

Formato do JSON em `result_file_id`:
```json
{
  "language": "pt",
  "duration": 3612.4,
  "segments": [
    {
      "id": 0, "start": 0.12, "end": 4.88,
      "text": "Hoje a gente vai falar sobre...",
      "speaker": "SPEAKER_00",
      "words": [
        {"word": "Hoje", "start": 0.12, "end": 0.38, "score": 0.94, "speaker": "SPEAKER_00"}
      ]
    }
  ],
  "speakers": ["SPEAKER_00", "SPEAKER_01"]
}
```

#### `POST /v1/video/analyze`

```json
Request:
{
  "file_id": "uuid-video",
  "fps_sample": 2,
  "detect_scenes": true,
  "detect_faces": true,
  "detect_active_speaker": true,
  "webhook_url": "https://opus.seudominio.com/v1/webhooks/analyze"
}

Webhook:
{
  "job_id": "va_def456",
  "status": "completed",
  "result_file_id": "file_abc123",
  "summary": {
    "scenes_count": 47, "faces_tracked": 3,
    "active_speakers": 2, "avg_speaker_switch_s": 12.4
  }
}
```

Formato do JSON:
```json
{
  "duration": 3612.4,
  "scenes": [{"start": 0.0, "end": 18.2, "dominant_faces": ["face_0"]}],
  "faces": [
    {"face_id": "face_0", "embedding": [512 floats],
     "appearances": [{"start": 0.0, "end": 180.0}]}
  ],
  "active_speaker_timeline": [
    {"start_ms": 120, "end_ms": 4880, "face_id": "face_0",
     "confidence": 0.91, "bbox_normalized": [0.35, 0.20, 0.25, 0.40]}
  ],
  "keyframes": [
    {"time_s": 9.1, "scene_idx": 0, "has_face": true, "faces_present": ["face_0"]}
  ]
}
```

#### `POST /v1/video/render`

Recebe EDL completa. Schema inline:

```json
{
  "source_file_id": "uuid-video-original",
  "edl": {
    "clip_start_ms": 142000,
    "clip_end_ms": 198000,
    "output_spec": {
      "width": 1080, "height": 1920, "fps": 30,
      "codec": "h264_nvenc", "preset": "p6", "cq": 19,
      "audio_codec": "aac", "audio_bitrate": "192k",
      "loudnorm": { "I": -14, "TP": -1, "LRA": 9 }
    },
    "reframe": {
      "mode": "active_speaker",
      "source_dimensions": {"width": 1920, "height": 1080},
      "tracks": [
        {"start_ms": 142000, "end_ms": 146200,
         "cx_ratio": 0.62, "cy_ratio": 0.40, "scale": 1.0}
      ],
      "smoothing": {"type": "ema", "alpha": 0.15},
      "min_hold_ms": 800
    },
    "captions": {
      "enabled": true,
      "style": "viral_yellow_karaoke",
      "font": "Montserrat Black",
      "font_size": 110,
      "words": [
        {"word": "HOJE", "start_ms": 142120, "end_ms": 142380, "emphasis": false},
        {"word": "VIDA", "start_ms": 142600, "end_ms": 142980,
         "emphasis": true, "color": "#FFD700"}
      ],
      "emojis": [
        {"time_ms": 145000, "emoji": "🔥", "duration_ms": 1200, "size_px": 140}
      ],
      "max_words_per_page": 3,
      "max_gap_s": 0.35,
      "position": {"v_anchor": "middle", "v_offset": 0}
    },
    "zooms": [
      {"start_ms": 168000, "end_ms": 170400, "scale": 1.15, "ease": "ease_in_out"}
    ],
    "broll_overlays": [
      {"start_ms": 155000, "end_ms": 160000,
       "source_file_id": "uuid-broll", "mode": "fullscreen", "audio_duck_db": -12}
    ],
    "sfx": [{"time_ms": 142000, "source_file_id": "uuid-whoosh", "volume": 0.5}],
    "background_music": {
      "source_file_id": "uuid-music",
      "volume": 0.12, "loop": true,
      "fade_in_ms": 500, "fade_out_ms": 1000
    },
    "watermark": {
      "source_file_id": "uuid-logo-png",
      "position": "top_right", "margin_px": 36,
      "width_px": 180, "opacity": 0.85
    }
  },
  "webhook_url": "https://opus.seudominio.com/v1/webhooks/render"
}

Webhook:
{
  "job_id": "rn_ghi789",
  "status": "completed",
  "result_file_id": "file_clip_final",
  "result_url": "http://69.19.137.207/outputs/rn_ghi789.mp4",
  "duration_s": 56.0,
  "file_size_bytes": 8421760,
  "dimensions": "1080x1920",
  "elapsed_seconds": 124.3
}
```

---

## 7. API do PC local (scraper-agent)

FastAPI rodando no PC do dev, exposto via **Cloudflare Tunnel**. URL no `.env`:

```
SCRAPER_AGENT_URL=https://opus-scraper.trycloudflare.com
SCRAPER_AGENT_TOKEN=<token bearer acordado>
```

**Endpoints que o orquestrador consome:**

```
POST /ig/user/{username}/posts        → lista últimos posts/reels
POST /ig/user/{username}/stories      → stories ativas (expiram 24h)
POST /ig/user/{username}/reels        → reels específicos
POST /tk/user/{username}/videos       → vídeos TikTok
POST /yt/channel/{channel_id}/latest  → últimos uploads (fallback do PubSub)
POST /yt/download                     → baixa e sobe direto no MinIO (presigned URL)
GET  /health                          → status + latência
```

**Contrato de `POST /yt/download`:**

```json
Request:
{
  "url": "https://www.youtube.com/watch?v=...",
  "minio_presigned_put_url": "https://..../raw/video-xxx.mp4?X-Amz...",
  "minio_presigned_info_url": "https://..../raw/video-xxx.info.json?X-Amz...",
  "format": "best[ext=mp4][height<=1080]/best[height<=1080]",
  "write_info_json": true,
  "extract_heatmap": true
}

Response:
{
  "status": "completed",
  "duration_s": 3612,
  "bytes_uploaded": 158234112,
  "info_json_key": "raw/video-xxx.info.json",
  "video_key": "raw/video-xxx.mp4",
  "heatmap": [[0.01, 0.3], ...],
  "title": "...", "description": "...",
  "published_at": "2026-04-10T14:22:00Z",
  "view_count": 12340, "like_count": 890
}
```

**Política de falhas:** se scraper offline ou 5xx, **não assuma ausência de vídeo**. Marque job como `retry_later` com backoff e tente daqui a 10–30 min. IG e TikTok às vezes exigem refresh de sessão no PC local.

---

## 8. Schema Postgres (banco `opus_clone` na porta 5632)

Criar em `migrations/001_initial.sql`. Use Alembic ou SQL puro — sua escolha, mas documente.

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========== CANAIS MONITORADOS ==========
CREATE TYPE platform_type AS ENUM ('youtube', 'instagram', 'tiktok');
CREATE TYPE source_type AS ENUM ('feed', 'stories', 'reels', 'shorts', 'video', 'live');

CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    poll_interval_seconds INT DEFAULT 900,
    source_types source_type[] DEFAULT ARRAY['video']::source_type[],
    last_polled_at TIMESTAMPTZ,
    last_content_at TIMESTAMPTZ,
    pubsub_subscription_expires_at TIMESTAMPTZ,
    pubsub_secret VARCHAR(64),
    preferred_clip_duration_s INT[] DEFAULT ARRAY[20,70],
    min_viral_score INT DEFAULT 65,
    max_clips_per_video INT DEFAULT 8,
    style_preset VARCHAR(64) DEFAULT 'default',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, external_id)
);
CREATE INDEX idx_channels_active_polled ON channels(is_active, last_polled_at) WHERE is_active;
CREATE INDEX idx_channels_platform_username ON channels(platform, username);

-- ========== VÍDEOS FONTE ==========
CREATE TYPE video_status AS ENUM (
    'discovered', 'downloading', 'downloaded',
    'transcribing', 'analyzing', 'scoring',
    'ready_to_clip', 'clipping',
    'completed', 'failed', 'skipped'
);

CREATE TABLE source_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    source_type source_type NOT NULL,
    url TEXT NOT NULL,
    title TEXT, description TEXT,
    published_at TIMESTAMPTZ,
    duration_s INT,
    view_count BIGINT, like_count BIGINT, comment_count BIGINT,
    heatmap JSONB,
    comments_with_timestamps JSONB,
    minio_bucket VARCHAR(64),
    minio_key TEXT,
    file_size_bytes BIGINT,
    width INT, height INT, fps NUMERIC(5,2),
    transcript_file_id VARCHAR(128),
    transcript_json JSONB,
    language_detected VARCHAR(8),
    speakers_count INT,
    scene_analysis JSONB,
    status video_status DEFAULT 'discovered',
    error_message TEXT,
    retry_count INT DEFAULT 0,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(channel_id, external_id)
);
CREATE INDEX idx_source_status ON source_videos(status);
CREATE INDEX idx_source_channel_published ON source_videos(channel_id, published_at DESC);

-- ========== CLIPES GERADOS ==========
CREATE TYPE clip_status AS ENUM (
    'planned', 'rendering', 'ready',
    'approved', 'rejected',
    'publishing', 'published', 'failed'
);

CREATE TABLE clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_video_id UUID NOT NULL REFERENCES source_videos(id) ON DELETE CASCADE,
    start_ms INT NOT NULL,
    end_ms INT NOT NULL,
    duration_ms INT GENERATED ALWAYS AS (end_ms - start_ms) STORED,
    hook_text TEXT,
    transcript_slice JSONB,
    title_suggestion TEXT,
    description TEXT,
    hashtags TEXT[],
    viral_score NUMERIC(5,2),
    confidence NUMERIC(4,3),
    hook_type VARCHAR(64),
    category VARCHAR(64),
    target_audience VARCHAR(64),
    rationale TEXT,
    edl JSONB NOT NULL,
    render_job_id VARCHAR(128),
    minio_key TEXT,
    final_url TEXT,
    thumbnail_url TEXT,
    file_size_bytes BIGINT,
    published_to JSONB DEFAULT '[]'::jsonb,
    status clip_status DEFAULT 'planned',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rendered_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
);
CREATE INDEX idx_clips_source ON clips(source_video_id);
CREATE INDEX idx_clips_status ON clips(status);
CREATE INDEX idx_clips_viral_score ON clips(viral_score DESC) WHERE status = 'ready';

-- ========== JOBS (rastreamento de chamadas à API GPU) ==========
CREATE TYPE job_type AS ENUM (
    'transcribe', 'analyze_video', 'score_clips',
    'render_clip', 'generate_broll', 'generate_thumbnail',
    'generate_voiceover'
);
CREATE TYPE job_status AS ENUM (
    'queued', 'dispatched', 'processing',
    'completed', 'failed', 'timeout'
);

CREATE TABLE gpu_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type job_type NOT NULL,
    source_video_id UUID REFERENCES source_videos(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES clips(id) ON DELETE CASCADE,
    gpu_job_id VARCHAR(128),
    request_payload JSONB,
    response_payload JSONB,
    status job_status DEFAULT 'queued',
    error_message TEXT,
    retry_count INT DEFAULT 0,
    dispatched_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_gpu_jobs_status ON gpu_jobs(status);
CREATE INDEX idx_gpu_jobs_external ON gpu_jobs(gpu_job_id) WHERE gpu_job_id IS NOT NULL;

-- ========== STYLE PRESETS ==========
CREATE TABLE style_presets (
    name VARCHAR(64) PRIMARY KEY,
    captions_config JSONB NOT NULL,
    reframe_config JSONB NOT NULL,
    overlay_config JSONB NOT NULL,
    audio_config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== VIRAL REFERENCE BANK (few-shot retrieval) ==========
CREATE TABLE viral_reference_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    url TEXT NOT NULL,
    transcript TEXT NOT NULL,
    hook_type VARCHAR(64),
    real_views BIGINT,
    real_engagement_rate NUMERIC(5,4),
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_viral_ref_embedding ON viral_reference_clips
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========== PUBLISHING ACCOUNTS (OAuth) ==========
CREATE TABLE publishing_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== TRIGGERS ==========
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_channels_updated BEFORE UPDATE ON channels
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

LangGraph PostgresSaver cria automaticamente `langgraph_checkpoints` e `langgraph_checkpoint_writes` ao chamar `PostgresSaver.setup()`. **Não crie manualmente.**

---

## 9. Estrutura do repositório

```
/root/opus-clone/
├── CLAUDE.md                          ← este arquivo
├── README.md
├── pyproject.toml                     ← uv (preferido)
├── .env.example
├── .gitignore
├── docker-compose.yml                 ← stack completa
├── Dockerfile
├── Caddyfile                          ← ou traefik.yml
│
├── migrations/
│   ├── 001_initial.sql
│   └── ...
│
├── src/
│   └── opus_clone/
│       ├── __init__.py
│       ├── config.py                  ← Pydantic Settings
│       ├── db.py                      ← asyncpg + SQLAlchemy async
│       ├── logging.py                 ← structlog
│       │
│       ├── api/                       ← FastAPI routes
│       │   ├── main.py
│       │   ├── health.py
│       │   ├── channels.py            ← CRUD canais
│       │   ├── videos.py              ← query vídeos
│       │   ├── clips.py               ← query + aprovar/rejeitar
│       │   ├── webhooks.py            ← receiver webhooks GPU + PubSub
│       │   └── admin.py               ← dashboards, stats
│       │
│       ├── clients/                   ← HTTP clients (httpx async)
│       │   ├── gpu_api.py             ← cliente API GPU c/ retry + circuit breaker
│       │   ├── scraper_agent.py       ← cliente PC local
│       │   └── youtube_data.py        ← YouTube Data API v3
│       │
│       ├── scheduler/                 ← APScheduler
│       │   ├── poller.py              ← polling IG/TikTok
│       │   └── pubsub_renewer.py      ← renova subscriptions YT a cada 5d
│       │
│       ├── workers/                   ← Dramatiq actors
│       │   ├── ingest.py              ← download via scraper-agent
│       │   ├── process.py             ← roda LangGraph
│       │   └── publish.py             ← publica em YT/Meta/TikTok
│       │
│       ├── agent/                     ← LangGraph
│       │   ├── state.py               ← TypedDict
│       │   ├── graph.py               ← StateGraph + PostgresSaver
│       │   ├── nodes/
│       │   │   ├── prepare.py
│       │   │   ├── transcribe.py
│       │   │   ├── analyze.py
│       │   │   ├── score.py           ← Qwen via /v1/chat
│       │   │   ├── build_edl.py       ← gera EDL por candidato
│       │   │   ├── render.py
│       │   │   └── thumbnail.py       ← /v1/images/generations
│       │   └── prompts/
│       │       ├── viral_selection.txt
│       │       ├── editing_metadata.txt
│       │       └── title_hashtags.txt
│       │
│       ├── services/
│       │   ├── minio.py               ← wrapper MinIO + presigned URLs
│       │   ├── viral_score.py         ← combina sinais multimodais
│       │   ├── edl_builder.py         ← monta EDL completo
│       │   └── hmac_webhook.py        ← verifica assinatura
│       │
│       ├── models/                    ← Pydantic
│       │   ├── db.py                  ← SQLAlchemy models
│       │   ├── domain.py              ← Clip, Video, Channel DTOs
│       │   ├── edl.py                 ← schema EDL
│       │   └── gpu_api.py             ← request/response da API GPU
│       │
│       └── publishing/
│           ├── youtube.py             ← Data API v3 upload
│           ├── instagram.py           ← Meta Graph API
│           └── tiktok.py              ← Content Posting API
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       ├── sample_transcript.json
│       ├── sample_analyze.json
│       └── sample_edl.json
│
└── scripts/
    ├── seed_style_presets.py
    ├── seed_viral_references.py
    └── manual_process.py              ← processa 1 vídeo fim-a-fim (debug)
```

---

## 10. Stack técnica (versões exatas)

```toml
[project]
name = "opus-clone"
version = "0.1.0"
requires-python = ">=3.11,<3.13"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "httpx>=0.27.0",
    "tenacity>=9.0.0",
    "asyncpg>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "alembic>=1.13.0",
    "redis>=5.1.0",
    "dramatiq[redis]>=1.17.0",
    "apscheduler>=3.10.4",
    "langgraph>=0.2.40",
    "langgraph-checkpoint-postgres>=2.0.0",
    "psycopg[binary,pool]>=3.2.0",
    "minio>=7.2.0",
    "structlog>=24.4.0",
    "prometheus-client>=0.21.0",
    "google-api-python-client>=2.145.0",  # YouTube Data API
    "google-auth-oauthlib>=1.2.0",
    "pyjwt[crypto]>=2.9.0",
    "cryptography>=43.0.0",
    "backoff>=2.2.0",
    "pytz>=2024.2",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-httpx>=0.35.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
]
```

**Gerenciador:** `uv` (10× mais rápido que pip). `uv sync` para instalar.
**Python:** 3.12 (não use 3.13 — wheels ainda não consolidados).

---

## 11. Variáveis de ambiente (`.env.example`)

```bash
# ========== APP ==========
APP_ENV=production
APP_LOG_LEVEL=INFO
APP_BASE_URL=https://opus.seudominio.com

# ========== DB (Postgres dedicado do opus-clone) ==========
DATABASE_URL=postgres://opus:<gerar>@46.224.85.179:5632/opus_clone?sslmode=disable
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20

# ========== REDIS (dedicado do opus-clone) ==========
REDIS_URL=redis://:<gerar>@46.224.85.179:6479
REDIS_DB_BROKER=0
REDIS_DB_CACHE=1
REDIS_DB_LOCKS=2

# ========== MINIO ==========
MINIO_ENDPOINT=46.224.85.179:9600
MINIO_ACCESS_KEY=<gerar>
MINIO_SECRET_KEY=<gerar>
MINIO_BUCKET_RAW=raw
MINIO_BUCKET_CLIPS=clips
MINIO_BUCKET_ASSETS=assets
MINIO_SECURE=false
MINIO_PUBLIC_ENDPOINT=https://storage.seudominio.com

# ========== GPU API ==========
GPU_API_URL=http://69.19.137.207
GPU_API_KEY=<solicitar>
GPU_API_TIMEOUT_S=60
GPU_API_MAX_RETRIES=5

# ========== SCRAPER AGENT (PC local) ==========
SCRAPER_AGENT_URL=https://opus-scraper.trycloudflare.com
SCRAPER_AGENT_TOKEN=<acordar com o dev>
SCRAPER_AGENT_TIMEOUT_S=300

# ========== YOUTUBE DATA API ==========
YOUTUBE_API_KEY=<Google Cloud Console>
YOUTUBE_PUBSUB_CALLBACK_URL=https://opus.seudominio.com/v1/webhooks/youtube-pubsub
YOUTUBE_PUBSUB_HUB=https://pubsubhubbub.appspot.com/subscribe

# ========== WEBHOOK AUTH ==========
WEBHOOK_SHARED_SECRET=<gerar 32 bytes hex>

# ========== WORKERS ==========
DRAMATIQ_CONCURRENCY=4
DRAMATIQ_THREADS=2
```

---

## 12. Docker Compose

```yaml
services:
  opus-postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: opus
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: opus_clone
    volumes:
      - /var/lib/opus-postgres:/var/lib/postgresql/data
    ports:
      - "5632:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U opus -d opus_clone"]
      interval: 10s

  opus-redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - /var/lib/opus-redis:/data
    ports:
      - "6479:6379"
    restart: unless-stopped

  opus-minio:
    image: minio/minio:latest
    command: server /data --console-address ":9601"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - /var/lib/opus-minio:/data
    ports:
      - "9600:9000"
      - "9601:9601"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s

  opus-api:
    build: .
    command: uvicorn opus_clone.api.main:app --host 0.0.0.0 --port 8080 --workers 2
    env_file: .env
    ports:
      - "8080:8080"
    depends_on:
      opus-postgres: { condition: service_healthy }
      opus-minio: { condition: service_healthy }
    restart: unless-stopped

  opus-scheduler:
    build: .
    command: python -m opus_clone.scheduler
    env_file: .env
    depends_on: [opus-postgres, opus-redis]
    restart: unless-stopped

  opus-worker:
    build: .
    command: dramatiq opus_clone.workers --processes 2 --threads 2
    env_file: .env
    depends_on: [opus-postgres, opus-redis, opus-minio]
    restart: unless-stopped
    deploy:
      replicas: 1  # subir pra 2 se fila cresce
```

Caddy (ou Traefik) expõe `opus-api:8080` em `https://opus.seudominio.com`.

---

## 13. Roadmap técnico em fases

### v0.1 — MVP YouTube-only (1 semana)

**Meta:** cadastrar 1 canal YouTube, detectar upload, processar, gerar 5 clipes no MinIO.

- [ ] Migrations aplicadas
- [ ] Docker stack sobe (postgres/redis/minio/api/worker/scheduler)
- [ ] Cliente GPU API com retry + circuit breaker + teste smoke
- [ ] PubSubHubbub inscreve canal e recebe callback
- [ ] Worker `ingest_video` baixa via scraper-agent (pode ser mock por ora)
- [ ] LangGraph end-to-end com PostgresSaver
- [ ] 5 clipes renderizados e reproduzíveis

### v0.2 — Instagram + TikTok + qualidade (2 semanas)

- [ ] Scraper-agent integrado (feed, stories, reels, TikTok)
- [ ] Polling agressivo de stories (TTL 24h)
- [ ] Self-consistency N=3 no scoring
- [ ] Re-rank com sinais de áudio + heatmap + comentários timestampados
- [ ] Legendas com keywords coloridas + emojis contextuais
- [ ] Reframe dinâmico com active speaker + EMA smoothing
- [ ] Style presets (3 no mínimo: `viral_yellow_karaoke`, `minimal_white`, `hormozi_style`)
- [ ] Thumbnails via `/v1/images/generations`

### v0.3 — Aprovação + publicação (1 semana)

- [ ] Dashboard admin (preview, approve/reject, editar metadata)
- [ ] OAuth flows YouTube, Meta, TikTok
- [ ] Worker `publish` com fila separada
- [ ] Scheduler de publicação (horários ótimos por plataforma)
- [ ] Retries de publicação

### v0.4 — B-roll + voice-over + refinamento (contínuo)

- [ ] B-roll via Pexels API (quando houver keywords)
- [ ] Fallback B-roll via `/v1/videos/generations` (LTX-2.3)
- [ ] Voice-over opcional via `/v1/tts/generate` (hooks narrados, intros)
- [ ] Few-shot retrieval com pgvector (banco de clips virais reais)
- [ ] A/B testing de títulos (2 variantes, compara views em 48h)
- [ ] VLM em keyframes (quando `/v1/video/analyze` suportar)

---

## 14. Regras de desenvolvimento

### Gerais

1. **Zero processamento pesado na VPS.** Qualquer tarefa >500MB RAM ou >30s CPU vira endpoint na GPU.
2. **Tudo assíncrono.** FastAPI async. asyncpg. httpx.AsyncClient. Nada de `time.sleep`.
3. **Idempotência obrigatória.** Persista `gpu_job_id` antes de disparar. Unique constraints ou upsert em toda mutation.
4. **Webhooks com HMAC.** Valide `X-Signature: sha256=...` usando `WEBHOOK_SHARED_SECRET`.
5. **Structured logs.** `structlog` com keys: `trace_id`, `source_video_id`, `clip_id`, `gpu_job_id`. Zero `print`.
6. **Métricas Prometheus.** Exponha `/metrics`. Counters: `videos_ingested_total`, `clips_rendered_total`, `gpu_api_calls_total{endpoint,status}`. Histograms: `pipeline_stage_duration_seconds{stage}`.
7. **Config via Pydantic Settings.** Nunca `os.getenv` solto.
8. **Pydantic v2 everywhere.** Request/response, EDL, webhook payloads. Zero dict solto.

### Git

- Branch main protegida.
- Commits convencionais (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
- Features em `feat/`, fixes em `fix/`.

### Testes

- **Unit:** lógica pura — EDL builder, viral score fusion, prompts.
- **Integration:** DB + MinIO + clientes GPU/scraper mockados com `pytest-httpx`.
- **Fixtures:** 1 vídeo YT curto (~3 min), transcript sample, analyze sample, EDL sample.
- Meta: ≥70% cover nos módulos `agent/` e `services/`.

### Error handling

- **Retryable (5xx, timeout, rede):** backoff exponencial via `tenacity`, 3× default, 8× em webhook.
- **Não-retryable (4xx exceto 429/503):** marcar job `failed`, log, alertar.
- **503 com Retry-After:** respeitar o header.
- **Context exceeded no Qwen:** chunk agressivo ou truncate middle (lost-in-the-middle).

### Segurança

- Secrets só em `.env` (gitignore). Em produção, Docker secrets.
- HTTPS obrigatório em `APP_BASE_URL` — PubSub e GPU exigem.
- Rate limit nos endpoints públicos (exceto webhooks, que usam HMAC).

---

## 15. Critérios de aceitação do MVP (v0.1)

Considera-se pronto quando, rodando na VPS sem intervenção manual:

1. Canal YouTube novo inscrito via `POST /api/channels` com `platform=youtube, external_id=UCxxx`.
2. PubSubHubbub confirma subscription em <60s.
3. Upload novo no canal chega no webhook em <5 min.
4. Worker baixa, transcreve, analisa, gera 5 clipes e salva em MinIO em <20 min para vídeo de 30 min.
5. Os 5 clipes reproduzíveis em player padrão (MPV, VLC, browser).
6. Cada clipe: duração 20–70s, legendas word-level (<100ms drift), reframe 9:16, áudio −14 LUFS, watermark.
7. Reinício de container retoma do último checkpoint (LangGraph).
8. Falha de dependência (GPU 503, scraper offline) marca `retry_later` e tenta em 10 min.

---

## 16. Não faça

- ❌ Rodar Whisper/pyannote/FFmpeg encode na VPS.
- ❌ Compartilhar Postgres/Redis com outros projetos do servidor.
- ❌ Usar Temporal ou qualquer orquestrador externo nessa fase.
- ❌ Polling do YouTube quando PubSubHubbub serve.
- ❌ Scraping direto da VPS (IP datacenter queima).
- ❌ Mesmo DB Redis para broker + cache + locks.
- ❌ Hardcode de prompt — tudo em `prompts/*.txt` com versionamento.
- ❌ `print()` em vez de `structlog`.
- ❌ Dicts soltos — tudo Pydantic v2.
- ❌ Chamar GPU sem circuit breaker e retry.
- ❌ Salvar binário em Postgres — só metadata.

---

## 17. Primeiras ações

1. Ler este arquivo 2 vezes.
2. `cd /root && mkdir opus-clone && cd opus-clone && git init`
3. Criar `pyproject.toml` (seção 10). Rodar `uv sync`.
4. Criar `migrations/001_initial.sql` (seção 8). Aplicar: `psql $DATABASE_URL -f migrations/001_initial.sql`.
5. Subir docker-compose (seção 12). Criar buckets: `mc alias set opus http://localhost:9600 $KEY $SECRET && mc mb opus/raw opus/clips opus/assets`.
6. Criar estrutura de pastas (seção 9).
7. Implementar nessa ordem: `config.py` → `db.py` → `logging.py` → `clients/gpu_api.py`.
8. Smoke test: chamada a `/v1/chat/completions` retornando "ping-pong".
9. Implementar v0.1 do roadmap.

**Em caso de dúvida estrutural:** pergunte antes de implementar. Melhor perder 5 min discutindo do que 2h reescrevendo.
