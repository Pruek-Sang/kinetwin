# KineTwin — รายงานเทคนิค: สถาปัตยกรรมปัจจุบัน + บั๊กที่แก้

> อัปเดต 2026-06-24 · commit `e946c69`

---

## 🏗️ สถาปัตยกรรมปัจจุบัน (2 ชั้น AI)

```
┌─ BROWSER (React + TypeScript) ──────────────────────────────┐
│                                                              │
│  ผู้ใช้กด "มือปกติ" / "มืออ่อนแรง" / อัปโหลด                    │
│         │                                                    │
│         ▼                                                    │
│  ① analyzer.ts (MediaPipe Web WASM)                         │
│     · โหลดโมเดล hand_landmarker.task จาก Google CDN        │
│     · seek ทุกเฟรมของวิดีโอ → detectForVideo()               │
│     · เก็บ 21 จุด landmark ต่อเฟรม (image x,y)               │
│         │                                                    │
│         ▼                                                    │
│  ② คำนวณใน browser (สูตรเดียวกับ Python, port เป็น TS)        │
│     · per-landmark deltas → เทียบ REF_DELTAS → สี           │
│     · Speed / Accuracy / Quality → คะแนน 0-100              │
│     · Progressive overlay (อัปเดตระหว่าง track)              │
│         │                                                    │
│         ├──→ HandOverlay.tsx (วาด canvas: เส้น flat +       │
│         │    ลูกแก้ว glossy + กรอบ + เส้นแขน + legend)        │
│         │                                                    │
│         ▼                                                    │
│  ③ ส่ง landmarks ไป backend (POST /predict-landmarks)       │
│     · body: { fps, landmarks: [[[x,y]×21]×T] }             │
│                                                              │
└──────────────────┬───────────────────────────────────────────┘
                   │ ~50KB JSON (เล็ก เร็ว)
                   ▼
┌─ BACKEND (FastAPI / Cloud Run) ─────────────────────────────┐
│                                                              │
│  POST /predict-landmarks                                     │
│     · รับ landmarks → สกัดฟีเจอร์ (speed/acc/quality)         │
│     · sklearn classifier ทำนาย normal/impaired              │
│     · คืน { prediction, confidence, lnu_probability }        │
│                                                              │
│  POST /analyze-one (ยังมีไว้ สำหรับอัปโหลดผ่าน backend)       │
│  POST /analyze-landmarks (test endpoint)                     │
│  GET /health                                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 ไฟล์หลัก + หน้าที่

| ไฟล์ | หน้าที่ | รันที่ไหน |
|---|---|---|
| `src/frontend/src/lib/analyzer.ts` | **MediaPipe Web + คำนวณ metrics + สี** | Browser |
| `src/frontend/src/App.tsx` | **Flow control** — กดปุ่ม → track → ส่ง backend → โชว์ผล | Browser |
| `src/frontend/src/components/HandOverlay.tsx` | **วาด overlay** (เส้น + จุด + กรอบ + เส้นแขน) | Browser canvas |
| `src/frontend/src/components/ScorePanel.tsx` | **แสดงคะแนน + คำอธิบาย** | Browser |
| `src/frontend/src/components/SplitScreen.tsx` | **เล่นวิดีโอ ซ้าย/ขวา + overlay** | Browser |
| `src/backend/app/main.py` | **API endpoints** (/predict-landmarks, /analyze-one) | Cloud Run |
| `src/backend/app/services.py` | **scikit-learn classifier + metrics** | Cloud Run |
| `src/ai/metrics/` | **สูตร Speed/Accuracy/Quality** (Python, สำหรับ backend + tests) | Cloud Run |
| `src/ai/tracking/hand_tracker.py` | **MediaPipe Python** (สำหรับ backend /analyze-one) | Cloud Run |

---

## 🔧 บั๊กที่แก้ (commit `e946c69`)

### บั๊ก 1: `[object Event]` error
- **สาเหตุ:** `document.querySelector("video")` จับผิดตัว (อาจจับ reference video หรือ null) → `analyzeVideo(null)` → crash → catch ได้ Event object → `String(Event)` = `"[object Event]"`
- **แก้:**
  - สร้าง **dedicated hidden `<video>` element** สำหรับ analysis โดยเฉพาะ (ไม่ใช้ querySelector)
  - catch block ตรวจ `instanceof Event` → แสดงข้อความที่อ่านได้
- **ไฟล์ที่แก้:** `App.tsx` บรรทัด 65-69 (dedicated video) + บรรทัด 94-97 (error handling)

### บั๊ก 2: เส้นมือหาย (overlay ไม่แสดง)
- **สาเหตุ:** progressive callback อ้างถึง `rpt` **ก่อน**ที่ `analyzeVideo` จะ return ค่า → `rpt` เป็น undefined → `setReport({ ...undefined, overlay })` → overlay เป็น undefined → HandOverlay ไม่วาด
- **แก้:**
  - เปลี่ยน callback เป็น `setReport(prev => ({ ...prev.defaults..., overlay: progOverlay }))`
  - ใช้ fallback defaults (score=0, raw={}, etc.) เมื่อ prev เป็น null
- **ไฟล์ที่แก้:** `App.tsx` บรรทัด 75-82

### บั๊ก 3 (ยังไม่ได้แก้): `/predict-landmarks` endpoint ไม่มีบน backend
- **สถานะ:** Frontend เรียก `/predict-landmarks` แต่ backend **ยังไม่มี endpoint นี้** → 404 (silent fail, ไม่ crash)
- **แก้ต่อ:** เพิ่ม endpoint ใน `src/backend/app/main.py` + sklearn classifier

---

## 🔄 Flow แบบละเอียด (ตอนกดปุ่มตัวอย่าง)

```
User clicks "✋ มือปกติ"
  │
  ├─ 1. setLoading(true), setReport(null)
  ├─ 2. setStatusText("Loading AI model…")
  │
  ├─ 3. fetch("/samples/normal.mp4") → blob → File
  ├─ 4. setUrl(blob URL) → SplitScreen แสดงวิดีโอทันที
  │
  ├─ 5. สร้าง hidden <video> (analysisVideo) สำหรับประมวลผล
  │     └─ โหลด metadata → resolve
  │
  ├─ 6. setStatusText("AI tracking hand…")
  ├─ 7. analyzeVideo(analysisVideo):
  │     ├─ getLandmarker() → โหลด MediaPipe Web (WASM) จาก CDN
  │     │   (ครั้งแรก ~2-3วิ, cached หลังนั้น)
  │     ├─ seek เฟรม 0..N:
  │     │   ├─ analysisVideo.currentTime = i/fps
  │     │   ├─ รอ seeked event (timeout 200ms fallback)
  │     │   ├─ landmarker.detectForVideo(analysisVideo, timestamp)
  │     │   └─ เก็บ landmarks หรือ null
  │     ├─ ทุก 10 เฟรม: onProgress({ frames, colors: all-cyan })
  │     │   └─ setReport → HandOverlay วาด skeleton (cyan)
  │     └─ ประมวลผลเสร็จ:
  │         ├─ computeDeltas(frames) → per-landmark
  │         ├─ colorsFromDeltas → เทียบ REF_DELTAS
  │         ├─ computeMetrics → speed/acc/quality
  │         └─ scoreFromMetrics → 0-100
  │
  ├─ 8. setReport({ score, raw, vs_reference, overlay })
  │     └─ ScorePanel แสดงคะแนน + HandOverlay วาดสีจริง
  │
  ├─ 9. setStatusText("AI classifier predicting…")
  ├─ 10. POST /predict-landmarks → backend
  │      └─ (ถ้ายังไม่มี endpoint → 404 → silent fail)
  │
  └─ 11. setLoading(false), setStatusText("")
```

---

## 🚀 Deploy (CI/CD อัตโนมัติ)

```
push → main
  ├─ CI: pytest (backend tests) + vite build (frontend)
  │   ↓ ผ่านทั้งคู่
  ├─ CD: build backend image → push Artifact Registry → deploy Cloud Run kinetwin-backend
  └─ CD: build frontend image → push → deploy Cloud Run kinetwin-frontend
```

- **Frontend:** https://kinetwin-frontend-rc5mtgajza-as.a.run.app
- **Backend:** https://kinetwin-backend-rc5mtgajza-as.a.run.app
- **GCP project:** gen-lang-client-0658701327 (repo `kinetwin`, services `kinetwin-*`)

---

## ⚠️ สิ่งที่ยังต้องทำ (TODO)

1. **เพิ่ม `/predict-landmarks` endpoint บน backend** — sklearn classifier ทำนาย LNU จาก landmarks
2. **ลองบนเว็บจริง** — MediaPipe Web อาจต่างจาก local (browser compatibility, GPU)
3. **ถ้า MediaPipe Web ไม่ stable** — fallback เป็น pre-baked (มีไฟล์อยู่แล้ว)
4. **อัดคลิปเดโม** — โจทย์บังคับ
